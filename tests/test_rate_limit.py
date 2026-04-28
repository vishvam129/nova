"""Tests for nova.tools.rate_limit."""

from __future__ import annotations

import pytest

from nova.tools.rate_limit import RateLimited, RateLimiter


def test_check_allows_under_limit() -> None:
    rl = RateLimiter(per_minute=3)
    assert rl.check("foo") is True


def test_acquire_allows_up_to_limit() -> None:
    rl = RateLimiter(per_minute=3)
    rl.acquire("foo")
    rl.acquire("foo")
    rl.acquire("foo")


def test_acquire_blocks_over_limit() -> None:
    rl = RateLimiter(per_minute=2)
    rl.acquire("foo")
    rl.acquire("foo")
    with pytest.raises(RateLimited) as ctx:
        rl.acquire("foo")
    assert ctx.value.tool == "foo"
    assert ctx.value.per_minute == 2


def test_check_false_when_capped() -> None:
    rl = RateLimiter(per_minute=1)
    rl.acquire("foo")
    assert rl.check("foo") is False


def test_per_tool_isolation() -> None:
    rl = RateLimiter(per_minute=1)
    rl.acquire("foo")
    rl.acquire("bar")
    assert rl.usage("foo") == 1
    assert rl.usage("bar") == 1


def test_overrides() -> None:
    rl = RateLimiter(per_minute=1, overrides={"slow": 5})
    for _ in range(5):
        rl.acquire("slow")
    with pytest.raises(RateLimited):
        rl.acquire("slow")


def test_window_expiry() -> None:
    rl = RateLimiter(per_minute=1, window_s=0.05)
    rl.acquire("foo")
    import time as _t

    _t.sleep(0.07)
    assert rl.check("foo") is True
    rl.acquire("foo")


def test_reset() -> None:
    rl = RateLimiter(per_minute=1)
    rl.acquire("foo")
    rl.reset("foo")
    assert rl.check("foo") is True


def test_reset_all() -> None:
    rl = RateLimiter(per_minute=1)
    rl.acquire("a")
    rl.acquire("b")
    rl.reset()
    assert rl.usage("a") == 0
    assert rl.usage("b") == 0
