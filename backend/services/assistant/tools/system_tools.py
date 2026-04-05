from __future__ import annotations

import asyncio
import json
import logging

from tavily import TavilyClient

from config import TAVILY_API_KEY
from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry

logger = logging.getLogger(__name__)

# Course-specific domains: AI Agent design curriculum
SEARCH_DOMAINS = [
    "https://code.claude.com/docs/",
    "https://opencode.ai/docs",
    "https://docs.openclaw.ai/",
    "https://developers.openai.com/codex",
]

# Minimum relevance score to include a content item
MIN_CONTENT_SCORE = 0.6
MAX_CONTENT_ITEMS = 3


# ---------------------------------------------------------------------------
# 1. ask_user
# ---------------------------------------------------------------------------

async def execute_ask_user(args: dict, ctx: ToolContext) -> str:
    """Placeholder — actual handling is intercepted by AssistantService."""
    return ""


# ---------------------------------------------------------------------------
# 2. tavily_search
# ---------------------------------------------------------------------------

def _call_tavily(query: str) -> str:
    """Call Tavily API and return formatted answer + high-relevance content."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="advanced",
        include_answer="advanced",
        max_results=6,
        include_domains=SEARCH_DOMAINS,
    )

    parts: list[str] = []

    # Answer: Tavily's built-in agent summary across all results
    answer = response.get("answer", "")
    if answer:
        parts.append(f"## 摘要\n\n{answer}")

    # Content: only items with score >= threshold, max 3
    results = response.get("results", [])
    high_score = [r for r in results if r.get("score", 0) >= MIN_CONTENT_SCORE]
    for result in high_score[:MAX_CONTENT_ITEMS]:
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")
        parts.append(f"### {title}\n**URL:** {url}\n\n{content}")

    return "\n\n---\n\n".join(parts) if parts else "No results found."


async def execute_tavily_search(args: dict, ctx: ToolContext) -> str:
    query = args.get("query", "").strip()
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    try:
        result_text = await asyncio.to_thread(_call_tavily, query)
    except Exception:
        logger.exception("Tavily search failed for query: %s", query)
        return json.dumps({"error": "搜索失败，请稍后重试"}, ensure_ascii=False)

    return result_text


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_system_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="ask_user",
            description=(
                "向用户提问以澄清意图或确认操作。支持单选和多选模式。"
                "options 中的每个选项可以是纯字符串，也可以是 {label, description} "
                "对象以提供更多上下文。select_mode='multiple' 时用户可以选择多个选项。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "向用户提出的问题",
                    },
                    "options": {
                        "type": "array",
                        "description": (
                            "选项列表。每个选项可以是字符串，"
                            "或包含 label 和 description 的对象"
                        ),
                        "items": {
                            "oneOf": [
                                {"type": "string"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "label": {
                                            "type": "string",
                                            "description": "选项标签",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "选项说明",
                                        },
                                    },
                                    "required": ["label"],
                                },
                            ],
                        },
                    },
                    "select_mode": {
                        "type": "string",
                        "enum": ["single", "multiple"],
                        "description": (
                            "选择模式：single 单选（默认）、multiple 多选"
                        ),
                    },
                },
                "required": ["question"],
            },
        ),
        execute=execute_ask_user,
        display_name="向用户提问",
    ))

    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="tavily_search",
            description=(
                "搜索网络获取最新信息。用于查找课程资料、技术文档、学术资源等。"
                "返回搜索结果摘要。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词（建议使用英文以获得更好的结果）",
                    },
                },
                "required": ["query"],
            },
        ),
        execute=execute_tavily_search,
        display_name="搜索网络",
    ))
