from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from models.class_ import Class
from models.roster import StudentRoster
from models.sharing import SharingTopic
from models.task import Task
from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


async def _verify_class_ownership(
    class_id: uuid.UUID, ctx: ToolContext,
) -> Class | None:
    result = await ctx.db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == ctx.admin_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 1. create_task
# ---------------------------------------------------------------------------

async def execute_create_task(args: dict, ctx: ToolContext) -> str:
    title = args.get("title", "").strip()
    description = args.get("description", "").strip()
    grading_criteria = args.get("grading_criteria", "").strip()
    class_id_raw = args.get("class_id")

    if not title:
        return _json({"error": "请提供作业标题"})
    if not class_id_raw:
        return _json({"error": "请指定班级（class_id）"})

    class_id = uuid.UUID(str(class_id_raw))
    cls = await _verify_class_ownership(class_id, ctx)
    if not cls:
        return _json({"error": "班级不存在或无权访问"})

    task = Task(
        title=title,
        description=description,
        grading_criteria=grading_criteria,
        class_id=class_id,
        created_by=ctx.admin_id,
    )
    ctx.db.add(task)
    await ctx.db.commit()
    await ctx.db.refresh(task)

    return _json({
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "class_name": cls.name,
        "message": f"已创建草稿作业「{task.title}」",
    })


# ---------------------------------------------------------------------------
# 2. publish_task
# ---------------------------------------------------------------------------

async def execute_publish_task(args: dict, ctx: ToolContext) -> str:
    task_id_raw = args.get("task_id")
    if not task_id_raw:
        return _json({"error": "请指定作业 ID（task_id）"})

    result = await ctx.db.execute(
        select(Task).where(Task.id == uuid.UUID(str(task_id_raw)))
    )
    task = result.scalar_one_or_none()
    if not task:
        return _json({"error": "作业不存在"})

    if not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该作业"})

    if task.status != "draft":
        return _json({"error": f"作业当前状态为 {task.status}，只有草稿状态可以发布"})

    if not task.title or not task.description or not task.grading_criteria:
        return _json({"error": "发布作业需要填写标题、任务说明和打分标准"})

    task.status = "published"
    await ctx.db.commit()
    await ctx.db.refresh(task)

    return _json({
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "message": f"已发布作业「{task.title}」",
    })


# ---------------------------------------------------------------------------
# 3. create_sharing_topic
# ---------------------------------------------------------------------------

async def execute_create_sharing_topic(args: dict, ctx: ToolContext) -> str:
    title = args.get("title", "").strip()
    class_id_raw = args.get("class_id")

    if not title:
        return _json({"error": "请提供主题标题"})
    if not class_id_raw:
        return _json({"error": "请指定班级（class_id）"})

    class_id = uuid.UUID(str(class_id_raw))
    cls = await _verify_class_ownership(class_id, ctx)
    if not cls:
        return _json({"error": "班级不存在或无权访问"})

    topic_status = args.get("status", "voting")
    presenters = args.get("presenters")
    session_number = args.get("session_number")
    shared_at = args.get("shared_at")
    materials_content = args.get("materials_content")

    if topic_status == "completed":
        if not presenters:
            return _json({"error": "已分享状态需要填写汇报人"})
        if session_number is None:
            return _json({"error": "已分享状态需要填写分享次数"})

    parsed_shared_at = None
    if shared_at:
        try:
            parsed_shared_at = datetime.fromisoformat(str(shared_at))
            if parsed_shared_at.tzinfo is None:
                parsed_shared_at = parsed_shared_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return _json({"error": f"shared_at 格式无效，请使用 ISO 8601 格式（如 2026-04-05T10:00:00）"})

    topic = SharingTopic(
        title=title,
        status=topic_status,
        presenters=presenters,
        session_number=session_number,
        shared_at=parsed_shared_at,
        materials_content=materials_content,
        class_id=class_id,
    )
    ctx.db.add(topic)
    await ctx.db.commit()
    await ctx.db.refresh(topic)

    return _json({
        "id": str(topic.id),
        "title": topic.title,
        "status": topic.status,
        "class_name": cls.name,
        "message": f"已创建分享主题「{topic.title}」",
    })


