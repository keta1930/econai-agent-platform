import json
import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI, OpenAI

from services.ai.base import (
    BaseAIAdapter,
    ChatResponse,
    GradingResult,
    GRADING_PROMPT_TEMPLATE,
    StreamEvent,
    ToolCall,
    ToolDefinition,
    parse_grading_response,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAIAdapter):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        super().__init__(api_key, base_url, model_name)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Malformed tool call arguments: %s", tc.function.arguments[:200])
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        return ChatResponse(text=choice.content, tool_calls=tool_calls)

    async def async_chat(
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

        response = await self.async_client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Malformed tool call arguments: %s", tc.function.arguments[:200])
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        return ChatResponse(text=choice.content, tool_calls=tool_calls)

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
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

        stream = await self.async_client.chat.completions.create(**kwargs)

        # Accumulate tool calls keyed by index
        pending_tool_calls: dict[int, dict] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            finish_reason = chunk.choices[0].finish_reason

            # Text content
            if delta.content:
                yield StreamEvent(type="text_delta", text=delta.content)

            # Tool calls — OpenAI streams them incrementally, using index
            # to distinguish parallel calls within a single message.
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index

                    if idx not in pending_tool_calls:
                        # First chunk for this tool call carries id and name
                        pending_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": (tc_delta.function.name if tc_delta.function else "") or "",
                            "arguments": "",
                        }
                        if tc_delta.id and tc_delta.function and tc_delta.function.name:
                            yield StreamEvent(
                                type="tool_call_start",
                                tool_call_id=tc_delta.id,
                                tool_name=tc_delta.function.name,
                            )

                    # Accumulate argument fragments
                    if tc_delta.function and tc_delta.function.arguments:
                        fragment = tc_delta.function.arguments
                        pending_tool_calls[idx]["arguments"] += fragment
                        yield StreamEvent(
                            type="tool_call_args_delta",
                            tool_call_id=pending_tool_calls[idx]["id"],
                            partial_json=fragment,
                        )

            # Stream finished — emit tool_call_end for each pending call,
            # then message_end with the complete list.
            if finish_reason is not None:
                completed: list[ToolCall] = []
                for idx in sorted(pending_tool_calls):
                    tc = pending_tool_calls[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        logger.warning("Malformed tool call arguments: %s", tc["arguments"][:200])
                        args = {}
                    completed.append(ToolCall(id=tc["id"], name=tc["name"], arguments=args))
                    yield StreamEvent(type="tool_call_end", tool_call_id=tc["id"])

                yield StreamEvent(
                    type="message_end",
                    tool_calls=completed if completed else None,
                )
