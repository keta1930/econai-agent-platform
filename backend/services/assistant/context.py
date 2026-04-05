"""Context management: token estimation and automatic conversation compression."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation, ConversationMessage
from services.assistant.prompts import SUMMARY_PROMPT

if TYPE_CHECKING:
    from services.ai.base import BaseAIAdapter

logger = logging.getLogger(__name__)

# ---------- Constants ----------

DEFAULT_MAX_CONTEXT = 200_000
"""Fallback context window size when model-specific limit is unknown."""

# Known context window sizes for common models. Keys are matched as prefixes
# against the model name (e.g. "claude-sonnet-4-20250514" matches "claude-").
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
    """Return the context window size for a model name using prefix matching."""
    lower = model_name.lower()
    for prefix, limit in MODEL_CONTEXT_LIMITS.items():
        if lower.startswith(prefix):
            return limit
    return DEFAULT_MAX_CONTEXT


COMPRESS_THRESHOLD = 0.7
"""Trigger compression when token usage exceeds this ratio of available budget."""

TOKENS_PER_TOOL = 200
"""Approximate token overhead per tool definition sent to the model."""

_ENCODING: tiktoken.Encoding | None = None


def _get_encoding() -> tiktoken.Encoding:
    """Lazily initialise the tiktoken encoder (cl100k_base covers GPT-4 / Claude)."""
    global _ENCODING  # noqa: PLW0603
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


# ---------- Token estimation ----------


def estimate_tokens(text: str) -> int:
    """Estimate the token count for a plain text string."""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def estimate_message_tokens(content_blocks: list[dict]) -> int:
    """Estimate token count for a list of JSONB content blocks.

    Handles text, tool_use, tool_result, and file block types.
    """
    total = 0
    for block in content_blocks:
        block_type = block.get("type", "")
        if block_type == "text":
            total += estimate_tokens(block.get("text", ""))
        elif block_type == "tool_use":
            # Tool name + serialised input arguments
            total += estimate_tokens(block.get("name", ""))
            input_data = block.get("input")
            if input_data:
                total += estimate_tokens(
                    json.dumps(input_data, ensure_ascii=False)
                    if isinstance(input_data, dict)
                    else str(input_data)
                )
            # Overhead for structural tokens (id, type markers, etc.)
            total += 20
        elif block_type == "tool_result":
            total += estimate_tokens(block.get("content", ""))
            total += 10  # structural overhead
        elif block_type == "file":
            # File references are short metadata — filename + mime
            total += estimate_tokens(block.get("filename", ""))
            total += 10
    return total


# ---------- Public API ----------


async def prepare_messages(
    conversation_id: str,
    db: AsyncSession,
    adapter: BaseAIAdapter,
    system_prompt: str,
    tool_count: int,
    max_context: int = DEFAULT_MAX_CONTEXT,
) -> tuple[list[dict], int]:
    """Load conversation messages, compress if over threshold, return API-format messages.

    Returns:
        (api_messages, total_token_count) where api_messages is ready for
        ``adapter.chat_stream()`` and total_token_count includes system prompt
        and tool overhead.
    """
    # Query messages directly instead of loading via relationship.
    # This avoids SQLAlchemy identity-map caching issues where a
    # previously loaded Conversation object returns stale (empty)
    # messages even after new ones have been flushed in the same session.
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at)
    )
    messages: list[ConversationMessage] = list(result.scalars().all())
    if not messages:
        logger.warning("No messages found for conversation %s", conversation_id)
        system_tokens = estimate_tokens(system_prompt)
        tool_overhead = tool_count * TOKENS_PER_TOOL
        return [], system_tokens + tool_overhead

    system_tokens = estimate_tokens(system_prompt)
    tool_overhead = tool_count * TOKENS_PER_TOOL
    available = max_context - tool_overhead - system_tokens

    message_tokens = sum(m.token_count for m in messages)

    if message_tokens <= available * COMPRESS_THRESHOLD:
        api_messages = rebuild_api_messages(messages)
        total = system_tokens + tool_overhead + message_tokens
        return api_messages, total

    # Compression needed
    logger.info(
        "Compressing conversation %s: %d tokens exceeds %.0f%% of %d available",
        conversation_id,
        message_tokens,
        COMPRESS_THRESHOLD * 100,
        available,
    )
    compressed_orm = await compress_messages(messages, adapter, available)
    api_messages = rebuild_api_messages(compressed_orm)
    compressed_tokens = sum(
        m.token_count if isinstance(m, ConversationMessage) else estimate_tokens(m.get("_text", ""))
        for m in compressed_orm
    )
    total = system_tokens + tool_overhead + compressed_tokens

    # Update conversation token count in DB
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
    """Compress messages by summarising the middle portion.

    Strategy:
    - Keep the earliest 2 messages (establishes conversation context)
    - Keep the most recent N messages within 60% of available budget
    - Summarise the middle messages into a single synthetic message

    Returns a mixed list: original ORM messages + one synthetic summary dict.
    """
    if len(messages) <= 4:
        # Too few messages to compress meaningfully
        return list(messages)

    # Partition: early | middle | recent
    early = messages[:2]

    # Select recent messages, working backwards, within 60% budget
    recent_budget = int(available_tokens * 0.6)
    recent: list[ConversationMessage] = []
    recent_tokens = 0

    for msg in reversed(messages[2:]):
        msg_tokens = msg.token_count or 0
        if recent_tokens + msg_tokens > recent_budget:
            break
        recent.insert(0, msg)
        recent_tokens += msg_tokens

    # Ensure tool_use/tool_result pairing at the boundary
    recent = _fix_pair_boundary(messages[2:], recent)

    # If recent covers everything after early, no compression needed
    middle_end = len(messages) - len(recent) if recent else len(messages)
    middle = messages[2:middle_end]

    if not middle:
        return list(messages)

    # Generate summary of middle messages
    conversation_text = _format_messages_for_summary(middle)
    summary_text = await _generate_summary(conversation_text, adapter)

    # Build synthetic summary message (dict, not ORM)
    summary_msg = {
        "_synthetic": True,
        "_text": summary_text,
        "role": "user",
        "content": [{"type": "text", "text": f"[对话历史摘要]\n{summary_text}"}],
        "token_count": estimate_tokens(summary_text),
    }

    return list(early) + [summary_msg] + list(recent)


def rebuild_api_messages(
    orm_messages: list[ConversationMessage | dict],
) -> list[dict]:
    """Convert ORM messages (or synthetic dicts) to the OpenAI API message format.

    Output uses OpenAI's standard format as the internal representation:
    - Assistant messages with tool calls use top-level ``tool_calls`` field.
    - Tool result messages use ``role: "tool"`` with ``tool_call_id``.
    - The Anthropic adapter's ``_convert_messages()`` handles conversion
      from this format to Anthropic's native format.
    """
    api_messages: list[dict] = []

    for msg in orm_messages:
        if isinstance(msg, dict):
            # Synthetic summary message
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"][0]["text"] if msg.get("content") else "",
            })
            continue

        role = msg.role
        blocks: list[dict] = msg.content if isinstance(msg.content, list) else []

        if role == "user":
            # Extract text content; include file references as text annotations
            text_parts: list[str] = []
            for block in blocks:
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "file":
                    text_parts.append(
                        f'[附件: {block.get("filename", "unknown")}]'
                    )
            api_messages.append({
                "role": "user",
                "content": "\n".join(text_parts) if text_parts else "",
            })

        elif role == "assistant":
            # Separate text and tool_use blocks, output OpenAI format
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
            # Each tool block maps to a tool_result message.
            # is_error is kept in JSONB for frontend display but excluded
            # from API messages — OpenAI rejects unknown fields.  Error
            # status is encoded as a "[ERROR] " content prefix instead.
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
            # System messages pass through as-is
            text = " ".join(
                b.get("text", "") for b in blocks if b.get("type") == "text"
            )
            if text:
                api_messages.append({"role": "system", "content": text})

    return api_messages


def validate_message_pairs(messages: list[dict]) -> bool:
    """Check that every tool_call in an assistant message has a matching tool result.

    Expects OpenAI-format api_messages (top-level ``tool_calls`` field).
    Returns True if all pairs are complete, False otherwise.
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
        logger.warning("Unpaired tool_use IDs: %s", pending_ids)
        return False
    return True


