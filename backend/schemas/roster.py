import uuid
from datetime import datetime

from pydantic import BaseModel


class RosterAddRequest(BaseModel):
    student_id: str


class RosterBatchRequest(BaseModel):
    student_ids: list[str]


class ExpectedRosterItem(BaseModel):
    student_id: str
    matched: bool


class ActualRosterItem(BaseModel):
    user_id: uuid.UUID
    student_id: str
    display_name: str | None
    college: str | None
    joined_at: datetime


class RosterListResponse(BaseModel):
    expected: list[ExpectedRosterItem]
    actual: list[ActualRosterItem]


class RosterBatchResponse(BaseModel):
    added: int
    duplicates: int


class ResetStudentPasswordRequest(BaseModel):
    user_id: uuid.UUID
    new_password: str


class RosterBatchDeleteRequest(BaseModel):
    student_ids: list[str]


class RosterBatchDeleteResponse(BaseModel):
    deleted: int


class MemberBatchRemoveRequest(BaseModel):
    user_ids: list[uuid.UUID]


class MemberBatchRemoveResponse(BaseModel):
    removed: int
