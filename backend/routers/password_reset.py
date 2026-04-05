import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_admin, TokenPayload
from models.class_ import Class
from models.class_member import ClassMember
from models.password_reset_request import PasswordResetRequest
from models.user import User
from schemas.password_reset import (
    ForgotPasswordRequest, ForgotPasswordResponse,
    PasswordResetListResponse, PasswordResetRequestItem,
    PasswordResetCountResponse,
    PasswordResetApproveRequest, PasswordResetApproveResponse,
)
from services.auth_service import hash_password

public_router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(
    prefix="/api/admin/classes/{class_id}",
    tags=["password-reset"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _verify_class_ownership(
    class_id: uuid.UUID, admin: TokenPayload, db: AsyncSession,
) -> Class:
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    return cls


# ---------------------------------------------------------------------------
# Public: student forgot password
# ---------------------------------------------------------------------------


@public_router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Find student by username
    result = await db.execute(
        select(User).where(User.username == req.username, User.role == "student")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到该学号对应的账号",
        )

    # Get all class memberships
    result = await db.execute(
        select(ClassMember.class_id).where(ClassMember.user_id == user.id)
    )
    class_ids = [row[0] for row in result.all()]

    if not class_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号尚未加入任何班级，请联系老师",
        )

    # Check for existing pending requests
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "pending",
        ).limit(1)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已有申请在处理中，请等待老师审批",
        )

    # Create one request per class
    for class_id in class_ids:
        db.add(PasswordResetRequest(user_id=user.id, class_id=class_id))

    await db.commit()
    return ForgotPasswordResponse(message="申请已提交，请联系老师审批")


# ---------------------------------------------------------------------------
# Admin: list pending requests
# ---------------------------------------------------------------------------


@admin_router.get("/password-reset-requests", response_model=PasswordResetListResponse)
async def list_requests(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(PasswordResetRequest, User.username, User.display_name)
        .join(User, PasswordResetRequest.user_id == User.id)
        .where(
            PasswordResetRequest.class_id == class_id,
            PasswordResetRequest.status == "pending",
        )
        .order_by(PasswordResetRequest.created_at.desc())
    )
    rows = result.all()

    items = [
        PasswordResetRequestItem(
            id=req.id,
            user_id=req.user_id,
            username=username,
            display_name=display_name,
            created_at=req.created_at,
        )
        for req, username, display_name in rows
    ]
    return PasswordResetListResponse(items=items)


# ---------------------------------------------------------------------------
# Admin: count pending requests (for sidebar badge)
# ---------------------------------------------------------------------------


@admin_router.get("/password-reset-requests/count", response_model=PasswordResetCountResponse)
async def count_requests(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(sa_func.count()).select_from(PasswordResetRequest).where(
            PasswordResetRequest.class_id == class_id,
            PasswordResetRequest.status == "pending",
        )
    )
    count = result.scalar_one()
    return PasswordResetCountResponse(count=count)


# ---------------------------------------------------------------------------
# Admin: approve requests
# ---------------------------------------------------------------------------


@admin_router.post("/password-reset-requests/approve", response_model=PasswordResetApproveResponse)
async def approve_requests(
    class_id: uuid.UUID,
    req: PasswordResetApproveRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    # Fetch requested records, verify they belong to this class and are pending
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.id.in_(req.request_ids),
            PasswordResetRequest.class_id == class_id,
            PasswordResetRequest.status == "pending",
        )
    )
    requests = result.scalars().all()

    if not requests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可批准的申请",
        )

    # Collect unique user_ids
    user_ids = list({r.user_id for r in requests})

    # Hash password once (expensive operation)
    new_hash = await asyncio.to_thread(hash_password, "123456")
    now = datetime.now(timezone.utc)

    # Reset passwords
    result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = result.scalars().all()
    for user in users:
        user.password_hash = new_hash

    # Mark ALL pending requests for these users as approved (cross-class)
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id.in_(user_ids),
            PasswordResetRequest.status == "pending",
        )
    )
    all_pending = result.scalars().all()
    for pending_req in all_pending:
        pending_req.status = "approved"
        pending_req.resolved_at = now

    await db.commit()
    return PasswordResetApproveResponse(approved_count=len(user_ids))
