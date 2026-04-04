import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_student, require_admin
from config import MAX_TEXT_SIZE, MAX_IMAGE_SIZE
from models.user import User
from models.task import Task
from models.class_ import Class
from models.submission import Submission
from schemas.submission import (
    SubmissionCreateResponse, SubmissionDetail, SubmissionListResponse,
    SubmissionContentResponse,
)
from services.storage import storage_service

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

admin_submissions_router = APIRouter(
    prefix="/api/admin",
    tags=["admin-submissions"],
)

ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".py", ".yaml", ".jsonl"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# MIME type mapping for storage
_TEXT_CONTENT_TYPES: dict[str, str] = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".json": "text/plain",
    ".py": "text/x-python",
    ".yaml": "text/yaml",
    ".jsonl": "text/plain",
}
_IMAGE_CONTENT_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


async def _handle_text_submission(
    text_content: str | None, task_id: uuid.UUID, student_id: uuid.UUID, timestamp: str,
) -> str:
    """Validate and upload a text submission. Returns the storage path."""
    if not text_content or not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="内容不能为空",
        )
    file_data = text_content.encode("utf-8")
    if len(file_data) > MAX_TEXT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文本内容超过 {MAX_TEXT_SIZE // (1024 * 1024)}MB 限制",
        )
    safe_filename = f"{timestamp}_paste.md"
    rel_path = f"submissions/{task_id}/{student_id}/{safe_filename}"
    await asyncio.to_thread(
        storage_service.put_object, rel_path, file_data, "text/markdown",
    )
    return rel_path


async def _handle_file_submission(
    file: UploadFile | None, task_id: uuid.UUID, student_id: uuid.UUID, timestamp: str,
) -> str:
    """Validate and upload a file submission. Returns the storage path."""
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请选择文件",
        )
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))} 格式",
        )
    file_data = await file.read()
    if len(file_data) > MAX_TEXT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过 {MAX_TEXT_SIZE // (1024 * 1024)}MB 限制",
        )
    safe_filename = f"{timestamp}_{file.filename}"
    rel_path = f"submissions/{task_id}/{student_id}/{safe_filename}"
    mime = _TEXT_CONTENT_TYPES.get(ext, "application/octet-stream")
    await asyncio.to_thread(storage_service.put_object, rel_path, file_data, mime)
    return rel_path