# ---------- Internal helpers ----------


def _fix_pair_boundary(
    all_after_early: list[ConversationMessage],
    recent: list[ConversationMessage],
) -> list[ConversationMessage]:
    """Ensure the first message in `recent` doesn't orphan a tool_use/tool_result pair.

    If the first recent message is a tool-role message, prepend the preceding
    assistant message that contains the matching tool_use.
    """
    if not recent:
        return recent

    first = recent[0]
    if first.role != "tool":
        return recent

    # Find the position of `first` in the full list and walk backwards
    try:
        idx = all_after_early.index(first)
    except ValueError:
        return recent

    # Walk backwards to find the assistant message with the tool_use
    for i in range(idx - 1, -1, -1):
        candidate = all_after_early[i]
        if candidate.role == "assistant":
            # Check this assistant message contains tool_use blocks
            blocks = candidate.content if isinstance(candidate.content, list) else []
            has_tool_use = any(b.get("type") == "tool_use" for b in blocks)
            if has_tool_use:
                # Also include any tool messages between this assistant and `first`
                return list(all_after_early[i:idx]) + recent
            break

    return recent


def _format_messages_for_summary(messages: list[ConversationMessage]) -> str:
    """Format ORM messages into readable text for the summary prompt."""
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
            elif btype == "tool_use":
                text_parts.append(f'[调用工具: {block.get("name", "")}]')
            elif btype == "tool_result":
                content = block.get("content", "")
                # Truncate long tool results
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
    """Call the adapter to generate a conversation summary."""
    prompt = SUMMARY_PROMPT.format(conversation_text=conversation_text)
    response = await adapter.async_chat(
        messages=[{"role": "user", "content": prompt}],
        tools=None,
    )
    return response.text or ""
