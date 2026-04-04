import uuid
from datetime import datetime

from pydantic import BaseModel


class InviteCodeCreateRequest(BaseModel):
    category: str


class InviteCodeResponse(BaseModel):
    id: uuid.UUID
    category: str
    registered_count: int
    created_at: datetime


class InviteCodeCreateResponse(InviteCodeResponse):
    """Returned only on create/regenerate — includes the plaintext code once."""

    code: str


class InviteCodeListResponse(BaseModel):
    items: list[InviteCodeResponse]
