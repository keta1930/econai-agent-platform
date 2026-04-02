import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from auth.deps import require_student, require_admin
from models.user import User
from models.task import Task
from models.submission import Submission
from schemas.submission import (
    SubmissionCreateResponse, SubmissionDetail, SubmissionListResponse,
    SubmissionContentResponse,
)
from config import STORAGE_DIR

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

admin_submissions_router = APIRouter(
    prefix="/api/admin",
    tags=["admin-submissions"],
    dependencies=[Depends(require_admin)],
)

ALLOWED_EXTENSIONS = {".md", ".txt"}


def _build_submission_detail(s: Submission, task_title: str) -> SubmissionDetail:
    return SubmissionDetail(
        id=s.id,
        task_id=s.task_id,
        task_title=task_title,
        version=s.version,
        status=s.status,
        score=s.score,
        suggestion=s.suggestion,
        submitted_at=s.submitted_at,
        graded_at=s.graded_at,
    )


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

    # Calculate next version number
    max_version = (
        db.query(func.max(Submission.version))
        .filter(Submission.task_id == task_id, Submission.student_id == student.id)
        .scalar()
    )
    new_version = (max_version or 0) + 1

    # Save file with timestamp prefix to avoid overwrites
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    rel_path = f"submissions/{task_id}/{student.id}/{safe_filename}"
    abs_dir = Path(STORAGE_DIR) / "submissions" / str(task_id) / student.id
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / safe_filename

    content = file.file.read()
    abs_path.write_bytes(content)

    # Create submission record
    submission = Submission(
        task_id=task_id,
        student_id=student.id,
        version=new_version,
        file_path=rel_path,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Trigger async grading
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
        items.append(_build_submission_detail(s, task.title if task else ""))
    return SubmissionListResponse(items=items)


@router.get("/my/{task_id}", response_model=SubmissionListResponse)
def get_my_submission(
    task_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == student.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    task = db.query(Task).filter(Task.id == task_id).first()
    task_title = task.title if task else ""
    items = [_build_submission_detail(s, task_title) for s in submissions]
    return SubmissionListResponse(items=items)


@admin_submissions_router.get(
    "/students/{student_id}/submissions",
    response_model=SubmissionListResponse,
)
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
        items.append(_build_submission_detail(s, task.title if task else ""))
    return SubmissionListResponse(items=items)


@admin_submissions_router.get(
    "/submissions/{submission_id}/content",
    response_model=SubmissionContentResponse,
)
def get_submission_content(
    submission_id: int,
    db: Session = Depends(get_db),
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在")

    file_path = Path(STORAGE_DIR) / submission.file_path
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交文件不存在")

    text_content = file_path.read_text(encoding="utf-8")
    filename = Path(submission.file_path).name

    return SubmissionContentResponse(
        submission_id=submission.id,
        filename=filename,
        content=text_content,
    )


@admin_submissions_router.get(
    "/tasks/{task_id}/students/{student_id}/submissions",
    response_model=SubmissionListResponse,
)
def get_student_task_submissions(
    task_id: int,
    student_id: str,
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == student_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    task = db.query(Task).filter(Task.id == task_id).first()
    task_title = task.title if task else ""
    items = [_build_submission_detail(s, task_title) for s in submissions]
    return SubmissionListResponse(items=items)
