from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from analysis_agent.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": expire, "type": "access"}, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode({"sub": user_id, "exp": expire, "type": "refresh"}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, expected_type: str = "access") -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    """Returns (plaintext_key, hashed_key). Plaintext returned only once."""
    raw = secrets.token_hex(32)
    plaintext = f"tsrx_{raw}"
    hashed = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, hashed


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_reset_token() -> tuple[str, str]:
    """Returns (plaintext_token, hashed_token). Plaintext is embedded in the reset link and never stored."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_reset_token(raw)
