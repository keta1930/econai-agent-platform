from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.base import ToolDefinition

if TYPE_CHECKING:
    from services.ai.base import BaseAIAdapter


@dataclass
class ToolContext:
    """Execution context passed to every tool handler."""

    user_id: uuid.UUID
    admin_id: uuid.UUID
    class_id: uuid.UUID | None
    db: AsyncSession
    adapter: BaseAIAdapter | None = None


# Type alias for tool execute functions:
#   async def execute(args: dict, ctx: ToolContext) -> str
ToolExecuteFn = Callable[[dict[str, Any], ToolContext], Coroutine[Any, Any, str]]


@dataclass
class ToolHandler:
    """A registered tool: its AI-facing definition + runtime metadata."""

    definition: ToolDefinition
    execute: ToolExecuteFn
    display_name: str
    allowed_roles: list[str] = field(default_factory=lambda: ["admin"])
    requires_confirmation: bool = False


class ToolRegistry:
    """Central registry for all assistant tools."""

    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, handler: ToolHandler) -> None:
        self._handlers[handler.definition.name] = handler

    def get_definitions(self, role: str) -> list[ToolDefinition]:
        """Return tool definitions visible to the given role."""
        return [
            h.definition
            for h in self._handlers.values()
            if role in h.allowed_roles
        ]

    def get_handler(self, name: str) -> ToolHandler | None:
        return self._handlers.get(name)

    def get_display_name(self, name: str) -> str:
        handler = self._handlers.get(name)
        return handler.display_name if handler else name


# Module-level singleton
registry = ToolRegistry()
