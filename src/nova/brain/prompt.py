"""Dynamic system prompt template.

Assembles Nova's system message from personality, current date/time,
locale, active device + window, and per-session notes. Used by every
agent so the model always has the context it needs to sound grounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_PERSONALITY = (
    "You are Nova, a calm and concise personal AI. You run across the "
    "user's laptop and phone as one brain. You prefer short, direct "
    "answers and only use tools when genuinely needed. You speak like a "
    "trusted colleague, not a sales agent."
)


@dataclass(frozen=True, slots=True)
class DeviceContext:
    name: str
    platform: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class WindowContext:
    app: str
    title: str | None = None


@dataclass
class PromptContext:
    personality: str = DEFAULT_PERSONALITY
    timezone: str = "UTC"
    locale: str = "en-US"
    location: str | None = None
    device: DeviceContext | None = None
    window: WindowContext | None = None
    extra_notes: list[str] = field(default_factory=list)
    now_fn: object = field(default=None)

    def now(self) -> datetime:
        if callable(self.now_fn):
            result = self.now_fn()
            if isinstance(result, datetime):
                return result
        return datetime.now(tz=ZoneInfo(self.timezone))


def render_system_prompt(ctx: PromptContext) -> str:
    lines: list[str] = [ctx.personality.strip()]
    now = ctx.now()
    lines.append("")
    lines.append("## Context")
    lines.append(f"- Current time: {now.isoformat(timespec='seconds')} ({ctx.timezone})")
    lines.append(f"- Locale: {ctx.locale}")
    if ctx.location:
        lines.append(f"- Location: {ctx.location}")
    if ctx.device is not None:
        active = " (active)" if ctx.device.is_active else ""
        lines.append(f"- Device: {ctx.device.name} [{ctx.device.platform}]{active}")
    if ctx.window is not None:
        title = f" — {ctx.window.title}" if ctx.window.title else ""
        lines.append(f"- Active window: {ctx.window.app}{title}")
    for note in ctx.extra_notes:
        lines.append(f"- Note: {note}")
    return "\n".join(lines)
