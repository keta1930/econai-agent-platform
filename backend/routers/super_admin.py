import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_super_admin
from models.backup import Backup
from models.class_ import Class
from models.model_config import ModelConfig
from models.roster import StudentRoster
from models.sharing import SharingTopic, TopicVote
from models.submission import Submission
from models.task import Task
from models.user import User
from schemas.super_admin import AdminCreateRequest, AdminResponse, AdminListResponse, ResetPasswordRequest
from services.auth_service import hash_password
from services.storage import storage_service

router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


@router.get("/admins", response_model=AdminListResponse)
async def list_admins(
    _super: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.role == "admin").order_by(User.created_at.desc())
    )
    admins = result.scalars().all()

    # Batch count classes per admin
    admin_ids = [a.id for a in admins]
    class_counts: dict[uuid.UUID, int] = {}
    if admin_ids:
        result = await db.execute(
            select(Class.created_by, func.count(Class.id))
            .where(Class.created_by.in_(admin_ids))
            .group_by(Class.created_by)
        )
        class_counts = {aid: cnt for aid, cnt in result.all()}

    items = [
        AdminResponse(
            id=a.id,
            username=a.username,
            role=a.role,
            is_active=a.is_active,
            class_count=class_counts.get(a.id, 0),
            created_at=a.created_at,
        )
        for a in admins
    ]
    return AdminListResponse(items=items)


@router.post("/admins", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    req: AdminCreateRequest,
    _super: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness among admin/super_admin usernames
    result = await db.execute(
        select(User).where(
            User.username == req.username,
            User.role.in_(["admin", "super_admin"]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号已存在",
        )

    pw_hash = await asyncio.to_thread(hash_password, req.password)
    admin = User(
        username=req.username,
        password_hash=pw_hash,
        role="admin",
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    return AdminResponse(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        is_active=admin.is_active,
        class_count=0,
        created_at=admin.created_at,
    )


@router.put("/admins/{admin_id}/toggle-active", response_model=AdminResponse)
async def toggle_admin_active(
    admin_id: uuid.UUID,
    super_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin_id == super_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账号",
        )

    result = await db.execute(
        select(User).where(User.id == admin_id, User.role == "admin")
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在",
        )

    admin.is_active = not admin.is_active
    await db.commit()
    await db.refresh(admin)

    # Fetch class count
    result = await db.execute(
        select(func.count(Class.id)).where(Class.created_by == admin.id)
    )
    class_count = result.scalar() or 0

    return AdminResponse(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        is_active=admin.is_active,
        class_count=class_count,
        created_at=admin.created_at,
    )


@router.put("/admins/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: uuid.UUID,
    req: ResetPasswordRequest,
    _super: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == admin_id, User.role == "admin")
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在",
        )

    admin.password_hash = await asyncio.to_thread(hash_password, req.new_password)
    await db.commit()
    return {"message": "密码已重置"}


@router.delete("/admins/{admin_id}", status_code=204)
async def delete_admin(
    admin_id: uuid.UUID,
    super_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin_id == super_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )

    result = await db.execute(
        select(User).where(User.id == admin_id, User.role == "admin")
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在",
        )

    # Collect all class IDs owned by this admin
    result = await db.execute(
        select(Class.id).where(Class.created_by == admin_id)
    )
    class_ids = [cid for (cid,) in result.all()]

    file_paths: list[str] = []

    if class_ids:
        # 1. Delete topic_votes for topics in admin's classes
        topic_ids_stmt = select(SharingTopic.id).where(SharingTopic.class_id.in_(class_ids))
        await db.execute(delete(TopicVote).where(TopicVote.topic_id.in_(topic_ids_stmt)))

        # 2. Delete sharing_topics
        await db.execute(delete(SharingTopic).where(SharingTopic.class_id.in_(class_ids)))

        # 3. Delete submissions + collect file paths
        task_ids_stmt = select(Task.id).where(Task.class_id.in_(class_ids))
        result = await db.execute(
            select(Submission.file_path).where(Submission.task_id.in_(task_ids_stmt))
        )
        file_paths = [fp for (fp,) in result.all() if fp]

        await db.execute(delete(Submission).where(Submission.task_id.in_(task_ids_stmt)))

        # 4. Delete tasks
        await db.execute(delete(Task).where(Task.class_id.in_(class_ids)))

        # 5. Delete student users in admin's classes
        await db.execute(
            delete(User).where(User.class_id.in_(class_ids), User.role == "student")
        )

        # 6. Delete roster entries
        await db.execute(delete(StudentRoster).where(StudentRoster.class_id.in_(class_ids)))

        # 7. Delete classes
        await db.execute(delete(Class).where(Class.created_by == admin_id))

    # 8. Delete model configs
    await db.execute(delete(ModelConfig).where(ModelConfig.admin_id == admin_id))

    # 9. Delete backups
    await db.execute(delete(Backup).where(Backup.admin_id == admin_id))

    # 10. Delete the admin user
    await db.delete(admin)
    await db.commit()

    # Clean up files in MinIO
    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)

    return Response(status_code=204)
