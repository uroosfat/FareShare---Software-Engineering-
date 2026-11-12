"""SQLAlchemy models. They map the tables created by db/schema.sql
(the SQL file is the source of truth, we do NOT call create_all)."""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, TIMESTAMP, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20))
    completed_trips_count = Column(Integer, nullable=False, server_default="0")
    fcm_token = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    vehicles = relationship("Vehicle", back_populates="owner")
    trips = relationship("Trip", back_populates="manager")


class Vehicle(Base):
    __tablename__ = "vehicles"
    vehicle_id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    color = Column(String(30), nullable=False)
    plate_number = Column(String(20), nullable=False)
    total_seats = Column(Integer, nullable=False)

    owner = relationship("User", back_populates="vehicles")


class Trip(Base):
    __tablename__ = "trips"
    trip_id = Column(Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.vehicle_id"))
    origin_area = Column(String(100), nullable=False)
    destination_area = Column(String(100), nullable=False)
    departure_time = Column(TIMESTAMP(timezone=True), nullable=False)
    available_seats = Column(Integer, nullable=False)
    cost_per_person = Column(Numeric(8, 2), nullable=False, server_default="0")
    gender_filter = Column(String(10), nullable=False, server_default="any")
    status = Column(String(15), nullable=False, server_default="open")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    manager = relationship("User", back_populates="trips")
    requests = relationship("TripRequest", back_populates="trip")


class TripRequest(Base):
    __tablename__ = "trip_requests"
    request_id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(String(15), nullable=False, server_default="pending")
    message = Column(String(300))
    requested_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    responded_at = Column(TIMESTAMP(timezone=True))

    trip = relationship("Trip", back_populates="requests")
