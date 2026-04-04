import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.class_ import Class
from models.class_member import ClassMember
from models.invite_code import InviteCode
from models.roster import StudentRoster
from models.refresh_token import RefreshToken
from auth.jwt import create_access_token, create_refresh_token, hash_refresh_token
from config import REFRESH_TOKEN_EXPIRE_DAYS


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Student registration
# ---------------------------------------------------------------------------


async def register_student(
    db: AsyncSession,
    student_id: str,
    college: str,
    password: str,
) -> User:
    """Register a new student account (no class association).

    display_name is left NULL — the student fills it in after first login.
    """
    result = await db.execute(
        select(User).where(User.username == student_id, User.role == "student")
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学号已被注册",
        )

    pw_hash = await asyncio.to_thread(hash_password, password)
    user = User(
        username=student_id,
        password_hash=pw_hash,
        role="student",
        college=college,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> dict[str, Any]:
    """Authenticate and return a routing dict.

    Return shape:
        {"type": "single_user", "user": User}                       — admin/super_admin or student with 1 class
        {"type": "no_class", "user": User}                          — student with 0 classes
        {"type": "multi_class", "user": User, "classes": [...]}     — student with N classes
    """
    result = await db.execute(select(User).where(User.username == username))
    candidates = result.scalars().all()
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # Match by password (handles student/admin same-name scenario)
    user = None
    for candidate in candidates:
        if await asyncio.to_thread(verify_password, password, candidate.password_hash):
            user = candidate
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    # Non-student: straightforward
    if user.role in ("admin", "super_admin"):
        return {"type": "single_user", "user": user}

    # Student: check class memberships
    memberships = await _get_student_classes(db, user.id)

    if len(memberships) == 0:
        return {"type": "no_class", "user": user}
    elif len(memberships) == 1:
        return {"type": "single_user", "user": user, "class_info": memberships[0]}
    else:
        return {"type": "multi_class", "user": user, "classes": memberships}


async def _get_student_classes(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Return list of {class_id, class_name, admin_name} for a student."""
    result = await db.execute(
        select(ClassMember.class_id).where(ClassMember.user_id == user_id)
    )
    class_ids = [row[0] for row in result.all()]
    if not class_ids:
        return []

    result = await db.execute(select(Class).where(Class.id.in_(class_ids)))
    classes = result.scalars().all()

    admin_ids = {c.created_by for c in classes}
    result = await db.execute(select(User).where(User.id.in_(admin_ids)))
    admin_map = {u.id: u.username for u in result.scalars().all()}

    return [
        {
            "class_id": c.id,
            "class_name": c.name,
            "admin_name": admin_map.get(c.created_by, ""),
        }
        for c in classes
    ]


# ---------------------------------------------------------------------------
# Class selection / switching / joining
# ---------------------------------------------------------------------------


async def select_class(
    db: AsyncSession, user_id: uuid.UUID, class_id: uuid.UUID
) -> dict[str, Any]:
    """Verify membership and issue tokens for the selected class.

    Returns {"access_token", "refresh_token", "class_id", "class_name", "admin_name", "role"}.
    """
    return await _issue_class_tokens(db, user_id, class_id)


async def join_class(
    db: AsyncSession, user_id: uuid.UUID, join_token: str
) -> dict[str, Any]:
    """Join a class via token. Returns token data like select_class."""
    result = await db.execute(
        select(Class).where(Class.join_token == join_token)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="班级 token 无效",
        )

    # Check duplicate membership
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.user_id == user_id,
            ClassMember.class_id == cls.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="你已在该班级中",
        )

    # Create membership
    db.add(ClassMember(user_id=user_id, class_id=cls.id))

    # Auto-match roster
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()
    result = await db.execute(
        select(StudentRoster).where(
            StudentRoster.student_id == user.username,
            StudentRoster.class_id == cls.id,
        )
    )
    # Roster match is informational only — no action needed beyond
    # the existence of the class_members record for the matching logic.

    await db.flush()

    return await _issue_class_tokens(db, user_id, cls.id)


async def switch_class(
    db: AsyncSession, user_id: uuid.UUID, class_id: uuid.UUID
) -> dict[str, Any]:
    """Switch to a different class. Verify membership, issue new tokens."""
    return await _issue_class_tokens(db, user_id, class_id)


async def _issue_class_tokens(
    db: AsyncSession, user_id: uuid.UUID, class_id: uuid.UUID
) -> dict[str, Any]:
    """Verify membership, fetch class info, issue access + refresh tokens."""
    # Verify membership
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.user_id == user_id,
            ClassMember.class_id == class_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="你不是该班级的成员",
        )

    # Fetch class + admin info
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one()
    result = await db.execute(select(User).where(User.id == cls.created_by))
    admin = result.scalar_one()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    access_token = create_access_token(
        sub=user.id, role=user.role, class_id=class_id,
        display_name=user.display_name,
    )
    refresh_token_raw = await create_refresh_token_record(
        db, user.id, class_id=class_id
    )
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_raw,
        "class_id": cls.id,
        "class_name": cls.name,
        "admin_name": admin.username,
        "role": user.role,
    }


# ---------------------------------------------------------------------------
# Password management
# ---------------------------------------------------------------------------


async def change_student_password(
    db: AsyncSession,
    user_id: uuid.UUID,
    current_password: str,
    new_password: str,
) -> int:
    """Change student password. Enforces max 3 changes. Returns new count."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
        )

    valid = await asyncio.to_thread(verify_password, current_password, user.password_hash)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )

    if user.password_change_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码修改次数已达上限",
        )

    user.password_hash = await asyncio.to_thread(hash_password, new_password)
    user.password_change_count += 1
    await db.commit()
    return user.password_change_count


