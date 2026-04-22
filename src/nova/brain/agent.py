"""ReAct agent loop.

Implements the classic Reason→Act→Observe cycle on top of ``LlmBackend``:
ask the model, execute any tool calls it returned, feed the results
back, and repeat until the model stops calling tools or the step cap
is reached.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from nova.brain.llm import ChatMessage, ChatResponse, LlmBackend, ToolCall

ToolHandler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True, slots=True)
class Tool:
    """A callable tool exposed to the agent."""

    name: str
    description: str
    schema: dict[str, Any]
    handler: ToolHandler


@dataclass(frozen=True, slots=True)
class AgentStep:
    message: ChatMessage
    tool_calls: tuple[ToolCall, ...]
    tool_results: tuple[ChatMessage, ...]


@dataclass(frozen=True, slots=True)
class AgentResult:
    final: ChatMessage
    steps: tuple[AgentStep, ...]


@dataclass
class ReactAgent:
    llm: LlmBackend
    tools: dict[str, Tool] = field(default_factory=dict)
    system_prompt: str = "You are Nova, a helpful personal assistant."
    max_steps: int = 7

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def _tool_specs(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.schema}
            for t in self.tools.values()
        ]

    def _execute(self, call: ToolCall) -> ChatMessage:
        tool = self.tools.get(call.name)
        if tool is None:
            return ChatMessage(
                role="tool",
                content=f"error: unknown tool {call.name!r}",
                tool_call_id=call.id,
            )
        try:
            result = tool.handler(call.arguments)
        except Exception as e:  # noqa: BLE001 — surface tool errors to the model
            result = f"error: {e}"
        return ChatMessage(role="tool", content=str(result), tool_call_id=call.id)

    def run(self, user_message: str) -> AgentResult:
        history: list[ChatMessage] = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=user_message),
        ]
        steps: list[AgentStep] = []
        for _ in range(self.max_steps):
            response: ChatResponse = self.llm.chat(history, tools=self._tool_specs())
            if not response.tool_calls:
                steps.append(AgentStep(response.message, (), ()))
                history.append(response.message)
                return AgentResult(final=response.message, steps=tuple(steps))
            tool_messages = tuple(self._execute(tc) for tc in response.tool_calls)
            steps.append(AgentStep(response.message, response.tool_calls, tool_messages))
            history.append(response.message)
            history.extend(tool_messages)
        # Fell off the step cap.
        last = history[-1]
        return AgentResult(
            final=ChatMessage(
                role="assistant",
                content=last.content + "\n\n(step cap reached)",
            ),
            steps=tuple(steps),
        )