# ---------------------------------------------------------------------------
# 4. import_roster
# ---------------------------------------------------------------------------

async def execute_import_roster(args: dict, ctx: ToolContext) -> str:
    class_id_raw = args.get("class_id")
    student_ids = args.get("student_ids", [])

    if not class_id_raw:
        return _json({"error": "请指定班级（class_id）"})
    if not student_ids:
        return _json({"error": "学生学号列表为空"})

    class_id = uuid.UUID(str(class_id_raw))
    cls = await _verify_class_ownership(class_id, ctx)
    if not cls:
        return _json({"error": "班级不存在或无权访问"})

    # Check existing entries
    result = await ctx.db.execute(
        select(StudentRoster.student_id).where(
            StudentRoster.student_id.in_(student_ids),
            StudentRoster.class_id == class_id,
        )
    )
    existing_ids = set(result.scalars().all())

    added = 0
    duplicates = 0
    for sid in student_ids:
        if sid in existing_ids:
            duplicates += 1
        else:
            ctx.db.add(StudentRoster(student_id=sid, class_id=class_id))
            existing_ids.add(sid)
            added += 1

    await ctx.db.commit()

    return _json({
        "class_name": cls.name,
        "added": added,
        "duplicates": duplicates,
        "total": len(student_ids),
        "message": f"已导入 {added} 个学号到「{cls.name}」（{duplicates} 个重复跳过）",
    })


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_action_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="create_task",
            description=(
                "创建作业草稿。执行前必须先用 ask_user 向用户确认标题、描述、"
                "评分标准和目标班级。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "作业标题",
                    },
                    "description": {
                        "type": "string",
                        "description": "作业说明",
                    },
                    "grading_criteria": {
                        "type": "string",
                        "description": "评分标准",
                    },
                    "class_id": {
                        "type": "string",
                        "description": "目标班级 ID（UUID）",
                    },
                },
                "required": ["title", "class_id"],
            },
        ),
        execute=execute_create_task,
        display_name="创建作业",
        requires_confirmation=True,
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="publish_task",
            description=(
                "将草稿状态的作业发布。发布前必须先用 ask_user 向用户确认。"
                "只有草稿（draft）状态的作业可以发布，且需要标题、说明和评分标准都已填写。"
            ),
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
        execute=execute_publish_task,
        display_name="发布作业",
        requires_confirmation=True,
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="create_sharing_topic",
            description=(
                "创建分享主题。执行前必须先用 ask_user 向用户确认标题和目标班级。"
                "status 可选 voting（投票中，默认）/ confirmed / completed。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "主题标题",
                    },
                    "class_id": {
                        "type": "string",
                        "description": "目标班级 ID（UUID）",
                    },
                    "presenters": {
                        "type": "string",
                        "description": "汇报人（completed 状态时必填）",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["voting", "confirmed", "completed"],
                        "description": "主题状态，默认 voting",
                    },
                    "session_number": {
                        "type": "integer",
                        "description": "分享次数（completed 状态时必填）",
                    },
                    "shared_at": {
                        "type": "string",
                        "description": "分享日期时间（ISO 8601 格式，如 2026-04-05T10:00:00）",
                    },
                    "materials_content": {
                        "type": "string",
                        "description": "分享素材内容（Markdown）",
                    },
                },
                "required": ["title", "class_id"],
            },
        ),
        execute=execute_create_sharing_topic,
        display_name="创建分享主题",
        requires_confirmation=True,
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="import_roster",
            description=(
                "批量导入学生名单到指定班级。执行前必须先用 ask_user 向用户确认学号列表和目标班级。"
                "已存在的学号会自动跳过。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "class_id": {
                        "type": "string",
                        "description": "目标班级 ID（UUID）",
                    },
                    "student_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "学生学号列表",
                    },
                },
                "required": ["class_id", "student_ids"],
            },
        ),
        execute=execute_import_roster,
        display_name="导入学生名单",
        requires_confirmation=True,
    ))
