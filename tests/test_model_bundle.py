"""Tests for nova.model_bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nova.model_bundle import ModelBundle, ModelEntry, default_models


def _entry(name: str, content: bytes) -> ModelEntry:
    return ModelEntry(
        name=name,
        kind="stt",
        url=f"https://example.com/{name}.bin",
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )


def test_default_models_returns_three() -> None:
    items = list(default_models())
    assert len(items) >= 3
    kinds = {e.kind for e in items}
    assert {"stt", "tts", "wake"} <= kinds


def test_path_for_uses_target_dir(tmp_path: Path) -> None:
    e = _entry("foo", b"hi")
    b = ModelBundle(target_dir=tmp_path, entries=[e])
    assert b.path_for(e).parent == tmp_path


def test_is_present(tmp_path: Path) -> None:
    e = _entry("foo", b"data")
    b = ModelBundle(target_dir=tmp_path, entries=[e])
    assert b.is_present(e) is False
    b.path_for(e).write_bytes(b"data")
    assert b.is_present(e) is True


def test_missing_filters_present(tmp_path: Path) -> None:
    a = _entry("a", b"x")
    bb = _entry("b", b"y")
    bundle = ModelBundle(target_dir=tmp_path, entries=[a, bb])
    bundle.path_for(a).write_bytes(b"x")
    missing = bundle.missing()
    assert len(missing) == 1
    assert missing[0].name == "b"


def test_total_bytes(tmp_path: Path) -> None:
    e1 = _entry("a", b"x" * 10)
    e2 = _entry("b", b"x" * 20)
    bundle = ModelBundle(target_dir=tmp_path, entries=[e1, e2])
    assert bundle.total_bytes() == 30


def test_download_all_with_fetcher(tmp_path: Path) -> None:
    e = _entry("foo", b"payload")
    bundle = ModelBundle(target_dir=tmp_path, entries=[e])

    fetched: list[str] = []

    def fetcher(url: str) -> bytes:
        fetched.append(url)
        return b"payload"

    written = bundle.download_all(fetcher=fetcher)
    assert len(written) == 1
    assert written[0].read_bytes() == b"payload"
    assert fetched == [e.url]


def test_download_all_skips_present(tmp_path: Path) -> None:
    e = _entry("foo", b"payload")
    bundle = ModelBundle(target_dir=tmp_path, entries=[e])
    bundle.path_for(e).write_bytes(b"payload")

    def fetcher(url: str) -> bytes:
        raise AssertionError("should not be called")

    assert bundle.download_all(fetcher=fetcher) == []


def test_verify_matches(tmp_path: Path) -> None:
    e = _entry("foo", b"payload")
    bundle = ModelBundle(target_dir=tmp_path, entries=[e])
    bundle.path_for(e).write_bytes(b"payload")
    assert bundle.verify() == {"foo": True}


def test_verify_mismatch(tmp_path: Path) -> None:
    e = _entry("foo", b"payload")
    bundle = ModelBundle(target_dir=tmp_path, entries=[e])
    bundle.path_for(e).write_bytes(b"different")
    assert bundle.verify() == {"foo": False}


def test_write_manifest(tmp_path: Path) -> None:
    e = _entry("foo", b"x")
    bundle = ModelBundle(target_dir=tmp_path, entries=[e])
    manifest = bundle.write_manifest(tmp_path / "manifest.json")
    data = json.loads(manifest.read_text())
    assert data["models"][0]["name"] == "foo"
    assert data["models"][0]["sha256"] == e.sha256
