"""Tests for nova.tools.file_watcher."""

from __future__ import annotations

import time
from pathlib import Path

from nova.tools.file_watcher import FileChange, FileEvent, FileWatcher, ingest


def test_first_poll_is_all_added(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hi")
    (tmp_path / "b.txt").write_text("hi")
    w = FileWatcher(roots=[tmp_path])
    events = w.poll()
    assert {e.change for e in events} == {FileChange.ADDED}
    assert len(events) == 2


def test_no_change_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hi")
    w = FileWatcher(roots=[tmp_path])
    w.poll()
    assert w.poll() == []


def test_modified_detected(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("v1")
    w = FileWatcher(roots=[tmp_path])
    w.poll()
    time.sleep(0.05)
    f.write_text("v2")
    # also bump mtime explicitly to avoid filesystem mtime resolution issues
    new_mtime = f.stat().st_mtime + 1.0
    import os

    os.utime(f, (new_mtime, new_mtime))
    events = w.poll()
    assert any(e.change is FileChange.MODIFIED for e in events)


def test_deleted_detected(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("hi")
    w = FileWatcher(roots=[tmp_path])
    w.poll()
    f.unlink()
    events = w.poll()
    assert events == [FileEvent(f, FileChange.DELETED)]


def test_ignore_dirs(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "secret").write_text("nope")
    (tmp_path / "a.txt").write_text("hi")
    w = FileWatcher(roots=[tmp_path])
    events = w.poll()
    paths = {e.path.name for e in events}
    assert "a.txt" in paths
    assert "secret" not in paths


def test_pattern_filter(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    w = FileWatcher(roots=[tmp_path], patterns=("*.py",))
    events = w.poll()
    assert {e.path.name for e in events} == {"a.py"}


def test_missing_root_is_skipped(tmp_path: Path) -> None:
    w = FileWatcher(roots=[tmp_path / "ghost"])
    assert w.poll() == []


def test_ingest_dispatches(tmp_path: Path) -> None:
    added: list[Path] = []
    deleted: list[Path] = []
    f = tmp_path / "a.txt"
    events = [
        FileEvent(f, FileChange.ADDED),
        FileEvent(f, FileChange.DELETED),
    ]
    ingest(events, add_or_update=added.append, remove=deleted.append)
    assert added == [f]
    assert deleted == [f]
