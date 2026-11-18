"""Password hashing, JWT tokens and the 'who is logged in' dependency."""
import datetime as dt

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import ALLOWED_EMAIL_DOMAIN, JWT_SECRET
from app.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)
TOKEN_DAYS = 7


def allowed_domain() -> str:
    return ALLOWED_EMAIL_DOMAIN.lower().lstrip("@")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=TOKEN_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, JWT_SECRET, algorithm="HS256")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Not logged in")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user
