"""Tests for system prompt rendering."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from nova.brain.prompt import (
    DEFAULT_PERSONALITY,
    DeviceContext,
    PromptContext,
    WindowContext,
    render_system_prompt,
)


def _fixed(year: int = 2026, month: int = 4, day: int = 23, hour: int = 9) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=ZoneInfo("UTC"))


def test_includes_personality() -> None:
    out = render_system_prompt(PromptContext(now_fn=_fixed))
    assert DEFAULT_PERSONALITY.split(".")[0] in out


def test_includes_current_time_and_locale() -> None:
    ctx = PromptContext(now_fn=_fixed, timezone="UTC", locale="hi-IN")
    out = render_system_prompt(ctx)
    assert "2026-04-23T09:00:00" in out
    assert "hi-IN" in out


def test_includes_device_when_present() -> None:
    ctx = PromptContext(
        now_fn=_fixed,
        device=DeviceContext(name="thinkpad", platform="linux", is_active=True),
    )
    out = render_system_prompt(ctx)
    assert "thinkpad" in out
    assert "linux" in out
    assert "(active)" in out


def test_includes_window_when_present() -> None:
    ctx = PromptContext(
        now_fn=_fixed,
        window=WindowContext(app="firefox", title="Anthropic docs"),
    )
    out = render_system_prompt(ctx)
    assert "firefox" in out
    assert "Anthropic docs" in out


def test_extra_notes_surface() -> None:
    ctx = PromptContext(now_fn=_fixed, extra_notes=["user prefers short answers"])
    out = render_system_prompt(ctx)
    assert "short answers" in out


def test_location_optional() -> None:
    ctx_no = PromptContext(now_fn=_fixed)
    assert "Location:" not in render_system_prompt(ctx_no)
    ctx_yes = PromptContext(now_fn=_fixed, location="Delhi, IN")
    assert "Delhi" in render_system_prompt(ctx_yes)


def test_now_defaults_to_current_time() -> None:
    ctx = PromptContext()
    t = ctx.now()
    assert abs((t - datetime.now(tz=ZoneInfo("UTC"))).total_seconds()) < 2