async def _handle_image_submission(
    file: UploadFile | None, task_id: uuid.UUID, student_id: uuid.UUID, timestamp: str,
) -> str:
    """Validate and upload an image submission. Returns the storage path."""
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请选择图片",
        )
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持 {', '.join(sorted(IMAGE_EXTENSIONS))} 格式",
        )
    file_data = await file.read()
    if len(file_data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图片大小超过 {MAX_IMAGE_SIZE // (1024 * 1024)}MB 限制",
        )
    safe_filename = f"{timestamp}_{file.filename}"
    rel_path = f"submissions/{task_id}/{student_id}/{safe_filename}"
    mime = _IMAGE_CONTENT_TYPES.get(ext, "application/octet-stream")
    await asyncio.to_thread(storage_service.put_object, rel_path, file_data, mime)
    return rel_path


def _build_submission_detail(s: Submission, task_title: str) -> SubmissionDetail:
    return SubmissionDetail(
        id=s.id,
        task_id=s.task_id,
        task_title=task_title,
        version=s.version,
        content_type=s.content_type,
        status=s.status,
        score=s.score,
        suggestion=s.suggestion,
        submitted_at=s.submitted_at,
        graded_at=s.graded_at,
    )


async def _verify_admin_owns_task(task: Task, admin: User, db: AsyncSession) -> None:
    """Verify admin owns the class the task belongs to."""
    result = await db.execute(
        select(Class).where(Class.id == task.class_id, Class.created_by == admin.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在")


@router.post("", response_model=SubmissionCreateResponse, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    task_id: uuid.UUID = Form(...),
    content_type: str = Form(...),
    text_content: str | None = Form(None),
    file: UploadFile | None = File(None),
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    # Validate content_type
    if content_type not in ("text", "file", "image"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content_type 必须为 text、file 或 image",
        )

    # Validate task exists and belongs to student's class
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.class_id != student.class_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权提交该任务")

    # Calculate next version number
    result = await db.execute(
        select(func.max(Submission.version))
        .where(Submission.task_id == task_id, Submission.student_id == student.id)
    )
    max_version = result.scalar_one_or_none()
    new_version = (max_version or 0) + 1

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Dispatch to content-type-specific handler
    if content_type == "text":
        rel_path = await _handle_text_submission(text_content, task_id, student.id, timestamp)
    elif content_type == "file":
        rel_path = await _handle_file_submission(file, task_id, student.id, timestamp)
    else:  # image
        rel_path = await _handle_image_submission(file, task_id, student.id, timestamp)

    # Determine initial status
    initial_status = "manual_review" if content_type == "image" else "pending"

    # Create submission record
    submission = Submission(
        task_id=task_id,
        student_id=student.id,
        version=new_version,
        file_path=rel_path,
        content_type=content_type,
        status=initial_status,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Trigger async grading for text/file only
    if content_type != "image":
        from services.grading_service import grade_submission
        asyncio.create_task(grade_submission(submission.id))

    return SubmissionCreateResponse(
        id=submission.id,
        task_id=submission.task_id,
        student_id=submission.student_id,
        version=submission.version,
        content_type=submission.content_type,
        status=submission.status,
        submitted_at=submission.submitted_at,
        task_title=task.title,
    )


@router.get("/my", response_model=SubmissionListResponse)
async def list_my_submissions(
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.student_id == student.id)
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    items = []
    for s in submissions:
        result = await db.execute(select(Task).where(Task.id == s.task_id))
        task = result.scalar_one_or_none()
        items.append(_build_submission_detail(s, task.title if task else ""))
    return SubmissionListResponse(items=items)


@router.get("/my/{task_id}", response_model=SubmissionListResponse)
async def get_my_submission(
    task_id: uuid.UUID,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.task_id == task_id, Submission.student_id == student.id)
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    task_title = task.title if task else ""
    items = [_build_submission_detail(s, task_title) for s in submissions]
    return SubmissionListResponse(items=items)


@admin_submissions_router.get(
    "/students/{student_id}/submissions",
    response_model=SubmissionListResponse,
)
async def get_student_submissions(
    student_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify admin owns the student's class
    result = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student or not student.class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    result = await db.execute(
        select(Class).where(Class.id == student.class_id, Class.created_by == admin.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    result = await db.execute(
        select(Submission)
        .where(Submission.student_id == student_id)
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    items = []
    for s in submissions:
        result = await db.execute(select(Task).where(Task.id == s.task_id))
        task = result.scalar_one_or_none()
        items.append(_build_submission_detail(s, task.title if task else ""))
    return SubmissionListResponse(items=items)


@admin_submissions_router.get(
    "/submissions/{submission_id}/content",
    response_model=SubmissionContentResponse,
)
async def get_submission_content(
    submission_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在")

    # Verify admin owns the task's class
    result = await db.execute(select(Task).where(Task.id == submission.task_id))
    task = result.scalar_one_or_none()
    if task:
        await _verify_admin_owns_task(task, admin, db)

    filename = Path(submission.file_path).name
    file_extension = Path(submission.file_path).suffix.lower()

    if submission.content_type == "image":
        # Return presigned URL for image content
        try:
            url = await asyncio.to_thread(
                storage_service.presigned_get_url, submission.file_path,
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片文件不存在")
        return SubmissionContentResponse(
            submission_id=submission.id,
            filename=filename,
            content=url,
            content_type=submission.content_type,
            file_extension=file_extension,
        )

    # Text / file: read content as string
    try:
        text_content = await asyncio.to_thread(storage_service.get_text, submission.file_path)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交文件不存在")

    return SubmissionContentResponse(
        submission_id=submission.id,
        filename=filename,
        content=text_content,
        content_type=submission.content_type,
        file_extension=file_extension,
    )


@admin_submissions_router.get(
    "/tasks/{task_id}/students/{student_id}/submissions",
    response_model=SubmissionListResponse,
)
async def get_student_task_submissions(
    task_id: uuid.UUID,
    student_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify admin owns the task's class
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    await _verify_admin_owns_task(task, admin, db)

    # Get student username
    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none()

    result = await db.execute(
        select(Submission)
        .where(Submission.task_id == task_id, Submission.student_id == student_id)
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()

    task_title = task.title
    items = [_build_submission_detail(s, task_title) for s in submissions]
    return SubmissionListResponse(
        items=items,
        student_name=student.username if student else None,
    )
