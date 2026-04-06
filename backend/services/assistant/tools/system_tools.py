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
MIN_CONTENT_SCORE = 0.5
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
                "向教师提问以澄清意图或确认操作参数。\n"
                "格式要求：\n"
                "- 当选项有限且可枚举时，必须提供 options 让教师点选，而非要求手动输入。"
                "例如：确认班级选择、确认是否执行、在多个方案中选择\n"
                "- 每个 option 可以是字符串，或 {label, description} 对象（需额外解释时用对象格式）\n"
                "- select_mode: 'single'（默认，互斥选择）/ 'multiple'（可多选）\n"
                "- 需要一次收集多个信息时，在 questions 数组中放多个元素，教师逐一回答后统一提交\n"
                "- 仅在真正开放式的问题（如「请描述作业内容」）时省略 options"
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
                "搜索网络获取课程相关资料。搜索范围限定在 Claude Code、OpenCode、OpenClaw、Codex 文档站。\n"
                "英文关键词效果更好。返回：AI 生成的跨结果摘要 + 高相关度的原始内容（含 URL）。\n"
                "搜索结果中的 URL 可传入 manage_task 的 learning_resources 参数。"
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
