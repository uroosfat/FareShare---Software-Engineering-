from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trip, User

app = FastAPI(title="FareShare API")


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
