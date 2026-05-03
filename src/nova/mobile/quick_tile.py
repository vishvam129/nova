"""Quick-tile + floating bubble: one-tap Nova invocation.

The Android side ships ``NovaQuickSettingsTile`` (TileService) and a
floating bubble overlay; this Python module owns the message contract
they push to the brain on tap, plus the per-state label.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum


class TileState(StrEnum):
    INACTIVE = "inactive"  # bubble dismissed, tile shows "Nova"
    LISTENING = "listening"  # bubble pulsing, mic open
    THINKING = "thinking"  # bubble spinner, brain working
    SPEAKING = "speaking"  # bubble lit, TTS playing
    ERROR = "error"


_LABELS: dict[TileState, str] = {
    TileState.INACTIVE: "Nova",
    TileState.LISTENING: "Listening…",
    TileState.THINKING: "Thinking…",
    TileState.SPEAKING: "Speaking",
    TileState.ERROR: "Tap to retry",
}


def label_for(state: TileState) -> str:
    return _LABELS[state]


@dataclass
class TileTapEvent:
    """Sent over WebSocket when the user taps the quick-tile or bubble."""

    source: str  # 'quick_tile' | 'bubble' | 'shortcut'
    current_state: TileState
    extras: dict[str, str] = field(default_factory=dict)

    MESSAGE_TYPE: str = field(default="quick_tile_tap", init=False, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.MESSAGE_TYPE,
            "source": self.source,
            "current_state": self.current_state.value,
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> TileTapEvent:
        return cls(
            source=str(d["source"]),
            current_state=TileState(d["current_state"]),
            extras=dict(d.get("extras") or {}),  # type: ignore[arg-type]
        )

    def encode(self) -> str:
        return json.dumps(self.to_dict())


def next_state_after_tap(current: TileState) -> TileState:
    """What the tile should look like immediately after a tap."""
    if current is TileState.INACTIVE:
        return TileState.LISTENING
    if current is TileState.LISTENING:
        return TileState.INACTIVE  # cancel
    if current is TileState.THINKING:
        return TileState.THINKING  # tap is no-op while thinking
    if current is TileState.SPEAKING:
        return TileState.INACTIVE  # tap = barge-in / stop
    return TileState.INACTIVE


__all__ = ["TileState", "TileTapEvent", "label_for", "next_state_after_tap"]
