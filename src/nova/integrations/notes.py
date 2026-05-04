"""Notes MCP: Obsidian vault + Markdown + SQLite backends.

Tools exposed via ``NotesToolHandler``:
    notes.create   { title, body, folder? }
    notes.read     { id }
    notes.search   { query, limit? }
    notes.list     { folder? }
    notes.delete   { id }

Backends share ``NotesBackend``.  ObsidianVault writes plain Markdown
files (Obsidian reads them live); SqliteNotes is a self-contained
single-file store for users who don't have Obsidian.
"""

from __future__ import annotations

import re
import sqlite3
from builtins import list as _BList
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Note:
    id: str
    title: str
    body: str
    folder: str = ""
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "folder": self.folder,
            "updated_at": self.updated_at.isoformat(),
        }


class NotesBackend(Protocol):
    def create(self, title: str, body: str, *, folder: str = "") -> Note: ...
    def read(self, note_id: str) -> Note | None: ...
    def list(self, folder: str = "") -> Iterable[Note]: ...
    def search(self, query: str, *, limit: int = 20) -> Iterable[Note]: ...
    def delete(self, note_id: str) -> bool: ...


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slug(title: str) -> str:
    return _SLUG_PATTERN.sub("-", title.lower()).strip("-") or "note"


@dataclass
class ObsidianVault:
    """Writes Markdown files into a folder Obsidian opens as a vault."""

    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, note_id: str, folder: str = "") -> Path:
        sub = self.root / folder if folder else self.root
        sub.mkdir(parents=True, exist_ok=True)
        return sub / f"{note_id}.md"

    def create(self, title: str, body: str, *, folder: str = "") -> Note:
        note_id = _slug(title)
        path = self._path(note_id, folder)
        path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        return Note(id=note_id, title=title, body=body, folder=folder)

    def read(self, note_id: str) -> Note | None:
        for md in self.root.rglob(f"{note_id}.md"):
            text = md.read_text(encoding="utf-8")
            title = md.stem
            body = text
            if text.startswith("# "):
                first, rest = text.split("\n", 1)
                title = first[2:].strip()
                body = rest.lstrip("\n")
            folder = str(md.parent.relative_to(self.root)) if md.parent != self.root else ""
            return Note(id=note_id, title=title, body=body, folder=folder)
        return None

    def list(self, folder: str = "") -> _BList[Note]:
        base = self.root / folder if folder else self.root
        notes = [self.read(p.stem) for p in base.rglob("*.md")]
        return [n for n in notes if n is not None]

    def search(self, query: str, *, limit: int = 20) -> _BList[Note]:
        q = query.lower()
        matches: _BList[Note] = []
        for md in self.root.rglob("*.md"):
            text = md.read_text(encoding="utf-8").lower()
            if q in text:
                note = self.read(md.stem)
                if note:
                    matches.append(note)
                if len(matches) >= limit:
                    break
        return matches

    def delete(self, note_id: str) -> bool:
        for md in self.root.rglob(f"{note_id}.md"):
            md.unlink()
            return True
        return False


@dataclass
class SqliteNotes:
    """Single-file SQLite notes store."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS notes("
                "id TEXT PRIMARY KEY, title TEXT, body TEXT, folder TEXT, updated_at TEXT)"
            )

    def create(self, title: str, body: str, *, folder: str = "") -> Note:
        note = Note(id=_slug(title), title=title, body=body, folder=folder)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO notes VALUES (?, ?, ?, ?, ?)",
                (note.id, note.title, note.body, note.folder, note.updated_at.isoformat()),
            )
        return note

    def read(self, note_id: str) -> Note | None:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "SELECT id, title, body, folder, updated_at FROM notes WHERE id = ?",
                (note_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return Note(
            id=row[0],
            title=row[1],
            body=row[2],
            folder=row[3] or "",
            updated_at=datetime.fromisoformat(row[4]),
        )

    def list(self, folder: str = "") -> _BList[Note]:
        with sqlite3.connect(self.path) as conn:
            if folder:
                cur = conn.execute("SELECT id FROM notes WHERE folder = ?", (folder,))
            else:
                cur = conn.execute("SELECT id FROM notes")
            ids = [r[0] for r in cur.fetchall()]
        return [self.read(i) for i in ids if self.read(i) is not None]  # type: ignore[misc]

    def search(self, query: str, *, limit: int = 20) -> _BList[Note]:
        like = f"%{query.lower()}%"
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "SELECT id FROM notes WHERE LOWER(title) LIKE ? OR LOWER(body) LIKE ? LIMIT ?",
                (like, like, limit),
            )
            ids = [r[0] for r in cur.fetchall()]
        return [self.read(i) for i in ids if self.read(i) is not None]  # type: ignore[misc]

    def delete(self, note_id: str) -> bool:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0


@dataclass
class NotesToolHandler:
    backend: NotesBackend

    def call(self, tool: str, **kwargs: Any) -> object:
        if tool == "notes.create":
            note = self.backend.create(
                str(kwargs["title"]),
                str(kwargs.get("body", "")),
                folder=str(kwargs.get("folder", "")),
            )
            return note.to_dict()
        if tool == "notes.read":
            found = self.backend.read(str(kwargs["id"]))
            return found.to_dict() if found else None
        if tool == "notes.search":
            return [
                n.to_dict()
                for n in self.backend.search(
                    str(kwargs["query"]),
                    limit=int(kwargs.get("limit", 20)),
                )
            ]
        if tool == "notes.list":
            return [n.to_dict() for n in self.backend.list(str(kwargs.get("folder", "")))]
        if tool == "notes.delete":
            return {"ok": self.backend.delete(str(kwargs["id"]))}
        raise ValueError(f"unknown notes.* tool: {tool!r}")


__all__ = [
    "Note",
    "NotesBackend",
    "NotesToolHandler",
    "ObsidianVault",
    "SqliteNotes",
]
