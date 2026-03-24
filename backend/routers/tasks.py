import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth.deps import get_current_user, require_admin
from models.task import Task
from models.submission import Submission
from models.roster import StudentRoster
from models.user import User
from schemas.task import (
    TaskCreateRequest, TaskResponse, TaskListResponse,
    TaskSubmissionItem, TaskStatsResponse,
    GenerateCriteriaRequest, GenerateCriteriaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_tasks(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks]
    )


@router.post("/generate-criteria", response_model=GenerateCriteriaResponse)
async def generate_criteria_endpoint(
    req: GenerateCriteriaRequest,
    _admin: User = Depends(require_admin),
):
    from services.criteria_generator import generate_criteria

    try:
        criteria = await generate_criteria(req.title, req.description)
        return GenerateCriteriaResponse(criteria=criteria)
    except Exception:
        logger.exception("Failed to generate criteria")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成失败，请稍后重试",
        )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return TaskResponse.model_validate(task)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    req: TaskCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    task = Task(
        title=req.title,
        description=req.description,
        grading_criteria=req.grading_criteria,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}/stats", response_model=TaskStatsResponse)
def get_task_stats(
    task_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    all_student_ids = [
        r.student_id for r in db.query(StudentRoster.student_id).all()
    ]
    total_students = len(all_student_ids)

    submissions = (
        db.query(Submission)
        .filter(Submission.task_id == task_id)
        .all()
    )
    submitted_ids = {s.student_id for s in submissions}

    submission_items = [
        TaskSubmissionItem(
            student_id=s.student_id,
            status=s.status,
            score=s.score,
            submitted_at=s.submitted_at,
        )
        for s in submissions
    ]

    not_submitted = [sid for sid in all_student_ids if sid not in submitted_ids]
    submitted_count = len(submitted_ids)
    rate = submitted_count / total_students if total_students > 0 else 0.0

    return TaskStatsResponse(
        task_id=task_id,
        total_students=total_students,
        submitted_count=submitted_count,
        submission_rate=round(rate, 3),
        submissions=submission_items,
        not_submitted=not_submitted,
    )
