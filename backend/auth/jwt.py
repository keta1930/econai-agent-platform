import uuid
from datetime import datetime, timedelta, timezone

import jwt

from config import SECRET_KEY, TOKEN_EXPIRE_HOURS

ALGORITHM = "HS256"


def create_access_token(sub: uuid.UUID, role: str, class_id: uuid.UUID | None = None) -> str:
    payload = {
        "sub": str(sub),
        "role": role,
        "class_id": str(class_id) if class_id else None,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
