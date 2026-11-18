from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import vehicle_dict
from app.models import Trip, User, Vehicle
from app.security import get_current_user

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


class VehicleIn(BaseModel):
    make: str
    model: str
    color: str
    plate_number: str
    total_seats: int


def validate(body: VehicleIn) -> None:
    if not all(x.strip() for x in (body.make, body.model, body.color, body.plate_number)):
        raise HTTPException(422, "Make, model, colour and plate number are required")
    if not 1 <= body.total_seats <= 4:
        raise HTTPException(422, "Passenger seats must be between 1 and 4")


def own_vehicle(db: Session, user: User, vehicle_id: int) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None or v.owner_id != user.user_id:
        raise HTTPException(404, "Vehicle not found")
    return v


@router.get("")
def list_vehicles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Vehicle).filter(Vehicle.owner_id == user.user_id).order_by(Vehicle.vehicle_id).all()
    return [vehicle_dict(v) for v in rows]


@router.post("", status_code=201)
def add_vehicle(body: VehicleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    validate(body)
    v = Vehicle(
        owner_id=user.user_id,
        make=body.make.strip(),
        model=body.model.strip(),
        color=body.color.strip(),
        plate_number=body.plate_number.strip().upper(),
        total_seats=body.total_seats,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return vehicle_dict(v)


@router.put("/{vehicle_id}")
def edit_vehicle(
    vehicle_id: int, body: VehicleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    validate(body)
    v = own_vehicle(db, user, vehicle_id)
    v.make, v.model, v.color = body.make.strip(), body.model.strip(), body.color.strip()
    v.plate_number, v.total_seats = body.plate_number.strip().upper(), body.total_seats
    db.commit()
    return vehicle_dict(v)


@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    v = own_vehicle(db, user, vehicle_id)
    upcoming = (
        db.query(Trip)
        .filter(Trip.vehicle_id == v.vehicle_id, Trip.status.in_(("open", "confirmed")))
        .first()
    )
    if upcoming:
        raise HTTPException(409, "This vehicle is used by an upcoming trip and cannot be deleted")
    if db.query(Trip).filter(Trip.vehicle_id == v.vehicle_id).first():
        raise HTTPException(409, "This vehicle appears in your trip history and cannot be deleted")
    db.delete(v)
    db.commit()
    return {"detail": "Vehicle deleted"}
