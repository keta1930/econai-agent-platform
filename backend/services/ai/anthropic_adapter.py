import json
import logging
import re
from collections.abc import AsyncIterator

from anthropic import Anthropic, AsyncAnthropic

from services.ai.base import (
    BaseAIAdapter,
    ChatResponse,
    StreamEvent,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = Anthropic(api_key=api_key, base_url=base_url)
        self.async_client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    def _convert_messages(
        self, messages: list[dict]
    ) -> tuple[str | None, list[dict]]:
        """将 OpenAI 格式消息转换为 Anthropic API 格式。

        返回 (system_content, api_messages)。
        """
        system_content = None
        api_messages: list[dict] = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"],
                        }
                    ],
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                content: list[dict] = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    tc_args = func.get("arguments", tc.get("arguments", {}))
                    if isinstance(tc_args, str):
                        try:
                            tc_args = json.loads(tc_args)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning("工具调用参数格式错误: %s", tc_args[:200])
                            tc_args = {}
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": func.get("name", tc.get("name")),
                        "input": tc_args,
                    })
                api_messages.append({"role": "assistant", "content": content})
            else:
                content = msg["content"]
                if isinstance(content, list):
                    content = self._convert_content_blocks(content)
                api_messages.append({"role": msg["role"], "content": content})
        return system_content, api_messages

    @staticmethod
    def _convert_content_blocks(blocks: list[dict]) -> list[dict]:
        """将 OpenAI 格式内容块转换为 Anthropic 格式。

        处理 image_url 块：从 data URI 中提取 base64 数据，
        转换为 Anthropic 的 image source 格式。
        """
        converted: list[dict] = []
        for block in blocks:
            if block.get("type") == "image_url":
                url = block["image_url"]["url"]
                match = re.match(r"data:([^;]+);base64,(.+)", url, re.DOTALL)
                if match:
                    converted.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": match.group(1),
                            "data": match.group(2),
                        },
                    })
                else:
                    # 非 base64 的 URL 图片 — 直接透传
                    converted.append({
                        "type": "image",
                        "source": {"type": "url", "url": url},
                    })
            else:
                converted.append(block)
        return converted

    @staticmethod
    def _build_tools_param(tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    def chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        system_content, api_messages = self._convert_messages(messages)

        kwargs: dict = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": api_messages,
            "timeout": 120,
        }
        if system_content:
            kwargs["system"] = system_content
        if tools:
            kwargs["tools"] = self._build_tools_param(tools)

        logger.info("Anthropic 调用 — 模型=%s, 消息数=%d", self.model_name, len(api_messages))
        try:
            response = self.client.messages.create(**kwargs)
        except Exception:
            logger.exception("Anthropic 调用失败 — 模型=%s", self.model_name)
            raise
        logger.info("Anthropic 完成 — 输入 token=%d, 输出 token=%d", response.usage.input_tokens, response.usage.output_tokens)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return ChatResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )

    async def async_chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        system_content, api_messages = self._convert_messages(messages)

        kwargs: dict = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": api_messages,
            "timeout": 120,
        }
        if system_content:
            kwargs["system"] = system_content
        if tools:
            kwargs["tools"] = self._build_tools_param(tools)

        logger.info("Anthropic 异步调用 — 模型=%s, 消息数=%d", self.model_name, len(api_messages))
        try:
            response = await self.async_client.messages.create(**kwargs)
        except Exception:
            logger.exception("Anthropic 异步调用失败 — 模型=%s", self.model_name)
            raise
        logger.info("Anthropic 异步完成 — 输入 token=%d, 输出 token=%d", response.usage.input_tokens, response.usage.output_tokens)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return ChatResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        system_content, api_messages = self._convert_messages(messages)

        kwargs: dict = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": api_messages,
            "timeout": 120,
        }
        if system_content:
            kwargs["system"] = system_content
        if tools:
            kwargs["tools"] = self._build_tools_param(tools)

        logger.info("Anthropic 流式调用 — 模型=%s, 消息数=%d", self.model_name, len(api_messages))

        # 按 index 追踪内容块 — Anthropic 通过整数 index
        # 发送 content_block_start/delta/stop 事件
        active_blocks: dict[int, dict] = {}
        completed_tool_calls: list[ToolCall] = []

        try:
            stream_ctx = self.async_client.messages.stream(**kwargs)
        except Exception:
            logger.exception("Anthropic 流式调用启动失败 — 模型=%s", self.model_name)
            raise

        async with stream_ctx as stream:
            async for event in stream:
                event_type = event.type

                if event_type == "content_block_start":
                    block = event.content_block
                    idx = event.index
                    if block.type == "text":
                        active_blocks[idx] = {"type": "text"}
                    elif block.type == "tool_use":
                        active_blocks[idx] = {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "arguments": "",
                        }
                        yield StreamEvent(
                            type="tool_call_start",
                            tool_call_id=block.id,
                            tool_name=block.name,
                        )

                elif event_type == "content_block_delta":
                    idx = event.index
                    delta = event.delta

                    if delta.type == "text_delta":
                        yield StreamEvent(type="text_delta", text=delta.text)
                    elif delta.type == "input_json_delta":
                        block_info = active_blocks.get(idx)
                        if block_info and block_info["type"] == "tool_use":
                            block_info["arguments"] += delta.partial_json
                            yield StreamEvent(
                                type="tool_call_args_delta",
                                tool_call_id=block_info["id"],
                                partial_json=delta.partial_json,
                            )

                elif event_type == "content_block_stop":
                    idx = event.index
                    block_info = active_blocks.pop(idx, None)
                    if block_info and block_info["type"] == "tool_use":
                        try:
                            args = json.loads(block_info["arguments"]) if block_info["arguments"] else {}
                        except json.JSONDecodeError:
                            logger.warning("工具调用参数格式错误: %s", block_info["arguments"][:200])
                            args = {}
                        completed_tool_calls.append(
                            ToolCall(id=block_info["id"], name=block_info["name"], arguments=args)
                        )
                        yield StreamEvent(type="tool_call_end", tool_call_id=block_info["id"])

                elif event_type == "message_stop":
                    yield StreamEvent(
                        type="message_end",
                        tool_calls=completed_tool_calls if completed_tool_calls else None,
                    )
