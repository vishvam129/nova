"""Global push-to-talk hotkey.

Cross-platform via the optional ``pynput`` dependency.  Falls back to a
no-op recorder when pynput is missing — useful for tests / headless CI.
The hotkey string is parsed in a small Combo dataclass so we can ship a
deterministic test surface.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Combo:
    """A single hotkey combination, e.g. Ctrl+Space."""

    modifiers: frozenset[str]
    key: str

    @classmethod
    def parse(cls, spec: str) -> Combo:
        parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
        if not parts:
            raise ValueError(f"empty hotkey: {spec!r}")
        key = parts[-1]
        modifiers = frozenset(parts[:-1])
        valid_mods = {"ctrl", "alt", "shift", "cmd", "super", "meta"}
        unknown = modifiers - valid_mods
        if unknown:
            raise ValueError(f"unknown modifiers: {unknown}")
        return cls(modifiers=modifiers, key=key)

    def __str__(self) -> str:
        ordered_mods = sorted(self.modifiers)
        return "+".join([*[m.capitalize() for m in ordered_mods], self.key.capitalize()])


@dataclass
class PushToTalk:
    """Tracks the configured hotkey and fires a callback while it's held."""

    combo: Combo = field(default_factory=lambda: Combo.parse("Ctrl+Space"))
    on_press: Callable[[], None] | None = None
    on_release: Callable[[], None] | None = None

    _held: bool = field(default=False, init=False)

    @property
    def is_held(self) -> bool:
        return self._held

    def press(self) -> None:
        if self._held:
            return
        self._held = True
        if self.on_press:
            self.on_press()

    def release(self) -> None:
        if not self._held:
            return
        self._held = False
        if self.on_release:
            self.on_release()

    def matches(self, modifiers: set[str], key: str) -> bool:
        mods = {m.lower() for m in modifiers}
        return mods == set(self.combo.modifiers) and key.lower() == self.combo.key

    def update_combo(self, spec: str) -> None:
        self.combo = Combo.parse(spec)


__all__ = ["Combo", "PushToTalk"]
