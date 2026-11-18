from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import (
    active_request_for,
    aware,
    expire_stale_requests,
    expiry_minutes,
    gender_allowed,
    request_dict,
    trip_dict,
    user_public,
    utcnow,
)
from app.models import Trip, TripRequest, User
import datetime as dt
from app.security import get_current_user

router = APIRouter(tags=["requests"])


class RequestIn(BaseModel):
    message: str | None = None


def get_request(db: Session, request_id: int) -> TripRequest:
    expire_stale_requests(db)
    r = db.get(TripRequest, request_id)
    if r is None:
        raise HTTPException(404, "Request not found")
    return r


@router.post("/trips/{trip_id}/requests", status_code=201)
def send_request(
    trip_id: int, body: RequestIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    t = db.get(Trip, trip_id)
    if t is None:
        raise HTTPException(404, "Trip not found")
    if t.manager_id == user.user_id:
        raise HTTPException(409, "You cannot request your own trip")
    if t.status != "open" or aware(t.departure_time) <= utcnow():
        raise HTTPException(409, "This trip is no longer open")
    if t.available_seats <= 0:
        raise HTTPException(409, "No seats left on this trip")
    if not gender_allowed(t, user):
        raise HTTPException(403, "This trip is restricted to another gender")
    msg = (body.message or "").strip()
    if len(msg) > 300:
        raise HTTPException(422, "Message can be at most 300 characters")
    busy = active_request_for(db, user.user_id)
    if busy is not None:
        raise HTTPException(
            409,
            "You already have an active request. You can request one trip at a time: "
            "wait for the answer or cancel it first.",
        )
    now = utcnow()
    expires = now + dt.timedelta(minutes=expiry_minutes())
    r = db.query(TripRequest).filter(TripRequest.trip_id == trip_id, TripRequest.requester_id == user.user_id).first()
    if r is None:  # UNIQUE(trip_id, requester_id): reuse an old declined/expired/cancelled row
        r = TripRequest(trip_id=trip_id, requester_id=user.user_id)
        db.add(r)
    r.status, r.message = "pending", msg or None
    r.requested_at, r.responded_at, r.expires_at = now, None, expires
    db.commit()
    db.refresh(r)
    return request_dict(r)


@router.get("/requests/sent")
def sent_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expire_stale_requests(db)
    rows = (
        db.query(TripRequest)
        .filter(TripRequest.requester_id == user.user_id)
        .order_by(TripRequest.requested_at.desc())
        .all()
    )
    out = []
    for r in rows:
        t = db.get(Trip, r.trip_id)
        d = request_dict(r)
        d["trip"] = trip_dict(t, user, db)
        # the manager's phone is shared only after acceptance
        d["manager_phone"] = t.manager.phone if r.status == "accepted" else None
        out.append(d)
    return out


@router.get("/requests/received")
def received_requests(
    status: str | None = "pending", user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    expire_stale_requests(db)
    q = (
        db.query(TripRequest)
        .join(Trip, Trip.trip_id == TripRequest.trip_id)
        .filter(Trip.manager_id == user.user_id)
        .order_by(TripRequest.requested_at)
    )
    if status:
        q = q.filter(TripRequest.status == status)
    out = []
    for r in q.all():
        rider = db.get(User, r.requester_id)
        d = request_dict(r)
        d["rider"] = {**user_public(rider), "phone": rider.phone if r.status == "accepted" else None}
        d["trip"] = trip_dict(db.get(Trip, r.trip_id), user, db)
        out.append(d)
    return out


@router.post("/requests/{request_id}/accept")
def accept_request(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = get_request(db, request_id)
    t = db.get(Trip, r.trip_id)
    if t.manager_id != user.user_id:
        raise HTTPException(403, "Only the trip manager can answer this request")
    if r.status == "expired":
        raise HTTPException(409, "This request has expired")
    if r.status != "pending":
        raise HTTPException(409, f"This request is already {r.status}")
    if t.status != "open":
        raise HTTPException(409, f"This trip is {t.status}")
    if t.available_seats <= 0:
        raise HTTPException(409, "No seats left on this trip")
    r.status, r.responded_at = "accepted", utcnow()
    t.available_seats -= 1
    db.commit()
    return request_dict(r)


@router.post("/requests/{request_id}/decline")
def decline_request(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = get_request(db, request_id)
    t = db.get(Trip, r.trip_id)
    if t.manager_id != user.user_id:
        raise HTTPException(403, "Only the trip manager can answer this request")
    if r.status == "expired":
        raise HTTPException(409, "This request has expired")
    if r.status != "pending":
        raise HTTPException(409, f"This request is already {r.status}")
    r.status, r.responded_at = "declined", utcnow()
    db.commit()
    return request_dict(r)


@router.post("/requests/{request_id}/cancel")
def cancel_request(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Rider withdraws a pending request."""
    r = get_request(db, request_id)
    if r.requester_id != user.user_id:
        raise HTTPException(403, "This is not your request")
    if r.status != "pending":
        raise HTTPException(409, f"Only a pending request can be cancelled (this one is {r.status})")
    r.status, r.responded_at = "cancelled", utcnow()
    db.commit()
    return request_dict(r)


@router.post("/requests/{request_id}/leave")
def leave_trip(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """An accepted rider leaves the trip; the seat is released."""
    r = get_request(db, request_id)
    if r.requester_id != user.user_id:
        raise HTTPException(403, "This is not your request")
    if r.status != "accepted":
        raise HTTPException(409, "You are not an accepted rider on this trip")
    t = db.get(Trip, r.trip_id)
    r.status, r.responded_at = "cancelled", utcnow()
    if t.status in ("open", "confirmed"):
        t.available_seats += 1
    db.commit()
    return request_dict(r)
