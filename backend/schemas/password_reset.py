import uuid
from datetime import datetime

from pydantic import BaseModel


class ForgotPasswordRequest(BaseModel):
    username: str


class ForgotPasswordResponse(BaseModel):
    message: str


class PasswordResetRequestItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    display_name: str | None
    created_at: datetime


class PasswordResetListResponse(BaseModel):
    items: list[PasswordResetRequestItem]


class PasswordResetCountResponse(BaseModel):
    count: int


class PasswordResetApproveRequest(BaseModel):
    request_ids: list[uuid.UUID]


class PasswordResetApproveResponse(BaseModel):
    approved_count: int
