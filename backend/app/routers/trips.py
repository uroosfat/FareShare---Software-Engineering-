import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import (
    CAMPUSES,
    user_private,
    GENDER_FILTERS,
    active_request_for,
    aware,
    expire_stale_requests,
    gender_allowed,
    trip_dict,
    utcnow,
)
from app.models import Trip, TripRequest, User, Vehicle
from app.security import get_current_user

router = APIRouter(prefix="/trips", tags=["trips"])


class ConfirmIn(BaseModel):
    pickup_point: str


class CompleteIn(BaseModel):
    rider_ids: list[int]   # user ids of the riders who travelled


class TripIn(BaseModel):
    origin_area: str
    destination_area: str
    departure_time: dt.datetime
    seats: int
    cost_per_person: float = 0
    gender_filter: str = "any"
    ride_type: str = "own_car"          # own_car | indrive_group
    vehicle_id: int | None = None       # required for own_car


def validate_trip(body: TripIn, user: User, db: Session) -> Vehicle | None:
    if not body.origin_area.strip() or not body.destination_area.strip():
        raise HTTPException(422, "Pickup area and campus are required")
    if body.origin_area.strip() not in CAMPUSES and body.destination_area.strip() not in CAMPUSES:
        raise HTTPException(422, "Either the pickup or the drop-off must be an IBA campus")
    if aware(body.departure_time) <= utcnow():
        raise HTTPException(422, "Departure time must be in the future")
    if not 1 <= body.seats <= 4:
        raise HTTPException(422, "Seats must be between 1 and 4")
    if body.cost_per_person < 0:
        raise HTTPException(422, "Cost cannot be negative")
    if body.gender_filter not in GENDER_FILTERS:
        raise HTTPException(422, "gender_filter must be any, female or male")
    if body.gender_filter != "any" and body.gender_filter != user.gender:
        raise HTTPException(422, f"You can only post '{user.gender}' or 'any' trips")
    if body.ride_type not in ("own_car", "indrive_group"):
        raise HTTPException(422, "ride_type must be own_car or indrive_group")
    if body.ride_type == "indrive_group":
        return None
    if body.vehicle_id is None:
        raise HTTPException(422, "Choose a vehicle for an own-car trip")
    v = db.get(Vehicle, body.vehicle_id)
    if v is None or v.owner_id != user.user_id:
        raise HTTPException(404, "Vehicle not found")
    if body.seats > v.total_seats:
        raise HTTPException(422, f"This vehicle has only {v.total_seats} passenger seats")
    return v


def get_trip(db: Session, trip_id: int) -> Trip:
    t = db.get(Trip, trip_id)
    if t is None:
        raise HTTPException(404, "Trip not found")
    return t


def accepted_count(db: Session, trip_id: int) -> int:
    return db.query(TripRequest).filter(TripRequest.trip_id == trip_id, TripRequest.status == "accepted").count()


@router.post("", status_code=201)
def post_trip(body: TripIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    veh = validate_trip(body, user, db)
    t = Trip(
        manager_id=user.user_id,
        vehicle_id=veh.vehicle_id if veh else None,
        origin_area=body.origin_area.strip(),
        destination_area=body.destination_area.strip(),
        departure_time=body.departure_time,
        available_seats=body.seats,
        cost_per_person=body.cost_per_person,
        gender_filter=body.gender_filter,
        status="open",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return trip_dict(t, user, db)


@router.get("")
def browse_trips(
    origin: str | None = Query(None, description="Pickup place, partial match, e.g. Clifton"),
    campus: str | None = Query(None, description="IBA City Campus or IBA Main Campus"),
    date: dt.date | None = Query(None, description="YYYY-MM-DD"),
    gender: str | None = Query(None, description="any | female | male (trip restriction)"),
    after: dt.datetime | None = Query(None, description="only trips departing at or after this time"),
    before: dt.datetime | None = Query(None, description="only trips departing before this time"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Open trips the user is allowed to join, filtered by pickup place and campus."""
    expire_stale_requests(db)
    q = db.query(Trip).filter(
        Trip.status == "open",
        Trip.available_seats > 0,
        Trip.departure_time > utcnow(),
        Trip.manager_id != user.user_id,
    )
    if origin and origin.strip():
        q = q.filter(Trip.origin_area.ilike(f"%{origin.strip()}%"))
    if campus and campus.strip():
        q = q.filter(Trip.destination_area == campus.strip())
    if date:
        start = dt.datetime.combine(date, dt.time.min, tzinfo=dt.timezone.utc)
        q = q.filter(Trip.departure_time >= start, Trip.departure_time < start + dt.timedelta(days=1))
    if after:
        q = q.filter(Trip.departure_time >= after)
    if before:
        q = q.filter(Trip.departure_time < before)
    if gender in GENDER_FILTERS:
        q = q.filter(Trip.gender_filter == gender)
    trips = [t for t in q.order_by(Trip.departure_time).all() if gender_allowed(t, user)]
    busy = active_request_for(db, user.user_id)
    out = []
    for t in trips:
        d = trip_dict(t, user, db)
        # one request at a time: other trips are locked while a request is active
        d["locked"] = busy is not None and busy.trip_id != t.trip_id
        out.append(d)
    return out


@router.get("/mine")
def my_trips(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expire_stale_requests(db)
    managing = db.query(Trip).filter(Trip.manager_id == user.user_id).order_by(Trip.departure_time).all()
    joined_ids = [
        r.trip_id
        for r in db.query(TripRequest).filter(
            TripRequest.requester_id == user.user_id, TripRequest.status.in_(("pending", "accepted"))
        )
    ]
    joined = db.query(Trip).filter(Trip.trip_id.in_(joined_ids)).order_by(Trip.departure_time).all() if joined_ids else []
    out_m = []
    for t in managing:
        d = trip_dict(t, user, db)
        d["pending_requests"] = db.query(TripRequest).filter(
            TripRequest.trip_id == t.trip_id, TripRequest.status == "pending"
        ).count()
        d["accepted_riders"] = accepted_count(db, t.trip_id)
        out_m.append(d)
    return {"managing": out_m, "joined": [trip_dict(t, user, db) for t in joined]}


@router.get("/{trip_id}")
def trip_details(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expire_stale_requests(db)
    return trip_dict(get_trip(db, trip_id), user, db)


@router.put("/{trip_id}")
def edit_trip(trip_id: int, body: TripIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = get_trip(db, trip_id)
    if t.manager_id != user.user_id:
        raise HTTPException(403, "Only the trip manager can edit this trip")
    if t.status != "open":
        raise HTTPException(409, f"A {t.status} trip cannot be edited")
    veh = validate_trip(body, user, db)
    taken = accepted_count(db, t.trip_id)
    if taken and (veh.vehicle_id if veh else None) != t.vehicle_id:
        raise HTTPException(409, "Ride type and vehicle are locked once a rider is accepted")
    if body.seats < taken:
        raise HTTPException(409, f"{taken} riders are already accepted, seats cannot go below that")
    t.origin_area = body.origin_area.strip()
    t.destination_area = body.destination_area.strip()
    t.departure_time = body.departure_time
    t.available_seats = body.seats - taken
    t.cost_per_person = body.cost_per_person
    t.gender_filter = body.gender_filter
    t.vehicle_id = veh.vehicle_id if veh else None
    db.commit()
    db.refresh(t)
    return trip_dict(t, user, db)


@router.post("/{trip_id}/cancel")
def cancel_trip(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = get_trip(db, trip_id)
    if t.manager_id != user.user_id:
        raise HTTPException(403, "Only the trip manager can cancel this trip")
    if t.status in ("cancelled", "completed"):
        raise HTTPException(409, f"This trip is already {t.status}")
    t.status = "cancelled"
    db.query(TripRequest).filter(
        TripRequest.trip_id == t.trip_id, TripRequest.status.in_(("pending", "accepted"))
    ).update({"status": "cancelled"}, synchronize_session=False)
    db.commit()
    return {"detail": "Trip cancelled"}


def manager_trip(db: Session, trip_id: int, user: User) -> Trip:
    t = get_trip(db, trip_id)
    if t.manager_id != user.user_id:
        raise HTTPException(403, "Only the trip manager can do this")
    return t


@router.get("/{trip_id}/riders")
def trip_riders(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Accepted riders of my trip (the manager sees their phone numbers)."""
    expire_stale_requests(db)
    t = manager_trip(db, trip_id, user)
    rows = db.query(TripRequest).filter(TripRequest.trip_id == t.trip_id, TripRequest.status == "accepted").all()
    out = []
    for r in rows:
        rider = db.get(User, r.requester_id)
        out.append({"request_id": r.request_id, "rider": user_private(rider),
                    "manager_marked": bool(r.manager_marked), "rider_confirmed": r.rider_confirmed})
    return out


@router.post("/{trip_id}/confirm")
def confirm_pickup(trip_id: int, body: ConfirmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manager confirms the pickup point. The trip becomes 'confirmed' and stops taking requests."""
    expire_stale_requests(db)
    t = manager_trip(db, trip_id, user)
    if t.status != "open":
        raise HTTPException(409, f"A {t.status} trip cannot be confirmed")
    if not body.pickup_point.strip():
        raise HTTPException(422, "Enter the pickup point")
    if accepted_count(db, t.trip_id) < 1:
        raise HTTPException(409, "Accept at least one rider before confirming the pickup")
    t.pickup_point = body.pickup_point.strip()
    t.status = "confirmed"
    # requests still waiting are closed
    db.query(TripRequest).filter(TripRequest.trip_id == t.trip_id, TripRequest.status == "pending").update(
        {"status": "declined", "responded_at": utcnow()}, synchronize_session=False
    )
    db.commit()
    db.refresh(t)
    return trip_dict(t, user, db)


@router.post("/{trip_id}/complete")
def complete_trip(trip_id: int, body: CompleteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manager marks the trip completed and ticks who travelled. Each ticked rider is then asked to
    confirm; the rider's trips-completed count only goes up when they confirm. The manager's goes up now."""
    t = manager_trip(db, trip_id, user)
    if t.status != "confirmed":
        raise HTTPException(409, "Only a confirmed trip can be marked completed")
    accepted = db.query(TripRequest).filter(TripRequest.trip_id == t.trip_id, TripRequest.status == "accepted").all()
    allowed = {r.requester_id for r in accepted}
    if not set(body.rider_ids) <= allowed:
        raise HTTPException(422, "rider_ids must be accepted riders of this trip")
    for r in accepted:
        r.manager_marked = r.requester_id in body.rider_ids
    t.status = "completed"
    user.completed_trips_count += 1
    db.commit()
    db.refresh(t)
    return trip_dict(t, user, db)
