import json
import re
import logging

from anthropic import Anthropic

from services.ai.base import BaseAIAdapter, GradingResult

logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = Anthropic(api_key=api_key, base_url=base_url)

    def grade(self, content: str, criteria: str) -> GradingResult:
        from services.grading_service import GRADING_PROMPT_TEMPLATE

        prompt = GRADING_PROMPT_TEMPLATE.format(
            grading_criteria=criteria,
            submission_content=content,
        )

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )

        raw = response.content[0].text if response.content else ""
        return _parse_grading_response(raw)


def _parse_grading_response(raw: str) -> GradingResult:
    try:
        data = json.loads(raw)
        return GradingResult(score=float(data["score"]), suggestion=str(data["suggestion"]))
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    match = re.search(r"\{[^}]*\"score\"[^}]*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return GradingResult(score=float(data["score"]), suggestion=str(data["suggestion"]))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    raise ValueError(f"Failed to parse grading response: {raw[:200]}")
