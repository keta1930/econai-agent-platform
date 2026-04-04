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
    class_count: int
    created_at: datetime


class AdminListResponse(BaseModel):
    items: list[AdminResponse]
