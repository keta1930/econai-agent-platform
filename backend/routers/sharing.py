from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.deps import require_student, require_admin
from models.user import User
from models.class_ import Class
from models.sharing import SharingTopic, TopicVote
from schemas.sharing import (
    MAX_VOTES_PER_STUDENT,
    TopicCreateRequest,
    TopicUpdateRequest,
    TopicSuggestRequest,
    TopicListItem,
    TopicListResponse,
    TopicMaterialsResponse,
    VoteResponse,
    AdminTopicListItem,
    AdminTopicListResponse,
)

# ---------------------------------------------------------------------------
# Student router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/sharing", tags=["sharing"])


async def _build_topic_items(
    db: AsyncSession, user_id: int, class_id: int,
    status_filter: str | None, *, include_materials: bool = False
) -> list[dict]:
    """Query topics and compute vote_count / current_user_voted."""
    stmt = select(SharingTopic).where(SharingTopic.class_id == class_id)
    if status_filter:
        stmt = stmt.where(SharingTopic.status == status_filter)
    result = await db.execute(stmt)
    topics = result.scalars().all()

    # Batch-load vote counts and user votes
    topic_ids = [t.id for t in topics]
    vote_counts: dict[int, int] = {}
    user_votes: set[int] = set()

    if topic_ids:
        result = await db.execute(
            select(TopicVote.topic_id, func.count(TopicVote.id))
            .where(TopicVote.topic_id.in_(topic_ids))
            .group_by(TopicVote.topic_id)
        )
        vote_counts = {tid: cnt for tid, cnt in result.all()}

        result = await db.execute(
            select(TopicVote.topic_id)
            .where(TopicVote.topic_id.in_(topic_ids), TopicVote.student_id == user_id)
        )
        user_votes = {row for row in result.scalars().all()}

    items = []
    for t in topics:
        vc = vote_counts.get(t.id, 0)
        item = {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "presenters": t.presenters,
            "session_number": t.session_number,
            "shared_at": t.shared_at,
            "has_materials": bool(t.materials_content),
            "vote_count": vc,
            "current_user_voted": t.id in user_votes,
            "is_student_submitted": t.submitted_by is not None,
            "submitted_by_name": "同学推荐" if t.submitted_by is not None else None,
        }
        if include_materials:
            item["materials_content"] = t.materials_content
        items.append(item)

    def sort_key(item: dict):
        s = item["status"]
        if s == "completed":
            return (0, -(item["session_number"] or 0))
        if s == "confirmed":
            return (1, 0)
        return (2, -item["vote_count"])

    items.sort(key=sort_key)
    return items


