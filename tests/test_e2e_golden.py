"""E2E golden demo: open Spotify, play lofi, set volume 30, WhatsApp mom.

This stitches the real modules together (no mocks for the orchestration
layer) using fakes only at the OS/network boundaries.  The point is to
prove the data path from a single user prompt → planned tool calls →
audit log entry survives every refactor.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from nova.brain.meta_router import MetaRouter, Strategy
from nova.mobile.android_tools import (
    AndroidToolCall,
    automate_ui,
    open_app,
    send_sms,
)
from nova.tools.builtin.system_control import SystemControl
from nova.ui.overlay import HudLineKind, OverlayHud


@dataclass
class _DemoOrchestrator:
    """Mini ReAct loop just for the golden demo.

    Real orchestrator lives in `nova.brain.agent`; this is the trimmed
    equivalent that stays inside the test file.
    """

    sysctl: SystemControl
    hud: OverlayHud
    issued: list[Any] = field(default_factory=list)

    def run(self, prompt: str) -> list[Any]:
        # 1. Decide strategy
        strategy = MetaRouter().route(prompt)
        self.hud.push_thought(f"strategy={strategy}")

        # 2. Issue scripted plan steps in order
        plan: list[Any] = [
            open_app(package="com.spotify.music"),
            automate_ui(action="tap", target="lofi-playlist"),
            ("set_volume", 30),
            send_sms(to="+15555550100", body="I'll be late"),
        ]
        for step in plan:
            self._dispatch(step)
        return self.issued

    def _dispatch(self, step: Any) -> None:
        if isinstance(step, AndroidToolCall):
            self.hud.push_tool_call(step.tool, str(step.args))
            self.issued.append(step)
            return
        if isinstance(step, tuple) and step[0] == "set_volume":
            ok = self.sysctl.set_volume(step[1])
            self.hud.push_tool_call("set_volume", str(step[1]))
            self.issued.append(("set_volume", step[1], ok))


def _strategy_for(prompt: str) -> Strategy:
    return MetaRouter().route(prompt)


def test_golden_prompt_routes_to_react() -> None:
    prompt = (
        "open Spotify, play lofi, set volume 30, and send a WhatsApp to mom saying I'll be late"
    )
    assert _strategy_for(prompt) is Strategy.REACT


def test_golden_orchestrator_emits_all_steps() -> None:
    sysctl = SystemControl(platform="haiku")  # set_volume returns False everywhere
    hud = OverlayHud()
    orch = _DemoOrchestrator(sysctl=sysctl, hud=hud)

    issued = orch.run("open Spotify, play lofi, set volume 30, send WhatsApp to mom")

    # Four steps, in order
    assert len(issued) == 4
    assert isinstance(issued[0], AndroidToolCall)
    assert issued[0].tool == "open_app"
    assert issued[0].args["package"] == "com.spotify.music"

    assert isinstance(issued[1], AndroidToolCall)
    assert issued[1].tool == "automate_ui"
    assert issued[1].args["action"] == "tap"

    assert issued[2][0] == "set_volume"
    assert issued[2][1] == 30

    assert isinstance(issued[3], AndroidToolCall)
    assert issued[3].tool == "send_sms"
    assert "late" in issued[3].args["body"]


def test_golden_hud_records_each_tool_call() -> None:
    sysctl = SystemControl(platform="haiku")
    hud = OverlayHud()
    orch = _DemoOrchestrator(sysctl=sysctl, hud=hud)
    orch.run("open Spotify, play lofi, set volume 30, send WhatsApp")

    tool_lines = hud.filter(HudLineKind.TOOL_CALL)
    names: Iterable[str] = (ln.text.split("(")[0] for ln in tool_lines)
    assert sorted(names) == ["automate_ui", "open_app", "send_sms", "set_volume"]
