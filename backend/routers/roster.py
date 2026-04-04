import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_admin
from models.class_ import Class
from models.roster import StudentRoster
from models.submission import Submission
from models.user import User
from schemas.roster import (
    RosterAddRequest, RosterBatchRequest,
    RosterItem, RosterListResponse, RosterBatchResponse,
)
from services.storage import storage_service

router = APIRouter(
    prefix="/api/admin/classes/{class_id}/roster",
    tags=["roster"],
)


async def _verify_class_ownership(
    class_id: uuid.UUID, admin: User, db: AsyncSession,
) -> Class:
    """Verify class exists and belongs to admin."""
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    return cls


@router.get("", response_model=RosterListResponse)
async def list_roster(
    class_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(StudentRoster).where(StudentRoster.class_id == class_id)
    )
    entries = result.scalars().all()

    # Check which students have registered in this class
    result = await db.execute(
        select(User.username).where(User.class_id == class_id, User.role == "student")
    )
    registered_usernames = {row for row in result.scalars().all()}

    items = [
        RosterItem(
            student_id=e.student_id,
            registered=e.student_id in registered_usernames,
        )
        for e in entries
    ]
    return RosterListResponse(items=items, total=len(items))


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_student(
    class_id: uuid.UUID,
    req: RosterAddRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(StudentRoster).where(
            StudentRoster.student_id == req.student_id,
            StudentRoster.class_id == class_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学号已在名单中",
        )

    entry = StudentRoster(student_id=req.student_id, class_id=class_id)
    db.add(entry)
    await db.commit()
    return {"student_id": req.student_id}


@router.post("/batch", response_model=RosterBatchResponse)
async def batch_import(
    class_id: uuid.UUID,
    req: RosterBatchRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(StudentRoster.student_id).where(
            StudentRoster.student_id.in_(req.student_ids),
            StudentRoster.class_id == class_id,
        )
    )
    existing_ids = {row for row in result.scalars().all()}

    added = 0
    duplicates = 0
    for sid in req.student_ids:
        if sid in existing_ids:
            duplicates += 1
        else:
            db.add(StudentRoster(student_id=sid, class_id=class_id))
            existing_ids.add(sid)
            added += 1
    await db.commit()
    return RosterBatchResponse(added=added, duplicates=duplicates)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    class_id: uuid.UUID,
    student_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(StudentRoster).where(
            StudentRoster.student_id == student_id,
            StudentRoster.class_id == class_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学号不在名单中",
        )

    # Find user record for this student in this class
    result = await db.execute(
        select(User).where(
            User.username == student_id,
            User.class_id == class_id,
            User.role == "student",
        )
    )
    user = result.scalar_one_or_none()

    file_paths: list[str] = []
    if user:
        # Cascade: delete submissions, then user
        result = await db.execute(
            select(Submission).where(Submission.student_id == user.id)
        )
        submissions = result.scalars().all()
        file_paths = [s.file_path for s in submissions if s.file_path]

        await db.execute(delete(Submission).where(Submission.student_id == user.id))
        await db.delete(user)

    await db.delete(entry)
    await db.commit()

    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)
