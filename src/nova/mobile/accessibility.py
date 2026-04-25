"""Accessibility event protocol — Android NovaAccessibilityService → brain.

The Android AccessibilityService captures on-screen context (active app,
focused text, window title) and streams it as ``accessibility_event``
WebSocket frames so Nova can answer questions about what's on the screen
without taking a screenshot.

Play Store policy: the app must display a disclosure dialog before the
user enables the service, explaining *why* it reads screen content.
``POLICY_DISCLOSURE_TEXT`` is the canonical text shown in that dialog and
must match what the Play Console policy declaration says.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

POLICY_DISCLOSURE_TEXT = (
    "Nova reads on-screen text and the active app name so it can answer "
    "questions about what you're looking at. No screen data is stored or "
    "shared with third parties. You can revoke this permission at any time "
    "in Settings → Accessibility → Nova."
)


@dataclass
class AccessibilityEvent:
    """Screen-context snapshot streamed from the Android service."""

    event_type: str
    package_name: str
    class_name: str
    text: list[str] = field(default_factory=list)
    content_description: str = ""
    window_title: str = ""

    # Wire type label used in WebSocket frames
    MESSAGE_TYPE: str = field(default="accessibility_event", init=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.MESSAGE_TYPE,
            "event_type": self.event_type,
            "package_name": self.package_name,
            "class_name": self.class_name,
            "text": self.text,
            "content_description": self.content_description,
            "window_title": self.window_title,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccessibilityEvent:
        return cls(
            event_type=data["event_type"],
            package_name=data["package_name"],
            class_name=data.get("class_name", ""),
            text=data.get("text", []),
            content_description=data.get("content_description", ""),
            window_title=data.get("window_title", ""),
        )

    def encode(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def decode(cls, raw: str | bytes) -> AccessibilityEvent:
        data: dict[str, Any] = json.loads(raw)
        return cls.from_dict(data)

    def screen_summary(self) -> str:
        """Human-readable summary for the brain context window."""
        parts = [f"App: {self.package_name}"]
        if self.window_title:
            parts.append(f"Window: {self.window_title}")
        if self.text:
            parts.append(f"Text: {' / '.join(self.text[:5])}")
        return " | ".join(parts)


__all__ = ["AccessibilityEvent", "POLICY_DISCLOSURE_TEXT"]
