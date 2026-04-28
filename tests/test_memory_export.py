"""Tests for nova.memory.export."""

from __future__ import annotations

import json
from pathlib import Path

from nova.memory.export import export_to_files, to_json, to_markdown

_SAMPLE = [
    {"content": "user likes jazz", "importance": 0.8, "id": "m1"},
    {"content": "user lives in SF", "importance": 0.9, "id": "m2"},
]


def test_to_json_roundtrip() -> None:
    s = to_json(_SAMPLE)
    parsed = json.loads(s)
    assert parsed["schema_version"] == 1
    assert len(parsed["memories"]) == 2
    assert parsed["memories"][0]["content"] == "user likes jazz"


def test_to_json_includes_export_timestamp() -> None:
    s = to_json(_SAMPLE)
    assert "exported_at" in json.loads(s)


def test_to_markdown_contains_content() -> None:
    md = to_markdown(_SAMPLE, title="Test")
    assert md.startswith("# Test")
    assert "user likes jazz" in md
    assert "user lives in SF" in md
    assert "Total memories: 2" in md


def test_to_markdown_lists_attributes_alphabetically() -> None:
    md = to_markdown([{"content": "x", "z_field": "z", "a_field": "a"}])
    a_pos = md.find("a_field")
    z_pos = md.find("z_field")
    assert 0 < a_pos < z_pos


def test_export_to_files_writes_both(tmp_path: Path) -> None:
    j, m = export_to_files(_SAMPLE, tmp_path)
    assert j.exists() and j.suffix == ".json"
    assert m.exists() and m.suffix == ".md"
    assert "user likes jazz" in m.read_text()
    parsed = json.loads(j.read_text())
    assert len(parsed["memories"]) == 2


def test_export_to_files_custom_basename(tmp_path: Path) -> None:
    j, m = export_to_files(_SAMPLE, tmp_path, base_name="export-2026")
    assert j.name == "export-2026.json"
    assert m.name == "export-2026.md"


def test_to_json_handles_unknown_types() -> None:
    from datetime import datetime

    s = to_json([{"content": "x", "when": datetime(2026, 4, 25)}])
    parsed = json.loads(s)
    assert "2026-04-25" in parsed["memories"][0]["when"]


def test_empty_export(tmp_path: Path) -> None:
    j, m = export_to_files([], tmp_path)
    parsed = json.loads(j.read_text())
    assert parsed["memories"] == []
    assert "Total memories: 0" in m.read_text()
