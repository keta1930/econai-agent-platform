import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from config import STORAGE_DIR

from database import get_db
from auth.deps import get_current_user, require_admin
from models.task import Task
from models.submission import Submission
from models.roster import StudentRoster
from models.user import User
from schemas.task import (
    TaskDraftRequest, TaskUpdateRequest, TaskResponse, TaskListResponse,
    TaskSubmissionItem, TaskStatsResponse,
    GenerateCriteriaRequest, GenerateCriteriaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status_filter is not None:
        query = query.filter(Task.status == status_filter)
    tasks = query.order_by(Task.created_at.desc()).all()
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if user.role != "admin" and task.status == "draft":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return TaskResponse.model_validate(task)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    req: TaskDraftRequest,
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


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    req: TaskUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="已发布任务不可编辑",
        )

    updates = req.model_dump(exclude_unset=True)

    if "status" in updates:
        if updates["status"] == "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的状态变更",
            )
        if updates["status"] == "published":
            # Apply other field updates first so validation sees latest values
            for field, value in updates.items():
                if field != "status":
                    setattr(task, field, value)
            if not task.title or not task.description or not task.grading_criteria:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="发布任务需要填写标题、任务说明和打分标准",
                )
            task.status = "published"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的状态值",
            )
    else:
        for field, value in updates.items():
            setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    # Cascade: delete submissions and task, then clean up files
    submissions = db.query(Submission).filter(Submission.task_id == task_id).all()
    file_paths = [Path(STORAGE_DIR) / s.file_path for s in submissions if s.file_path]
    db.query(Submission).filter(Submission.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    for fp in file_paths:
        if fp.exists():
            fp.unlink()
    return Response(status_code=204)


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
        .order_by(Submission.student_id, Submission.version.desc())
        .all()
    )

    # Group by student: pick latest version, count total submissions
    latest_by_student: dict[str, Submission] = {}
    count_by_student: dict[str, int] = {}
    for s in submissions:
        count_by_student[s.student_id] = count_by_student.get(s.student_id, 0) + 1
        if s.student_id not in latest_by_student:
            latest_by_student[s.student_id] = s  # first hit is latest (desc order)

    submitted_ids = set(latest_by_student.keys())

    submission_items = [
        TaskSubmissionItem(
            student_id=s.student_id,
            version=s.version,
            submission_count=count_by_student[s.student_id],
            status=s.status,
            score=s.score,
            submitted_at=s.submitted_at,
        )
        for s in latest_by_student.values()
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
