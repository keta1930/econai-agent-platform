import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminCreateRequest(BaseModel):
    username: str
    password: str


class AdminResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    is_active: bool
    class_count: int
    created_at: datetime


class AdminListResponse(BaseModel):
    items: list[AdminResponse]


class ResetPasswordRequest(BaseModel):
    new_password: str
