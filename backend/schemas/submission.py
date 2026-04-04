import uuid
from datetime import datetime

from pydantic import BaseModel


class SubmissionCreateResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    student_id: uuid.UUID
    version: int
    content_type: str
    status: str
    submitted_at: datetime
    task_title: str


class SubmissionDetail(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_title: str
    version: int
    content_type: str
    status: str
    score: float | None
    suggestion: str | None
    submitted_at: datetime
    graded_at: datetime | None


class SubmissionListResponse(BaseModel):
    items: list[SubmissionDetail]
    student_name: str | None = None


class SubmissionContentResponse(BaseModel):
    submission_id: uuid.UUID
    filename: str
    content: str
    content_type: str
    file_extension: str
