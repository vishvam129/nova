"""Tests for SettingsService."""

from __future__ import annotations

from typing import Any

import pytest

from nova.ui.settings import SettingsSection, SettingsService


def _section(name: str, initial: dict[str, Any]) -> tuple[SettingsSection, dict[str, Any]]:
    store = dict(initial)

    def load() -> dict[str, Any]:
        return dict(store)

    def save(data: dict[str, Any]) -> None:
        store.clear()
        store.update(data)

    return (
        SettingsSection(name=name, title=name.title(), load=load, save=save),
        store,
    )


def test_register_and_list_sections() -> None:
    svc = SettingsService()
    s1, _ = _section("config", {"theme": "dark"})
    s2, _ = _section("memory", {"max_facts": 5000})
    svc.register(s1)
    svc.register(s2)
    out = svc.sections()
    assert {s["name"] for s in out} == {"config", "memory"}


def test_duplicate_register_raises() -> None:
    svc = SettingsService()
    s1, _ = _section("config", {})
    svc.register(s1)
    with pytest.raises(ValueError):
        svc.register(s1)


def test_get_returns_copy() -> None:
    svc = SettingsService()
    s, store = _section("config", {"theme": "dark"})
    svc.register(s)
    result = svc.get("config")
    assert result == {"theme": "dark"}
    result["theme"] = "light"
    assert store["theme"] == "dark"


def test_set_persists_via_callback() -> None:
    svc = SettingsService()
    s, store = _section("config", {"theme": "dark"})
    svc.register(s)
    svc.set("config", {"theme": "light", "font_size": 14})
    assert store == {"theme": "light", "font_size": 14}


def test_get_missing_raises_keyerror() -> None:
    svc = SettingsService()
    with pytest.raises(KeyError):
        svc.get("ghost")


def test_dispatch_sections_list() -> None:
    svc = SettingsService()
    s, _ = _section("config", {})
    svc.register(s)
    out = svc.dispatch("sections.list", {})
    assert isinstance(out, list)
    assert out[0]["name"] == "config"


def test_dispatch_get_and_set() -> None:
    svc = SettingsService()
    s, store = _section("config", {"theme": "dark"})
    svc.register(s)
    assert svc.dispatch("sections.get", {"name": "config"}) == {"theme": "dark"}
    svc.dispatch("sections.set", {"name": "config", "data": {"theme": "light"}})
    assert store["theme"] == "light"


def test_dispatch_unknown_method_raises() -> None:
    svc = SettingsService()
    with pytest.raises(ValueError):
        svc.dispatch("bogus", {})
