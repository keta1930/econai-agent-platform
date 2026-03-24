import json
import logging

from openai import OpenAI

from services.ai.base import (
    BaseAIAdapter,
    ChatResponse,
    GradingResult,
    GRADING_PROMPT_TEMPLATE,
    ToolCall,
    ToolDefinition,
    parse_grading_response,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def grade(self, content: str, criteria: str, task_description: str) -> GradingResult:
        prompt = GRADING_PROMPT_TEMPLATE.format(
            task_description=task_description,
            grading_criteria=criteria,
            submission_content=content,
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )

        raw = response.choices[0].message.content or ""
        return parse_grading_response(raw)

    def chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "timeout": 120,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        return ChatResponse(text=choice.content, tool_calls=tool_calls)
