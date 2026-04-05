from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.class_ import Class
from models.class_member import ClassMember
from models.roster import StudentRoster
from models.sharing import SharingTopic, TopicVote
from models.submission import Submission
from models.task import Task
from models.user import User
from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


async def _verify_class_ownership(
    class_id: uuid.UUID, ctx: ToolContext,
) -> Class | None:
    """Return the Class if it belongs to the admin, otherwise None."""
    result = await ctx.db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == ctx.admin_id)
    )
    return result.scalar_one_or_none()


def _resolve_class_id(args: dict, ctx: ToolContext) -> uuid.UUID | None:
    """Extract class_id from args, falling back to ctx.class_id."""
    raw = args.get("class_id") or ctx.class_id
    if raw is None:
        return None
    return uuid.UUID(str(raw)) if not isinstance(raw, uuid.UUID) else raw


# ---------------------------------------------------------------------------
# 1. list_classes
# ---------------------------------------------------------------------------

async def execute_list_classes(args: dict, ctx: ToolContext) -> str:
    result = await ctx.db.execute(
        select(Class).where(Class.created_by == ctx.admin_id).order_by(Class.created_at.desc())
    )
    classes = result.scalars().all()

    class_ids = [c.id for c in classes]
    student_counts: dict[uuid.UUID, int] = {}
    task_counts: dict[uuid.UUID, int] = {}

    if class_ids:
        result = await ctx.db.execute(
            select(ClassMember.class_id, func.count(ClassMember.id))
            .where(ClassMember.class_id.in_(class_ids))
            .group_by(ClassMember.class_id)
        )
        student_counts = {cid: cnt for cid, cnt in result.all()}

        result = await ctx.db.execute(
            select(Task.class_id, func.count(Task.id))
            .where(Task.class_id.in_(class_ids), Task.status == "published")
            .group_by(Task.class_id)
        )
        task_counts = {cid: cnt for cid, cnt in result.all()}

    items = [
        {
            "id": str(c.id),
            "name": c.name,
            "student_count": student_counts.get(c.id, 0),
            "task_count": task_counts.get(c.id, 0),
            "created_at": str(c.created_at),
        }
        for c in classes
    ]
    return _json({"classes": items})


# ---------------------------------------------------------------------------
# 2. list_tasks
# ---------------------------------------------------------------------------

async def execute_list_tasks(args: dict, ctx: ToolContext) -> str:
    class_id = _resolve_class_id(args, ctx)
    if class_id is None:
        return _json({"error": "请指定班级（class_id）"})

    if not await _verify_class_ownership(class_id, ctx):
        return _json({"error": "班级不存在或无权访问"})

    stmt = (
        select(Task)
        .where(Task.class_id == class_id)
        .order_by(Task.created_at.desc())
    )
    status_filter = args.get("status")
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)

    result = await ctx.db.execute(stmt)
    tasks = result.scalars().all()

    items = [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "created_at": str(t.created_at),
        }
        for t in tasks
    ]
    return _json({"tasks": items})


# ---------------------------------------------------------------------------
# 3. get_task_detail
# ---------------------------------------------------------------------------

async def execute_get_task_detail(args: dict, ctx: ToolContext) -> str:
    task_id = args.get("task_id")
    if not task_id:
        return _json({"error": "请指定作业 ID（task_id）"})

    result = await ctx.db.execute(
        select(Task).where(Task.id == uuid.UUID(str(task_id)))
    )
    task = result.scalar_one_or_none()
    if not task:
        return _json({"error": "作业不存在"})

    if not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该作业"})

    cls = await ctx.db.get(Class, task.class_id)
    return _json({
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "grading_criteria": task.grading_criteria,
        "status": task.status,
        "class_id": str(task.class_id),
        "class_name": cls.name if cls else "",
        "created_at": str(task.created_at),
    })


# ---------------------------------------------------------------------------
# 4. get_task_stats
# ---------------------------------------------------------------------------

