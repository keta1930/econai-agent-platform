import asyncio
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_super_admin, TokenPayload
from models.invite_code import InviteCode
from models.user import User
from schemas.invite_code import (
    InviteCodeCreateRequest,
    InviteCodeCreateResponse,
    InviteCodeListResponse,
    InviteCodeResponse,
)
from services.auth_service import hash_password, verify_password

router = APIRouter(prefix="/api/super-admin", tags=["invite-codes"])


def _generate_invite_code() -> str:
    return secrets.token_urlsafe(16)


@router.post(
    "/invite-codes",
    response_model=InviteCodeCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite_code(
    req: InviteCodeCreateRequest,
    _super: TokenPayload = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    raw_code = _generate_invite_code()
    code_hash = await asyncio.to_thread(hash_password, raw_code)

    invite = InviteCode(
        category=req.category,
        code_hash=code_hash,
        code_prefix=raw_code[:8],
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return InviteCodeCreateResponse(
        id=invite.id,
        category=invite.category,
        registered_count=0,
        created_at=invite.created_at,
        code=raw_code,
    )


@router.get("/invite-codes", response_model=InviteCodeListResponse)
async def list_invite_codes(
    _super: TokenPayload = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InviteCode).order_by(InviteCode.created_at.desc())
    )
    codes = result.scalars().all()

    # Batch count registered teachers per invite code
    registered_counts: dict[uuid.UUID, int] = {}
    if codes:
        code_ids = [c.id for c in codes]
        count_result = await db.execute(
            select(User.invite_code_id, func.count(User.id))
            .where(User.role == "admin", User.invite_code_id.in_(code_ids))
            .group_by(User.invite_code_id)
        )
        registered_counts = {cid: cnt for cid, cnt in count_result.all()}

    items = [
        InviteCodeResponse(
            id=code.id,
            category=code.category,
            registered_count=registered_counts.get(code.id, 0),
            created_at=code.created_at,
        )
        for code in codes
    ]
    return InviteCodeListResponse(items=items)


@router.delete(
    "/invite-codes/{code_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_invite_code(
    code_id: uuid.UUID,
    _super: TokenPayload = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InviteCode).where(InviteCode.id == code_id)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在",
        )

    await db.delete(invite)
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/invite-codes/{code_id}/regenerate",
    response_model=InviteCodeCreateResponse,
)
async def regenerate_invite_code(
    code_id: uuid.UUID,
    _super: TokenPayload = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InviteCode).where(InviteCode.id == code_id)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在",
        )

    raw_code = _generate_invite_code()
    invite.code_hash = await asyncio.to_thread(hash_password, raw_code)
    invite.code_prefix = raw_code[:8]

    await db.commit()
    await db.refresh(invite)

    # Count registered teachers for this invite code
    count_result = await db.execute(
        select(func.count(User.id)).where(
            User.role == "admin", User.invite_code_id == invite.id
        )
    )
    registered_count = count_result.scalar() or 0

    return InviteCodeCreateResponse(
        id=invite.id,
        category=invite.category,
        registered_count=registered_count,
        created_at=invite.created_at,
        code=raw_code,
    )