async def update_student_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    display_name: str,
) -> str:
    """Update student display_name. Returns the updated value."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
        )

    display_name = display_name.strip()
    if not display_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="姓名不能为空",
        )

    user.display_name = display_name
    await db.commit()
    return display_name


async def get_student_classes(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Return all classes a student belongs to."""
    return await _get_student_classes(db, user_id)


# ---------------------------------------------------------------------------
# Refresh token management
# ---------------------------------------------------------------------------


async def create_refresh_token_record(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    class_id: uuid.UUID | None = None,
) -> str:
    """Generate a refresh token, store its hash (with class context), return raw token."""
    raw_token, token_hash = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        class_id=class_id,
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()
    return raw_token


async def refresh_access_token(db: AsyncSession, refresh_token_plain: str) -> str:
    """Validate a refresh token and issue a new access token.

    Reads class_id from the RefreshToken record. If the class no longer
    exists or the user is no longer a member, raises 401.
    """
    token_hash = hash_refresh_token(refresh_token_plain)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token 无效",
        )

    now = datetime.now(timezone.utc)
    if record.expires_at < now:
        await db.delete(record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token 已过期",
        )

    # Check user is_active
    user_result = await db.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    # Validate class context for students
    class_id = record.class_id
    if class_id and user.role == "student":
        # Check class still exists
        cls_result = await db.execute(select(Class).where(Class.id == class_id))
        if not cls_result.scalar_one_or_none():
            await db.delete(record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="班级已不存在，请重新选择班级",
            )
        # Check user is still a member
        mem_result = await db.execute(
            select(ClassMember).where(
                ClassMember.user_id == user.id,
                ClassMember.class_id == class_id,
            )
        )
        if not mem_result.scalar_one_or_none():
            await db.delete(record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="你已不是该班级的成员，请重新选择班级",
            )

    access_token = create_access_token(
        sub=user.id, role=user.role, class_id=class_id,
        display_name=user.display_name,
    )

    # Clean up expired tokens for this user
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == record.user_id,
            RefreshToken.expires_at < now,
        )
    )
    await db.commit()

    return access_token


async def revoke_refresh_token(db: AsyncSession, refresh_token_plain: str) -> None:
    """Delete a specific refresh token record."""
    token_hash = hash_refresh_token(refresh_token_plain)
    await db.execute(
        delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.commit()


async def revoke_all_user_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete all refresh tokens for a user."""
    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    await db.flush()


# ---------------------------------------------------------------------------
# Teacher registration via invite code
# ---------------------------------------------------------------------------


async def register_teacher(
    db: AsyncSession,
    invite_code: str,
    username: str,
    password: str,
) -> User:
    """Register a teacher using an invite code."""
    prefix = invite_code[:8]
    result = await db.execute(
        select(InviteCode).where(InviteCode.code_prefix == prefix)
    )
    candidates = result.scalars().all()

    matched_invite: InviteCode | None = None
    for candidate in candidates:
        valid = await asyncio.to_thread(
            verify_password, invite_code, candidate.code_hash
        )
        if valid:
            matched_invite = candidate
            break

    if not matched_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码无效",
        )

    existing = await db.execute(
        select(User).where(
            User.username == username,
            User.role.in_(("admin", "super_admin")),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在，请联系管理员。",
        )

    pw_hash = await asyncio.to_thread(hash_password, password)
    user = User(
        username=username,
        password_hash=pw_hash,
        role="admin",
        invite_code_id=matched_invite.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
