"""Demo data for FareShare: a few drivers, vehicles and upcoming trips.
Run from the backend folder (with .env pointing at the database):   python seed.py
Safe to run again: users that already exist are skipped, trips are only added for new drivers.
Every seeded account has the password  password1"""
import datetime as dt

from app.database import SessionLocal
from app.models import Trip, User, Vehicle
from app.security import hash_password

DRIVERS = [
    ("Ayesha Khan", "ayesha.demo@khi.iba.edu.pk", "female", "0300 1000001", ("Suzuki", "Alto", "Silver", "KAB-101", 4),
     [("Clifton", "IBA City Campus", 1, 8, 200, "female"), ("IBA City Campus", "Clifton", 1, 17, 200, "female")]),
    ("Hamza Ali", "hamza.demo@khi.iba.edu.pk", "male", "0300 1000002", ("Honda", "City", "White", "KBC-202", 4),
     [("Gulshan-e-Iqbal", "IBA Main Campus", 1, 7, 250, "any"), ("IBA Main Campus", "Gulshan-e-Iqbal", 1, 16, 250, "any")]),
    ("Sana Raza", "sana.demo@khi.iba.edu.pk", "female", "0300 1000003", ("Toyota", "Corolla", "Black", "KCD-303", 4),
     [("DHA Phase 6", "IBA City Campus", 2, 8, 300, "any"), ("Nazimabad", "IBA Main Campus", 2, 9, 250, "female")]),
    ("Bilal Ahmed", "bilal.demo@khi.iba.edu.pk", "male", "0300 1000004", ("Suzuki", "Cultus", "Blue", "KDE-404", 3),
     [("North Nazimabad", "IBA City Campus", 3, 7, 200, "male"), ("Malir", "IBA Main Campus", 3, 8, 300, "any")]),
]


def main():
    db = SessionLocal()
    now = dt.datetime.now(dt.timezone.utc)
    added = 0
    for name, email, gender, phone, car, trips in DRIVERS:
        if db.query(User).filter(User.email == email).first():
            print("skip (exists):", email)
            continue
        u = User(full_name=name, email=email, password_hash=hash_password("password1"), gender=gender, phone=phone)
        db.add(u)
        db.flush()
        v = Vehicle(owner_id=u.user_id, make=car[0], model=car[1], color=car[2], plate_number=car[3], total_seats=car[4])
        db.add(v)
        db.flush()
        for origin, dest, days, hour, cost, gf in trips:
            when = (now + dt.timedelta(days=days)).astimezone(dt.timezone(dt.timedelta(hours=5)))
            when = when.replace(hour=hour, minute=0, second=0, microsecond=0)   # Karachi local time
            db.add(Trip(manager_id=u.user_id, vehicle_id=v.vehicle_id, origin_area=origin, destination_area=dest,
                        departure_time=when, available_seats=car[4] - 1, cost_per_person=cost, gender_filter=gf))
            added += 1
        print("added:", email)
    db.commit()
    print(f"done, {added} trips added. Password for every demo account: password1")


if __name__ == "__main__":
    main()
