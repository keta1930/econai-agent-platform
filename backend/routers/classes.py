import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_admin, TokenPayload
from models.class_ import Class
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

    # Batch count students per class
    class_ids = [c.id for c in classes]
    student_counts: dict[uuid.UUID, int] = {}
    if class_ids:
        result = await db.execute(
            select(User.class_id, func.count(User.id))
            .where(User.class_id.in_(class_ids), User.role == "student")
            .group_by(User.class_id)
        )
        student_counts = {cid: cnt for cid, cnt in result.all()}

    items = [
        ClassResponse(
            id=c.id,
            name=c.name,
            student_count=student_counts.get(c.id, 0),
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
    # Check uniqueness within admin's classes
    result = await db.execute(
        select(Class).where(Class.name == req.name, Class.created_by == admin.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该班级名称已存在",
        )

    cls = Class(name=req.name, created_by=admin.id)
    db.add(cls)
    await db.commit()
    await db.refresh(cls)
    return ClassResponse(id=cls.id, name=cls.name, student_count=0, created_at=cls.created_at)


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")

    # Cascade delete: topic_votes -> sharing_topics -> submissions (+ files) -> tasks -> users -> roster -> class

    # 1. Delete topic_votes for topics in this class
    topic_ids_stmt = select(SharingTopic.id).where(SharingTopic.class_id == class_id)
    await db.execute(delete(TopicVote).where(TopicVote.topic_id.in_(topic_ids_stmt)))

    # 2. Delete sharing_topics
    await db.execute(delete(SharingTopic).where(SharingTopic.class_id == class_id))

    # 3. Delete submissions + collect file paths for cleanup
    task_ids_stmt = select(Task.id).where(Task.class_id == class_id)
    result = await db.execute(
        select(Submission.file_path).where(Submission.task_id.in_(task_ids_stmt))
    )
    file_paths = [fp for (fp,) in result.all() if fp]

    await db.execute(delete(Submission).where(Submission.task_id.in_(task_ids_stmt)))

    # 4. Delete tasks
    await db.execute(delete(Task).where(Task.class_id == class_id))

    # 5. Delete student users in this class
    await db.execute(
        delete(User).where(User.class_id == class_id, User.role == "student")
    )

    # 6. Delete roster entries
    await db.execute(delete(StudentRoster).where(StudentRoster.class_id == class_id))

    # 7. Delete the class
    await db.delete(cls)
    await db.commit()

    # Clean up files in MinIO
    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)

    return Response(status_code=204)
