"""工具子系统 — 所有助手工具的注册与分发。"""

from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry, registry
from services.assistant.tools.query_tools import register_query_tools
from services.assistant.tools.action_tools import register_action_tools
from services.assistant.tools.system_tools import register_system_tools
from services.assistant.tools.file_tools import register_file_tools
from services.assistant.tools.skill_tools import register_skill_tools


def _register_all() -> None:
    """将所有工具类别注册到全局注册表。"""
    register_query_tools(registry)
    register_action_tools(registry)
    register_system_tools(registry)
    register_file_tools(registry)
    register_skill_tools(registry)


_register_all()

__all__ = ["ToolContext", "ToolHandler", "ToolRegistry", "registry"]
