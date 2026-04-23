"""Tests for UnifiedSession."""

from __future__ import annotations

from nova.memory.crdt import merge
from nova.server.session import SessionRegistry, UnifiedSession


def test_append_and_iterate_in_order() -> None:
    s = UnifiedSession(session_id="s1")
    s.append("user", "hi", ts=100.0, origin_device="phone")
    s.append("assistant", "hello", ts=101.0, origin_device="laptop")
    msgs = s.messages()
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[0].origin_device == "phone"
    assert msgs[1].content == "hello"


def test_active_device_defaults_none() -> None:
    s = UnifiedSession(session_id="s1")
    assert s.active_device is None


def test_active_device_set_and_get() -> None:
    s = UnifiedSession(session_id="s1")
    s.set_active_device("phone-uuid")
    assert s.active_device == "phone-uuid"


def test_session_registry_creates_unique_ids() -> None:
    reg = SessionRegistry()
    a = reg.create()
    b = reg.create()
    assert a.session_id != b.session_id
    assert reg.get(a.session_id) is a


def test_sessions_converge_after_offline_edits() -> None:
    # Laptop and phone each hold their own doc; neither has talked to
    # the other yet. Both append messages independently.
    laptop = UnifiedSession(session_id="shared")
    phone = UnifiedSession(session_id="shared")
    laptop.append("user", "on laptop", ts=100.0, origin_device="laptop")
    phone.append("user", "on phone", ts=101.0, origin_device="phone")
    merge(laptop.doc, phone.doc)
    # Both replicas now see both messages in timestamp order.
    laptop_msgs = laptop.messages()
    phone_msgs = phone.messages()
    assert len(laptop_msgs) == 2
    assert len(phone_msgs) == 2
    assert [m.content for m in laptop_msgs] == ["on laptop", "on phone"]
    assert [m.content for m in phone_msgs] == ["on laptop", "on phone"]


def test_registry_all_returns_snapshot() -> None:
    reg = SessionRegistry()
    reg.create()
    reg.create()
    assert len(list(reg.all())) == 2
