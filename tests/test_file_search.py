"""Tests for local file search."""

from __future__ import annotations

from pathlib import Path

from nova.tools.builtin.file_search import FileHit, FileIndex


def _write(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_index_counts_text_files(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "notes about taxes and budget")
    _write(tmp_path, "b.py", "def calc(): ...")
    _write(tmp_path, "c.bin", "\x00\x01")  # non-text extension: skipped
    idx = FileIndex()
    count = idx.index_paths([tmp_path])
    assert count == 2
    assert len(idx) == 2


def test_search_finds_relevant_file(tmp_path: Path) -> None:
    tax = _write(tmp_path, "tax-return-2025.md", "my tax PDF summary for 2025")
    _write(tmp_path, "grocery.md", "list of groceries I need")
    _write(tmp_path, "poem.md", "a short poem about the sea")
    idx = FileIndex()
    idx.index_paths([tmp_path])
    hits = idx.search("find my tax document", k=1)
    assert len(hits) == 1
    assert hits[0].path == tax
    assert isinstance(hits[0], FileHit)


def test_search_returns_empty_on_fresh_index() -> None:
    idx = FileIndex()
    assert idx.search("anything", k=3) == []


def test_index_skips_oversized_files(tmp_path: Path) -> None:
    big = tmp_path / "big.md"
    big.write_text("x" * 100_000)
    idx = FileIndex(max_bytes=1000)
    count = idx.index_paths([tmp_path])
    assert count == 0


def test_index_single_file(tmp_path: Path) -> None:
    f = _write(tmp_path, "one.md", "hello nova")
    idx = FileIndex()
    count = idx.index_paths([f])
    assert count == 1


def test_preview_truncated_to_400_chars(tmp_path: Path) -> None:
    _write(tmp_path, "long.md", "a" * 5000)
    idx = FileIndex()
    idx.index_paths([tmp_path])
    hits = idx.search("a", k=1)
    assert len(hits[0].preview) <= 400
