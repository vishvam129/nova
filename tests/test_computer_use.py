"""Tests for Computer Use session orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nova.tools.computer_use import ComputerAction, ComputerExecutor, ComputerSession


@dataclass
class FakeExecutor:
    width: int = 1024
    height: int = 768
    performed: list[ComputerAction] = field(default_factory=list)

    def execute(self, action: ComputerAction) -> bytes:
        self.performed.append(action)
        return b"PNG-FAKE"


def _tool_use_block(
    name: str = "computer", action: str = "screenshot", **kw: Any
) -> dict[str, Any]:
    return {
        "type": "tool_use",
        "id": f"t-{action}",
        "name": name,
        "input": {"action": action, **kw},
    }


def test_fake_executor_is_protocol() -> None:
    assert isinstance(FakeExecutor(), ComputerExecutor)


def test_session_stops_when_no_tool_use() -> None:
    calls = iter([[{"type": "text", "text": "done"}]])

    def llm(_h: Any, _t: Any) -> list[dict[str, Any]]:
        return next(calls)

    session = ComputerSession(executor=FakeExecutor(), llm_call=llm)
    actions = session.run("just answer")
    assert actions == []


def test_session_executes_and_feeds_back_screenshot() -> None:
    responses = iter(
        [
            [_tool_use_block(action="left_click", x=100, y=200)],
            [{"type": "text", "text": "clicked"}],
        ]
    )
    captured_histories: list[list[dict[str, Any]]] = []

    def llm(history: list[dict[str, Any]], _t: Any) -> list[dict[str, Any]]:
        captured_histories.append([dict(m) for m in history])
        return next(responses)

    exec_ = FakeExecutor()
    session = ComputerSession(executor=exec_, llm_call=llm)
    actions = session.run("click at 100,200")
    assert len(actions) == 1
    assert actions[0].name == "left_click"
    assert actions[0].params == {"x": 100, "y": 200}
    assert exec_.performed[0].name == "left_click"
    # The second history should include an image tool_result.
    second_call_history = captured_histories[1]
    tool_result_msg = second_call_history[-1]
    content = tool_result_msg["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "tool_result"


def test_session_respects_max_steps() -> None:
    def llm(_h: Any, _t: Any) -> list[dict[str, Any]]:
        return [_tool_use_block(action="screenshot")]

    session = ComputerSession(executor=FakeExecutor(), llm_call=llm, max_steps=2)
    actions = session.run("loop forever")
    assert len(actions) == 2


def test_tool_spec_uses_executor_dimensions() -> None:
    session = ComputerSession(
        executor=FakeExecutor(width=2560, height=1440),
        llm_call=lambda _h, _t: [],
    )
    spec = session._tool_spec()
    assert spec["display_width_px"] == 2560
    assert spec["display_height_px"] == 1440
    assert spec["type"] == "computer_20250124"
