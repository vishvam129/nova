"""Wear OS companion: wake word on the watch + quick replies via phone brain.

Watch ships only the wake word and a small reply UI; STT/LLM/TTS run on
the paired phone over the Wearable Data Layer.  This module owns the
message contracts the watch and phone exchange.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WatchMessageType(StrEnum):
    WAKE = "watch_wake"
    QUICK_REPLY = "watch_quick_reply"
    NUDGE = "watch_nudge"
    ACK = "watch_ack"


@dataclass
class WatchWake:
    """Watch reports a confirmed wake-word detection."""

    confidence: float
    battery_pct: int = 100

    @property
    def type(self) -> str:
        return WatchMessageType.WAKE

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "confidence": self.confidence,
            "battery_pct": self.battery_pct,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WatchWake:
        return cls(
            confidence=float(d["confidence"]),
            battery_pct=int(d.get("battery_pct", 100)),
        )


@dataclass
class WatchQuickReply:
    """Tap one of the prebuilt 4-button quick-reply chips."""

    chip_id: str
    text: str

    @property
    def type(self) -> str:
        return WatchMessageType.QUICK_REPLY

    def to_dict(self) -> dict[str, object]:
        return {"type": self.type, "chip_id": self.chip_id, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WatchQuickReply:
        return cls(chip_id=str(d["chip_id"]), text=str(d["text"]))


@dataclass
class WatchNudge:
    """Phone → watch: short text + vibration pattern."""

    text: str
    vibration_ms: int = 200
    suggested_chips: list[str] = field(default_factory=list)

    @property
    def type(self) -> str:
        return WatchMessageType.NUDGE

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "text": self.text,
            "vibration_ms": self.vibration_ms,
            "suggested_chips": list(self.suggested_chips),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WatchNudge:
        return cls(
            text=str(d["text"]),
            vibration_ms=int(d.get("vibration_ms", 200)),
            suggested_chips=list(d.get("suggested_chips") or []),
        )


_DEFAULT_CHIPS: tuple[str, ...] = (
    "yes",
    "no",
    "later",
    "details",
)


def default_chips() -> tuple[str, ...]:
    return _DEFAULT_CHIPS


def encode(msg: object) -> str:
    if hasattr(msg, "to_dict"):
        return json.dumps(msg.to_dict())
    raise TypeError(f"not a watch message: {msg!r}")


__all__ = [
    "WatchMessageType",
    "WatchNudge",
    "WatchQuickReply",
    "WatchWake",
    "default_chips",
    "encode",
]
