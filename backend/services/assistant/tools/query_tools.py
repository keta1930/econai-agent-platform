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
# 1. list_classes (unchanged)
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
# 2. query_class — merged from list_tasks + list_roster + list_sharing_topics
# ---------------------------------------------------------------------------

async def _query_tasks(class_id: uuid.UUID, args: dict, ctx: ToolContext) -> str:
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


async def _query_roster(class_id: uuid.UUID, ctx: ToolContext) -> str:
    result = await ctx.db.execute(
        select(StudentRoster).where(StudentRoster.class_id == class_id)
    )
    roster_entries = result.scalars().all()

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


async def _query_topics(class_id: uuid.UUID, ctx: ToolContext) -> str:
    result = await ctx.db.execute(
        select(SharingTopic).where(SharingTopic.class_id == class_id)
    )
    topics = result.scalars().all()

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


_ENTITY_DISPATCHERS = {
    "tasks": lambda class_id, args, ctx: _query_tasks(class_id, args, ctx),
    "roster": lambda class_id, args, ctx: _query_roster(class_id, ctx),
    "topics": lambda class_id, args, ctx: _query_topics(class_id, ctx),
}


async def execute_query_class(args: dict, ctx: ToolContext) -> str:
    class_id = _resolve_class_id(args, ctx)
    if class_id is None:
        return _json({"error": "请指定班级（class_id）"})

    if not await _verify_class_ownership(class_id, ctx):
        return _json({"error": "班级不存在或无权访问"})

    entity = args.get("entity")
    dispatcher = _ENTITY_DISPATCHERS.get(entity)  # type: ignore[arg-type]
    if dispatcher is None:
        return _json({"error": f"不支持的查询类型: {entity}，可选: tasks / roster / topics"})

    return await dispatcher(class_id, args, ctx)


# ---------------------------------------------------------------------------
# 3. get_task — merged from get_task_detail + get_task_stats
# ---------------------------------------------------------------------------

async def execute_get_task(args: dict, ctx: ToolContext) -> str:
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
    data: dict = {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "grading_criteria": task.grading_criteria,
        "learning_resources": task.learning_resources,
        "status": task.status,
        "class_id": str(task.class_id),
        "class_name": cls.name if cls else "",
        "created_at": str(task.created_at),
    }

    if args.get("include_stats"):
        # Total expected students from roster
        result = await ctx.db.execute(
            select(func.count(StudentRoster.id)).where(StudentRoster.class_id == task.class_id)
        )
        total_students = result.scalar_one()

        # All submissions, ordered for latest-version extraction
        result = await ctx.db.execute(
            select(Submission)
            .where(Submission.task_id == task.id)
            .order_by(Submission.student_id, Submission.version.desc())
        )
        submissions = result.scalars().all()

        # Keep only latest version per student
        latest_by_student: dict[uuid.UUID, Submission] = {}
        for s in submissions:
            if s.student_id not in latest_by_student:
                latest_by_student[s.student_id] = s

        submitted_count = len(latest_by_student)
        rate = submitted_count / total_students if total_students > 0 else 0.0

        scores = [s.score for s in latest_by_student.values() if s.score is not None]
        avg_score = sum(scores) / len(scores) if scores else None

        # Resolve usernames
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

        data.update({
            "total_students": total_students,
            "submitted_count": submitted_count,
            "submission_rate": round(rate, 3),
            "average_score": round(avg_score, 1) if avg_score is not None else None,
            "submissions": submission_items,
        })

    return _json(data)


# ---------------------------------------------------------------------------
# 4. query_submissions — merged from get_student_submissions + get_submission_content
# ---------------------------------------------------------------------------

async def _query_single_submission(
    submission_id: uuid.UUID, include_content: bool, ctx: ToolContext,
) -> str:
    result = await ctx.db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return _json({"error": "提交记录不存在"})

    # Verify ownership via task's class
    result = await ctx.db.execute(select(Task).where(Task.id == submission.task_id))
    task = result.scalar_one_or_none()
    if not task or not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该提交"})

    data: dict = {
        "id": str(submission.id),
        "task_id": str(submission.task_id),
        "task_title": task.title,
        "student_id": str(submission.student_id),
        "version": submission.version,
        "content_type": submission.content_type,
        "status": submission.status,
        "score": submission.score,
        "suggestion": submission.suggestion,
        "submitted_at": str(submission.submitted_at),
    }

    if include_content:
        if submission.content_type == "image":
            data["message"] = "该提交为图片类型，无法在对话中展示具体内容"
        else:
            import asyncio
            from services.storage import storage_service

            try:
                text_content = await asyncio.to_thread(storage_service.get_text, submission.file_path)
                data["content"] = text_content
            except Exception:
                data["content_error"] = "提交文件不存在或无法读取"

    return _json(data)


