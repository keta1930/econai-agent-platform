"""AssistantService — Agent Loop core engine with tool orchestration and SSE streaming."""

from __future__ import annotations

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
from services.assistant.prompts import build_system_prompt
from services.assistant.tools import ToolContext, registry

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS_PER_TURN = 50


def format_sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event string (event + data + blank line)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


class AssistantService:
    """Manages conversations and drives the Agent Loop."""

    # Class-level cancel flags shared across instances (keyed by conversation id).
    _cancel_flags: dict[uuid.UUID, bool] = {}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
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
    # Message handling
    # ------------------------------------------------------------------

    async def handle_message(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        files: list[dict] | None = None,
        class_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """Send a user message and stream back the assistant response via SSE."""
        conversation = await self._load_owned_conversation(
            conversation_id, user_id, with_messages=True,
        )
        if conversation.status == "pending_answer":
            yield format_sse("error", {"type": "error", "message": "请先回答助教的问题"})
            return

        # Build user message content blocks
        blocks: list[dict] = [{"type": "text", "text": content}]
        if files:
            for f in files:
                blocks.append({
                    "type": "file",
                    "file_id": f["file_id"],
                    "filename": f["filename"],
                    "mime_type": f["mime_type"],
                })

        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=blocks,
            token_count=estimate_message_tokens(blocks),
        )
        self.db.add(user_msg)

        # Auto-generate title from first user message
        if conversation.title is None:
            conversation.title = content[:30]

        await self.db.flush()

        # Resolve model config
        adapter = await self._get_adapter(user_id)
        if adapter is None:
            yield format_sse("error", {"type": "error", "message": "未配置 AI 模型，请先在模型管理中添加并激活模型"})
            return

        # Resolve context window limit for this model
        max_context = get_model_context_limit(adapter.model_name)

        # Resolve class context for system prompt
        effective_class_id = class_id or conversation.class_id
        system_prompt = await self._build_system_prompt(user_id, effective_class_id)

        # Prepare tool definitions
        tool_defs = registry.get_definitions(role="admin")

        # Prepare API messages (loads history, compresses if needed)
        api_messages, total_tokens = await prepare_messages(
            str(conversation.id), self.db, adapter, system_prompt, len(tool_defs),
            max_context=max_context,
        )

        # Update token count
        conversation.token_count = total_tokens
        if effective_class_id and not conversation.class_id:
            conversation.class_id = effective_class_id
        await self.db.flush()

        # Run agent loop
        tool_ctx = ToolContext(
            user_id=user_id,
            admin_id=user_id,
            class_id=effective_class_id,
            db=self.db,
            adapter=adapter,
        )
        async for sse_event in self._agent_loop(
            conversation, api_messages, adapter, tool_defs, tool_ctx, system_prompt,
            max_context=max_context,
        ):
            yield sse_event

    async def handle_answer(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        answer: str,
    ) -> AsyncGenerator[str, None]:
        """Resume the agent loop after the user answers an ask_user question."""
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

        # Save the user's answer as a tool_result message
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

        # Reset conversation status
        conversation.status = "active"
        conversation.pending_tool_call_id = None
        await self.db.flush()

        # Resume the loop
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
        )
        async for sse_event in self._agent_loop(
            conversation, api_messages, adapter, tool_defs, tool_ctx, system_prompt,
            max_context=max_context,
        ):
            yield sse_event

    async def stop_generation(self, conversation_id: uuid.UUID) -> None:
        """Signal the agent loop to stop at the next yield point."""
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
        """Core loop: stream model output, execute tools, repeat until done."""
        conv_id = conversation.id
        AssistantService._cancel_flags[conv_id] = False
        tool_call_count = 0
        current_tools: list[ToolDefinition] | None = tool_defs

        try:
            while True:
                # Check cancel flag
                if AssistantService._cancel_flags.get(conv_id, False):
                    yield format_sse("done", {"type": "done"})
                    break

                # Accumulate the full assistant response
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
                                # Emit parsed args to frontend
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
                    logger.exception("Error during chat_stream for conversation %s", conv_id)
                    yield format_sse("error", {"type": "error", "message": "模型调用失败，请稍后重试"})
                    return

                # Cancelled mid-stream
                if AssistantService._cancel_flags.get(conv_id, False):
                    # Save whatever text we have so far
                    if text_parts:
                        await self._save_assistant_message(conversation, text_parts, [])
                    yield format_sse("done", {"type": "done"})
                    break

                # Process tool calls if any
                if completed_tool_calls:
                    # Build assistant message blocks (text + tool_use blocks)
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

                    # Save assistant message
                    assistant_msg = ConversationMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=assistant_blocks,
                        token_count=estimate_message_tokens(assistant_blocks),
                    )
                    self.db.add(assistant_msg)
                    await self.db.flush()

                    # Append to api_messages in OpenAI format for adapter compatibility
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

                    # Execute each tool
                    for tc in completed_tool_calls:
                        if AssistantService._cancel_flags.get(conv_id, False):
                            break

                        # --- ask_user interception ---
                        if tc.name == "ask_user":
                            question = tc.arguments.get("question", "")
                            options = tc.arguments.get("options")
                            yield format_sse("ask_user", {
                                "type": "ask_user",
                                "tool_call_id": tc.id,
                                "question": question,
                                "options": options,
                            })

                            # Insert placeholder tool_results for all remaining
                            # tool_calls (including this ask_user's siblings that
                            # haven't been executed) to keep tool_use/tool_result
                            # pairs complete.
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

                            # Pause the loop
                            conversation.status = "pending_answer"
                            conversation.pending_tool_call_id = tc.id
                            await self.db.commit()
                            yield format_sse("done", {"type": "done"})
                            return

                        # --- Normal tool execution ---
                        handler = registry.get_handler(tc.name)
                        if handler is None:
                            result_content = f"错误：未知工具 {tc.name}"
                            is_error = True
                        else:
                            try:
                                result_content = await handler.execute(tc.arguments, tool_ctx)
                                is_error = False
                            except Exception:
                                logger.exception("Tool %s execution failed", tc.name)
                                result_content = f"工具执行失败: {tc.name}"
                                is_error = True

                        yield format_sse("tool_call_result", {
                            "type": "tool_call_result",
                            "id": tc.id,
                            "result": result_content,
                            "is_error": is_error,
                        })

                        # Save tool result message
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

                        # Append to api_messages (encode error status in content
                        # text — OpenAI API rejects unknown fields like is_error)
                        api_content = f"[ERROR] {result_content}" if is_error else result_content
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": api_content,
                        })

                    # Update tool call count and enforce limit
                    tool_call_count += len(completed_tool_calls)
                    if tool_call_count >= MAX_TOOL_CALLS_PER_TURN:
                        logger.info(
                            "Tool call limit reached (%d) for conversation %s",
                            tool_call_count, conv_id,
                        )
                        current_tools = None  # Force final text response

                    # Continue loop for next model turn
                    continue

                # No tool calls — this is the final text response
                full_text = "".join(text_parts)
                if full_text:
                    await self._save_assistant_message(conversation, text_parts, [])

                # Emit token usage
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
                yield format_sse("done", {"type": "done"})
                break
        finally:
            AssistantService._cancel_flags.pop(conv_id, None)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_owned_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        with_messages: bool = False,
    ) -> Conversation:
        """Load a conversation and verify ownership."""
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
        """Resolve the active model config for the admin and create an adapter."""
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
        """Build the system prompt with class context if available."""
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
        # Fallback: no specific class context
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
        """Save a complete assistant message to the database."""
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
