"""Android Advanced Protection fallback: Shizuku / ADB path.

When Android 17's Advanced Protection blocks an AccessibilityService,
Nova falls back to Shizuku (or wireless ADB) which keeps shell-level
control without the AccessibilityService API.

This module is the Python-side message contract; the Kotlin app picks
which transport is currently usable and signals the brain so it can
adjust which tools it advertises.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ControlChannel(StrEnum):
    ACCESSIBILITY = "accessibility"  # preferred
    SHIZUKU = "shizuku"  # fallback 1
    ADB = "adb"  # fallback 2 (wireless ADB)
    NONE = "none"  # no control surface available


@dataclass
class ChannelStatus:
    """Reported by the Android app on every connect / channel change."""

    active: ControlChannel
    accessibility_blocked: bool = False
    shizuku_running: bool = False
    adb_authorized: bool = False
    advanced_protection_on: bool = False

    MESSAGE_TYPE: str = field(default="control_channel_status", init=False, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.MESSAGE_TYPE,
            "active": self.active.value,
            "accessibility_blocked": self.accessibility_blocked,
            "shizuku_running": self.shizuku_running,
            "adb_authorized": self.adb_authorized,
            "advanced_protection_on": self.advanced_protection_on,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChannelStatus:
        return cls(
            active=ControlChannel(d["active"]),
            accessibility_blocked=bool(d.get("accessibility_blocked", False)),
            shizuku_running=bool(d.get("shizuku_running", False)),
            adb_authorized=bool(d.get("adb_authorized", False)),
            advanced_protection_on=bool(d.get("advanced_protection_on", False)),
        )

    def encode(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def decode(cls, raw: str | bytes) -> ChannelStatus:
        return cls.from_dict(json.loads(raw))


def pick_channel(
    *,
    accessibility_blocked: bool,
    shizuku_running: bool,
    adb_authorized: bool,
) -> ControlChannel:
    """Choose the best available control channel.

    Order of preference:
        1. AccessibilityService (lowest friction, no extra setup)
        2. Shizuku (single tap, persistent across reboots on rooted phones)
        3. ADB (wireless, requires per-session re-pair on stock Android)
    """
    if not accessibility_blocked:
        return ControlChannel.ACCESSIBILITY
    if shizuku_running:
        return ControlChannel.SHIZUKU
    if adb_authorized:
        return ControlChannel.ADB
    return ControlChannel.NONE


def tools_for_channel(channel: ControlChannel) -> set[str]:
    """Subset of Android tools usable on this channel."""
    common = {"send_sms", "make_call", "read_notifications", "open_app"}
    if channel is ControlChannel.ACCESSIBILITY:
        return common | {"automate_ui"}
    if channel in (ControlChannel.SHIZUKU, ControlChannel.ADB):
        # Shell-driven UI automation via input/dumpsys instead of Accessibility
        return common | {"automate_ui_shell"}
    return set()


__all__ = [
    "ChannelStatus",
    "ControlChannel",
    "pick_channel",
    "tools_for_channel",
]
