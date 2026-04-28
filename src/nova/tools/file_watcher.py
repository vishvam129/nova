"""Polling file watcher: auto-ingest changes from watched dirs.

Pure-stdlib (no inotify dep) — call ``poll()`` from a periodic timer or
loop.  Yields ``FileEvent`` objects describing add / modify / delete since
the last call.

Watcher is decoupled from the memory index — pass the events to whatever
ingestion callback you want.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class FileChange(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FileEvent:
    path: Path
    change: FileChange


@dataclass
class FileWatcher:
    """Polls watched directories and yields events on each ``poll()``."""

    roots: list[Path]
    patterns: tuple[str, ...] = ("*",)
    ignore_dirs: tuple[str, ...] = (".git", "__pycache__", "node_modules", ".venv")

    _state: dict[Path, float] = field(default_factory=dict, init=False)

    def _scan(self) -> dict[Path, float]:
        seen: dict[Path, float] = {}
        for root in self.roots:
            if not root.exists():
                continue
            for path in self._walk(root):
                try:
                    seen[path] = path.stat().st_mtime
                except OSError:
                    continue
        return seen

    def _walk(self, root: Path) -> Iterator[Path]:
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if any(part in self.ignore_dirs for part in path.parts):
                continue
            if not any(path.match(p) for p in self.patterns):
                continue
            yield path

    def poll(self) -> list[FileEvent]:
        new_state = self._scan()
        events: list[FileEvent] = []

        for path, mtime in new_state.items():
            if path not in self._state:
                events.append(FileEvent(path, FileChange.ADDED))
            elif self._state[path] != mtime:
                events.append(FileEvent(path, FileChange.MODIFIED))

        for path in self._state.keys() - new_state.keys():
            events.append(FileEvent(path, FileChange.DELETED))

        self._state = new_state
        return events

    def watch_count(self) -> int:
        return len(self._state)


def ingest(
    events: Iterable[FileEvent],
    add_or_update: object,
    remove: object | None = None,
) -> None:
    """Drive ingestion callbacks from a list of FileEvent."""
    for evt in events:
        if evt.change is FileChange.DELETED:
            if callable(remove):
                remove(evt.path)
        elif callable(add_or_update):
            add_or_update(evt.path)


__all__ = ["FileChange", "FileEvent", "FileWatcher", "ingest"]
