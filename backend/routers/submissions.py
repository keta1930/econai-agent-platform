import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session

from database import get_db
from auth.deps import require_student, require_admin
from models.user import User
from models.task import Task
from models.submission import Submission
from schemas.submission import (
    SubmissionCreateResponse, SubmissionDetail, SubmissionListResponse,
)
from config import STORAGE_DIR

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

admin_submissions_router = APIRouter(
    prefix="/api/admin/students",
    tags=["admin-submissions"],
    dependencies=[Depends(require_admin)],
)

ALLOWED_EXTENSIONS = {".md", ".txt"}


@router.post("", response_model=SubmissionCreateResponse, status_code=status.HTTP_201_CREATED)
def submit_assignment(
    background_tasks: BackgroundTasks,
    task_id: int = Form(...),
    file: UploadFile = File(...),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    # Validate file extension
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 .md 和 .txt 格式",
        )

    # Validate task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # Check duplicate submission
    existing = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == student.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该任务已提交，不可重复提交",
        )

    # Save file
    rel_path = f"submissions/{task_id}/{student.id}/{file.filename}"
    abs_dir = Path(STORAGE_DIR) / "submissions" / str(task_id) / student.id
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / file.filename

    content = file.file.read()
    abs_path.write_bytes(content)

    # Create submission record
    submission = Submission(
        task_id=task_id,
        student_id=student.id,
        file_path=rel_path,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Trigger async grading (will be connected in Phase 4)
    from services.grading_service import grade_submission
    background_tasks.add_task(grade_submission, submission.id)

    return SubmissionCreateResponse.model_validate(submission)


@router.get("/my", response_model=SubmissionListResponse)
def list_my_submissions(
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(Submission)
        .filter(Submission.student_id == student.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    items = []
    for s in submissions:
        task = db.query(Task).filter(Task.id == s.task_id).first()
        items.append(
            SubmissionDetail(
                id=s.id,
                task_id=s.task_id,
                task_title=task.title if task else "",
                status=s.status,
                score=s.score,
                suggestion=s.suggestion,
                submitted_at=s.submitted_at,
                graded_at=s.graded_at,
            )
        )
    return SubmissionListResponse(items=items)


@router.get("/my/{task_id}", response_model=SubmissionDetail)
def get_my_submission(
    task_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    submission = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == student.id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到提交记录")
    task = db.query(Task).filter(Task.id == submission.task_id).first()
    return SubmissionDetail(
        id=submission.id,
        task_id=submission.task_id,
        task_title=task.title if task else "",
        status=submission.status,
        score=submission.score,
        suggestion=submission.suggestion,
        submitted_at=submission.submitted_at,
        graded_at=submission.graded_at,
    )


@admin_submissions_router.get("/{student_id}/submissions", response_model=SubmissionListResponse)
def get_student_submissions(
    student_id: str,
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(Submission)
        .filter(Submission.student_id == student_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    items = []
    for s in submissions:
        task = db.query(Task).filter(Task.id == s.task_id).first()
        items.append(
            SubmissionDetail(
                id=s.id,
                task_id=s.task_id,
                task_title=task.title if task else "",
                status=s.status,
                score=s.score,
                suggestion=s.suggestion,
                submitted_at=s.submitted_at,
                graded_at=s.graded_at,
            )
        )
    return SubmissionListResponse(items=items)
