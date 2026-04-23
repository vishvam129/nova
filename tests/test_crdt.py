"""Tests for DictCrdt + merge."""

from __future__ import annotations

from nova.memory.crdt import Crdt, DictCrdt, merge


def test_is_crdt_protocol() -> None:
    assert isinstance(DictCrdt(), Crdt)


def test_set_and_get() -> None:
    c = DictCrdt()
    c.set("fruit", "apple")
    assert c.get("fruit") == "apple"


def test_delete_tombstones_key() -> None:
    c = DictCrdt()
    c.set("k", 1)
    c.delete("k")
    assert c.get("k") is None
    assert "k" not in tuple(c.keys())


def test_merge_converges_both_directions() -> None:
    a = DictCrdt()
    b = DictCrdt()
    a.set("user_lives_in", "Delhi")
    b.set("wife_favorite", "biryani")
    merge(a, b)
    assert a.get("user_lives_in") == "Delhi"
    assert a.get("wife_favorite") == "biryani"
    assert b.get("user_lives_in") == "Delhi"
    assert b.get("wife_favorite") == "biryani"


def test_lamport_preserves_latest_write() -> None:
    a = DictCrdt()
    b = DictCrdt()
    a.set("mode", "dark", lamport=1)
    b.set("mode", "light", lamport=5)  # later wins
    merge(a, b)
    assert a.get("mode") == "light"
    assert b.get("mode") == "light"


def test_concurrent_writes_resolved_by_lamport() -> None:
    a = DictCrdt()
    b = DictCrdt()
    a.set("theme", "ocean", lamport=10)
    b.set("theme", "forest", lamport=10)
    merge(a, b)
    # With equal timestamps, ties are broken by insertion order; the
    # important property is that both replicas converge.
    assert a.get("theme") == b.get("theme")


def test_encode_roundtrip() -> None:
    a = DictCrdt()
    a.set("x", 42)
    a.set("y", [1, 2, 3])
    b = DictCrdt()
    b.apply(a.encode())
    assert b.get("x") == 42
    assert b.get("y") == [1, 2, 3]


def test_offline_phone_syncs_to_laptop() -> None:
    laptop = DictCrdt()
    phone = DictCrdt()
    phone.set("fact:i_live_in", "Delhi")
    # Reconnect: laptop pulls phone state.
    laptop.apply(phone.encode())
    assert laptop.get("fact:i_live_in") == "Delhi"
