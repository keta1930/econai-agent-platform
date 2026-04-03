from datetime import datetime

from pydantic import BaseModel


class SubmissionCreateResponse(BaseModel):
    id: int
    task_id: int
    student_id: int
    version: int
    content_type: str
    status: str
    submitted_at: datetime

    model_config = {"from_attributes": True}


class SubmissionDetail(BaseModel):
    id: int
    task_id: int
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
    submission_id: int
    filename: str
    content: str
    content_type: str
    file_extension: str
