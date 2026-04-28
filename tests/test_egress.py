"""Tests for nova.safety.egress."""

from __future__ import annotations

import pytest

from nova.safety.egress import EgressBlocked, EgressPolicy


def test_default_deny_blocks_unknown() -> None:
    p = EgressPolicy()
    assert p.is_allowed("https://example.com/foo") is False


def test_exact_host_allowed() -> None:
    p = EgressPolicy()
    p.add("example.com")
    assert p.is_allowed("https://example.com/foo") is True


def test_url_with_port_extracts_host() -> None:
    p = EgressPolicy()
    p.add("example.com")
    assert p.is_allowed("example.com:8080") is True


def test_suffix_wildcard() -> None:
    p = EgressPolicy()
    p.add("*.example.com")
    assert p.is_allowed("https://api.example.com/x") is True
    assert p.is_allowed("https://example.com") is False  # bare host doesn't match *.suffix


def test_global_wildcard() -> None:
    p = EgressPolicy()
    p.add("*")
    assert p.is_allowed("https://anything.example.com") is True


def test_check_raises_when_blocked() -> None:
    p = EgressPolicy()
    with pytest.raises(EgressBlocked) as ctx:
        p.check("https://blocked.com")
    assert ctx.value.host == "blocked.com"


def test_check_passes_when_allowed() -> None:
    p = EgressPolicy()
    p.add("ok.com")
    p.check("https://ok.com/path")  # no raise


def test_loopback_allowed_via_pattern() -> None:
    p = EgressPolicy()
    p.add("loopback")
    assert p.is_allowed("127.0.0.1") is True
    assert p.is_allowed("localhost") is True


def test_loopback_blocked_by_default() -> None:
    p = EgressPolicy()
    assert p.is_allowed("127.0.0.1") is False


def test_remove() -> None:
    p = EgressPolicy()
    p.add("example.com")
    p.remove("example.com")
    assert p.is_allowed("example.com") is False


def test_default_allow_mode() -> None:
    p = EgressPolicy(default_deny=False)
    assert p.is_allowed("anything.com") is True


def test_case_insensitive() -> None:
    p = EgressPolicy()
    p.add("Example.com")
    assert p.is_allowed("EXAMPLE.com") is True
