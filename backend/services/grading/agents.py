from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from services.ai.base import BaseAIAdapter
from services.grading.prompts import (
    HIGHLIGHT_DISCOVERER_SYSTEM,
    HIGHLIGHT_DISCOVERER_USER,
    STANDARD_REVIEWER_SYSTEM,
    STANDARD_REVIEWER_USER,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2  # 3 attempts total


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
    """Raised when LLM response cannot be parsed into valid grading result."""


def parse_json_response(raw: str) -> dict:
    """Extract JSON object from LLM response text.

    Tries direct parse first, then falls back to regex extraction
    for responses wrapped in markdown code blocks or mixed text.
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
    """Validate and coerce score to int in [0, 100]."""
    if not isinstance(value, (int, float)):
        raise GradingParseError(f"score must be numeric, got {type(value).__name__}")
    score = int(value)
    if not 0 <= score <= 100:
        raise GradingParseError(f"score must be 0-100, got {score}")
    return score


def validate_standard_review(data: dict) -> StandardReviewResult:
    """Validate Agent 1 output and convert to typed result."""
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
    """Validate Agent 2 output and convert to typed result."""
    score = _validate_score(data.get("score"))

    highlights = data.get("highlights")
    if not isinstance(highlights, list):
        raise GradingParseError("highlights must be a list")

    return HighlightResult(
        score=score,
        highlights=[str(item) for item in highlights],
    )


def format_learning_resources(resources: list[dict] | None) -> str:
    """Format Task.learning_resources array into prompt text."""
    if not resources:
        return "无"
    parts = []
    for r in resources:
        parts.append(f"### {r['title']}\n**URL:** {r['url']}\n\n{r['content']}")
    return "\n\n---\n\n".join(parts)


async def run_standard_reviewer(
    adapter: BaseAIAdapter,
    context: dict,
) -> StandardReviewResult:
    """Execute the Standard Reviewer agent with retry on parse failure."""
    messages = [
        {"role": "system", "content": STANDARD_REVIEWER_SYSTEM},
        {
            "role": "user",
            "content": STANDARD_REVIEWER_USER.format(**context),
        },
    ]

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await adapter.async_chat(messages)
            data = parse_json_response(response.text or "")
            return validate_standard_review(data)
        except (GradingParseError, KeyError, TypeError) as exc:
            last_error = exc
            logger.warning(
                "Standard reviewer attempt %d/%d failed: %s",
                attempt + 1,
                MAX_RETRIES + 1,
                exc,
            )
            continue

    raise last_error  # type: ignore[misc]


async def run_highlight_discoverer(
    adapter: BaseAIAdapter,
    context: dict,
) -> HighlightResult:
    """Execute the Highlight Discoverer agent with retry on parse failure."""
    messages = [
        {"role": "system", "content": HIGHLIGHT_DISCOVERER_SYSTEM},
        {
            "role": "user",
            "content": HIGHLIGHT_DISCOVERER_USER.format(**context),
        },
    ]

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await adapter.async_chat(messages)
            data = parse_json_response(response.text or "")
            return validate_highlight(data)
        except (GradingParseError, KeyError, TypeError) as exc:
            last_error = exc
            logger.warning(
                "Highlight discoverer attempt %d/%d failed: %s",
                attempt + 1,
                MAX_RETRIES + 1,
                exc,
            )
            continue

    raise last_error  # type: ignore[misc]
