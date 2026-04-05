from __future__ import annotations

import asyncio
import json
import logging

from tavily import TavilyClient

from config import TAVILY_API_KEY
from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry

logger = logging.getLogger(__name__)

SEARCH_SUMMARY_PROMPT = (
    "将以下搜索结果精炼为 500 字以内的中文摘要，保留关键事实和数据。"
    "只输出摘要内容，不要添加前言或说明。"
)


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
    """Call Tavily API and format raw results as text."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="advanced",
        include_answer="advanced",
    )

    parts: list[str] = []
    if response.get("answer"):
        parts.append(f"Answer: {response['answer']}")

    for result in response.get("results", [])[:5]:
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")
        parts.append(f"[{title}]({url})\n{content}")

    return "\n\n---\n\n".join(parts) if parts else "No results found."


async def _summarise(raw_results: str, adapter: object) -> str:
    """Use a lightweight async AI call to condense raw search results."""
    from services.ai.base import BaseAIAdapter

    if not isinstance(adapter, BaseAIAdapter):
        return raw_results

    messages = [
        {"role": "system", "content": SEARCH_SUMMARY_PROMPT},
        {"role": "user", "content": raw_results},
    ]
    response = await adapter.async_chat(messages)
    return response.text or raw_results


async def execute_tavily_search(args: dict, ctx: ToolContext) -> str:
    query = args.get("query", "").strip()
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    try:
        raw_results = await asyncio.to_thread(_call_tavily, query)
    except Exception:
        logger.exception("Tavily search failed for query: %s", query)
        return json.dumps({"error": "搜索失败，请稍后重试"}, ensure_ascii=False)

    # Sub-agent summarisation: condense raw results via a lightweight AI call
    if ctx.adapter is not None:
        try:
            raw_results = await _summarise(raw_results, ctx.adapter)
        except Exception:
            logger.warning("Search summary failed, returning truncated raw results")
            if len(raw_results) > 3000:
                raw_results = raw_results[:3000] + "\n\n[... truncated]"
    elif len(raw_results) > 3000:
        raw_results = raw_results[:3000] + "\n\n[... truncated]"

    return json.dumps({"query": query, "results": raw_results}, ensure_ascii=False)


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
