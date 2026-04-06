from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class StreamEvent:
    """所有适配器 chat_stream() 统一的流式事件。"""

    type: Literal[
        "text_delta",
        "tool_call_start",
        "tool_call_args_delta",
        "tool_call_end",
        "message_end",
    ]
    text: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    partial_json: str | None = None
    tool_calls: list[ToolCall] | None = None


class BaseAIAdapter(ABC):
    """AI 模型适配器基类。

    消息统一使用 OpenAI 格式作为内部表示。
    每条消息的 ``content`` 字段可以是：
    - ``str`` — 纯文本消息
    - ``list[dict]`` — 多模态内容块数组（text + image_url 块）

    具体适配器负责将此格式转换为各供应商的原生格式
    （如 Anthropic 的 image source 块）。
    """

    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        ...

    @abstractmethod
    async def async_chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        ...

