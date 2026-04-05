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
    """Unified streaming event emitted by chat_stream() across all adapters."""

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

