"""Tests for nova.auto_update."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nova.auto_update import (
    AutoUpdater,
    Channel,
    is_newer,
    parse_manifest,
    verify_signature,
)


def test_is_newer_simple() -> None:
    assert is_newer("1.2.0", "1.1.0") is True
    assert is_newer("1.1.0", "1.2.0") is False
    assert is_newer("1.2.0", "1.2.0") is False


def test_is_newer_v_prefix() -> None:
    assert is_newer("v2.0.0", "1.9.9") is True


def test_is_newer_strips_pre_release() -> None:
    assert is_newer("1.2.0-rc1", "1.1.0") is True


def test_parse_manifest_finds_channel() -> None:
    text = json.dumps(
        {
            "stable": {
                "version": "1.0.0",
                "artifact_url": "https://x/a.tgz",
                "signature_url": "https://x/a.sig",
            },
            "beta": {
                "version": "1.1.0-rc1",
                "artifact_url": "https://x/b.tgz",
                "signature_url": "https://x/b.sig",
            },
        }
    )
    out = parse_manifest(text, Channel.BETA)
    assert out is not None
    assert out.version == "1.1.0-rc1"


def test_parse_manifest_missing_channel() -> None:
    text = json.dumps({"stable": {"version": "1.0.0", "artifact_url": "x", "signature_url": "y"}})
    assert parse_manifest(text, Channel.NIGHTLY) is None


def test_verify_signature_round_trip() -> None:
    pytest.importorskip("nacl")
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    msg = b"release artifact bytes"
    sig = sk.sign(msg).signature
    pub = bytes(sk.verify_key)
    assert verify_signature(msg, sig, pub) is True


def test_verify_signature_rejects_tampered() -> None:
    pytest.importorskip("nacl")
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    sig = sk.sign(b"original").signature
    pub = bytes(sk.verify_key)
    assert verify_signature(b"tampered", sig, pub) is False


def test_verify_signature_returns_false_on_bad_key() -> None:
    assert verify_signature(b"x", b"sig", b"not-a-key") is False


def test_check_returns_release_when_newer(tmp_path: Path) -> None:
    u = AutoUpdater(current_version="1.0.0", stage_dir=tmp_path)
    fake_manifest = json.dumps(
        {"stable": {"version": "1.1.0", "artifact_url": "x", "signature_url": "y"}}
    )
    with patch.object(AutoUpdater, "_fetch", return_value=fake_manifest.encode()):
        rel = u.check()
    assert rel is not None
    assert rel.version == "1.1.0"


def test_check_returns_none_when_up_to_date(tmp_path: Path) -> None:
    u = AutoUpdater(current_version="1.1.0", stage_dir=tmp_path)
    fake_manifest = json.dumps(
        {"stable": {"version": "1.1.0", "artifact_url": "x", "signature_url": "y"}}
    )
    with patch.object(AutoUpdater, "_fetch", return_value=fake_manifest.encode()):
        assert u.check() is None


def test_download_stages_artifact(tmp_path: Path) -> None:
    u = AutoUpdater(
        current_version="1.0.0",
        stage_dir=tmp_path,
        public_key=b"",  # disables signature check
    )
    from nova.auto_update import ReleaseInfo

    rel = ReleaseInfo(
        version="1.1.0",
        channel=Channel.STABLE,
        artifact_url="https://x/a.tgz",
        signature_url="https://x/a.sig",
    )
    fetched: list[str] = []

    def fake_fetch(self, url: str) -> bytes:
        fetched.append(url)
        return b"artifact-bytes" if "tgz" in url else b"sig-bytes"

    with patch.object(AutoUpdater, "_fetch", fake_fetch):
        out = u.download_and_verify(rel)
    assert out is not None
    assert out.read_bytes() == b"artifact-bytes"


def test_download_handles_empty_artifact(tmp_path: Path) -> None:
    u = AutoUpdater(current_version="1.0.0", stage_dir=tmp_path)
    from nova.auto_update import ReleaseInfo

    rel = ReleaseInfo(
        version="1.1.0",
        channel=Channel.STABLE,
        artifact_url="x",
        signature_url="y",
    )
    with patch.object(AutoUpdater, "_fetch", return_value=b""):
        assert u.download_and_verify(rel) is None
