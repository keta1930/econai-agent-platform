import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import get_current_user, require_admin, TokenPayload
from models.task import Task
from models.submission import Submission
from models.roster import StudentRoster
from models.class_ import Class
from models.user import User
from models.model_config import ModelConfig
from schemas.task import (
    TaskDraftRequest, TaskUpdateRequest, TaskResponse, TaskListResponse,
    TaskSubmissionItem, TaskStatsResponse,
    GenerateCriteriaRequest, GenerateCriteriaResponse,
    BatchPublishRequest, BatchPublishItem, BatchPublishResponse,
)
from services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _build_task_response(task: Task, db: AsyncSession) -> TaskResponse:
    """Build a TaskResponse with joined class_name and created_by_name."""
    cls = await db.get(Class, task.class_id)
    creator = await db.get(User, task.created_by)
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        grading_criteria=task.grading_criteria,
        status=task.status,
        class_id=task.class_id,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        class_name=cls.name if cls else "",
        created_by_name=creator.username if creator else "",
    )


async def _verify_task_ownership(task: Task, admin: TokenPayload, db: AsyncSession) -> None:
    """Verify admin owns the class that this task belongs to."""
    result = await db.execute(
        select(Class).where(Class.id == task.class_id, Class.created_by == admin.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    class_id: uuid.UUID | None = Query(None),
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Task, Class.name, User.username)
        .join(Class, Task.class_id == Class.id)
        .join(User, Task.created_by == User.id)
    )

    if user.role in ("admin", "super_admin"):
        admin_class_ids = select(Class.id).where(Class.created_by == user.id)
        stmt = stmt.where(Task.class_id.in_(admin_class_ids))
        if class_id is not None:
            stmt = stmt.where(Task.class_id == class_id)
    else:
        stmt = stmt.where(Task.class_id == user.class_id)

    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)

    stmt = stmt.order_by(Task.created_at.desc())
    result = await db.execute(stmt)

    items = [
        TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            grading_criteria=task.grading_criteria,
            status=task.status,
            class_id=task.class_id,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
            class_name=class_name,
            created_by_name=creator_name,
        )
        for task, class_name, creator_name in result.all()
    ]
    return TaskListResponse(items=items)


@router.post("/generate-criteria", response_model=GenerateCriteriaResponse)
async def generate_criteria_endpoint(
    req: GenerateCriteriaRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Find admin's active model
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.admin_id == admin.id,
            ModelConfig.is_active == True,
        )
    )
    model_config = result.scalar_one_or_none()
    if not model_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先配置并激活 AI 模型",
        )

    from services.criteria_generator import generate_criteria

    try:
        criteria = await generate_criteria(req.title, req.description, model_config)
        return GenerateCriteriaResponse(criteria=criteria)
    except Exception:
        logger.exception("Failed to generate criteria")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成失败，请稍后重试",
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if user.role in ("admin", "super_admin"):
        await _verify_task_ownership(task, user, db)
    else:
        if task.class_id != user.class_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        if task.status == "draft":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    return await _build_task_response(task, db)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    req: TaskDraftRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify class belongs to admin
    result = await db.execute(
        select(Class).where(Class.id == req.class_id, Class.created_by == admin.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="班级不存在")

    task = Task(
        title=req.title,
        description=req.description,
        grading_criteria=req.grading_criteria,
        class_id=req.class_id,
        created_by=admin.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return await _build_task_response(task, db)


@router.post("/batch-publish", response_model=BatchPublishResponse, status_code=status.HTTP_201_CREATED)
async def batch_publish(
    req: BatchPublishRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify all class_ids belong to admin
    result = await db.execute(
        select(Class).where(Class.id.in_(req.class_ids), Class.created_by == admin.id)
    )
    valid_classes = {c.id: c for c in result.scalars().all()}

    if len(valid_classes) != len(req.class_ids):
        invalid = set(req.class_ids) - set(valid_classes.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的班级 ID: {invalid}",
        )

    # Validate content
    if not req.title.strip() or not req.description.strip() or not req.grading_criteria.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="发布任务需要填写标题、任务说明和打分标准",
        )

    created_items = []
    for cid in req.class_ids:
        task = Task(
            title=req.title,
            description=req.description,
            grading_criteria=req.grading_criteria,
            status="published",
            class_id=cid,
            created_by=admin.id,
        )
        db.add(task)
        await db.flush()
        created_items.append(
            BatchPublishItem(
                id=task.id,
                class_id=cid,
                class_name=valid_classes[cid].name,
            )
        )

    await db.commit()
    return BatchPublishResponse(created=created_items)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    req: TaskUpdateRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    await _verify_task_ownership(task, admin, db)

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

    await db.commit()
    await db.refresh(task)
    return await _build_task_response(task, db)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    await _verify_task_ownership(task, admin, db)

    # Cascade: delete submissions and task, then clean up files
    result = await db.execute(select(Submission).where(Submission.task_id == task_id))
    submissions = result.scalars().all()
    file_paths = [s.file_path for s in submissions if s.file_path]

    await db.execute(delete(Submission).where(Submission.task_id == task_id))
    await db.delete(task)
    await db.commit()

    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)

    return Response(status_code=204)


@router.get("/{task_id}/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    task_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    await _verify_task_ownership(task, admin, db)

    # Get roster for the task's class
    result = await db.execute(
        select(StudentRoster.student_id).where(StudentRoster.class_id == task.class_id)
    )
    all_student_ids = result.scalars().all()
    total_students = len(all_student_ids)

    # Get submissions for this task
    result = await db.execute(
        select(Submission)
        .where(Submission.task_id == task_id)
        .order_by(Submission.student_id, Submission.version.desc())
    )
    submissions = result.scalars().all()

    # Build user_id -> username map for submitted students
    submitted_user_ids = {s.student_id for s in submissions}
    username_map: dict[uuid.UUID, str] = {}
    if submitted_user_ids:
        result = await db.execute(
            select(User.id, User.username).where(User.id.in_(submitted_user_ids))
        )
        username_map = {uid: uname for uid, uname in result.all()}

    # Group by student: pick latest version, count total submissions
    latest_by_student: dict[uuid.UUID, Submission] = {}
    count_by_student: dict[uuid.UUID, int] = {}
    for s in submissions:
        count_by_student[s.student_id] = count_by_student.get(s.student_id, 0) + 1
        if s.student_id not in latest_by_student:
            latest_by_student[s.student_id] = s

    # Build set of submitted student_ids (usernames) for not_submitted calculation
    submitted_usernames = {username_map.get(uid, "") for uid in latest_by_student}

    submission_items = [
        TaskSubmissionItem(
            student_id=s.student_id,
            username=username_map.get(s.student_id, ""),
            version=s.version,
            submission_count=count_by_student[s.student_id],
            status=s.status,
            score=s.score,
            submitted_at=s.submitted_at,
        )
        for s in latest_by_student.values()
    ]

    not_submitted = [sid for sid in all_student_ids if sid not in submitted_usernames]
    submitted_count = len(latest_by_student)
    rate = submitted_count / total_students if total_students > 0 else 0.0

    return TaskStatsResponse(
        task_id=task_id,
        total_students=total_students,
        submitted_count=submitted_count,
        submission_rate=round(rate, 3),
        submissions=submission_items,
        not_submitted=not_submitted,
    )
