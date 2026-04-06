from __future__ import annotations

import asyncio
import json
import logging

from tavily import TavilyClient

from config import TAVILY_API_KEY
from models.search_result import SearchResult
from services.ai.base import ToolDefinition
from services.assistant.tools.registry import ToolContext, ToolHandler, ToolRegistry

logger = logging.getLogger(__name__)

# 课程相关的搜索域：AI 智能体设计课程
SEARCH_DOMAINS = [
    "https://code.claude.com/docs/",
    "https://opencode.ai/docs",
    "https://docs.openclaw.ai/",
    "https://developers.openai.com/codex",
]

# 纳入内容项的最低相关性分数
MIN_CONTENT_SCORE = 0.6
MAX_CONTENT_ITEMS = 3


# ---------------------------------------------------------------------------
# 1. ask_user
# ---------------------------------------------------------------------------

async def execute_ask_user(args: dict, ctx: ToolContext) -> str:
    """占位 — 实际处理由 AssistantService 拦截。"""
    return ""


# ---------------------------------------------------------------------------
# 2. tavily_search
# ---------------------------------------------------------------------------

def _call_tavily(query: str) -> tuple[str, list[dict]]:
    """调用 Tavily API，返回格式化答案 + 结构化过滤结果。"""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="advanced",
        include_answer="advanced",
        max_results=6,
        include_domains=SEARCH_DOMAINS,
    )

    parts: list[str] = []
    filtered: list[dict] = []

    # 摘要：Tavily 内置的跨结果 agent 总结
    answer = response.get("answer", "")
    if answer:
        parts.append(f"## 摘要\n\n{answer}")

    # 内容：仅分数 >= 阈值的条目，最多 3 条
    results = response.get("results", [])
    high_score = [r for r in results if r.get("score", 0) >= MIN_CONTENT_SCORE]
    for result in high_score[:MAX_CONTENT_ITEMS]:
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")
        score = result.get("score", 0)
        parts.append(f"### {title}\n**URL:** {url}\n\n{content}")
        filtered.append({"url": url, "title": title, "content": content, "score": score})

    text = "\n\n---\n\n".join(parts) if parts else "No results found."
    return text, filtered


async def execute_tavily_search(args: dict, ctx: ToolContext) -> str:
    query = args.get("query", "").strip()
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    logger.info("Tavily 搜索 — 查询=%s", query)

    try:
        result_text, filtered_results = await asyncio.to_thread(_call_tavily, query)
    except Exception:
        logger.exception("Tavily 搜索失败 — 查询=%s", query)
        return json.dumps({"error": "搜索失败，请稍后重试"}, ensure_ascii=False)

    # 持久化高相关性结果供 learning_resources URL 验证
    if ctx.conversation_id and filtered_results:
        for item in filtered_results:
            ctx.db.add(SearchResult(
                conversation_id=ctx.conversation_id,
                url=item["url"],
                title=item["title"],
                content=item["content"],
                query=query,
                relevance_score=item["score"],
            ))
        await ctx.db.flush()

    return result_text


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

def register_system_tools(reg: ToolRegistry) -> None:
    reg.register(ToolHandler(
        definition=ToolDefinition(
            name="ask_user",
            description=(
                "向用户提问以澄清意图或确认操作。通过 questions 数组传入一个或多个问题，"
                "每个问题可以带选项（单选或多选）。用户逐一回答后统一提交。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "description": "问题列表，每个元素是一个独立问题",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "问题文本",
                                },
                                "options": {
                                    "type": "array",
                                    "description": (
                                        "选项列表。每个选项可以是字符串，"
                                        "或 {label, description} 对象"
                                    ),
                                    "items": {
                                        "oneOf": [
                                            {"type": "string"},
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "label": {"type": "string"},
                                                    "description": {"type": "string"},
                                                },
                                                "required": ["label"],
                                            },
                                        ],
                                    },
                                },
                                "select_mode": {
                                    "type": "string",
                                    "enum": ["single", "multiple"],
                                    "description": "选择模式，默认 single",
                                },
                            },
                            "required": ["question"],
                        },
                    },
                },
                "required": ["questions"],
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
