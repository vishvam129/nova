"""Tests for nova.server.users."""

from __future__ import annotations

from pathlib import Path

from nova.server.users import UserProfile, UserRouter, UserStore


def test_create_and_get(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    u = s.create("Vishvam")
    assert u.display_name == "Vishvam"
    assert s.get(u.id) is not None


def test_per_user_memory_dir_isolated(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    a = s.create("Alice")
    b = s.create("Bob")
    assert s.memory_dir(a.id) != s.memory_dir(b.id)
    assert s.memory_dir(a.id).exists()


def test_by_name_case_insensitive(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    s.create("Carol")
    assert s.by_name("carol") is not None
    assert s.by_name("ghost") is None


def test_list_returns_all(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    s.create("a")
    s.create("b")
    assert len(s.list()) == 2


def test_delete(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    u = s.create("X")
    assert s.delete(u.id) is True
    assert s.delete(u.id) is False


def test_persistence(tmp_path: Path) -> None:
    s1 = UserStore(root=tmp_path)
    u = s1.create("Persisted", is_admin=True)
    s2 = UserStore(root=tmp_path)
    fetched = s2.get(u.id)
    assert fetched is not None
    assert fetched.is_admin is True


def test_profile_dict_roundtrip() -> None:
    p = UserProfile(id="abc", display_name="X", locale="fr-FR", is_admin=True)
    assert UserProfile.from_dict(p.to_dict()) == p


def test_router_for_voice(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    u = s.create("Alice")
    r = UserRouter(store=s)
    r.map_voice_print("vp-1", u.id)
    out = r.resolve(voice_id="vp-1")
    assert out is not None
    assert out.id == u.id


def test_router_for_text_fallback(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    u = s.create("Bob")
    r = UserRouter(store=s, current_user_id=u.id)
    assert r.resolve() is not None


def test_router_no_match(tmp_path: Path) -> None:
    s = UserStore(root=tmp_path)
    r = UserRouter(store=s)
    assert r.resolve(voice_id="ghost") is None