async def execute_get_task_stats(args: dict, ctx: ToolContext) -> str:
    task_id = args.get("task_id")
    if not task_id:
        return _json({"error": "请指定作业 ID（task_id）"})

    result = await ctx.db.execute(
        select(Task).where(Task.id == uuid.UUID(str(task_id)))
    )
    task = result.scalar_one_or_none()
    if not task:
        return _json({"error": "作业不存在"})

    if not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该作业"})

    # Expected student count from roster
    result = await ctx.db.execute(
        select(func.count(StudentRoster.id)).where(StudentRoster.class_id == task.class_id)
    )
    total_students = result.scalar_one()

    # Submissions for this task
    result = await ctx.db.execute(
        select(Submission)
        .where(Submission.task_id == task.id)
        .order_by(Submission.student_id, Submission.version.desc())
    )
    submissions = result.scalars().all()

    # Group by student: latest version
    latest_by_student: dict[uuid.UUID, Submission] = {}
    for s in submissions:
        if s.student_id not in latest_by_student:
            latest_by_student[s.student_id] = s

    submitted_count = len(latest_by_student)
    rate = submitted_count / total_students if total_students > 0 else 0.0

    # Score distribution
    scores = [s.score for s in latest_by_student.values() if s.score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    # Fetch usernames for submitted students
    submitted_ids = list(latest_by_student.keys())
    username_map: dict[uuid.UUID, str] = {}
    if submitted_ids:
        result = await ctx.db.execute(
            select(User.id, User.username).where(User.id.in_(submitted_ids))
        )
        username_map = {uid: uname for uid, uname in result.all()}

    submission_items = [
        {
            "student_id": str(s.student_id),
            "username": username_map.get(s.student_id, ""),
            "version": s.version,
            "status": s.status,
            "score": s.score,
            "submitted_at": str(s.submitted_at),
        }
        for s in latest_by_student.values()
    ]

    return _json({
        "task_id": str(task.id),
        "task_title": task.title,
        "total_students": total_students,
        "submitted_count": submitted_count,
        "submission_rate": round(rate, 3),
        "average_score": round(avg_score, 1) if avg_score is not None else None,
        "submissions": submission_items,
    })


# ---------------------------------------------------------------------------
# 5. list_roster
# ---------------------------------------------------------------------------

async def execute_list_roster(args: dict, ctx: ToolContext) -> str:
    class_id = _resolve_class_id(args, ctx)
    if class_id is None:
        return _json({"error": "请指定班级（class_id）"})

    if not await _verify_class_ownership(class_id, ctx):
        return _json({"error": "班级不存在或无权访问"})

    # Expected roster
    result = await ctx.db.execute(
        select(StudentRoster).where(StudentRoster.class_id == class_id)
    )
    roster_entries = result.scalars().all()

    # Actual registered students
    result = await ctx.db.execute(
        select(User, ClassMember.joined_at)
        .join(ClassMember, ClassMember.user_id == User.id)
        .where(ClassMember.class_id == class_id, User.role == "student")
    )
    actual_rows = result.all()

    registered_usernames = {user.username for user, _ in actual_rows}

    expected = [
        {"student_id": e.student_id, "matched": e.student_id in registered_usernames}
        for e in roster_entries
    ]
    actual = [
        {
            "user_id": str(user.id),
            "student_id": user.username,
            "display_name": user.display_name,
            "joined_at": str(joined_at),
        }
        for user, joined_at in actual_rows
    ]

    return _json({
        "expected_count": len(expected),
        "actual_count": len(actual),
        "expected": expected,
        "actual": actual,
    })


# ---------------------------------------------------------------------------
# 6. get_student_submissions
# ---------------------------------------------------------------------------

async def execute_get_student_submissions(args: dict, ctx: ToolContext) -> str:
    student_id_raw = args.get("student_id")
    if not student_id_raw:
        return _json({"error": "请指定学生 ID（student_id）"})

    student_id = uuid.UUID(str(student_id_raw))

    # Verify student is in one of the admin's classes
    result = await ctx.db.execute(
        select(ClassMember).where(
            ClassMember.user_id == student_id,
            ClassMember.class_id.in_(
                select(Class.id).where(Class.created_by == ctx.admin_id)
            ),
        )
    )
    if not result.first():
        return _json({"error": "学生不存在或不在您的班级中"})

    admin_class_ids = select(Class.id).where(Class.created_by == ctx.admin_id)
    stmt = (
        select(Submission)
        .join(Task, Submission.task_id == Task.id)
        .where(Submission.student_id == student_id, Task.class_id.in_(admin_class_ids))
        .order_by(Submission.submitted_at.desc())
    )
    task_id_raw = args.get("task_id")
    if task_id_raw:
        stmt = stmt.where(Submission.task_id == uuid.UUID(str(task_id_raw)))

    result = await ctx.db.execute(stmt)
    submissions = result.scalars().all()

    # Build task title map
    task_ids = list({s.task_id for s in submissions})
    task_map: dict[uuid.UUID, str] = {}
    if task_ids:
        result = await ctx.db.execute(
            select(Task.id, Task.title).where(Task.id.in_(task_ids))
        )
        task_map = {tid: title for tid, title in result.all()}

    items = [
        {
            "id": str(s.id),
            "task_id": str(s.task_id),
            "task_title": task_map.get(s.task_id, ""),
            "version": s.version,
            "content_type": s.content_type,
            "status": s.status,
            "score": s.score,
            "suggestion": s.suggestion,
            "submitted_at": str(s.submitted_at),
        }
        for s in submissions
    ]
    return _json({"submissions": items})


# ---------------------------------------------------------------------------
# 7. get_submission_content
# ---------------------------------------------------------------------------

async def execute_get_submission_content(args: dict, ctx: ToolContext) -> str:
    submission_id_raw = args.get("submission_id")
    if not submission_id_raw:
        return _json({"error": "请指定提交 ID（submission_id）"})

    result = await ctx.db.execute(
        select(Submission).where(Submission.id == uuid.UUID(str(submission_id_raw)))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return _json({"error": "提交记录不存在"})

    # Verify admin owns the task's class
    result = await ctx.db.execute(select(Task).where(Task.id == submission.task_id))
    task = result.scalar_one_or_none()
    if not task or not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该提交"})

    if submission.content_type == "image":
        return _json({
            "submission_id": str(submission.id),
            "content_type": "image",
            "message": "该提交为图片类型，无法在对话中展示具体内容",
        })

    # Read text content from MinIO
    import asyncio
    from services.storage import storage_service

    try:
        text_content = await asyncio.to_thread(storage_service.get_text, submission.file_path)
    except Exception:
        return _json({"error": "提交文件不存在或无法读取"})

    return _json({
        "submission_id": str(submission.id),
        "content_type": submission.content_type,
        "content": text_content,
    })


# ---------------------------------------------------------------------------
# 8. list_sharing_topics
# ---------------------------------------------------------------------------

async def execute_list_sharing_topics(args: dict, ctx: ToolContext) -> str:
    class_id = _resolve_class_id(args, ctx)
    if class_id is None:
        return _json({"error": "请指定班级（class_id）"})

    if not await _verify_class_ownership(class_id, ctx):
        return _json({"error": "班级不存在或无权访问"})

    result = await ctx.db.execute(
        select(SharingTopic).where(SharingTopic.class_id == class_id)
    )
    topics = result.scalars().all()

    # Batch vote counts
    topic_ids = [t.id for t in topics]
    vote_counts: dict[uuid.UUID, int] = {}
    if topic_ids:
        result = await ctx.db.execute(
            select(TopicVote.topic_id, func.count(TopicVote.id))
            .where(TopicVote.topic_id.in_(topic_ids))
            .group_by(TopicVote.topic_id)
        )
        vote_counts = {tid: cnt for tid, cnt in result.all()}

    items = [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "presenters": t.presenters,
            "session_number": t.session_number,
            "vote_count": vote_counts.get(t.id, 0),
        }
        for t in topics
    ]
    return _json({"topics": items})


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_query_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="list_classes",
            description="获取教师管理的所有班级列表，包含班级名称、学生数和作业数。",
            parameters={"type": "object", "properties": {}, "required": []},
        ),
        execute=execute_list_classes,
        display_name="获取班级列表",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="list_tasks",
            description="查询指定班级的作业列表。可选按状态（draft/published）过滤。",
            parameters={
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "班级 ID（UUID）",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                        "description": "作业状态过滤",
                    },
                },
                "required": ["class_id"],
            },
        ),
        execute=execute_list_tasks,
        display_name="查询作业列表",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="get_task_detail",
            description="获取作业详情，包含标题、描述、评分标准和状态。",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "作业 ID（UUID）",
                    },
                },
                "required": ["task_id"],
            },
        ),
        execute=execute_get_task_detail,
        display_name="获取作业详情",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="get_task_stats",
            description="查询作业的提交统计，包含提交率、平均分和每个学生的提交状态。",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "作业 ID（UUID）",
                    },
                },
                "required": ["task_id"],
            },
        ),
        execute=execute_get_task_stats,
        display_name="查询作业统计",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="list_roster",
            description="获取指定班级的学生名单，包含预期名单和已注册学生列表。",
            parameters={
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "班级 ID（UUID）",
                    },
                },
                "required": ["class_id"],
            },
        ),
        execute=execute_list_roster,
        display_name="获取学生名单",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="get_student_submissions",
            description="查看某个学生的提交历史，可选按作业过滤。",
            parameters={
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "学生的用户 ID（UUID）",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "作业 ID（UUID），可选，不填则返回该学生所有提交",
                    },
                },
                "required": ["student_id"],
            },
        ),
        execute=execute_get_student_submissions,
        display_name="查看学生提交",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="get_submission_content",
            description="读取某次提交的具体内容（文本/文件内容）。图片类型提交无法读取。",
            parameters={
                "type": "object",
                "properties": {
                    "submission_id": {
                        "type": "string",
                        "description": "提交记录 ID（UUID）",
                    },
                },
                "required": ["submission_id"],
            },
        ),
        execute=execute_get_submission_content,
        display_name="读取提交内容",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="list_sharing_topics",
            description="查询指定班级的分享主题列表，包含标题、状态和投票数。",
            parameters={
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "班级 ID（UUID）",
                    },
                },
                "required": ["class_id"],
            },
        ),
        execute=execute_list_sharing_topics,
        display_name="查询分享主题",
    ))
