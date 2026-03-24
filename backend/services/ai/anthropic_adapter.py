import logging

from anthropic import Anthropic

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


class AnthropicAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = Anthropic(api_key=api_key, base_url=base_url)

    def grade(self, content: str, criteria: str, task_description: str) -> GradingResult:
        prompt = GRADING_PROMPT_TEMPLATE.format(
            task_description=task_description,
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
        return parse_grading_response(raw)

    def chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> ChatResponse:
        # Separate system message and convert message formats
        system_content = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"],
                        }
                    ],
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    tc_args = func.get("arguments", tc.get("arguments", {}))
                    # arguments may be a JSON string (OpenAI format) or dict
                    if isinstance(tc_args, str):
                        import json
                        tc_args = json.loads(tc_args)
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": func.get("name", tc.get("name")),
                        "input": tc_args,
                    })
                api_messages.append({"role": "assistant", "content": content})
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": api_messages,
            "timeout": 120,
        }
        if system_content:
            kwargs["system"] = system_content
        if tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]

        response = self.client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return ChatResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )
