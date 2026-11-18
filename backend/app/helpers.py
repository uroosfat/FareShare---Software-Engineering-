"""Small shared helpers: time handling, request expiry, response shapes."""
import datetime as dt
import os

from sqlalchemy.orm import Session

from app.models import Trip, TripRequest, User, Vehicle

CAMPUSES = ("IBA City Campus", "IBA Main Campus")
GENDER_FILTERS = ("any", "female", "male")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def aware(d: dt.datetime | None) -> dt.datetime | None:
    """Treat naive datetimes (SQLite in tests) as UTC."""
    if d is not None and d.tzinfo is None:
        return d.replace(tzinfo=dt.timezone.utc)
    return d


def expiry_minutes() -> int:
    try:
        return int(os.getenv("REQUEST_EXPIRY_MINUTES", "10"))
    except ValueError:
        return 10


def expire_stale_requests(db: Session) -> None:
    """Pending requests past their expires_at become 'expired'.
    Called at the start of every request-related endpoint, so no background job is needed."""
    db.query(TripRequest).filter(
        TripRequest.status == "pending",
        TripRequest.expires_at.isnot(None),
        TripRequest.expires_at < utcnow(),
    ).update({"status": "expired"}, synchronize_session=False)
    db.commit()
    db.expire_all()  # make sure objects loaded earlier see the new status


def active_request_for(db: Session, user_id: int) -> TripRequest | None:
    """The one request that keeps a rider 'busy': pending, or accepted on a live trip."""
    expire_stale_requests(db)
    rows = (
        db.query(TripRequest)
        .join(Trip, Trip.trip_id == TripRequest.trip_id)
        .filter(
            TripRequest.requester_id == user_id,
            TripRequest.status.in_(("pending", "accepted")),
            Trip.status.in_(("open", "confirmed")),
        )
        .all()
    )
    return rows[0] if rows else None


def gender_allowed(trip: Trip, user: User) -> bool:
    return trip.gender_filter == "any" or trip.gender_filter == user.gender


def iso(d: dt.datetime | None) -> str | None:
    d = aware(d)
    return d.isoformat() if d else None


def user_public(u: User) -> dict:
    return {
        "user_id": u.user_id,
        "full_name": u.full_name,
        "gender": u.gender,
        "completed_trips_count": u.completed_trips_count,
    }


def user_private(u: User) -> dict:
    return {**user_public(u), "email": u.email, "phone": u.phone}


def vehicle_dict(v) -> dict:
    return {
        "vehicle_id": v.vehicle_id,
        "make": v.make,
        "model": v.model,
        "color": v.color,
        "plate_number": v.plate_number,
        "total_seats": v.total_seats,
    }


def request_dict(r: TripRequest) -> dict:
    return {
        "request_id": r.request_id,
        "trip_id": r.trip_id,
        "status": r.status,
        "message": r.message,
        "requested_at": iso(r.requested_at),
        "responded_at": iso(r.responded_at),
        "expires_at": iso(r.expires_at),
    }


def trip_dict(t: Trip, viewer: User, db: Session) -> dict:
    mine = (
        db.query(TripRequest)
        .filter(TripRequest.trip_id == t.trip_id, TripRequest.requester_id == viewer.user_id)
        .first()
    )
    veh = db.get(Vehicle, t.vehicle_id) if t.vehicle_id else None
    d = {
        "trip_id": t.trip_id,
        "origin_area": t.origin_area,
        "destination_area": t.destination_area,
        "departure_time": iso(t.departure_time),
        "available_seats": t.available_seats,
        "cost_per_person": float(t.cost_per_person),
        "gender_filter": t.gender_filter,
        "ride_type": "own_car" if t.vehicle_id else "indrive_group",
        "status": t.status,
        "manager": user_public(t.manager),
        "vehicle": vehicle_dict(veh) if veh else None,
        "my_request": request_dict(mine) if mine else None,
    }
    return d
