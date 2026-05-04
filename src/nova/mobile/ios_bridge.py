"""iOS companion: Shortcuts + URL-scheme bridge for receive-only flows.

iOS sandboxing prevents a real always-on agent, so the iOS companion is
limited to receiving:
    - notifications/replies pushed via APNs
    - Shortcuts that round-trip through the laptop daemon

This module owns the URL-scheme contract Shortcuts uses to call into Nova
and the payload format the laptop pushes back via APNs.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass, field
from enum import StrEnum

URL_SCHEME = "nova"


class ShortcutAction(StrEnum):
    ASK = "ask"
    REMIND = "remind"
    NOTE = "note"
    HANDOFF = "handoff"


@dataclass(frozen=True, slots=True)
class ShortcutInvocation:
    """Parsed nova:// URL the iOS Shortcut triggered."""

    action: ShortcutAction
    params: dict[str, str] = field(default_factory=dict)

    @classmethod
    def parse(cls, url: str) -> ShortcutInvocation:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != URL_SCHEME:
            raise ValueError(f"not a nova URL: {url!r}")
        action = ShortcutAction(parsed.netloc or parsed.path.lstrip("/"))
        params = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        return cls(action=action, params=params)

    def to_url(self) -> str:
        query = urllib.parse.urlencode(self.params)
        return f"{URL_SCHEME}://{self.action.value}?{query}"


@dataclass
class ApnsPayload:
    """Push payload sent from the laptop daemon to the iOS app."""

    title: str
    body: str
    handoff_id: str = ""
    extras: dict[str, object] = field(default_factory=dict)
    sound: str = "default"

    def to_dict(self) -> dict[str, object]:
        aps: dict[str, object] = {
            "alert": {"title": self.title, "body": self.body},
            "sound": self.sound,
        }
        payload: dict[str, object] = {"aps": aps, "nova": dict(self.extras)}
        if self.handoff_id:
            payload["nova_handoff_id"] = self.handoff_id
        return payload

    def encode(self) -> str:
        return json.dumps(self.to_dict())


def build_shortcut_url(action: ShortcutAction, **params: str) -> str:
    """Convenience for tests / docs."""
    return ShortcutInvocation(action=action, params=dict(params)).to_url()


__all__ = [
    "URL_SCHEME",
    "ApnsPayload",
    "ShortcutAction",
    "ShortcutInvocation",
    "build_shortcut_url",
]
