import asyncio
import logging
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

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(
    prefix="/api/admin/classes/{class_id}",
    tags=["password-reset"],
)


# ---------------------------------------------------------------------------
# 辅助函数
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
# 公开接口：学生忘记密码
# ---------------------------------------------------------------------------


@public_router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info("忘记密码申请 — username=%s", req.username)

    # 根据用户名查找学生
    result = await db.execute(
        select(User).where(User.username == req.username, User.role == "student")
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("忘记密码申请失败 — 学号不存在, username=%s", req.username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到该学号对应的账号",
        )

    # 获取所有班级成员关系
    result = await db.execute(
        select(ClassMember.class_id).where(ClassMember.user_id == user.id)
    )
    class_ids = [row[0] for row in result.all()]

    if not class_ids:
        logger.warning("忘记密码申请失败 — 未加入班级, user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号尚未加入任何班级，请联系老师",
        )

    # 检查是否已有待处理的申请
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "pending",
        ).limit(1)
    )
    if result.scalar_one_or_none():
        logger.warning("忘记密码申请失败 — 已有待处理申请, user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已有申请在处理中，请等待老师审批",
        )

    # 为每个班级创建一条申请
    for class_id in class_ids:
        db.add(PasswordResetRequest(user_id=user.id, class_id=class_id))

    await db.commit()
    return ForgotPasswordResponse(message="申请已提交，请联系老师审批")


# ---------------------------------------------------------------------------
# 管理员：查看待处理申请
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
# 管理员：待处理申请计数（侧边栏徽章）
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
# 管理员：批准申请
# ---------------------------------------------------------------------------


@admin_router.post("/password-reset-requests/approve", response_model=PasswordResetApproveResponse)
async def approve_requests(
    class_id: uuid.UUID,
    req: PasswordResetApproveRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("批准密码重置申请 — class_id=%s, 数量=%d", class_id, len(req.request_ids))
    await _verify_class_ownership(class_id, admin, db)

    # 获取属于该班级且待处理的申请
    result = await db.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.id.in_(req.request_ids),
            PasswordResetRequest.class_id == class_id,
            PasswordResetRequest.status == "pending",
        )
    )
    requests = result.scalars().all()

    if not requests:
        logger.warning("批准密码重置失败 — 无可批准的申请, class_id=%s", class_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可批准的申请",
        )

    # 收集唯一用户 ID
    user_ids = list({r.user_id for r in requests})

    # 统一哈希密码（耗时操作只执行一次）
    new_hash = await asyncio.to_thread(hash_password, "123456")
    now = datetime.now(timezone.utc)

    # 重置密码
    result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = result.scalars().all()
    for user in users:
        user.password_hash = new_hash

    # 将这些用户的所有待处理申请标记为已批准（跨班级）
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
