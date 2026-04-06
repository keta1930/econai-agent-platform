"""上下文管理：token 估算与自动对话压缩。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation, ConversationMessage
from services.ai.vision import build_image_block
from services.assistant.prompts import SUMMARY_PROMPT
from services.storage import storage_service

if TYPE_CHECKING:
    from services.ai.base import BaseAIAdapter

logger = logging.getLogger(__name__)

# ---------- 常量 ----------

DEFAULT_MAX_CONTEXT = 200_000
"""模型上下文窗口大小的默认回退值。"""

# 常用模型的上下文窗口大小。键作为前缀与模型名称匹配
# （例如 "claude-sonnet-4-20250514" 匹配 "claude-"）。
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "claude-":        200_000,
    "gpt-4o":         128_000,
    "gpt-4-turbo":    128_000,
    "gpt-4.1":        1_047_576,
    "gpt-4":            8_192,
    "o3":             200_000,
    "o4-mini":        200_000,
    "deepseek":       128_000,
}


def get_model_context_limit(model_name: str) -> int:
    """通过前缀匹配返回模型的上下文窗口大小。"""
    lower = model_name.lower()
    for prefix, limit in MODEL_CONTEXT_LIMITS.items():
        if lower.startswith(prefix):
            return limit
    return DEFAULT_MAX_CONTEXT


COMPRESS_THRESHOLD = 0.7
"""token 使用量超过可用预算的此比例时触发压缩。"""

TOKENS_PER_TOOL = 200
"""每个工具定义发送到模型时的近似 token 开销。"""

_ENCODING: tiktoken.Encoding | None = None


def _get_encoding() -> tiktoken.Encoding:
    """延迟初始化 tiktoken 编码器（cl100k_base 覆盖 GPT-4 / Claude）。"""
    global _ENCODING  # noqa: PLW0603
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


# ---------- Token 估算 ----------


def estimate_tokens(text: str) -> int:
    """估算纯文本字符串的 token 数。"""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def estimate_message_tokens(content_blocks: list[dict]) -> int:
    """估算 JSONB 内容块列表的 token 数。

    处理 text、tool_use、tool_result 和 file 块类型。
    """
    total = 0
    for block in content_blocks:
        block_type = block.get("type", "")
        if block_type == "text":
            total += estimate_tokens(block.get("text", ""))
        elif block_type == "tool_use":
            # 工具名称 + 序列化的输入参数
            total += estimate_tokens(block.get("name", ""))
            input_data = block.get("input")
            if input_data:
                total += estimate_tokens(
                    json.dumps(input_data, ensure_ascii=False)
                    if isinstance(input_data, dict)
                    else str(input_data)
                )
            # 结构性 token 开销（id、type 标记等）
            total += 20
        elif block_type == "tool_result":
            total += estimate_tokens(block.get("content", ""))
            total += 10  # 结构性开销
        elif block_type == "file":
            # 文件引用是简短元数据 — 文件名 + MIME 类型
            total += estimate_tokens(block.get("filename", ""))
            total += 10
        elif block_type == "image":
            # 图片 token 的保守估算（覆盖大多数 VLM 定价）
            total += 300
    return total


# ---------- 公开 API ----------


async def prepare_messages(
    conversation_id: str,
    db: AsyncSession,
    adapter: BaseAIAdapter,
    system_prompt: str,
    tool_count: int,
    max_context: int = DEFAULT_MAX_CONTEXT,
) -> tuple[list[dict], int]:
    """加载对话消息，超过阈值时压缩，返回 API 格式的消息。

    返回:
        (api_messages, total_token_count)，其中 api_messages 可直接传给
        ``adapter.chat_stream()``，total_token_count 包含 system prompt
        和工具开销。
    """
    # 直接查询消息而非通过 relationship 加载。
    # 避免 SQLAlchemy identity-map 缓存问题：之前加载的 Conversation
    # 对象在同一 session 中 flush 新消息后仍返回旧的（空的）消息。
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at)
    )
    messages: list[ConversationMessage] = list(result.scalars().all())
    if not messages:
        logger.warning("未找到消息 — 对话=%s", conversation_id)
        system_tokens = estimate_tokens(system_prompt)
        tool_overhead = tool_count * TOKENS_PER_TOOL
        return [], system_tokens + tool_overhead

    system_tokens = estimate_tokens(system_prompt)
    tool_overhead = tool_count * TOKENS_PER_TOOL
    available = max_context - tool_overhead - system_tokens

    message_tokens = sum(m.token_count for m in messages)

    if message_tokens <= available * COMPRESS_THRESHOLD:
        api_messages = await rebuild_api_messages(messages)
        total = system_tokens + tool_overhead + message_tokens
        return api_messages, total

    # 需要压缩
    logger.warning(
        "对话压缩触发 — token 使用率=%.0f%%, 对话=%s",
        message_tokens / available * 100,
        conversation_id,
    )
    logger.info(
        "对话压缩 — 消息 token=%d, 可用=%d, 对话=%s",
        message_tokens,
        available,
        conversation_id,
    )
    compressed_orm = await compress_messages(messages, adapter, available)
    api_messages = await rebuild_api_messages(compressed_orm)
    compressed_tokens = sum(
        m.token_count if isinstance(m, ConversationMessage) else estimate_tokens(m.get("_text", ""))
        for m in compressed_orm
    )
    total = system_tokens + tool_overhead + compressed_tokens

    # 更新数据库中的对话 token 计数
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalar_one_or_none()
    if conv:
        conv.token_count = total
        await db.flush()

    return api_messages, total


async def compress_messages(
    messages: list[ConversationMessage],
    adapter: BaseAIAdapter,
    available_tokens: int,
) -> list[ConversationMessage | dict]:
    """通过摘要中间部分来压缩消息。

    策略:
    - 保留最早的 2 条消息（建立对话上下文）
    - 保留最近的 N 条消息（占可用预算的 60%）
    - 将中间消息摘要为一条合成消息

    返回混合列表：原始 ORM 消息 + 一条合成摘要 dict。
    """
    if len(messages) <= 4:
        # 消息太少，无法有效压缩
        return list(messages)

    # 分区: early | middle | recent
    early = messages[:2]

    # 从后往前选择最近的消息，预算为 60%
    recent_budget = int(available_tokens * 0.6)
    recent: list[ConversationMessage] = []
    recent_tokens = 0

    for msg in reversed(messages[2:]):
        msg_tokens = msg.token_count or 0
        if recent_tokens + msg_tokens > recent_budget:
            break
        recent.insert(0, msg)
        recent_tokens += msg_tokens

    # 确保边界处 tool_use/tool_result 配对完整
    recent = _fix_pair_boundary(messages[2:], recent)

    # 如果 recent 覆盖了 early 之后的所有消息，则无需压缩
    middle_end = len(messages) - len(recent) if recent else len(messages)
    middle = messages[2:middle_end]

    if not middle:
        return list(messages)

    # 生成中间消息的摘要
    conversation_text = _format_messages_for_summary(middle)
    summary_text = await _generate_summary(conversation_text, adapter)

    # 构建合成摘要消息（dict，非 ORM）
    summary_msg = {
        "_synthetic": True,
        "_text": summary_text,
        "role": "user",
        "content": [{"type": "text", "text": f"[对话历史摘要]\n{summary_text}"}],
        "token_count": estimate_tokens(summary_text),
    }

    return list(early) + [summary_msg] + list(recent)


async def rebuild_api_messages(
    orm_messages: list[ConversationMessage | dict],
) -> list[dict]:
    """将 ORM 消息（或合成 dict）转换为 OpenAI API 消息格式。

    输出使用 OpenAI 标准格式作为内部表示：
    - 带工具调用的助手消息使用顶层 ``tool_calls`` 字段。
    - 工具结果消息使用 ``role: "tool"`` 加 ``tool_call_id``。
    - 图片块从存储中获取并转换为多模态内容块数组（base64 内联）。
    - Anthropic adapter 的 ``_convert_messages()`` 负责从此格式
      转换为 Anthropic 原生格式。
    """
    api_messages: list[dict] = []

    for msg in orm_messages:
        if isinstance(msg, dict):
            # 合成摘要消息
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"][0]["text"] if msg.get("content") else "",
            })
            continue

        role = msg.role
        blocks: list[dict] = msg.content if isinstance(msg.content, list) else []

        if role == "user":
            text_parts: list[str] = []
            image_blocks: list[dict] = []
            for block in blocks:
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "file":
                    filename = block.get("filename", "unknown")
                    file_id = block.get("file_id", "")
                    text_parts.append(
                        f'[附件: {filename} | file_id: {file_id}]'
                    )
                elif block.get("type") == "image":
                    file_id = block.get("file_id", "")
                    mime_type = block.get("mime_type", "image/png")
                    try:
                        img_bytes = await asyncio.to_thread(
                            storage_service.get_object, file_id,
                        )
                        image_blocks.append(
                            build_image_block(img_bytes, mime_type)
                        )
                    except Exception:
                        logger.warning("图片加载失败，跳过 — file_id=%s", file_id)
                        text_parts.append(f'[图片加载失败: {block.get("filename", "")}]')

            text_content = "\n".join(text_parts) if text_parts else ""
            if image_blocks:
                # 多模态：content 为块数组
                content: str | list[dict] = [{"type": "text", "text": text_content}] + image_blocks
            else:
                content = text_content
            api_messages.append({"role": "user", "content": content})

        elif role == "assistant":
            # 分离 text 和 tool_use 块，输出 OpenAI 格式
            text_parts: list[str] = []
            tool_calls_list: list[dict] = []
            for block in blocks:
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool_calls_list.append({
                        "id": block["tool_call_id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(
                                block.get("input", {}), ensure_ascii=False,
                            ),
                        },
                    })
            joined_text = " ".join(text_parts) if text_parts else None
            msg_dict: dict = {"role": "assistant", "content": joined_text}
            if tool_calls_list:
                msg_dict["tool_calls"] = tool_calls_list
            api_messages.append(msg_dict)

        elif role == "tool":
            # 每个 tool block 对应一条 tool_result 消息。
            # is_error 保留在 JSONB 中供前端显示，但从 API 消息中排除
            # — OpenAI 拒绝未知字段。错误状态改为 "[ERROR] " 内容前缀。
            for block in blocks:
                if block.get("type") == "tool_result":
                    content = block.get("content", "")
                    if block.get("is_error") and not content.startswith("[ERROR] "):
                        content = f"[ERROR] {content}"
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": block["tool_call_id"],
                        "content": content,
                    })

        elif role == "system":
            # system 消息直接透传
            text = " ".join(
                b.get("text", "") for b in blocks if b.get("type") == "text"
            )
            if text:
                api_messages.append({"role": "system", "content": text})

    return api_messages


def validate_message_pairs(messages: list[dict]) -> bool:
    """检查助手消息中每个 tool_call 是否都有对应的 tool result。

    期望 OpenAI 格式的 api_messages（顶层 ``tool_calls`` 字段）。
    所有配对完整返回 True，否则返回 False。
    """
    pending_ids: set[str] = set()

    for msg in messages:
        role = msg.get("role", "")

        if role == "assistant":
            for tc in msg.get("tool_calls", []):
                tc_id = tc.get("id", "")
                if tc_id:
                    pending_ids.add(tc_id)

        elif role == "tool":
            tool_call_id = msg.get("tool_call_id", "")
            if tool_call_id:
                pending_ids.discard(tool_call_id)

    if pending_ids:
        logger.warning("未配对的 tool_use ID: %s", pending_ids)
        return False
    return True


# ---------- 内部辅助函数 ----------


def _fix_pair_boundary(
    all_after_early: list[ConversationMessage],
    recent: list[ConversationMessage],
) -> list[ConversationMessage]:
    """确保 `recent` 的第一条消息不会孤立 tool_use/tool_result 配对。

    如果 recent 的第一条是 tool 角色消息，前置包含匹配 tool_use 的
    assistant 消息。
    """
    if not recent:
        return recent

    first = recent[0]
    if first.role != "tool":
        return recent

    # 在完整列表中找到 `first` 的位置并向前回溯
    try:
        idx = all_after_early.index(first)
    except ValueError:
        return recent

    # 向前回溯找到包含 tool_use 的 assistant 消息
    for i in range(idx - 1, -1, -1):
        candidate = all_after_early[i]
        if candidate.role == "assistant":
            # 检查此 assistant 消息是否包含 tool_use 块
            blocks = candidate.content if isinstance(candidate.content, list) else []
            has_tool_use = any(b.get("type") == "tool_use" for b in blocks)
            if has_tool_use:
                # 同时包含此 assistant 与 `first` 之间的所有 tool 消息
                return list(all_after_early[i:idx]) + recent
            break

    return recent


def _format_messages_for_summary(messages: list[ConversationMessage]) -> str:
    """将 ORM 消息格式化为可读文本，供摘要 prompt 使用。"""
    lines: list[str] = []
    for msg in messages:
        role_label = {"user": "教师", "assistant": "助教", "tool": "工具结果", "system": "系统"}.get(
            msg.role, msg.role
        )
        blocks = msg.content if isinstance(msg.content, list) else []
        text_parts: list[str] = []
        for block in blocks:
            btype = block.get("type", "")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "image":
                text_parts.append(f'[图片: {block.get("filename", "")}]')
            elif btype == "tool_use":
                text_parts.append(f'[调用工具: {block.get("name", "")}]')
            elif btype == "tool_result":
                content = block.get("content", "")
                # 截断过长的工具结果
                if len(content) > 200:
                    content = content[:200] + "..."
                text_parts.append(f"[工具返回: {content}]")
        if text_parts:
            lines.append(f"{role_label}: {' '.join(text_parts)}")
    return "\n".join(lines)


async def _generate_summary(
    conversation_text: str,
    adapter: BaseAIAdapter,
) -> str:
    """调用 adapter 生成对话摘要。"""
    prompt = SUMMARY_PROMPT.format(conversation_text=conversation_text)
    response = await adapter.async_chat(
        messages=[{"role": "user", "content": prompt}],
        tools=None,
    )
    return response.text or ""
