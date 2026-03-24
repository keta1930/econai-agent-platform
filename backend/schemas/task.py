from datetime import datetime

from pydantic import BaseModel


class TaskDraftRequest(BaseModel):
    title: str
    description: str = ""
    grading_criteria: str = ""


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
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]


class TaskSubmissionItem(BaseModel):
    student_id: str
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
