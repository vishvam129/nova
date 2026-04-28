"""Tests for nova.server.handoff."""

from __future__ import annotations

import time

import pytest

from nova.server.handoff import Handoff, HandoffCoordinator, HandoffState


def test_initiate_creates_pending() -> None:
    c = HandoffCoordinator()
    hid = c.initiate(session_id="s1", from_device="phone", to_device="laptop")
    h = c.get(hid)
    assert h is not None
    assert h.state is HandoffState.PENDING
    assert h.from_device == "phone"
    assert h.to_device == "laptop"


def test_initiate_same_device_raises() -> None:
    c = HandoffCoordinator()
    with pytest.raises(ValueError):
        c.initiate(session_id="s", from_device="x", to_device="x")


def test_accept_marks_accepted() -> None:
    c = HandoffCoordinator()
    hid = c.initiate(session_id="s", from_device="phone", to_device="laptop")
    h = c.accept(hid)
    assert h is not None
    assert h.state is HandoffState.ACCEPTED


def test_accept_unknown_returns_none() -> None:
    c = HandoffCoordinator()
    assert c.accept("nope") is None


def test_reject() -> None:
    c = HandoffCoordinator()
    hid = c.initiate(session_id="s", from_device="phone", to_device="laptop")
    assert c.reject(hid) is True
    assert c.get(hid).state is HandoffState.REJECTED  # type: ignore[union-attr]


def test_pending_for_returns_only_target_pending() -> None:
    c = HandoffCoordinator()
    a = c.initiate(session_id="s1", from_device="phone", to_device="laptop")
    c.initiate(session_id="s2", from_device="phone", to_device="watch")
    pending = c.pending_for("laptop")
    assert len(pending) == 1
    assert pending[0].id == a


def test_expire_after_ttl() -> None:
    c = HandoffCoordinator(ttl_s=0.05)
    hid = c.initiate(session_id="s", from_device="a", to_device="b")
    time.sleep(0.1)
    assert c.accept(hid) is None  # expired
    assert c.get(hid).state is HandoffState.EXPIRED  # type: ignore[union-attr]


def test_expire_old_marks_pending_as_expired() -> None:
    c = HandoffCoordinator(ttl_s=0.05)
    c.initiate(session_id="s", from_device="a", to_device="b")
    time.sleep(0.1)
    expired = c.expire_old()
    assert expired == 1


def test_on_transfer_callback_fires() -> None:
    captured: list[Handoff] = []
    c = HandoffCoordinator(on_transfer=captured.append)
    hid = c.initiate(session_id="s", from_device="a", to_device="b")
    c.accept(hid)
    assert len(captured) == 1
    assert captured[0].session_id == "s"