@router.get("/topics", response_model=TopicListResponse)
async def list_topics(
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    items = await _build_topic_items(db, user.id, user.class_id, status_filter)
    result = await db.execute(
        select(func.count(TopicVote.id)).where(TopicVote.student_id == user.id)
    )
    total_votes = result.scalar_one()
    return TopicListResponse(items=[TopicListItem(**i) for i in items], total_votes=total_votes)


@router.get("/topics/{topic_id}/materials", response_model=TopicMaterialsResponse)
async def get_topic_materials(
    topic_id: int,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharingTopic).where(SharingTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")
    if topic.class_id != user.class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")
    if topic.status != "completed" or not topic.materials_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="暂无素材")
    return TopicMaterialsResponse(
        topic_id=topic.id,
        title=topic.title,
        materials_content=topic.materials_content,
    )


@router.post("/topics/{topic_id}/vote", response_model=VoteResponse)
async def vote_topic(
    topic_id: int,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharingTopic).where(SharingTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")
    if topic.class_id != user.class_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作")
    if topic.status != "voting":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该主题不在投票中")

    result = await db.execute(
        select(func.count(TopicVote.id)).where(TopicVote.student_id == user.id)
    )
    current_vote_count = result.scalar_one()
    if current_vote_count >= MAX_VOTES_PER_STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多投 {MAX_VOTES_PER_STUDENT} 个主题",
        )

    vote = TopicVote(topic_id=topic_id, student_id=user.id)
    db.add(vote)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已投过票")
    await db.commit()

    result = await db.execute(
        select(func.count(TopicVote.id)).where(TopicVote.topic_id == topic_id)
    )
    count = result.scalar_one()
    return VoteResponse(vote_count=count)


@router.delete("/topics/{topic_id}/vote", response_model=VoteResponse)
async def unvote_topic(
    topic_id: int,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharingTopic).where(SharingTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")
    if topic.class_id != user.class_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作")
    if topic.status != "voting":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该主题不在投票中")

    result = await db.execute(
        select(TopicVote)
        .where(TopicVote.topic_id == topic_id, TopicVote.student_id == user.id)
    )
    vote = result.scalar_one_or_none()
    if not vote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未投过票")

    await db.delete(vote)
    await db.commit()

    result = await db.execute(
        select(func.count(TopicVote.id)).where(TopicVote.topic_id == topic_id)
    )
    count = result.scalar_one()
    return VoteResponse(vote_count=count)


@router.post("/topics/suggest", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def suggest_topic(
    req: TopicSuggestRequest,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标题不能为空")

    result = await db.execute(
        select(func.count(TopicVote.id)).where(TopicVote.student_id == user.id)
    )
    current_vote_count = result.scalar_one()
    if current_vote_count >= MAX_VOTES_PER_STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多投 {MAX_VOTES_PER_STUDENT} 个主题",
        )

    topic = SharingTopic(
        title=title,
        status="voting",
        submitted_by=user.id,
        class_id=user.class_id,
    )
    db.add(topic)
    await db.flush()

    vote = TopicVote(topic_id=topic.id, student_id=user.id)
    db.add(vote)
    await db.commit()

    return VoteResponse(vote_count=1)


# ---------------------------------------------------------------------------
# Admin router
# ---------------------------------------------------------------------------

admin_sharing_router = APIRouter(prefix="/api/admin/sharing", tags=["admin-sharing"])


async def _verify_topic_ownership(topic: SharingTopic, admin: User, db: AsyncSession) -> None:
    """Verify admin owns the class this topic belongs to."""
    result = await db.execute(
        select(Class).where(Class.id == topic.class_id, Class.created_by == admin.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")


@admin_sharing_router.get("/topics", response_model=AdminTopicListResponse)
async def admin_list_topics(
    status_filter: str | None = Query(None, alias="status"),
    class_id: int | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if class_id is not None:
        # Verify admin owns this class
        result = await db.execute(
            select(Class).where(Class.id == class_id, Class.created_by == admin.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")
        items = await _build_topic_items(db, admin.id, class_id, status_filter, include_materials=True)
    else:
        # Return topics across all admin's classes
        result = await db.execute(
            select(Class.id).where(Class.created_by == admin.id)
        )
        admin_class_ids = result.scalars().all()
        items = []
        for cid in admin_class_ids:
            items.extend(
                await _build_topic_items(db, admin.id, cid, status_filter, include_materials=True)
            )

    return AdminTopicListResponse(items=[AdminTopicListItem(**i) for i in items])


@admin_sharing_router.post("/topics", response_model=AdminTopicListItem, status_code=status.HTTP_201_CREATED)
async def admin_create_topic(
    req: TopicCreateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify admin owns the class
    result = await db.execute(
        select(Class).where(Class.id == req.class_id, Class.created_by == admin.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="班级不存在")

    if req.status == "completed":
        if not req.presenters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已分享状态需要填写汇报人",
            )
        if req.session_number is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已分享状态需要填写分享次数",
            )

    topic = SharingTopic(
        title=req.title,
        status=req.status,
        presenters=req.presenters,
        session_number=req.session_number,
        shared_at=req.shared_at,
        materials_content=req.materials_content,
        class_id=req.class_id,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return AdminTopicListItem(
        id=topic.id,
        title=topic.title,
        status=topic.status,
        presenters=topic.presenters,
        session_number=topic.session_number,
        shared_at=topic.shared_at,
        has_materials=bool(topic.materials_content),
        vote_count=0,
        current_user_voted=False,
        materials_content=topic.materials_content,
        is_student_submitted=topic.submitted_by is not None,
        submitted_by_name="同学推荐" if topic.submitted_by is not None else None,
    )


@admin_sharing_router.patch("/topics/{topic_id}", response_model=AdminTopicListItem)
async def admin_update_topic(
    topic_id: int,
    req: TopicUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharingTopic).where(SharingTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")

    await _verify_topic_ownership(topic, admin, db)

    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(topic, field, value)

    if topic.status == "completed":
        if not topic.presenters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已分享状态需要填写汇报人",
            )
        if topic.session_number is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已分享状态需要填写分享次数",
            )

    await db.commit()
    await db.refresh(topic)

    result = await db.execute(
        select(func.count(TopicVote.id)).where(TopicVote.topic_id == topic_id)
    )
    vote_count = result.scalar_one()
    return AdminTopicListItem(
        id=topic.id,
        title=topic.title,
        status=topic.status,
        presenters=topic.presenters,
        session_number=topic.session_number,
        shared_at=topic.shared_at,
        has_materials=bool(topic.materials_content),
        vote_count=vote_count,
        current_user_voted=False,
        materials_content=topic.materials_content,
        is_student_submitted=topic.submitted_by is not None,
        submitted_by_name="同学推荐" if topic.submitted_by is not None else None,
    )


@admin_sharing_router.delete("/topics/{topic_id}", status_code=204)
async def admin_delete_topic(
    topic_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharingTopic).where(SharingTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主题不存在")

    await _verify_topic_ownership(topic, admin, db)

    await db.delete(topic)
    await db.commit()
    return Response(status_code=204)
