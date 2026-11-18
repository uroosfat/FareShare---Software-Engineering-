from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.helpers import user_private
from app.models import User
from app.security import (
    allowed_domain,
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])


class RegisterIn(BaseModel):
    full_name: str
    email: str
    password: str
    gender: str
    phone: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


def check_password_rule(pw: str) -> None:
    if len(pw) < 8 or not any(c.isdigit() for c in pw):
        raise HTTPException(422, "Password must be at least 8 characters and include one number")


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email or email.split("@", 1)[1] != allowed_domain():
        raise HTTPException(422, f"Only @{allowed_domain()} email addresses can sign up")
    name = body.full_name.strip()
    if not name:
        raise HTTPException(422, "Full name is required")
    gender = body.gender.strip().lower()
    if gender not in ("female", "male"):
        raise HTTPException(422, "Gender must be 'female' or 'male'")
    check_password_rule(body.password)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    user = User(
        full_name=name,
        email=email,
        password_hash=hash_password(body.password),
        gender=gender,
        phone=(body.phone or None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.user_id), "user": user_private(user)}


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": create_token(user.user_id), "user": user_private(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_private(user)


@router.put("/me")
def update_me(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Name and phone can change. Email and gender are locked."""
    if body.full_name is not None:
        if not body.full_name.strip():
            raise HTTPException(422, "Full name cannot be empty")
        user.full_name = body.full_name.strip()
    if body.phone is not None:
        user.phone = body.phone.strip() or None
    db.commit()
    db.refresh(user)
    return user_private(user)


@router.post("/auth/change-password")
def change_password(
    body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(422, "New password must be different from the current one")
    check_password_rule(body.new_password)
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"detail": "Password updated"}
