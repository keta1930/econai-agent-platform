from datetime import datetime

from pydantic import BaseModel


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    grading_criteria: str


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    grading_criteria: str
    created_at: datetime

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
