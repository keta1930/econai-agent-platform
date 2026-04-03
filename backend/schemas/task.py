from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TaskDraftRequest(BaseModel):
    title: str
    description: str = ""
    grading_criteria: str = ""
    class_id: int


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    grading_criteria: str | None = None
    status: str | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    grading_criteria: str
    status: str
    class_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]


class TaskSubmissionItem(BaseModel):
    student_id: int
    username: str
    version: int
    submission_count: int
    status: str
    score: float | None
    submitted_at: datetime


class TaskStatsResponse(BaseModel):
    task_id: int
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
    class_ids: list[int]
    status: Literal["published"]


class BatchPublishItem(BaseModel):
    id: int
    class_id: int
    class_name: str


class BatchPublishResponse(BaseModel):
    created: list[BatchPublishItem]
