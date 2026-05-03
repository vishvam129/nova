"""Tests for nova.tools.browser_extension."""

from __future__ import annotations

import pytest

from nova.tools.browser_extension import (
    BrowserExtensionGate,
    DomCall,
    Grant,
    PermissionDenied,
    SitePermissions,
)


def test_default_grant_is_denied() -> None:
    p = SitePermissions()
    assert p.grant("example.com") is Grant.DENIED


def test_set_and_grant() -> None:
    p = SitePermissions()
    p.set("https://example.com/path", Grant.READ)
    assert p.grant("example.com") is Grant.READ


def test_can_read_and_write() -> None:
    p = SitePermissions()
    p.set("a.com", Grant.READ)
    p.set("b.com", Grant.READ_WRITE)
    assert p.can_read("a.com") is True
    assert p.can_write("a.com") is False
    assert p.can_write("b.com") is True


def test_revoke() -> None:
    p = SitePermissions()
    p.set("a.com", Grant.READ)
    assert p.revoke("a.com") is True
    assert p.revoke("a.com") is False


def test_origins_sorted() -> None:
    p = SitePermissions()
    p.set("z.com", Grant.READ)
    p.set("a.com", Grant.READ)
    assert list(p.origins()) == ["a.com", "z.com"]


def test_normalize_strips_path() -> None:
    p = SitePermissions()
    p.set("https://example.com:8080/foo/bar", Grant.READ)
    assert p.grant("example.com:8080") is Grant.READ


def test_gate_allows_read_for_read_grant() -> None:
    p = SitePermissions()
    p.set("a.com", Grant.READ)
    gate = BrowserExtensionGate(permissions=p)
    gate.check(DomCall(tool="dom.query", origin="a.com", args={"selector": "div"}))


def test_gate_blocks_write_for_read_grant() -> None:
    p = SitePermissions()
    p.set("a.com", Grant.READ)
    gate = BrowserExtensionGate(permissions=p)
    with pytest.raises(PermissionDenied):
        gate.check(DomCall(tool="dom.click", origin="a.com"))


def test_gate_allows_write_for_read_write() -> None:
    p = SitePermissions()
    p.set("a.com", Grant.READ_WRITE)
    gate = BrowserExtensionGate(permissions=p)
    gate.check(DomCall(tool="dom.fill", origin="a.com", args={"selector": "input", "value": "x"}))


def test_gate_blocks_unknown_tool() -> None:
    p = SitePermissions()
    p.set("a.com", Grant.READ_WRITE)
    gate = BrowserExtensionGate(permissions=p)
    with pytest.raises(PermissionDenied):
        gate.check(DomCall(tool="dom.bogus", origin="a.com"))


def test_dom_call_encode() -> None:
    import json

    call = DomCall(tool="dom.query", origin="a.com", args={"selector": "div"}, call_id="c1")
    parsed = json.loads(call.encode())
    assert parsed["type"] == "browser_dom_call"
    assert parsed["origin"] == "a.com"
    assert parsed["call_id"] == "c1"
