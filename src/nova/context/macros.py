"""Scripted macros: save frequent action chains under a spoken alias.

A ``Macro`` is a named, persistent sequence of step descriptions.  The
agent runs them sequentially via the supplied ``MacroRunner`` callable,
so this module owns only the recording / persistence / lookup parts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MacroStep:
    """One step inside a macro."""

    description: str
    delay_ms: int = 0  # optional pause before this step

    def to_dict(self) -> dict[str, object]:
        return {"description": self.description, "delay_ms": self.delay_ms}

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> MacroStep:
        return cls(
            description=str(d["description"]),
            delay_ms=int(d.get("delay_ms", 0)),  # type: ignore[arg-type]
        )


@dataclass
class Macro:
    name: str
    steps: list[MacroStep] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def matches(self, phrase: str) -> bool:
        p = phrase.lower().strip()
        if p == self.name.lower():
            return True
        return any(p == a.lower() for a in self.aliases)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "aliases": list(self.aliases),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Macro:
        return cls(
            name=str(d["name"]),
            steps=[MacroStep.from_dict(s) for s in d.get("steps", [])],  # type: ignore[arg-type]
            aliases=list(d.get("aliases") or []),  # type: ignore[arg-type]
            created_at=datetime.fromisoformat(str(d.get("created_at", datetime.now().isoformat()))),
        )


@dataclass
class MacroLibrary:
    """JSON-backed macro store."""

    path: Path | None = None
    _macros: dict[str, Macro] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text() or "[]")
            for entry in data:
                m = Macro.from_dict(entry)
                self._macros[m.name.lower()] = m

    def add(self, macro: Macro) -> None:
        self._macros[macro.name.lower()] = macro
        self._save()

    def remove(self, name: str) -> bool:
        if name.lower() not in self._macros:
            return False
        del self._macros[name.lower()]
        self._save()
        return True

    def find(self, phrase: str) -> Macro | None:
        for m in self._macros.values():
            if m.matches(phrase):
                return m
        return None

    def list(self) -> list[Macro]:
        return list(self._macros.values())

    def run(
        self,
        phrase: str,
        runner: Callable[[MacroStep], object],
    ) -> list[object]:
        """Find a macro matching *phrase* and dispatch each step to *runner*."""
        macro = self.find(phrase)
        if macro is None:
            return []
        return [runner(s) for s in macro.steps]

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([m.to_dict() for m in self._macros.values()], indent=2))


__all__ = ["Macro", "MacroLibrary", "MacroStep"]
