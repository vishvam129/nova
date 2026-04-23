"""Settings backend for the Tauri GUI.

The GUI is a Tauri webview frontend; this module exposes the typed
JSON bridge it talks to. Every settings page (config, MCPs, memory,
devices, safety) is a ``SettingsSection`` with ``load`` and ``save``
callbacks so the frontend never touches disk directly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SettingsSection:
    name: str
    title: str
    load: Callable[[], dict[str, Any]]
    save: Callable[[dict[str, Any]], None]


@dataclass
class SettingsService:
    """Registry + dispatcher for all settings sections."""

    _sections: dict[str, SettingsSection] = field(default_factory=dict)

    def register(self, section: SettingsSection) -> None:
        if section.name in self._sections:
            raise ValueError(f"section {section.name!r} already registered")
        self._sections[section.name] = section

    def sections(self) -> list[dict[str, str]]:
        return [{"name": s.name, "title": s.title} for s in self._sections.values()]

    def get(self, name: str) -> dict[str, Any]:
        section = self._sections.get(name)
        if section is None:
            raise KeyError(f"no section {name!r}")
        return dict(section.load())

    def set(self, name: str, data: dict[str, Any]) -> None:
        section = self._sections.get(name)
        if section is None:
            raise KeyError(f"no section {name!r}")
        section.save(data)

    def dispatch(self, method: str, params: dict[str, Any]) -> Any:
        """JSON-RPC style dispatch used by the Tauri bridge."""
        if method == "sections.list":
            return self.sections()
        if method == "sections.get":
            return self.get(params["name"])
        if method == "sections.set":
            self.set(params["name"], params["data"])
            return {"ok": True}
        raise ValueError(f"unknown method: {method!r}")


__all__ = ["SettingsSection", "SettingsService"]
