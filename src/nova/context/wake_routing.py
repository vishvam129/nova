"""Context-aware wake-word routing.

After "Nova, …" the rest of the utterance often names a tool directly:
"Nova, translate this", "Nova, set a timer for 5 minutes", "Nova, play
lofi".  The router maps the prefix-stripped utterance to a target route
without going through the full ReAct loop, so the tool fires within
~150 ms instead of ~1 s.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

_WAKE_PREFIX_PATTERN = re.compile(r"^\s*(hey\s+)?nova[\s,:.!]+", re.I)


def strip_wake_word(utterance: str) -> str:
    return _WAKE_PREFIX_PATTERN.sub("", utterance, count=1).strip()


@dataclass(frozen=True, slots=True)
class WakeRoute:
    """One direct-route rule triggered by a leading verb."""

    name: str
    triggers: tuple[str, ...]
    handler: Callable[[str], object] | None = None

    def matches(self, utterance: str) -> bool:
        first = utterance.split(" ", 1)[0].lower().rstrip(",.:!?")
        return first in {t.lower() for t in self.triggers}


@dataclass
class WakeRouter:
    """Looks up direct routes; returns None when ReAct should run."""

    routes: list[WakeRoute] = field(default_factory=list)

    def register(self, route: WakeRoute) -> None:
        self.routes.append(route)

    def route(self, utterance: str) -> WakeRoute | None:
        body = strip_wake_word(utterance)
        if not body:
            return None
        for r in self.routes:
            if r.matches(body):
                return r
        return None

    def dispatch(self, utterance: str) -> tuple[WakeRoute, object] | None:
        r = self.route(utterance)
        if r is None or r.handler is None:
            return None
        body = strip_wake_word(utterance)
        return r, r.handler(body)


def default_router() -> WakeRouter:
    """Built-in routes for the most common direct intents."""
    router = WakeRouter()
    router.register(WakeRoute(name="translate", triggers=("translate",)))
    router.register(WakeRoute(name="timer", triggers=("set", "timer", "remind")))
    router.register(WakeRoute(name="play", triggers=("play",)))
    router.register(WakeRoute(name="open", triggers=("open", "launch")))
    router.register(WakeRoute(name="search", triggers=("search", "find", "look")))
    router.register(WakeRoute(name="cancel", triggers=("cancel", "stop")))
    return router


__all__ = ["WakeRoute", "WakeRouter", "default_router", "strip_wake_word"]
