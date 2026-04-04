import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

ALGORITHM = "HS256"


def create_access_token(sub: uuid.UUID, role: str, class_id: uuid.UUID | None = None) -> str:
    payload = {
        "sub": str(sub),
        "role": role,
        "class_id": str(class_id) if class_id else None,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def create_refresh_token() -> tuple[str, str]:
    """Generate a refresh token.

    Returns (raw_token, token_hash) where token_hash is SHA-256 hex digest.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(token: str) -> str:
    """Compute SHA-256 hex digest of a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
