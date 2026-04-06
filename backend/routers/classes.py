import asyncio
import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from database import get_db
from auth.deps import require_admin, TokenPayload
from models.class_ import Class
from models.class_member import ClassMember
from models.user import User
from models.roster import StudentRoster
from models.task import Task
from models.submission import Submission
from models.sharing import SharingTopic, TopicVote
from schemas.class_ import ClassCreateRequest, ClassResponse, ClassListResponse
from services.storage import storage_service

router = APIRouter(prefix="/api/admin/classes", tags=["classes"])


@router.get("", response_model=ClassListResponse)
async def list_classes(
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Class).where(Class.created_by == admin.id).order_by(Class.created_at.desc())
    )
    classes = result.scalars().all()

    # 批量统计每个班级的学生数和已发布任务数
    class_ids = [c.id for c in classes]
    student_counts: dict[uuid.UUID, int] = {}
    task_counts: dict[uuid.UUID, int] = {}
    if class_ids:
        result = await db.execute(
            select(ClassMember.class_id, func.count(ClassMember.id))
            .where(ClassMember.class_id.in_(class_ids))
            .group_by(ClassMember.class_id)
        )
        student_counts = {cid: cnt for cid, cnt in result.all()}

        result = await db.execute(
            select(Task.class_id, func.count(Task.id))
            .where(Task.class_id.in_(class_ids), Task.status == "published")
            .group_by(Task.class_id)
        )
        task_counts = {cid: cnt for cid, cnt in result.all()}

    items = [
        ClassResponse(
            id=c.id,
            name=c.name,
            join_token=c.join_token,
            student_count=student_counts.get(c.id, 0),
            task_count=task_counts.get(c.id, 0),
            created_at=c.created_at,
        )
        for c in classes
    ]
    return ClassListResponse(items=items)


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    req: ClassCreateRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("创建班级 — 管理员=%s, 名称=%s", admin.id, req.name)

    # 检查同一管理员下班级名称是否重复
    result = await db.execute(
        select(Class).where(Class.name == req.name, Class.created_by == admin.id)
    )
    if result.scalar_one_or_none():
        logger.warning("创建班级失败 — 名称重复, 管理员=%s, 名称=%s", admin.id, req.name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该班级名称已存在",
        )

    cls = Class(name=req.name, created_by=admin.id)
    db.add(cls)
    await db.commit()
    await db.refresh(cls)
    return ClassResponse(
        id=cls.id, name=cls.name, join_token=cls.join_token,
        student_count=0, task_count=0, created_at=cls.created_at,
    )


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("删除班级 — class_id=%s, 管理员=%s", class_id, admin.id)

    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        logger.warning("删除班级失败 — 班级不存在, class_id=%s", class_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")

    # 级联删除：投票 → 分享主题 → 提交记录（含文件）→ 任务 → 成员 → 名单 → 班级

    # 1. 删除该班级下分享主题的投票
    topic_ids_stmt = select(SharingTopic.id).where(SharingTopic.class_id == class_id)
    await db.execute(delete(TopicVote).where(TopicVote.topic_id.in_(topic_ids_stmt)))

    # 2. 删除分享主题
    await db.execute(delete(SharingTopic).where(SharingTopic.class_id == class_id))

    # 3. 删除提交记录，收集文件路径用于清理存储
    task_ids_stmt = select(Task.id).where(Task.class_id == class_id)
    result = await db.execute(
        select(Submission.file_path).where(Submission.task_id.in_(task_ids_stmt))
    )
    file_paths = [fp for (fp,) in result.all() if fp]

    await db.execute(delete(Submission).where(Submission.task_id.in_(task_ids_stmt)))

    # 4. 删除任务
    await db.execute(delete(Task).where(Task.class_id == class_id))

    # 5. 删除班级成员关系
    await db.execute(
        delete(ClassMember).where(ClassMember.class_id == class_id)
    )

    # 6. 删除学生名单
    await db.execute(delete(StudentRoster).where(StudentRoster.class_id == class_id))

    # 7. 删除班级
    await db.delete(cls)
    await db.commit()

    # 清理 MinIO 中的文件
    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)

    return Response(status_code=204)


@router.get("/{class_id}/token")
async def get_class_token(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        logger.warning("获取加入凭证失败 — 班级不存在, class_id=%s", class_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    return {"join_token": cls.join_token}


@router.post("/{class_id}/token/regenerate")
async def regenerate_class_token(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("重新生成加入凭证 — class_id=%s, 管理员=%s", class_id, admin.id)

    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        logger.warning("重新生成加入凭证失败 — 班级不存在, class_id=%s", class_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")

    cls.join_token = secrets.token_urlsafe(16)
    await db.commit()
    await db.refresh(cls)
    return {"join_token": cls.join_token}
