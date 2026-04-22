"""Claude Computer Use integration.

Hosts a screen-driven agent loop around Anthropic's ``computer_20250124``
tool. The vision model issues high-level actions (click, type,
screenshot, key, scroll); a ``ComputerExecutor`` performs them and
returns a screenshot to feed back. Executors are swappable so tests
can drive the loop without real hardware.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

ActionName = Literal[
    "screenshot",
    "left_click",
    "right_click",
    "double_click",
    "type",
    "key",
    "scroll",
    "mouse_move",
    "cursor_position",
]


@dataclass(frozen=True, slots=True)
class ComputerAction:
    name: ActionName
    params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ComputerExecutor(Protocol):
    width: int
    height: int

    def execute(self, action: ComputerAction) -> bytes: ...


class PyAutoGuiExecutor:
    """Real executor built on ``pyautogui`` and ``mss``. Imports lazy."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self.width = width
        self.height = height

    def _screenshot(self) -> bytes:
        import io

        import mss
        import PIL.Image

        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[1])
            img = PIL.Image.frombytes("RGB", raw.size, raw.rgb)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

    def execute(self, action: ComputerAction) -> bytes:
        import pyautogui

        p = action.params
        if action.name == "screenshot":
            return self._screenshot()
        if action.name == "mouse_move":
            pyautogui.moveTo(p["x"], p["y"])
        elif action.name == "left_click":
            pyautogui.click(p.get("x"), p.get("y"))
        elif action.name == "right_click":
            pyautogui.rightClick(p.get("x"), p.get("y"))
        elif action.name == "double_click":
            pyautogui.doubleClick(p.get("x"), p.get("y"))
        elif action.name == "type":
            pyautogui.typewrite(p["text"])
        elif action.name == "key":
            pyautogui.press(p["key"])
        elif action.name == "scroll":
            pyautogui.scroll(int(p.get("amount", 3)))
        return self._screenshot()


@dataclass
class ComputerSession:
    """Orchestrates a Computer-Use turn through a Claude backend.

    The actual Anthropic API call is delegated to ``llm_call`` so the
    session is test-friendly. The default ``llm_call`` is a lazy
    wrapper over ``anthropic.Anthropic`` using the computer_use beta.
    """

    executor: ComputerExecutor
    llm_call: Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]]
    max_steps: int = 10

    def _tool_spec(self) -> dict[str, Any]:
        return {
            "type": "computer_20250124",
            "name": "computer",
            "display_width_px": self.executor.width,
            "display_height_px": self.executor.height,
        }

    def run(self, instruction: str) -> list[ComputerAction]:
        """Drive the Claude computer-use loop. Returns actions performed."""
        history: list[dict[str, Any]] = [
            {"role": "user", "content": instruction},
        ]
        performed: list[ComputerAction] = []
        for _ in range(self.max_steps):
            blocks = self.llm_call(history, self._tool_spec())
            tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
            if not tool_uses:
                break
            history.append({"role": "assistant", "content": blocks})
            tool_results: list[dict[str, Any]] = []
            for use in tool_uses:
                action_name: ActionName = use["input"].get("action", "screenshot")
                action = ComputerAction(
                    name=action_name,
                    params={k: v for k, v in use["input"].items() if k != "action"},
                )
                performed.append(action)
                screenshot_bytes = self.executor.execute(action)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use["id"],
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64.b64encode(screenshot_bytes).decode(),
                                },
                            }
                        ],
                    }
                )
            history.append({"role": "user", "content": tool_results})
        return performed


__all__ = [
    "ActionName",
    "ComputerAction",
    "ComputerExecutor",
    "ComputerSession",
    "PyAutoGuiExecutor",
]
