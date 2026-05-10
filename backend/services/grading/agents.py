from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from services.ai.base import BaseAIAdapter
from services.ai.vision import build_multimodal_content
from services.grading.prompts import (
    HIGHLIGHT_DISCOVERER_SYSTEM,
    HIGHLIGHT_DISCOVERER_USER,
    HIGHLIGHT_DISCOVERER_USER_IMAGE,
    STANDARD_REVIEWER_SYSTEM,
    STANDARD_REVIEWER_USER,
    STANDARD_REVIEWER_USER_IMAGE,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
BASE_DELAY = 1.0

T = TypeVar("T")


@dataclass
class StandardReviewResult:
    score: int
    dimensions: list[dict]
    improvements: list[str]
    overall_comment: str


@dataclass
class HighlightResult:
    score: int
    highlights: list[str]


class GradingParseError(Exception):
    """LLM 响应无法解析为有效批改结果时抛出。"""


def parse_json_response(raw: str) -> dict:
    """从 LLM 响应文本中提取 JSON 对象。

    先尝试直接解析，失败后回退到正则提取（处理 markdown 代码块或混合文本）。
    """
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    raise GradingParseError(f"No valid JSON in response: {raw[:300]}")


def _validate_score(value: object) -> int:
    """校验并转换分数为 [0, 100] 范围内的整数。"""
    if not isinstance(value, (int, float)):
        raise GradingParseError(f"score must be numeric, got {type(value).__name__}")
    score = int(value)
    if not 0 <= score <= 100:
        raise GradingParseError(f"score must be 0-100, got {score}")
    return score


def validate_standard_review(data: dict) -> StandardReviewResult:
    """校验标准评审 Agent 输出并转换为类型化结果。"""
    score = _validate_score(data.get("score"))

    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list):
        raise GradingParseError("dimensions must be a list")
    for i, dim in enumerate(dimensions):
        if not isinstance(dim, dict):
            raise GradingParseError(f"dimensions[{i}] must be a dict")
        for key in ("name", "score", "max_score", "comment"):
            if key not in dim:
                raise GradingParseError(f"dimensions[{i}] missing '{key}'")

    improvements = data.get("improvements")
    if not isinstance(improvements, list):
        raise GradingParseError("improvements must be a list")

    overall_comment = data.get("overall_comment")
    if not isinstance(overall_comment, str):
        raise GradingParseError("overall_comment must be a string")

    return StandardReviewResult(
        score=score,
        dimensions=dimensions,
        improvements=[str(item) for item in improvements],
        overall_comment=overall_comment,
    )


def validate_highlight(data: dict) -> HighlightResult:
    """校验亮点发现 Agent 输出并转换为类型化结果。"""
    score = _validate_score(data.get("score"))

    highlights = data.get("highlights")
    if not isinstance(highlights, list):
        raise GradingParseError("highlights must be a list")

    return HighlightResult(
        score=score,
        highlights=[str(item) for item in highlights],
    )


def format_learning_resources(resources: list[dict] | None) -> str:
    """将 Task.learning_resources 数组格式化为 prompt 文本。"""
    if not resources:
        return "无"
    parts = []
    for r in resources:
        parts.append(f"### {r['title']}\n**URL:** {r['url']}\n\n{r['content']}")
    return "\n\n---\n\n".join(parts)


async def _retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    agent_name: str,
) -> T:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await fn()
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "%s 第 %d/%d 次尝试失败 (%.1fs 后重试): %s",
                    agent_name, attempt + 1, MAX_RETRIES + 1, delay, exc,
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    "%s 第 %d/%d 次尝试失败 (已耗尽重试): %s",
                    agent_name, attempt + 1, MAX_RETRIES + 1, exc,
                )
    raise last_error  # type: ignore[misc]


async def _call_and_validate(
    adapter: BaseAIAdapter,
    messages: list[dict],
    validator: Callable[[dict], T],
) -> T:
    response = await adapter.async_chat(messages)
    data = parse_json_response(response.text or "")
    return validator(data)


def _build_user_content(
    text_template: str,
    image_template: str,
    context: dict,
) -> str | list[dict]:
    images: list[tuple[bytes, str]] | None = context.get("images")
    if images:
        prompt_text = image_template.format(**context)
        return build_multimodal_content(prompt_text, images)
    return text_template.format(**context)


async def run_standard_reviewer(
    adapter: BaseAIAdapter,
    context: dict,
) -> StandardReviewResult:
    user_content = _build_user_content(
        STANDARD_REVIEWER_USER, STANDARD_REVIEWER_USER_IMAGE, context,
    )
    messages = [
        {"role": "system", "content": STANDARD_REVIEWER_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    return await _retry_with_backoff(
        lambda: _call_and_validate(adapter, messages, validate_standard_review),
        agent_name="标准评审 Agent",
    )


async def run_highlight_discoverer(
    adapter: BaseAIAdapter,
    context: dict,
) -> HighlightResult:
    user_content = _build_user_content(
        HIGHLIGHT_DISCOVERER_USER, HIGHLIGHT_DISCOVERER_USER_IMAGE, context,
    )
    messages = [
        {"role": "system", "content": HIGHLIGHT_DISCOVERER_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    return await _retry_with_backoff(
        lambda: _call_and_validate(adapter, messages, validate_highlight),
        agent_name="亮点发现 Agent",
    )
