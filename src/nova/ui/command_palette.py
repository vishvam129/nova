"""Quick-command palette (Ctrl+Shift+Space) for text-only agent invocation.

Spotlight-style: open with a hotkey, fuzzy-match against registered
``Command`` items + recent prompts, hit Enter to execute.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Command:
    name: str
    description: str
    action: Callable[[str], object]
    keywords: tuple[str, ...] = ()


def _score(query: str, text: str) -> int:
    """Substring + prefix scoring; returns 0 if no match."""
    q = query.lower().strip()
    t = text.lower()
    if not q:
        return 1
    if t == q:
        return 1000
    if t.startswith(q):
        return 500
    if q in t:
        return 200
    # Fuzzy: every char of q appears in t in order
    i = 0
    for ch in t:
        if i < len(q) and ch == q[i]:
            i += 1
    return 100 if i == len(q) else 0


@dataclass
class CommandPalette:
    """Holds commands + recent prompts; produces a ranked match list."""

    commands: list[Command] = field(default_factory=list)
    recent: list[str] = field(default_factory=list)
    max_recent: int = 20

    def register(self, command: Command) -> None:
        self.commands.append(command)

    def remember(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            return
        if prompt in self.recent:
            self.recent.remove(prompt)
        self.recent.insert(0, prompt)
        del self.recent[self.max_recent :]

    def query(self, text: str, *, limit: int = 8) -> list[tuple[str, int]]:
        """Return ``(label, score)`` matches ordered by descending score."""
        results: list[tuple[str, int]] = []
        for cmd in self.commands:
            scores = [
                _score(text, cmd.name),
                _score(text, cmd.description) // 2,
                *[_score(text, k) for k in cmd.keywords],
            ]
            best = max(scores) if scores else 0
            if best > 0:
                results.append((cmd.name, best))
        for r in self.recent:
            s = _score(text, r)
            if s > 0:
                results.append((r, s // 2))
        results.sort(key=lambda x: x[1], reverse=True)
        seen: set[str] = set()
        out: list[tuple[str, int]] = []
        for name, score in results:
            if name in seen:
                continue
            seen.add(name)
            out.append((name, score))
            if len(out) >= limit:
                break
        return out

    def execute(self, name_or_prompt: str) -> object:
        """Run the command if name matches; otherwise treat as a free prompt."""
        for cmd in self.commands:
            if cmd.name == name_or_prompt:
                self.remember(name_or_prompt)
                return cmd.action(name_or_prompt)
        # Fallback: invoke the first command tagged 'free_prompt' if any
        for cmd in self.commands:
            if "free_prompt" in cmd.keywords:
                self.remember(name_or_prompt)
                return cmd.action(name_or_prompt)
        self.remember(name_or_prompt)
        return None


__all__ = ["Command", "CommandPalette"]
