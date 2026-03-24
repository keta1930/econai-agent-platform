import asyncio
import json
import logging

from tavily import TavilyClient

from config import TAVILY_API_KEY
from database import SessionLocal
from models.model_config import ModelConfig
from services.ai import get_adapter
from services.ai.base import ToolDefinition

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 3

CRITERIA_SYSTEM_PROMPT = """你是一位教育评估专家，擅长为各类作业任务设计结构化的评分标准。

## 你的工作流程

1. 分析任务标题和说明，理解任务的核心要求
2. 如果任务涉及特定工具、框架或技术标准（如 Claude Code、OpenCode、React、Docker 等），你应该先使用搜索工具查找相关文档，确保评分标准的专业性和准确性
3. 如果任务是通用性质的（如"写一篇作文"、"完成一道数学题"），可以直接基于你的知识生成评分标准
4. 根据收集到的信息，按照下面的模板格式生成评分标准

## 搜索工具使用指南

- 搜索查询请使用英文，以获得更好的结果
- 每次搜索应聚焦于一个具体问题
- 最多可以搜索 3 次

## 输出格式（严格遵循）

当你完成分析和搜索后，直接输出评分标准。禁止输出任何前言、思考过程、分析说明或总结。不要写"基于我的搜索"、"我认为"等内容。你的回复必须以"# 评分标准"开头，严格遵循以下格式：

# 评分标准：{任务标题}

## 1. 维度名称（XX 分）
- **优秀 (XX-XX分)**：描述
- **良好 (XX-XX分)**：描述
- **合格 (XX-XX分)**：描述
- **不合格 (0-XX分)**：描述

## 2. 维度名称（XX 分）
...

**总分：100 分**"""

TAVILY_TOOL = ToolDefinition(
    name="tavily_search",
    description=(
        "Search the web for documentation and reference materials. "
        "Use this when the task involves specific tools, frameworks, or technical standards "
        "to find accurate and up-to-date information."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query in English",
            }
        },
        "required": ["query"],
    },
)


def execute_tavily_search(query: str) -> str:
    """Call Tavily API and format results as markdown."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="advanced",
        include_answer="advanced",
        include_raw_content="text",
        include_domains=[
            "https://code.claude.com/docs/",
            "https://opencode.ai/docs",
        ],
    )

    parts = []

    # Include the AI-generated answer if present
    if response.get("answer"):
        parts.append(f"**Answer:** {response['answer']}")
        parts.append("---")

    # Include individual results — only extract raw_content, url, title
    for result in response.get("results", []):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        raw_content = result.get("raw_content", "")
        parts.append(f"### {title}\n**URL:** {url}\n\n{raw_content}")

    return "\n\n---\n\n".join(parts) if parts else "No results found."


async def generate_criteria(title: str, description: str) -> str:
    """Generate grading criteria using the active model with ReAct loop.

    The model can search for documentation via Tavily before generating
    the final criteria in the standardized template format.
    """
    db = SessionLocal()
    try:
        model_config = db.query(ModelConfig).filter(ModelConfig.is_active == True).first()
        if not model_config:
            raise RuntimeError("No active model configured")
    finally:
        db.close()

    adapter = get_adapter(model_config)

    messages = [
        {"role": "system", "content": CRITERIA_SYSTEM_PROMPT},
        {"role": "user", "content": f"任务标题：{title}\n\n任务说明：{description}"},
    ]

    tools = [TAVILY_TOOL]
    tool_call_count = 0

    # ReAct loop
    while True:
        response = await asyncio.to_thread(
            adapter.chat,
            messages,
            tools if tool_call_count < MAX_TOOL_CALLS else None,
        )

        if response.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": response.text,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                if tc.name == "tavily_search":
                    tool_call_count += 1
                    try:
                        result = execute_tavily_search(tc.arguments["query"])
                    except Exception:
                        logger.exception("Tavily search failed for query: %s", tc.arguments.get("query"))
                        result = "Search failed. Please generate criteria based on your existing knowledge."
                else:
                    result = f"Unknown tool: {tc.name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            continue

        if response.text:
            return response.text

        raise RuntimeError("Model returned empty response")
