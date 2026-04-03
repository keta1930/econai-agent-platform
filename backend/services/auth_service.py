import asyncio

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.class_ import Class
from models.roster import StudentRoster


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


async def register_student(
    db: AsyncSession,
    class_name: str,
    admin_name: str,
    student_id: str,
    password: str,
) -> User:
    # Step 1: find admin
    result = await db.execute(
        select(User).where(User.username == admin_name, User.role == "admin")
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在",
        )

    # Step 2: find class
    result = await db.execute(
        select(Class).where(Class.name == class_name, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班级不存在",
        )

    # Step 3: check roster
    result = await db.execute(
        select(StudentRoster).where(
            StudentRoster.student_id == student_id,
            StudentRoster.class_id == cls.id,
        )
    )
    roster_entry = result.scalar_one_or_none()
    if not roster_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号不在该班级名单中",
        )

    # Step 4: check existing registration
    result = await db.execute(
        select(User).where(
            User.username == student_id,
            User.class_id == cls.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学号已在此班级注册",
        )

    # Step 5: create user
    pw_hash = await asyncio.to_thread(hash_password, password)
    user = User(
        username=student_id,
        password_hash=pw_hash,
        role="student",
        class_id=cls.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | list[dict]:
    """Authenticate by username + password.

    Returns:
        User if exactly one match.
        list[dict] with class info if multiple matches.
        Raises 401 if zero matches.
    """
    result = await db.execute(select(User).where(User.username == username))
    candidates = result.scalars().all()
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    matched: list[User] = []
    for user in candidates:
        valid = await asyncio.to_thread(verify_password, password, user.password_hash)
        if valid:
            matched.append(user)

    if len(matched) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if len(matched) == 1:
        return matched[0]

    # If an admin/super_admin is among the matches, return them directly --
    # admin accounts don't participate in multi-class selection.
    for user in matched:
        if user.role in ("admin", "super_admin"):
            return user

    # Multiple student matches -- return class info for selection
    class_ids = [u.class_id for u in matched if u.class_id is not None]
    class_map: dict[int, Class] = {}
    if class_ids:
        result = await db.execute(select(Class).where(Class.id.in_(class_ids)))
        for cls in result.scalars().all():
            class_map[cls.id] = cls

    # Build admin name map
    admin_ids = {cls.created_by for cls in class_map.values()}
    admin_map: dict[int, str] = {}
    if admin_ids:
        result = await db.execute(select(User).where(User.id.in_(admin_ids)))
        for admin in result.scalars().all():
            admin_map[admin.id] = admin.username

    options = []
    for user in matched:
        if user.class_id and user.class_id in class_map:
            cls = class_map[user.class_id]
            options.append({
                "class_id": cls.id,
                "class_name": cls.name,
                "admin_name": admin_map.get(cls.created_by, ""),
            })
    return options


async def authenticate_user_with_class(
    db: AsyncSession, username: str, password: str, class_id: int
) -> User:
    """Authenticate with explicit class selection."""
    result = await db.execute(
        select(User).where(User.username == username, User.class_id == class_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    valid = await asyncio.to_thread(verify_password, password, user.password_hash)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return user
