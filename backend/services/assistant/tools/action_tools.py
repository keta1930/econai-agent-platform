from __future__ import annotations

import asyncio
import json
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from models.class_ import Class
from models.roster import StudentRoster
from models.search_result import SearchResult
from models.sharing import SharingTopic
from models.submission import Submission
from models.task import Task
from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry
from services.storage import storage_service


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


async def _verify_class_ownership(
    class_id: uuid.UUID, ctx: ToolContext,
) -> Class | None:
    """如果班级属于该管理员则返回 Class，否则返回 None。"""
    result = await ctx.db.execute(
        select(Class).where(Class.id == class_id, Class.created_by == ctx.admin_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 1. manage_class
# ---------------------------------------------------------------------------

async def execute_manage_class(args: dict, ctx: ToolContext) -> str:
    action = args.get("action")

    if action == "create":
        name = (args.get("name") or "").strip()
        if not name:
            return _json({"error": "请提供班级名称"})

        # 检查该管理员下班级名称唯一性
        existing = await ctx.db.execute(
            select(Class).where(
                Class.name == name, Class.created_by == ctx.admin_id,
            )
        )
        if existing.scalar_one_or_none():
            return _json({"error": f"已存在同名班级「{name}」"})

        cls = Class(
            name=name,
            created_by=ctx.admin_id,
            join_token=secrets.token_urlsafe(16),
        )
        ctx.db.add(cls)
        await ctx.db.commit()
        await ctx.db.refresh(cls)

        return _json({
            "id": str(cls.id),
            "name": cls.name,
            "join_token": cls.join_token,
            "message": f"已创建班级「{cls.name}」",
        })

    if action == "get_token":
        class_id_raw = args.get("class_id")
        if not class_id_raw:
            return _json({"error": "请指定班级 ID（class_id）"})

        cls = await _verify_class_ownership(uuid.UUID(str(class_id_raw)), ctx)
        if not cls:
            return _json({"error": "班级不存在或无权访问"})

        return _json({
            "class_name": cls.name,
            "join_token": cls.join_token,
        })

    if action == "regenerate_token":
        class_id_raw = args.get("class_id")
        if not class_id_raw:
            return _json({"error": "请指定班级 ID（class_id）"})

        cls = await _verify_class_ownership(uuid.UUID(str(class_id_raw)), ctx)
        if not cls:
            return _json({"error": "班级不存在或无权访问"})

        cls.join_token = secrets.token_urlsafe(16)
        await ctx.db.commit()
        await ctx.db.refresh(cls)

        return _json({
            "class_name": cls.name,
            "join_token": cls.join_token,
            "message": f"已为班级「{cls.name}」生成新凭证",
        })

    return _json({"error": f"未知操作：{action}"})


# ---------------------------------------------------------------------------
# 2. manage_task
# ---------------------------------------------------------------------------

async def execute_manage_task(args: dict, ctx: ToolContext) -> str:
    action = args.get("action")

    if action == "create":
        return await _task_create(args, ctx)
    if action == "update":
        return await _task_update(args, ctx)
    if action == "publish":
        return await _task_publish(args, ctx)
    if action == "delete":
        return await _task_delete(args, ctx)

    return _json({"error": f"未知操作：{action}"})


async def _task_create(args: dict, ctx: ToolContext) -> str:
    title = (args.get("title") or "").strip()
    description = (args.get("description") or "").strip()
    grading_criteria = (args.get("grading_criteria") or "").strip()
    class_id_raw = args.get("class_id")

    if not title:
        return _json({"error": "请提供作业标题"})
    if not class_id_raw:
        return _json({"error": "请指定班级（class_id）"})

    class_id = uuid.UUID(str(class_id_raw))
    cls = await _verify_class_ownership(class_id, ctx)
    if not cls:
        return _json({"error": "班级不存在或无权访问"})

    # 从搜索记录解析 learning_resources URL
    lr_urls = args.get("learning_resources") or []
    learning_resources = None
    rejected_urls: list[str] = []
    if lr_urls and ctx.conversation_id:
        result = await ctx.db.execute(
            select(SearchResult).where(
                SearchResult.conversation_id == ctx.conversation_id,
                SearchResult.url.in_(lr_urls),
            )
        )
        matched = result.scalars().all()
        # 按 URL 去重（同一 URL 可能出现在多次搜索中）
        seen: dict[str, SearchResult] = {}
        for r in matched:
            if r.url not in seen:
                seen[r.url] = r
        matched_urls = set(seen.keys())
        rejected_urls = [u for u in lr_urls if u not in matched_urls]
        if seen:
            learning_resources = [
                {"url": r.url, "title": r.title, "content": r.content}
                for r in seen.values()
            ]

    task = Task(
        title=title,
        description=description,
        grading_criteria=grading_criteria,
        learning_resources=learning_resources,
        class_id=class_id,
        created_by=ctx.admin_id,
    )
    ctx.db.add(task)
    await ctx.db.commit()
    await ctx.db.refresh(task)

    resp: dict = {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "class_name": cls.name,
        "message": f"已创建草稿作业「{task.title}」",
    }
    if learning_resources:
        resp["learning_resources_count"] = len(learning_resources)
    if rejected_urls:
        resp["rejected_urls"] = rejected_urls
        resp["rejected_message"] = f"以下 URL 不在当前对话的搜索记录中，已忽略：{', '.join(rejected_urls)}"

    return _json(resp)


async def _task_update(args: dict, ctx: ToolContext) -> str:
    task_id_raw = args.get("task_id")
    if not task_id_raw:
        return _json({"error": "请指定作业 ID（task_id）"})

    result = await ctx.db.execute(
        select(Task).where(Task.id == uuid.UUID(str(task_id_raw)))
    )
    task = result.scalar_one_or_none()
    if not task:
        return _json({"error": "作业不存在"})

    cls = await _verify_class_ownership(task.class_id, ctx)
    if not cls:
        return _json({"error": "无权访问该作业"})

    if task.status != "draft":
        return _json({"error": f"作业当前状态为 {task.status}，只有草稿状态可以编辑"})

    updatable_fields = ("title", "description", "grading_criteria", "learning_resources")
    updated = []
    for field in updatable_fields:
        if field not in args:
            continue
        value = args[field]
        if field == "learning_resources":
            # LLM 返回的 URL 字符串列表 -> 从 SearchResult 解析
            if isinstance(value, list) and value and isinstance(value[0], str):
                if ctx.conversation_id:
                    result = await ctx.db.execute(
                        select(SearchResult).where(
                            SearchResult.conversation_id == ctx.conversation_id,
                            SearchResult.url.in_(value),
                        )
                    )
                    matched = result.scalars().all()
                    # 按 URL 去重
                    seen_urls: dict[str, SearchResult] = {}
                    for r in matched:
                        if r.url not in seen_urls:
                            seen_urls[r.url] = r
                    value = [
                        {"url": r.url, "title": r.title, "content": r.content}
                        for r in seen_urls.values()
                    ] or None
                else:
                    value = None
        else:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return _json({"error": f"{field} 不能为空"})
        setattr(task, field, value)
        updated.append(field)

    if not updated:
        return _json({"error": "未提供任何需要更新的字段（可更新：title, description, grading_criteria, learning_resources）"})

    await ctx.db.commit()
    await ctx.db.refresh(task)

    return _json({
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "grading_criteria": task.grading_criteria,
        "learning_resources": task.learning_resources,
        "status": task.status,
        "class_name": cls.name,
        "updated_fields": updated,
        "message": f"已更新作业「{task.title}」的 {', '.join(updated)}",
    })


async def _task_publish(args: dict, ctx: ToolContext) -> str:
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


async def _task_delete(args: dict, ctx: ToolContext) -> str:
    task_id_raw = args.get("task_id")
    if not task_id_raw:
        return _json({"error": "请指定作业 ID（task_id）"})

    task_id = uuid.UUID(str(task_id_raw))
    result = await ctx.db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return _json({"error": "作业不存在"})

    if not await _verify_class_ownership(task.class_id, ctx):
        return _json({"error": "无权访问该作业"})

    task_title = task.title

    # 收集提交的文件路径用于 MinIO 清理
    sub_result = await ctx.db.execute(
        select(Submission.file_path).where(Submission.task_id == task_id)
    )
    file_paths = [row[0] for row in sub_result.all() if row[0]]

    # 先删提交再删作业
    await ctx.db.execute(
        Submission.__table__.delete().where(Submission.task_id == task_id)
    )
    await ctx.db.delete(task)
    await ctx.db.commit()

    # 异步清理 MinIO 文件（尽力而为）
    if file_paths:
        await asyncio.to_thread(storage_service.remove_objects, file_paths)

    return _json({
        "task_title": task_title,
        "message": f"已删除作业「{task_title}」及其 {len(file_paths)} 份提交文件",
    })


# ---------------------------------------------------------------------------
# 3. manage_topic
# ---------------------------------------------------------------------------

async def execute_manage_topic(args: dict, ctx: ToolContext) -> str:
    action = args.get("action")

    if action == "create":
        return await _topic_create(args, ctx)
    if action == "update":
        return await _topic_update(args, ctx)
    if action == "delete":
        return await _topic_delete(args, ctx)

    return _json({"error": f"未知操作：{action}"})


async def _topic_create(args: dict, ctx: ToolContext) -> str:
    title = (args.get("title") or "").strip()
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
            return _json({"error": "shared_at 格式无效，请使用 ISO 8601 格式（如 2026-04-05T10:00:00）"})

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


async def _topic_update(args: dict, ctx: ToolContext) -> str:
    topic_id_raw = args.get("topic_id")
    if not topic_id_raw:
        return _json({"error": "请指定主题 ID（topic_id）"})

    result = await ctx.db.execute(
        select(SharingTopic).where(SharingTopic.id == uuid.UUID(str(topic_id_raw)))
    )
    topic = result.scalar_one_or_none()
    if not topic:
        return _json({"error": "主题不存在"})

    cls = await _verify_class_ownership(topic.class_id, ctx)
    if not cls:
        return _json({"error": "无权访问该主题"})

    # 字段级更新（exclude_unset 语义）
    updatable_fields = ("title", "status", "presenters", "session_number", "shared_at", "materials_content")
    updated = []
    for field in updatable_fields:
        if field not in args:
            continue

        value = args[field]

        # 字符串字段：trim 后标题不允许为空
        if field == "title":
            value = (value or "").strip()
            if not value:
                return _json({"error": "标题不能为空"})

        # 解析 shared_at
        if field == "shared_at" and value is not None:
            try:
                value = datetime.fromisoformat(str(value))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return _json({"error": "shared_at 格式无效，请使用 ISO 8601 格式"})

        setattr(topic, field, value)
        updated.append(field)

    if not updated:
        return _json({"error": "未提供任何需要更新的字段"})

    # 状态校验：completed 需要 presenters + session_number
    if topic.status == "completed":
        if not topic.presenters:
            return _json({"error": "已分享状态需要填写汇报人"})
        if topic.session_number is None:
            return _json({"error": "已分享状态需要填写分享次数"})

    await ctx.db.commit()
    await ctx.db.refresh(topic)

    return _json({
        "id": str(topic.id),
        "title": topic.title,
        "status": topic.status,
        "presenters": topic.presenters,
        "session_number": topic.session_number,
        "shared_at": topic.shared_at,
        "materials_content": topic.materials_content,
        "class_name": cls.name,
        "updated_fields": updated,
        "message": f"已更新分享主题「{topic.title}」的 {', '.join(updated)}",
    })


async def _topic_delete(args: dict, ctx: ToolContext) -> str:
    topic_id_raw = args.get("topic_id")
    if not topic_id_raw:
        return _json({"error": "请指定主题 ID（topic_id）"})

    result = await ctx.db.execute(
        select(SharingTopic).where(SharingTopic.id == uuid.UUID(str(topic_id_raw)))
    )
    topic = result.scalar_one_or_none()
    if not topic:
        return _json({"error": "主题不存在"})

    if not await _verify_class_ownership(topic.class_id, ctx):
        return _json({"error": "无权访问该主题"})

    topic_title = topic.title
    # TopicVote 通过 FK 关系级联删除
    await ctx.db.delete(topic)
    await ctx.db.commit()

    return _json({
        "topic_title": topic_title,
        "message": f"已删除分享主题「{topic_title}」",
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

    # 检查已有记录
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
# 注册
# ---------------------------------------------------------------------------

def register_action_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="manage_class",
            description=(
                "班级管理，通过 action 区分操作：\n"
                "- create: 创建班级，需要 name。创建后自动生成并返回加入凭证\n"
                "- get_token: 获取班级的加入凭证，需要 class_id。只读操作\n"
                "- regenerate_token: 重新生成凭证（旧凭证立即失效），需要 class_id"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "get_token", "regenerate_token"],
                        "description": "操作类型",
                    },
                    "name": {
                        "type": "string",
                        "description": "班级名称（action=create 时必填）",
                    },
                    "class_id": {
                        "type": "string",
                        "description": "班级 ID（action=get_token/regenerate_token 时必填）",
                    },
                },
                "required": ["action"],
            },
        ),
        execute=execute_manage_class,
        display_name="班级管理",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="manage_task",
            description=(
                "作业管理，通过 action 区分操作：\n"
                "- create: 创建草稿，需要 title + class_id。description/grading_criteria/learning_resources 可选\n"
                "- update: 编辑草稿字段，需要 task_id + 至少一个修改字段。仅 draft 状态可编辑，"
                "只传需要改的字段，其余保持不变\n"
                "- publish: 发布草稿，需要 task_id。发布前 title、description、grading_criteria 必须齐全\n"
                "- delete: 删除作业及关联提交文件，需要 task_id\n"
                "learning_resources: 传入 URL 字符串数组，URL 必须来自当前对话中 tavily_search 的搜索结果，"
                "系统自动关联标题和内容。不在搜索记录中的 URL 会被忽略。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "publish", "delete"],
                        "description": "操作类型",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "作业 ID（update/publish/delete 时必填）",
                    },
                    "title": {
                        "type": "string",
                        "description": "作业标题（create 时必填，update 时可选）",
                    },
                    "description": {
                        "type": "string",
                        "description": "作业说明",
                    },
                    "grading_criteria": {
                        "type": "string",
                        "description": "评分标准",
                    },
                    "learning_resources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "学习资源 URL 列表，URL 必须来自本次对话的搜索结果",
                    },
                    "class_id": {
                        "type": "string",
                        "description": "目标班级 ID（create 时必填）",
                    },
                },
                "required": ["action"],
            },
        ),
        execute=execute_manage_task,
        display_name="作业管理",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="manage_topic",
            description=(
                "分享主题管理，通过 action 区分操作：\n"
                "- create: 创建主题，需要 title + class_id，默认 status='voting'\n"
                "- update: 编辑主题字段，需要 topic_id + 至少一个修改字段\n"
                "- delete: 删除主题（关联投票自动级联删除），需要 topic_id\n"
                "status 取值: voting（投票中）→ confirmed（已确定）→ completed（已分享）。"
                "设为 completed 时 presenters 和 session_number 必填。"
                "shared_at 使用 ISO 8601 格式（如 2026-04-05T10:00:00）。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete"],
                        "description": "操作类型",
                    },
                    "topic_id": {
                        "type": "string",
                        "description": "主题 ID（update/delete 时必填）",
                    },
                    "title": {
                        "type": "string",
                        "description": "主题标题（create 时必填，update 时可选）",
                    },
                    "class_id": {
                        "type": "string",
                        "description": "目标班级 ID（create 时必填）",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["voting", "confirmed", "completed"],
                        "description": "主题状态",
                    },
                    "presenters": {
                        "type": "string",
                        "description": "汇报人",
                    },
                    "session_number": {
                        "type": "integer",
                        "description": "分享次数",
                    },
                    "shared_at": {
                        "type": "string",
                        "description": "分享日期时间（ISO 8601）",
                    },
                    "materials_content": {
                        "type": "string",
                        "description": "分享素材内容（Markdown）",
                    },
                },
                "required": ["action"],
            },
        ),
        execute=execute_manage_topic,
        display_name="分享主题管理",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="import_roster",
            description=(
                "批量导入学生学号到指定班级。需要 class_id 和 student_ids 数组。"
                "已存在的学号自动跳过（幂等），返回新增数和跳过数。"
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
    ))
