"""AssistantService — Agent Loop 核心引擎，工具编排与 SSE 流式输出。"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.class_ import Class
from models.conversation import Conversation, ConversationMessage
from models.model_config import ModelConfig
from schemas.assistant import ConversationDetailResponse, ConversationResponse, MessageResponse
from services.ai import get_adapter
from services.ai.base import BaseAIAdapter, StreamEvent, ToolCall, ToolDefinition
from services.assistant.context import (
    estimate_message_tokens,
    get_model_context_limit,
    prepare_messages,
)
from services.assistant.prompts import TITLE_GENERATION_PROMPT, build_system_prompt
from services.assistant.tools import ToolContext, registry

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS_PER_TURN = 50


def format_sse(event_type: str, data: dict[str, Any]) -> str:
    """格式化单条 SSE 事件字符串（event + data + 空行）。"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


class AssistantService:
    """管理对话并驱动 Agent Loop。"""

    # 类级别的取消标志，所有实例共享（按对话 ID 索引）
    _cancel_flags: dict[uuid.UUID, bool] = {}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # CRUD 操作
    # ------------------------------------------------------------------

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        title: str | None = None,
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def list_conversations(
        self,
        user_id: uuid.UUID,
    ) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ConversationDetailResponse:
        conversation = await self._load_owned_conversation(
            conversation_id, user_id, with_messages=True,
        )
        messages = [
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                token_count=m.token_count,
                created_at=m.created_at,
            )
            for m in conversation.messages
        ]
        return ConversationDetailResponse(
            id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            token_count=conversation.token_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages,
        )

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        conversation = await self._load_owned_conversation(conversation_id, user_id)
        await self.db.delete(conversation)
        await self.db.commit()

    async def update_conversation_title(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
    ) -> Conversation:
        conversation = await self._load_owned_conversation(conversation_id, user_id)
        conversation.title = title
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    # ------------------------------------------------------------------
    # 消息处理
    # ------------------------------------------------------------------

    async def handle_message(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        files: list[dict] | None = None,
        class_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """发送用户消息并通过 SSE 流式返回助手响应。"""
        logger.info("收到用户消息 — 对话=%s, 内容长度=%d", conversation_id, len(content))

        conversation = await self._load_owned_conversation(
            conversation_id, user_id, with_messages=True,
        )
        if conversation.status == "pending_answer":
            yield format_sse("error", {"type": "error", "message": "请先回答助教的问题"})
            return

        # 构建用户消息内容块
        blocks: list[dict] = [{"type": "text", "text": content}]
        if files:
            for f in files:
                mime = f.get("mime_type", "")
                block_type = "image" if mime.startswith("image/") else "file"
                if block_type == "image":
                    logger.info("收到图片 — 文件名=%s, 类型=%s", f["filename"], mime)
                else:
                    logger.info("收到文件附件 — 文件名=%s, 类型=%s", f["filename"], mime)
                blocks.append({
                    "type": block_type,
                    "file_id": f["file_id"],
                    "filename": f["filename"],
                    "mime_type": mime,
                })

        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=blocks,
            token_count=estimate_message_tokens(blocks),
        )
        self.db.add(user_msg)

        # 自动生成标题：先设临时标题防止重复触发，
        # adapter 解析后再启动异步 LLM 标题生成。
        needs_title = conversation.title is None
        if needs_title:
            conversation.title = content[:20]

        await self.db.flush()

        # 解析模型配置
        adapter = await self._get_adapter(user_id)
        if adapter is None:
            yield format_sse("error", {"type": "error", "message": "未配置 AI 模型，请先在模型管理中添加并激活模型"})
            return

        # 启动后台标题生成（必须在 adapter 解析之后）
        title_queue: asyncio.Queue | None = None
        if needs_title:
            logger.info("标题生成启动 — 对话=%s", conversation_id)
            title_queue = asyncio.Queue()
            # 保留任务引用防止 GC 在完成前回收
            _title_task = asyncio.create_task(
                self._generate_title(
                    conversation.id, content, adapter, title_queue,
                )
            )

        # 解析模型上下文窗口限制
        max_context = get_model_context_limit(adapter.model_name)

        # 解析班级上下文用于 system prompt
        effective_class_id = class_id or conversation.class_id
        system_prompt = await self._build_system_prompt(user_id, effective_class_id)

        # 准备工具定义
        tool_defs = registry.get_definitions(role="admin")

        # 准备 API 消息（加载历史，必要时压缩）
        api_messages, total_tokens = await prepare_messages(
            str(conversation.id), self.db, adapter, system_prompt, len(tool_defs),
            max_context=max_context,
        )

        # 更新 token 计数
        conversation.token_count = total_tokens
        if effective_class_id and not conversation.class_id:
            conversation.class_id = effective_class_id
        await self.db.flush()

        # 运行 agent loop，穿插 title_update 事件
        tool_ctx = ToolContext(
            user_id=user_id,
            admin_id=user_id,
            class_id=effective_class_id,
            db=self.db,
            adapter=adapter,
            conversation_id=conversation.id,
        )
        async for sse_event in self._agent_loop(
            conversation, api_messages, adapter, tool_defs, tool_ctx, system_prompt,
            max_context=max_context,
        ):
            yield sse_event
            # 检查标题生成是否在 SSE 块之间完成
            if title_queue is not None:
                try:
                    title_data = title_queue.get_nowait()
                    yield await self._apply_title_update(conversation, title_data)
                    title_queue = None
                except asyncio.QueueEmpty:
                    pass

        # 流结束后，短暂等待标题生成（如仍在进行）
        if title_queue is not None:
            try:
                title_data = await asyncio.wait_for(title_queue.get(), timeout=3.0)
                yield await self._apply_title_update(conversation, title_data)
            except asyncio.TimeoutError:
                logger.warning("标题生成超时 — 对话=%s", conversation.id)

    async def handle_answer(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        answer: str,
    ) -> AsyncGenerator[str, None]:
        """用户回答 ask_user 问题后恢复 agent loop。"""
        logger.info("收到用户回答 — 对话=%s, 内容长度=%d", conversation_id, len(answer))
        conversation = await self._load_owned_conversation(
            conversation_id, user_id, with_messages=True,
        )
        if conversation.status != "pending_answer":
            yield format_sse("error", {"type": "error", "message": "当前对话不在等待回答状态"})
            return

        pending_tool_call_id = conversation.pending_tool_call_id
        if not pending_tool_call_id:
            yield format_sse("error", {"type": "error", "message": "缺少 pending_tool_call_id"})
            return

        # 将用户的回答保存为 tool_result 消息
        result_blocks: list[dict] = [{
            "type": "tool_result",
            "tool_call_id": pending_tool_call_id,
            "content": answer,
            "is_error": False,
        }]
        tool_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="tool",
            content=result_blocks,
            token_count=estimate_message_tokens(result_blocks),
        )
        self.db.add(tool_msg)

        # 重置对话状态
        conversation.status = "active"
        conversation.pending_tool_call_id = None
        await self.db.flush()

        # 恢复 loop
        adapter = await self._get_adapter(user_id)
        if adapter is None:
            yield format_sse("error", {"type": "error", "message": "未配置 AI 模型"})
            return

        max_context = get_model_context_limit(adapter.model_name)
        effective_class_id = conversation.class_id
        system_prompt = await self._build_system_prompt(user_id, effective_class_id)
        tool_defs = registry.get_definitions(role="admin")

        api_messages, total_tokens = await prepare_messages(
            str(conversation.id), self.db, adapter, system_prompt, len(tool_defs),
            max_context=max_context,
        )
        conversation.token_count = total_tokens
        await self.db.flush()

        tool_ctx = ToolContext(
            user_id=user_id,
            admin_id=user_id,
            class_id=effective_class_id,
            db=self.db,
            adapter=adapter,
            conversation_id=conversation.id,
        )
        async for sse_event in self._agent_loop(
            conversation, api_messages, adapter, tool_defs, tool_ctx, system_prompt,
            max_context=max_context,
        ):
            yield sse_event

    async def stop_generation(self, conversation_id: uuid.UUID) -> None:
        """通知 agent loop 在下一个 yield 点停止。"""
        logger.info("收到停止生成请求 — 对话=%s", conversation_id)
        AssistantService._cancel_flags[conversation_id] = True

    # ------------------------------------------------------------------
    # Agent Loop
    # ------------------------------------------------------------------

    async def _agent_loop(
        self,
        conversation: Conversation,
        api_messages: list[dict],
        adapter: BaseAIAdapter,
        tool_defs: list[ToolDefinition],
        tool_ctx: ToolContext,
        system_prompt: str,
        *,
        max_context: int = 200_000,
    ) -> AsyncGenerator[str, None]:
        """核心循环：流式输出模型响应，执行工具，重复直到完成。"""
        conv_id = conversation.id
        logger.info("流式响应开始 — 对话=%s", conv_id)
        AssistantService._cancel_flags[conv_id] = False
        tool_call_count = 0
        current_tools: list[ToolDefinition] | None = tool_defs

        try:
            while True:
                # 检查取消标志
                if AssistantService._cancel_flags.get(conv_id, False):
                    yield format_sse("done", {"type": "done"})
                    break

                # 累积完整的助手响应
                text_parts: list[str] = []
                tool_calls_accumulated: dict[str, dict] = {}  # id -> {name, args_json}
                completed_tool_calls: list[ToolCall] = []

                try:
                    messages_for_api = [{"role": "system", "content": system_prompt}] + api_messages
                    stream = adapter.chat_stream(messages_for_api, current_tools)
                    async for event in stream:
                        if AssistantService._cancel_flags.get(conv_id, False):
                            break

                        if event.type == "text_delta" and event.text:
                            text_parts.append(event.text)
                            yield format_sse("text_delta", {
                                "type": "text_delta",
                                "content": event.text,
                            })

                        elif event.type == "tool_call_start":
                            tc_id = event.tool_call_id or ""
                            tool_calls_accumulated[tc_id] = {
                                "name": event.tool_name or "",
                                "args_json": "",
                            }
                            display_name = registry.get_display_name(event.tool_name or "")
                            yield format_sse("tool_call_start", {
                                "type": "tool_call_start",
                                "id": tc_id,
                                "name": event.tool_name or "",
                                "display_name": display_name,
                            })

                        elif event.type == "tool_call_args_delta":
                            tc_id = event.tool_call_id or ""
                            if tc_id in tool_calls_accumulated:
                                tool_calls_accumulated[tc_id]["args_json"] += event.partial_json or ""

                        elif event.type == "tool_call_end":
                            tc_id = event.tool_call_id or ""
                            if tc_id in tool_calls_accumulated:
                                acc = tool_calls_accumulated[tc_id]
                                try:
                                    args = json.loads(acc["args_json"]) if acc["args_json"] else {}
                                except json.JSONDecodeError:
                                    args = {}
                                # 发送解析后的参数到前端
                                yield format_sse("tool_call_args", {
                                    "type": "tool_call_args",
                                    "id": tc_id,
                                    "args": args,
                                })
                                completed_tool_calls.append(
                                    ToolCall(id=tc_id, name=acc["name"], arguments=args)
                                )

                        elif event.type == "message_end":
                            if event.tool_calls:
                                completed_tool_calls = event.tool_calls

                except Exception:
                    logger.exception("模型流式调用异常 — 对话=%s", conv_id)
                    yield format_sse("error", {"type": "error", "message": "模型调用失败，请稍后重试"})
                    return

                # 流中途被取消
                if AssistantService._cancel_flags.get(conv_id, False):
                    # 保存已有的文本
                    if text_parts:
                        await self._save_assistant_message(conversation, text_parts, [])
                    yield format_sse("done", {"type": "done"})
                    break

                # 处理工具调用（如有）
                if completed_tool_calls:
                    # 构建助手消息块（text + tool_use 块）
                    assistant_blocks: list[dict] = []
                    full_text = "".join(text_parts)
                    if full_text:
                        assistant_blocks.append({"type": "text", "text": full_text})
                    for tc in completed_tool_calls:
                        assistant_blocks.append({
                            "type": "tool_use",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        })

                    # 保存助手消息
                    assistant_msg = ConversationMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=assistant_blocks,
                        token_count=estimate_message_tokens(assistant_blocks),
                    )
                    self.db.add(assistant_msg)
                    await self.db.flush()

                    # 以 OpenAI 格式追加到 api_messages 以兼容 adapter
                    openai_tool_calls = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in completed_tool_calls
                    ]
                    api_messages.append({
                        "role": "assistant",
                        "content": full_text if full_text else None,
                        "tool_calls": openai_tool_calls,
                    })

                    # 逐个执行工具
                    for tc in completed_tool_calls:
                        if AssistantService._cancel_flags.get(conv_id, False):
                            break

                        # --- ask_user 拦截 ---
                        if tc.name == "ask_user":
                            logger.info("ask_user 暂停 — 对话=%s, tool_call_id=%s", conv_id, tc.id)
                            # 归一化为 questions 数组（兼容旧版单问题格式）
                            questions = tc.arguments.get("questions")
                            if not questions:
                                questions = [{
                                    "question": tc.arguments.get("question", ""),
                                    "options": tc.arguments.get("options"),
                                    "select_mode": tc.arguments.get("select_mode", "single"),
                                }]

                            yield format_sse("ask_user", {
                                "type": "ask_user",
                                "tool_call_id": tc.id,
                                "questions": questions,
                            })

                            # 为所有剩余的 tool_calls 插入占位 tool_results
                            # （包括 ask_user 的同级未执行调用），保持
                            # tool_use/tool_result 配对完整。
                            current_idx = completed_tool_calls.index(tc)
                            for remaining_tc in completed_tool_calls[current_idx + 1:]:
                                skip_blocks: list[dict] = [{
                                    "type": "tool_result",
                                    "tool_call_id": remaining_tc.id,
                                    "content": "已跳过：等待用户回答",
                                    "is_error": False,
                                }]
                                skip_msg = ConversationMessage(
                                    conversation_id=conversation.id,
                                    role="tool",
                                    content=skip_blocks,
                                    token_count=estimate_message_tokens(skip_blocks),
                                )
                                self.db.add(skip_msg)

                            # 暂停循环
                            conversation.status = "pending_answer"
                            conversation.pending_tool_call_id = tc.id
                            await self.db.commit()
                            yield format_sse("done", {"type": "done"})
                            return

                        # --- 常规工具执行 ---
                        logger.info("工具调用开始 — 工具=%s, 对话=%s", tc.name, conv_id)
                        handler = registry.get_handler(tc.name)
                        if handler is None:
                            result_content = f"错误：未知工具 {tc.name}"
                            is_error = True
                        else:
                            try:
                                result_content = await handler.execute(tc.arguments, tool_ctx)
                                is_error = False
                                logger.info("工具调用完成 — 工具=%s, 对话=%s", tc.name, conv_id)
                            except Exception:
                                logger.exception("工具执行失败 — 工具=%s, 对话=%s", tc.name, conv_id)
                                result_content = f"工具执行失败: {tc.name}"
                                is_error = True

                        yield format_sse("tool_call_result", {
                            "type": "tool_call_result",
                            "id": tc.id,
                            "result": result_content,
                            "is_error": is_error,
                        })

                        # 保存工具结果消息
                        result_blocks: list[dict] = [{
                            "type": "tool_result",
                            "tool_call_id": tc.id,
                            "content": result_content,
                            "is_error": is_error,
                        }]
                        tool_msg = ConversationMessage(
                            conversation_id=conversation.id,
                            role="tool",
                            content=result_blocks,
                            token_count=estimate_message_tokens(result_blocks),
                        )
                        self.db.add(tool_msg)
                        await self.db.flush()

                        # 追加到 api_messages（将错误状态编码到内容文本中
                        # — OpenAI API 拒绝 is_error 等未知字段）
                        api_content = f"[ERROR] {result_content}" if is_error else result_content
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": api_content,
                        })

                    # 更新工具调用计数并检查限制
                    tool_call_count += len(completed_tool_calls)
                    if tool_call_count >= MAX_TOOL_CALLS_PER_TURN:
                        logger.info(
                            "工具调用次数达到上限 — 次数=%d, 对话=%s",
                            tool_call_count, conv_id,
                        )
                        current_tools = None  # 强制最终文本响应

                    # 继续循环进入下一轮模型调用
                    continue

                # 无工具调用 — 这是最终文本响应
                full_text = "".join(text_parts)
                if full_text:
                    await self._save_assistant_message(conversation, text_parts, [])

                # 发送 token 使用量
                total_tokens = conversation.token_count + estimate_message_tokens(
                    [{"type": "text", "text": full_text}]
                ) if full_text else conversation.token_count
                conversation.token_count = total_tokens
                await self.db.commit()

                yield format_sse("token_usage", {
                    "type": "token_usage",
                    "total_tokens": total_tokens,
                    "max_tokens": max_context,
                    "ratio": round(total_tokens / max_context, 4),
                })
                logger.info("流式响应结束 — 对话=%s, 工具调用次数=%d", conv_id, tool_call_count)
                yield format_sse("done", {"type": "done"})
                break
        finally:
            AssistantService._cancel_flags.pop(conv_id, None)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _apply_title_update(
        self,
        conversation: Conversation,
        title_data: dict[str, str],
    ) -> str:
        """持久化生成的标题并返回 SSE 事件字符串。"""
        conversation.title = title_data["title"]
        await self.db.flush()
        return format_sse("title_update", {
            "type": "title_update",
            "conversation_id": title_data["conversation_id"],
            "title": title_data["title"],
        })

    async def _generate_title(
        self,
        conversation_id: uuid.UUID,
        user_message: str,
        adapter: BaseAIAdapter,
        title_queue: asyncio.Queue,
    ) -> None:
        """后台任务：调用 LLM 生成对话标题，将结果放入队列。"""
        try:
            prompt = TITLE_GENERATION_PROMPT.format(user_message=user_message[:200])
            response = await adapter.async_chat(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
            )
            title = (response.text or "").strip()[:30] or user_message[:20]
            logger.info("标题生成完成 — 对话=%s, 标题=%s", conversation_id, title)
        except Exception:
            logger.warning("标题生成失败，使用回退 — 对话=%s", conversation_id)
            title = user_message[:20]

        await title_queue.put({
            "title": title,
            "conversation_id": str(conversation_id),
        })

    async def _load_owned_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        with_messages: bool = False,
    ) -> Conversation:
        """加载对话并验证所有权。"""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if with_messages:
            stmt = stmt.options(selectinload(Conversation.messages))
        conversation = await self.db.scalar(stmt)
        if conversation is None:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
        if conversation.user_id != user_id:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此对话")
        return conversation

    async def _get_adapter(self, admin_id: uuid.UUID) -> BaseAIAdapter | None:
        """解析管理员的活跃模型配置并创建 adapter。"""
        result = await self.db.execute(
            select(ModelConfig).where(
                ModelConfig.admin_id == admin_id,
                ModelConfig.is_active == True,  # noqa: E712
            )
        )
        model_config = result.scalar_one_or_none()
        if model_config is None:
            return None
        return get_adapter(model_config)

    async def _build_system_prompt(
        self,
        admin_id: uuid.UUID,
        class_id: uuid.UUID | None,
    ) -> str:
        """根据班级上下文构建 system prompt。"""
        if class_id:
            cls = await self.db.get(Class, class_id)
            if cls:
                from models.user import User
                admin = await self.db.get(User, admin_id)
                admin_name = admin.username if admin else "教师"
                return build_system_prompt(
                    class_name=cls.name,
                    class_id=str(cls.id),
                    admin_name=admin_name,
                )
        # 回退：无特定班级上下文
        return build_system_prompt(
            class_name="未指定班级",
            class_id="",
            admin_name="教师",
        )

    async def _save_assistant_message(
        self,
        conversation: Conversation,
        text_parts: list[str],
        tool_use_blocks: list[dict],
    ) -> ConversationMessage:
        """保存完整的助手消息到数据库。"""
        blocks: list[dict] = []
        full_text = "".join(text_parts)
        if full_text:
            blocks.append({"type": "text", "text": full_text})
        blocks.extend(tool_use_blocks)

        msg = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=blocks,
            token_count=estimate_message_tokens(blocks),
        )
        self.db.add(msg)
        await self.db.flush()
        return msg
