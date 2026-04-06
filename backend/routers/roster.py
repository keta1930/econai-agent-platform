import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_admin, TokenPayload
from models.class_ import Class
from models.class_member import ClassMember
from models.roster import StudentRoster
from models.submission import Submission
from models.task import Task
from models.user import User
from models.sharing import SharingTopic, TopicVote
from schemas.roster import (
    RosterAddRequest, RosterBatchRequest, RosterBatchResponse,
    RosterListResponse, ExpectedRosterItem, ActualRosterItem,
    ResetStudentPasswordRequest,
    RosterBatchDeleteRequest, RosterBatchDeleteResponse,
    MemberBatchRemoveRequest, MemberBatchRemoveResponse,
)
from services.auth_service import hash_password
from services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/classes/{class_id}",
    tags=["roster"],
)


async def _verify_class_ownership(
    class_id: uuid.UUID, admin: TokenPayload, db: AsyncSession,
) -> Class:
    """验证班级存在且属于该管理员。"""
    result = await db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == admin.id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
    return cls


@router.get("/roster", response_model=RosterListResponse)
async def list_roster(
    class_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _verify_class_ownership(class_id, admin, db)

    # 学生名单条目
    result = await db.execute(
        select(StudentRoster).where(StudentRoster.class_id == class_id)
    )
    roster_entries = result.scalars().all()

    # 已注册学生（班级成员 JOIN 用户表）
    result = await db.execute(
        select(User, ClassMember.joined_at)
        .join(ClassMember, ClassMember.user_id == User.id)
        .where(ClassMember.class_id == class_id, User.role == "student")
    )
    actual_rows = result.all()

    # 构建已注册用户名集合用于匹配
    registered_usernames = {user.username for user, _ in actual_rows}

    expected = [
        ExpectedRosterItem(
            student_id=e.student_id,
            matched=e.student_id in registered_usernames,
        )
        for e in roster_entries
    ]
    actual = [
        ActualRosterItem(
            user_id=user.id,
            student_id=user.username,
            display_name=user.display_name,
            joined_at=joined_at,
        )
        for user, joined_at in actual_rows
    ]

    return RosterListResponse(expected=expected, actual=actual)


@router.post("/roster", status_code=status.HTTP_201_CREATED)
async def add_student(
    class_id: uuid.UUID,
    req: RosterAddRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("添加学生到名单 — class_id=%s, student_id=%s", class_id, req.student_id)
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(StudentRoster).where(
            StudentRoster.student_id == req.student_id,
            StudentRoster.class_id == class_id,
        )
    )
    if result.scalar_one_or_none():
        logger.warning("添加学生失败 — 学号已存在, student_id=%s", req.student_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该学号已在名单中",
        )

    entry = StudentRoster(student_id=req.student_id, class_id=class_id)
    db.add(entry)
    await db.commit()
    return {"student_id": req.student_id}


@router.post("/roster/batch", response_model=RosterBatchResponse)
async def batch_import(
    class_id: uuid.UUID,
    req: RosterBatchRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info("批量导入学生名单 — class_id=%s, 数量=%d", class_id, len(req.student_ids))
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


@router.delete("/roster/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    class_id: uuid.UUID,
    student_id: str,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """从班级名单中删除学号。"""
    logger.info("删除名单学号 — class_id=%s, student_id=%s", class_id, student_id)
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        select(StudentRoster).where(
            StudentRoster.student_id == student_id,
            StudentRoster.class_id == class_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        logger.warning("删除名单学号失败 — 学号不存在, student_id=%s", student_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学号不在名单中",
        )

    await db.delete(entry)
    await db.commit()


@router.post("/roster/batch-delete", response_model=RosterBatchDeleteResponse)
async def batch_delete_students(
    class_id: uuid.UUID,
    req: RosterBatchDeleteRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量删除名单学号。"""
    logger.info("批量删除名单学号 — class_id=%s, 数量=%d", class_id, len(req.student_ids))
    await _verify_class_ownership(class_id, admin, db)

    result = await db.execute(
        delete(StudentRoster).where(
            StudentRoster.class_id == class_id,
            StudentRoster.student_id.in_(req.student_ids),
        )
    )
    await db.commit()
    return RosterBatchDeleteResponse(deleted=result.rowcount)


@router.post("/members/batch-remove", response_model=MemberBatchRemoveResponse)
async def batch_remove_members(
    class_id: uuid.UUID,
    req: MemberBatchRemoveRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量移除班级成员，删除成员关系及班级内数据。"""
    logger.info("批量移除班级成员 — class_id=%s, 数量=%d", class_id, len(req.user_ids))
    await _verify_class_ownership(class_id, admin, db)

    # 验证哪些 user_id 确实是该班级的成员
    result = await db.execute(
        select(ClassMember.user_id).where(
            ClassMember.class_id == class_id,
            ClassMember.user_id.in_(req.user_ids),
        )
    )
    verified_ids = [row for row in result.scalars().all()]
    if not verified_ids:
        return MemberBatchRemoveResponse(removed=0)

    # 收集提交记录的文件路径用于清理存储
    task_ids_stmt = select(Task.id).where(Task.class_id == class_id)
    result = await db.execute(
        select(Submission).where(
            Submission.student_id.in_(verified_ids),
            Submission.task_id.in_(task_ids_stmt),
        )
    )
    submissions = result.scalars().all()
    file_paths = [s.file_path for s in submissions if s.file_path]

    # 删除提交记录
    if submissions:
        await db.execute(
            delete(Submission).where(
                Submission.student_id.in_(verified_ids),
                Submission.task_id.in_(task_ids_stmt),
            )
        )

    # 删除投票记录
    topic_ids_stmt = select(SharingTopic.id).where(SharingTopic.class_id == class_id)
    await db.execute(
        delete(TopicVote).where(
            TopicVote.student_id.in_(verified_ids),
            TopicVote.topic_id.in_(topic_ids_stmt),
        )
    )

    # 删除班级成员关系
    await db.execute(
        delete(ClassMember).where(
            ClassMember.class_id == class_id,
            ClassMember.user_id.in_(verified_ids),
        )
    )

    await db.commit()

    # 清理 MinIO 中的文件
    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)

    return MemberBatchRemoveResponse(removed=len(verified_ids))


@router.post("/roster/reset-password")
async def reset_student_password(
    class_id: uuid.UUID,
    req: ResetStudentPasswordRequest,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置学生密码（教师发起，不计入修改次数限制）。"""
    logger.info("重置学生密码 — class_id=%s, user_id=%s", class_id, req.user_id)
    await _verify_class_ownership(class_id, admin, db)

    # 验证用户是该班级成员
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.user_id == req.user_id,
            ClassMember.class_id == class_id,
        )
    )
    if not result.scalar_one_or_none():
        logger.warning("重置学生密码失败 — 学生不在班级中, user_id=%s", req.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该学生不在此班级中",
        )

    result = await db.execute(select(User).where(User.id == req.user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("重置学生密码失败 — 用户不存在, user_id=%s", req.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    user.password_hash = await asyncio.to_thread(hash_password, req.new_password)
    await db.commit()
    return {"message": "密码已重置"}


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    class_id: uuid.UUID,
    user_id: uuid.UUID,
    admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """移除班级成员，删除成员关系及班级内提交记录。"""
    logger.info("移除班级成员 — class_id=%s, user_id=%s", class_id, user_id)
    await _verify_class_ownership(class_id, admin, db)

    # 验证成员关系存在
    result = await db.execute(
        select(ClassMember).where(
            ClassMember.user_id == user_id,
            ClassMember.class_id == class_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        logger.warning("移除班级成员失败 — 学生不在班级中, user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该学生不在此班级中",
        )

    # 收集该学生在该班级任务下的提交记录
    task_ids_stmt = select(Task.id).where(Task.class_id == class_id)
    result = await db.execute(
        select(Submission).where(
            Submission.student_id == user_id,
            Submission.task_id.in_(task_ids_stmt),
        )
    )
    submissions = result.scalars().all()
    file_paths = [s.file_path for s in submissions if s.file_path]

    # 删除提交记录
    if submissions:
        await db.execute(
            delete(Submission).where(
                Submission.student_id == user_id,
                Submission.task_id.in_(task_ids_stmt),
            )
        )

    # 删除该班级下的投票记录
    topic_ids_stmt = select(SharingTopic.id).where(SharingTopic.class_id == class_id)
    await db.execute(
        delete(TopicVote).where(
            TopicVote.student_id == user_id,
            TopicVote.topic_id.in_(topic_ids_stmt),
        )
    )

    # 删除班级成员关系
    await db.delete(member)
    await db.commit()

    # 清理 MinIO 中的文件
    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)
