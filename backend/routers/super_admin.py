import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_super_admin
from models.user import User
from models.class_ import Class
from schemas.super_admin import AdminCreateRequest, AdminResponse, AdminListResponse
from services.auth_service import hash_password

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
    class_counts: dict[int, int] = {}
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
        class_count=0,
        created_at=admin.created_at,
    )
