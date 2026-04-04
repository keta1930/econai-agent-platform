import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.jwt import decode_access_token

bearer_scheme = HTTPBearer()


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Identity extracted from a JWT access token. No database query."""

    id: uuid.UUID
    role: str
    class_id: uuid.UUID | None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenPayload:
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )

    class_id_raw = payload.get("class_id")
    class_id = uuid.UUID(class_id_raw) if class_id_raw else None

    return TokenPayload(id=user_id, role=payload.get("role", ""), class_id=class_id)


def require_admin(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


def require_student(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要学生权限",
        )
    return user


def require_super_admin(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return user
