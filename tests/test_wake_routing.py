"""Tests for nova.context.wake_routing."""

from __future__ import annotations

from nova.context.wake_routing import (
    WakeRoute,
    WakeRouter,
    default_router,
    strip_wake_word,
)


def test_strip_simple() -> None:
    assert strip_wake_word("Nova, translate this") == "translate this"


def test_strip_hey_nova() -> None:
    assert strip_wake_word("hey nova play jazz") == "play jazz"


def test_strip_no_wake_word_passthrough() -> None:
    assert strip_wake_word("just a sentence") == "just a sentence"


def test_route_matches_first_word() -> None:
    r = WakeRouter()
    r.register(WakeRoute(name="play", triggers=("play",)))
    out = r.route("Nova, play lofi")
    assert out is not None
    assert out.name == "play"


def test_route_no_match_returns_none() -> None:
    r = WakeRouter()
    r.register(WakeRoute(name="play", triggers=("play",)))
    assert r.route("Nova, what is 2+2?") is None


def test_default_router_translate() -> None:
    r = default_router()
    out = r.route("Nova, translate this to French")
    assert out is not None
    assert out.name == "translate"


def test_default_router_open() -> None:
    r = default_router()
    out = r.route("nova: open spotify")
    assert out is not None
    assert out.name == "open"


def test_dispatch_calls_handler() -> None:
    fired: list[str] = []
    r = WakeRouter()
    r.register(WakeRoute(name="echo", triggers=("echo",), handler=fired.append))
    result = r.dispatch("Nova, echo hello world")
    assert result is not None
    route, _ = result
    assert route.name == "echo"
    assert fired == ["echo hello world"]


def test_dispatch_no_handler_returns_none() -> None:
    r = WakeRouter()
    r.register(WakeRoute(name="echo", triggers=("echo",)))
    assert r.dispatch("Nova, echo hi") is None


def test_dispatch_no_match_returns_none() -> None:
    r = WakeRouter()
    r.register(WakeRoute(name="play", triggers=("play",), handler=lambda x: x))
    assert r.dispatch("Nova, what's the weather?") is None