async def _query_submissions_by_student(
    student_id: uuid.UUID, task_id: uuid.UUID | None, ctx: ToolContext,
) -> str:
    # Verify student belongs to one of admin's classes
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
    if task_id is not None:
        stmt = stmt.where(Submission.task_id == task_id)

    result = await ctx.db.execute(stmt)
    submissions = result.scalars().all()

    # Resolve task titles
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


async def _query_submissions_by_task(task_id: uuid.UUID, ctx: ToolContext) -> str:
    result = await ctx.db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return _json({"error": "作业不存在"})

    if not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该作业"})

    result = await ctx.db.execute(
        select(Submission)
        .where(Submission.task_id == task_id)
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()

    # Resolve usernames
    student_ids = list({s.student_id for s in submissions})
    username_map: dict[uuid.UUID, str] = {}
    if student_ids:
        result = await ctx.db.execute(
            select(User.id, User.username).where(User.id.in_(student_ids))
        )
        username_map = {uid: uname for uid, uname in result.all()}

    items = [
        {
            "id": str(s.id),
            "student_id": str(s.student_id),
            "username": username_map.get(s.student_id, ""),
            "version": s.version,
            "content_type": s.content_type,
            "status": s.status,
            "score": s.score,
            "submitted_at": str(s.submitted_at),
        }
        for s in submissions
    ]
    return _json({"task_title": task.title, "submissions": items})


async def execute_query_submissions(args: dict, ctx: ToolContext) -> str:
    submission_id_raw = args.get("submission_id")
    student_id_raw = args.get("student_id")
    task_id_raw = args.get("task_id")

    if not any([submission_id_raw, student_id_raw, task_id_raw]):
        return _json({"error": "请至少指定 submission_id、student_id 或 task_id 中的一个"})

    # Priority: submission_id > student_id > task_id
    if submission_id_raw:
        include_content = bool(args.get("include_content"))
        return await _query_single_submission(
            uuid.UUID(str(submission_id_raw)), include_content, ctx,
        )

    if student_id_raw:
        task_id = uuid.UUID(str(task_id_raw)) if task_id_raw else None
        return await _query_submissions_by_student(
            uuid.UUID(str(student_id_raw)), task_id, ctx,
        )

    # Only task_id provided
    return await _query_submissions_by_task(uuid.UUID(str(task_id_raw)), ctx)


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
            name="query_class",
            description=(
                "查询指定班级的数据。通过 entity 参数选择查询类型："
                "tasks（作业列表，可选按 status 过滤）、"
                "roster（学生名单，含预期与已注册对比）、"
                "topics（分享主题列表，含投票数）。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "班级 ID（UUID）",
                    },
                    "entity": {
                        "type": "string",
                        "enum": ["tasks", "roster", "topics"],
                        "description": "查询类型",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "published"],
                        "description": "作业状态过滤，仅 entity=tasks 时有效",
                    },
                },
                "required": ["class_id", "entity"],
            },
        ),
        execute=execute_query_class,
        display_name="查询班级数据",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="get_task",
            description=(
                "获取作业详情（标题、描述、评分标准、状态）。"
                "include_stats=true 时追加提交统计（提交率、平均分、每个学生的提交状态）。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "作业 ID（UUID）",
                    },
                    "include_stats": {
                        "type": "boolean",
                        "description": "是否包含提交统计数据，默认 false",
                    },
                },
                "required": ["task_id"],
            },
        ),
        execute=execute_get_task,
        display_name="获取作业信息",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="query_submissions",
            description=(
                "查询提交记录。三种查询模式（按优先级）："
                "① 指定 submission_id 查单个提交（include_content=true 可读取内容）；"
                "② 指定 student_id 查该学生的提交列表（可选 task_id 过滤）；"
                "③ 仅指定 task_id 查该作业所有提交。"
                "三个 ID 参数至少需要一个。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "submission_id": {
                        "type": "string",
                        "description": "提交记录 ID（UUID），指定时直接查该条提交",
                    },
                    "student_id": {
                        "type": "string",
                        "description": "学生的用户 ID（UUID）",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "作业 ID（UUID）",
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "是否读取提交内容，仅 submission_id 指定时有效，默认 false",
                    },
                },
                "required": [],
            },
        ),
        execute=execute_query_submissions,
        display_name="查询提交记录",
    ))
