import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TaskDraftRequest(BaseModel):
    title: str
    description: str = ""
    grading_criteria: str = ""
    class_id: uuid.UUID


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    grading_criteria: str | None = None
    status: str | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    grading_criteria: str
    status: str
    class_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    class_name: str
    created_by_name: str


class TaskListResponse(BaseModel):
    items: list[TaskResponse]


class TaskSubmissionItem(BaseModel):
    student_id: uuid.UUID
    username: str
    version: int
    submission_count: int
    status: str
    score: float | None
    submitted_at: datetime


class TaskStatsResponse(BaseModel):
    task_id: uuid.UUID
    total_students: int
    submitted_count: int
    submission_rate: float
    submissions: list[TaskSubmissionItem]
    not_submitted: list[str]


class GenerateCriteriaRequest(BaseModel):
    title: str
    description: str


class GenerateCriteriaResponse(BaseModel):
    criteria: str


class BatchPublishRequest(BaseModel):
    title: str
    description: str
    grading_criteria: str
    class_ids: list[uuid.UUID]
    status: Literal["published"]


class BatchPublishItem(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str


class BatchPublishResponse(BaseModel):
    created: list[BatchPublishItem]
