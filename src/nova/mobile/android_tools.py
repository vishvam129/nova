"""Android MCP tools: actions the brain can invoke on a paired phone.

Each tool is a plain dataclass describing the call (name + args).  The
WebSocket transport serialises it as an ``android_tool_call`` frame; the
Kotlin side deserialises and dispatches to the appropriate Android API.

Tools implemented:
    send_sms          — send a text message
    make_call         — initiate a phone call
    read_notifications — fetch pending notification summaries
    open_app          — launch an installed package
    automate_ui       — tap / type / scroll via AccessibilityService
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# Wire type for all frames from brain → Android
_FRAME_TYPE = "android_tool_call"
# Wire type for responses from Android → brain
_RESPONSE_TYPE = "android_tool_result"


@dataclass
class AndroidToolCall:
    """A single tool invocation sent from the Nova brain to the Android app."""

    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""

    def encode(self) -> str:
        return json.dumps(
            {"type": _FRAME_TYPE, "tool": self.tool, "args": self.args, "call_id": self.call_id}
        )

    @classmethod
    def decode(cls, raw: str | bytes) -> AndroidToolCall:
        data: dict[str, Any] = json.loads(raw)
        return cls(
            tool=data["tool"],
            args=data.get("args", {}),
            call_id=data.get("call_id", ""),
        )


@dataclass
class AndroidToolResult:
    """Result or error returned from the Android app to the brain."""

    call_id: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def encode(self) -> str:
        return json.dumps(
            {
                "type": _RESPONSE_TYPE,
                "call_id": self.call_id,
                "ok": self.ok,
                "data": self.data,
                "error": self.error,
            }
        )

    @classmethod
    def decode(cls, raw: str | bytes) -> AndroidToolResult:
        data: dict[str, Any] = json.loads(raw)
        return cls(
            call_id=data.get("call_id", ""),
            ok=data["ok"],
            data=data.get("data", {}),
            error=data.get("error", ""),
        )


# ---------------------------------------------------------------------------
# Typed builder helpers — brain code calls these instead of raw dicts
# ---------------------------------------------------------------------------


def send_sms(*, to: str, body: str, call_id: str = "") -> AndroidToolCall:
    """Send an SMS message to ``to`` with ``body``."""
    return AndroidToolCall(tool="send_sms", args={"to": to, "body": body}, call_id=call_id)


def make_call(*, number: str, call_id: str = "") -> AndroidToolCall:
    """Initiate a phone call to ``number``."""
    return AndroidToolCall(tool="make_call", args={"number": number}, call_id=call_id)


def read_notifications(*, limit: int = 10, call_id: str = "") -> AndroidToolCall:
    """Request up to ``limit`` pending notification summaries."""
    return AndroidToolCall(tool="read_notifications", args={"limit": limit}, call_id=call_id)


def open_app(*, package: str, call_id: str = "") -> AndroidToolCall:
    """Launch the app identified by ``package`` (e.g. ``com.spotify.music``)."""
    return AndroidToolCall(tool="open_app", args={"package": package}, call_id=call_id)


def automate_ui(
    *,
    action: str,
    target: str = "",
    text: str = "",
    call_id: str = "",
) -> AndroidToolCall:
    """Perform a UI action via AccessibilityService.

    Args:
        action: One of ``tap``, ``type``, ``scroll_down``, ``scroll_up``,
                ``back``, ``home``.
        target: Content-description or resource-id of the target node (optional).
        text:   Text to type when action is ``type``.
    """
    return AndroidToolCall(
        tool="automate_ui",
        args={"action": action, "target": target, "text": text},
        call_id=call_id,
    )


# Tools the brain may advertise to the MCP tool registry
ANDROID_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "send_sms",
        "description": "Send an SMS from the paired Android phone.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient phone number"},
                "body": {"type": "string", "description": "Message text"},
            },
            "required": ["to", "body"],
        },
    },
    {
        "name": "make_call",
        "description": "Initiate a phone call from the paired Android phone.",
        "parameters": {
            "type": "object",
            "properties": {
                "number": {"type": "string", "description": "Phone number to call"},
            },
            "required": ["number"],
        },
    },
    {
        "name": "read_notifications",
        "description": "Fetch pending notification summaries from the paired Android phone.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max notifications to return",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "open_app",
        "description": "Launch an app on the paired Android phone by package name.",
        "parameters": {
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "Android package name"},
            },
            "required": ["package"],
        },
    },
    {
        "name": "automate_ui",
        "description": "Perform a UI action on the paired Android phone via AccessibilityService.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["tap", "type", "scroll_down", "scroll_up", "back", "home"],
                },
                "target": {"type": "string", "description": "Content-description or resource-id"},
                "text": {"type": "string", "description": "Text to type (action=type only)"},
            },
            "required": ["action"],
        },
    },
]


__all__ = [
    "ANDROID_TOOL_SCHEMAS",
    "AndroidToolCall",
    "AndroidToolResult",
    "automate_ui",
    "make_call",
    "open_app",
    "read_notifications",
    "send_sms",
]
