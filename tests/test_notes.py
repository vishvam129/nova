"""Tests for nova.integrations.notes."""

from __future__ import annotations

from pathlib import Path

import pytest

from nova.integrations.notes import (
    NotesToolHandler,
    ObsidianVault,
    SqliteNotes,
)

# ---- Obsidian (Markdown) ----


def test_vault_create_writes_md(tmp_path: Path) -> None:
    v = ObsidianVault(root=tmp_path)
    note = v.create("Hello World", "body text")
    assert (tmp_path / f"{note.id}.md").exists()
    assert "Hello World" in (tmp_path / f"{note.id}.md").read_text()


def test_vault_create_in_folder(tmp_path: Path) -> None:
    v = ObsidianVault(root=tmp_path)
    note = v.create("Meeting", "agenda", folder="work")
    assert (tmp_path / "work" / f"{note.id}.md").exists()
    assert note.folder == "work"


def test_vault_read(tmp_path: Path) -> None:
    v = ObsidianVault(root=tmp_path)
    v.create("Some Title", "Body content here")
    out = v.read("some-title")
    assert out is not None
    assert out.title == "Some Title"
    assert "Body content" in out.body


def test_vault_search_returns_matches(tmp_path: Path) -> None:
    v = ObsidianVault(root=tmp_path)
    v.create("a", "the quick brown fox")
    v.create("b", "no animals here")
    out = v.search("brown")
    assert len(out) == 1
    assert out[0].title == "a"


def test_vault_delete(tmp_path: Path) -> None:
    v = ObsidianVault(root=tmp_path)
    note = v.create("Delete Me", "body")
    assert v.delete(note.id) is True
    assert v.delete(note.id) is False


# ---- SQLite ----


def test_sqlite_create_and_read(tmp_path: Path) -> None:
    s = SqliteNotes(path=tmp_path / "notes.db")
    note = s.create("Title", "body")
    out = s.read(note.id)
    assert out is not None
    assert out.body == "body"


def test_sqlite_list_filters_by_folder(tmp_path: Path) -> None:
    s = SqliteNotes(path=tmp_path / "notes.db")
    s.create("a", "x", folder="work")
    s.create("b", "x", folder="personal")
    assert len(s.list("work")) == 1
    assert len(s.list()) == 2


def test_sqlite_search(tmp_path: Path) -> None:
    s = SqliteNotes(path=tmp_path / "notes.db")
    s.create("a", "the quick brown fox")
    s.create("b", "calm seas")
    matches = s.search("brown")
    assert len(matches) == 1


def test_sqlite_delete(tmp_path: Path) -> None:
    s = SqliteNotes(path=tmp_path / "notes.db")
    note = s.create("x", "y")
    assert s.delete(note.id) is True
    assert s.delete(note.id) is False


# ---- Handler ----


def test_handler_create_and_read(tmp_path: Path) -> None:
    h = NotesToolHandler(backend=SqliteNotes(path=tmp_path / "n.db"))
    created = h.call("notes.create", title="Hello", body="World")
    assert isinstance(created, dict)
    out = h.call("notes.read", id=created["id"])
    assert out is not None


def test_handler_search(tmp_path: Path) -> None:
    h = NotesToolHandler(backend=SqliteNotes(path=tmp_path / "n.db"))
    h.call("notes.create", title="a", body="quick brown fox")
    out = h.call("notes.search", query="brown", limit=5)
    assert isinstance(out, list)
    assert len(out) == 1


def test_handler_delete(tmp_path: Path) -> None:
    h = NotesToolHandler(backend=SqliteNotes(path=tmp_path / "n.db"))
    created = h.call("notes.create", title="x", body="y")
    assert h.call("notes.delete", id=created["id"]) == {"ok": True}


def test_handler_unknown_tool(tmp_path: Path) -> None:
    h = NotesToolHandler(backend=SqliteNotes(path=tmp_path / "n.db"))
    with pytest.raises(ValueError):
        h.call("notes.bogus")
