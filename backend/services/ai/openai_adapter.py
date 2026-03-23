import json
import re
import logging

from openai import OpenAI

from services.ai.base import BaseAIAdapter, GradingResult

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def grade(self, content: str, criteria: str) -> GradingResult:
        from services.grading_service import GRADING_PROMPT_TEMPLATE

        prompt = GRADING_PROMPT_TEMPLATE.format(
            grading_criteria=criteria,
            submission_content=content,
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )

        raw = response.choices[0].message.content or ""
        return _parse_grading_response(raw)


def _parse_grading_response(raw: str) -> GradingResult:
    # Try direct JSON parse first
    try:
        data = json.loads(raw)
        return GradingResult(score=float(data["score"]), suggestion=str(data["suggestion"]))
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    # Fallback: extract JSON block from markdown or mixed text
    match = re.search(r"\{[^}]*\"score\"[^}]*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return GradingResult(score=float(data["score"]), suggestion=str(data["suggestion"]))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    raise ValueError(f"Failed to parse grading response: {raw[:200]}")
