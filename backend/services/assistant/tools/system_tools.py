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
                "向用户提问以澄清意图或确认操作。可以提供选项让用户选择。"
                "当你需要用户做出选择或确认时使用此工具。"
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
                        "items": {"type": "string"},
                        "description": "可选的选项列表，用户可以点击选择",
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
