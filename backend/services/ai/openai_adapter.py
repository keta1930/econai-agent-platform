import json
import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI, OpenAI

from services.ai.base import (
    BaseAIAdapter,
    ChatResponse,
    StreamEvent,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "timeout": 120,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        logger.info("OpenAI 调用 — 模型=%s, 消息数=%d", self.model_name, len(messages))
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception:
            logger.exception("OpenAI 调用失败 — 模型=%s", self.model_name)
            raise
        if response.usage:
            logger.info("OpenAI 完成 — 输入 token=%d, 输出 token=%d", response.usage.prompt_tokens, response.usage.completion_tokens)
        choice = response.choices[0].message

        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("工具调用参数格式错误: %s", tc.function.arguments[:200])
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        return ChatResponse(text=choice.content, tool_calls=tool_calls)

    async def async_chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "timeout": 120,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        logger.info("OpenAI 异步调用 — 模型=%s, 消息数=%d", self.model_name, len(messages))
        try:
            response = await self.async_client.chat.completions.create(**kwargs)
        except Exception:
            logger.exception("OpenAI 异步调用失败 — 模型=%s", self.model_name)
            raise
        if response.usage:
            logger.info("OpenAI 异步完成 — 输入 token=%d, 输出 token=%d", response.usage.prompt_tokens, response.usage.completion_tokens)
        choice = response.choices[0].message

        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("工具调用参数格式错误: %s", tc.function.arguments[:200])
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        return ChatResponse(text=choice.content, tool_calls=tool_calls)

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "timeout": 120,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        logger.info("OpenAI 流式调用 — 模型=%s, 消息数=%d", self.model_name, len(messages))
        try:
            stream = await self.async_client.chat.completions.create(**kwargs)
        except Exception:
            logger.exception("OpenAI 流式调用失败 — 模型=%s", self.model_name)
            raise

        # 按 index 累积工具调用
        pending_tool_calls: dict[int, dict] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            finish_reason = chunk.choices[0].finish_reason

            # 文本内容
            if delta.content:
                yield StreamEvent(type="text_delta", text=delta.content)

            # 工具调用 — OpenAI 增量式流式传输，
            # 通过 index 区分同一消息中的并行调用
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index

                    if idx not in pending_tool_calls:
                        # 该工具调用的第一个 chunk 携带 id 和 name
                        pending_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": (tc_delta.function.name if tc_delta.function else "") or "",
                            "arguments": "",
                        }
                        if tc_delta.id and tc_delta.function and tc_delta.function.name:
                            yield StreamEvent(
                                type="tool_call_start",
                                tool_call_id=tc_delta.id,
                                tool_name=tc_delta.function.name,
                            )

                    # 累积参数片段
                    if tc_delta.function and tc_delta.function.arguments:
                        fragment = tc_delta.function.arguments
                        pending_tool_calls[idx]["arguments"] += fragment
                        yield StreamEvent(
                            type="tool_call_args_delta",
                            tool_call_id=pending_tool_calls[idx]["id"],
                            partial_json=fragment,
                        )

            # 流结束 — 为每个待处理调用发出 tool_call_end，
            # 然后发出带完整列表的 message_end
            if finish_reason is not None:
                completed: list[ToolCall] = []
                for idx in sorted(pending_tool_calls):
                    tc = pending_tool_calls[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        logger.warning("工具调用参数格式错误: %s", tc["arguments"][:200])
                        args = {}
                    completed.append(ToolCall(id=tc["id"], name=tc["name"], arguments=args))
                    yield StreamEvent(type="tool_call_end", tool_call_id=tc["id"])

                yield StreamEvent(
                    type="message_end",
                    tool_calls=completed if completed else None,
                )
