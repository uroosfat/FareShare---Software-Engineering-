from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trip, User
from app.routers import auth, requests, trips, vehicles

app = FastAPI(title="FareShare API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(trips.router)
app.include_router(requests.router)


@app.get("/")
def hello():
    return {"message": "Hello from FareShare"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Confirms the API can reach PostgreSQL and the tables exist."""
    db.execute(text("SELECT 1"))
    return {
        "database": "connected",
        "users": db.query(User).count(),
        "trips": db.query(Trip).count(),
    }
