import uuid
from datetime import datetime

from pydantic import BaseModel


class ClassCreateRequest(BaseModel):
    name: str


class ClassResponse(BaseModel):
    id: uuid.UUID
    name: str
    student_count: int
    created_at: datetime


class ClassListResponse(BaseModel):
    items: list[ClassResponse]
