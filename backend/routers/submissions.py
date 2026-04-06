import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_student, require_admin, TokenPayload
from config import MAX_TEXT_SIZE, MAX_IMAGE_SIZE, MAX_IMAGES_PER_SUBMISSION, MAX_IMAGE_TOTAL_SIZE
from models.user import User
from models.task import Task
from models.class_ import Class
from models.class_member import ClassMember
from models.model_config import ModelConfig
from models.submission import Submission
from schemas.submission import (
    SubmissionCreateResponse, SubmissionDetail, SubmissionListResponse,
    SubmissionContentResponse,
)
from services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

admin_submissions_router = APIRouter(
    prefix="/api/admin",
    tags=["admin-submissions"],
)

ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".py", ".yaml", ".jsonl"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# MIME 类型映射
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
    """校验并上传文本提交，返回存储路径。"""
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
    """校验并上传文件提交，返回存储路径。"""
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


async def _handle_image_submissions(
    files: list[UploadFile],
    task_id: uuid.UUID,
    student_id: uuid.UUID,
    timestamp: str,
) -> list[str]:
    """校验并上传多张图片，返回存储路径列表。"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请选择图片",
        )
    if len(files) > MAX_IMAGES_PER_SUBMISSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多上传 {MAX_IMAGES_PER_SUBMISSION} 张图片",
        )

    paths: list[str] = []
    total_size = 0

    for i, f in enumerate(files):
        _, ext = os.path.splitext(f.filename or "")
        ext = ext.lower()
        if ext not in IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"第 {i + 1} 个文件格式不支持，仅支持 {', '.join(sorted(IMAGE_EXTENSIONS))}",
            )
        file_data = await f.read()
        if len(file_data) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"第 {i + 1} 张图片超过 {MAX_IMAGE_SIZE // (1024 * 1024)}MB 限制",
            )
        total_size += len(file_data)
        if total_size > MAX_IMAGE_TOTAL_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片总大小超过 {MAX_IMAGE_TOTAL_SIZE // (1024 * 1024)}MB 限制",
            )
        safe_filename = f"{timestamp}_{i:02d}_{f.filename}"
        rel_path = f"submissions/{task_id}/{student_id}/{safe_filename}"
        mime = _IMAGE_CONTENT_TYPES.get(ext, "application/octet-stream")
        await asyncio.to_thread(storage_service.put_object, rel_path, file_data, mime)
        paths.append(rel_path)

    return paths


def _build_submission_detail(s: Submission, task_title: str) -> SubmissionDetail:
    return SubmissionDetail(
        id=s.id,
        task_id=s.task_id,
        task_title=task_title,
        version=s.version,
        content_type=s.content_type,
        status=s.status,
        score=s.score,
        feedback=s.feedback,
        submitted_at=s.submitted_at,
        graded_at=s.graded_at,
    )


async def _verify_admin_owns_task(task: Task, admin: TokenPayload, db: AsyncSession) -> None:
    """验证管理员拥有该任务所属的班级。"""
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
    files: list[UploadFile] = File(default=[]),
    student: TokenPayload = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    logger.info("提交作业 — student_id=%s, task_id=%s, type=%s", student.id, task_id, content_type)

    # 校验 content_type
    if content_type not in ("text", "file", "image"):
        logger.warning("提交失败 — 无效的 content_type=%s", content_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content_type 必须为 text、file 或 image",
        )

    # 校验任务存在且属于学生所在班级
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("提交失败 — 任务不存在, task_id=%s", task_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.class_id != student.class_id:
        logger.warning("提交失败 — 无权提交, student_id=%s, task_id=%s", student.id, task_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权提交该任务")

    # 计算下一个版本号
    result = await db.execute(
        select(func.max(Submission.version))
        .where(Submission.task_id == task_id, Submission.student_id == student.id)
    )
    max_version = result.scalar_one_or_none()
    new_version = (max_version or 0) + 1

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # 按提交类型分发处理 — file_path 统一为 JSON 数组
    if content_type == "text":
        rel_path = await _handle_text_submission(text_content, task_id, student.id, timestamp)
        file_path = [rel_path]
    elif content_type == "file":
        rel_path = await _handle_file_submission(file, task_id, student.id, timestamp)
        file_path = [rel_path]
    else:  # image
        file_path = await _handle_image_submissions(files, task_id, student.id, timestamp)

    # 确定初始状态 — 图片提交需检查 VLM 支持
    if content_type == "image":
        result = await db.execute(
            select(Class).where(Class.id == task.class_id)
        )
        cls = result.scalar_one_or_none()
        model_config = None
        if cls:
            result = await db.execute(
                select(ModelConfig).where(
                    ModelConfig.admin_id == cls.created_by,
                    ModelConfig.is_active == True,  # noqa: E712
                )
            )
            model_config = result.scalar_one_or_none()

        if model_config and model_config.supports_vision:
            initial_status = "pending"
        else:
            initial_status = "manual_review"
    else:
        initial_status = "pending"

    # 创建提交记录
    submission = Submission(
        task_id=task_id,
        student_id=student.id,
        version=new_version,
        file_path=file_path,
        content_type=content_type,
        status=initial_status,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # 对所有 pending 状态的提交触发异步批改
    if submission.status == "pending":
        from services.grading import grade_submission
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
    student: TokenPayload = Depends(require_student),
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
    student: TokenPayload = Depends(require_student),
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
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # 验证学生存在且属于管理员的班级
    result = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        logger.warning("查看学生提交失败 — 学生不存在, student_id=%s", student_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    # 检查学生是否属于该管理员的某个班级
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.user_id == student_id,
            ClassMember.class_id.in_(
                select(Class.id).where(Class.created_by == admin.id)
            ),
        )
    )
    if not result.first():
        logger.warning("查看学生提交失败 — 学生不属于管理员的班级, student_id=%s", student_id)
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
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        logger.warning("查看提交内容失败 — 记录不存在, submission_id=%s", submission_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在")

    # 验证管理员拥有该任务所属的班级
    result = await db.execute(select(Task).where(Task.id == submission.task_id))
    task = result.scalar_one_or_none()
    if task:
        await _verify_admin_owns_task(task, admin, db)

    file_paths: list[str] = submission.file_path  # JSON 数组

    if submission.content_type == "image":
        # 返回所有图片的预签名 URL
        try:
            urls = []
            for path in file_paths:
                url = await asyncio.to_thread(
                    storage_service.presigned_get_url, path,
                )
                urls.append(url)
        except Exception:
            logger.warning("获取图片预签名 URL 失败 — submission_id=%s", submission_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片文件不存在")
        first_path = file_paths[0] if file_paths else ""
        return SubmissionContentResponse(
            submission_id=submission.id,
            filename=Path(first_path).name,
            content=urls,
            content_type=submission.content_type,
            file_extension=Path(first_path).suffix.lower(),
        )

    # 文本 / 文件：读取内容（取第一个路径）
    first_path = file_paths[0] if file_paths else ""
    try:
        text_content = await asyncio.to_thread(storage_service.get_text, first_path)
    except Exception:
        logger.warning("读取提交文件失败 — submission_id=%s, path=%s", submission_id, first_path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交文件不存在")

    return SubmissionContentResponse(
        submission_id=submission.id,
        filename=Path(first_path).name,
        content=text_content,
        content_type=submission.content_type,
        file_extension=Path(first_path).suffix.lower(),
    )


@admin_submissions_router.get(
    "/tasks/{task_id}/students/{student_id}/submissions",
    response_model=SubmissionListResponse,
)
async def get_student_task_submissions(
    task_id: uuid.UUID,
    student_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # 验证管理员拥有该任务所属的班级
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("查看学生任务提交失败 — 任务不存在, task_id=%s", task_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    await _verify_admin_owns_task(task, admin, db)

    # 获取学生用户名
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
