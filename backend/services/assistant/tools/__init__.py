"""Tool subsystem — registration and dispatch for all assistant tools."""

from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry, registry
from services.assistant.tools.query_tools import register_query_tools
from services.assistant.tools.action_tools import register_action_tools
from services.assistant.tools.system_tools import register_system_tools
from services.assistant.tools.file_tools import register_file_tools


def _register_all() -> None:
    """Register every tool category into the global registry."""
    register_query_tools(registry)
    register_action_tools(registry)
    register_system_tools(registry)
    register_file_tools(registry)


_register_all()

__all__ = ["ToolContext", "ToolHandler", "ToolRegistry", "registry"]
