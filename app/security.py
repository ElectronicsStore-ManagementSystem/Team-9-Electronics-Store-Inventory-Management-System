import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import (
    ACCESS_TOKEN_MINUTES,
    SECRET_KEY,
    SESSION_IDLE_TIMEOUT_MINUTES,
)
from .db import get_db
from .models import User

ALGORITHM = "HS256"
PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 310_000
PASSWORD_SALT_BYTES = 16
PASSWORD_DIGEST_BYTES = 32
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{PASSWORD_HASH_SCHEME}${PASSWORD_HASH_ITERATIONS}"
        f"${salt.hex()}${digest.hex()}"
    )

def verify_password(password: str, encoded: str) -> bool:
    if not isinstance(encoded, str):
        return False

    try:
        scheme, rounds, salt_hex, digest_hex = encoded.split("$")
        if scheme != PASSWORD_HASH_SCHEME:
            return False
        if int(rounds) != PASSWORD_HASH_ITERATIONS:
            return False

        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
        if (
            len(salt) != PASSWORD_SALT_BYTES
            or len(expected_digest) != PASSWORD_DIGEST_BYTES
        ):
            return False

        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            PASSWORD_HASH_ITERATIONS,
        )
        return hmac.compare_digest(candidate, expected_digest)
    except (ValueError, TypeError):
        return False

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "username": user.username, "role": user.role, "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)

    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)

    if user.last_activity is not None:
        last_activity = user.last_activity

        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        if now - last_activity >= timedelta(
            minutes=SESSION_IDLE_TIMEOUT_MINUTES
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to inactivity. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user.last_activity = now
    db.commit()

    return user

def require_manager(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"ADMIN", "MANAGER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager/Admin role required")
    return user
