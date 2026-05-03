"""Tests for nova.voice.voice_clone."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from nova.voice.voice_clone import VoiceCloneStore


class _FakeXtts:
    def __init__(self) -> None:
        self.encoded_pcm: bytes = b""
        self.synthesized: list[tuple[str, bytes]] = []

    def encode_speaker(self, pcm: bytes, sample_rate: int) -> bytes:
        self.encoded_pcm = pcm
        return b"vec-" + pcm[:4]

    def synthesize(self, text: str, speaker_vector: bytes) -> bytes:
        self.synthesized.append((text, speaker_vector))
        return b"audio:" + text.encode()


def _wav(path: Path, seconds: float, rate: int = 16_000) -> Path:
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{n}h", *([0] * n)))
    return path


def test_invalid_key_length(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"short", storage_dir=tmp_path)


def test_enroll_too_short(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    sample = _wav(tmp_path / "s.wav", seconds=2.0)
    store = VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"k" * 32, storage_dir=tmp_path)
    with pytest.raises(ValueError):
        store.enroll("alice", sample)


def test_enroll_too_long(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    sample = _wav(tmp_path / "s.wav", seconds=60.0)
    store = VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"k" * 32, storage_dir=tmp_path)
    with pytest.raises(ValueError):
        store.enroll("alice", sample)


def test_enroll_writes_encrypted_vector(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    sample = _wav(tmp_path / "s.wav", seconds=6.0)
    store = VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"k" * 32, storage_dir=tmp_path)
    profile = store.enroll("alice", sample)
    assert profile.user == "alice"
    assert profile.encrypted_vector_path.exists()
    blob = profile.encrypted_vector_path.read_bytes()
    # Encrypted bytes must not contain plaintext "vec-"
    assert b"vec-" not in blob


def test_synthesize_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    sample = _wav(tmp_path / "s.wav", seconds=6.0)
    backend = _FakeXtts()
    store = VoiceCloneStore(backend=backend, encryption_key=b"k" * 32, storage_dir=tmp_path)
    store.enroll("alice", sample)
    audio = store.synthesize("alice", "hello")
    assert audio == b"audio:hello"
    assert len(backend.synthesized) == 1
    assert backend.synthesized[0][1].startswith(b"vec-")


def test_synthesize_unknown_user(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    store = VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"k" * 32, storage_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.synthesize("ghost", "hi")


def test_forget_removes_profile(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    sample = _wav(tmp_path / "s.wav", seconds=6.0)
    store = VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"k" * 32, storage_dir=tmp_path)
    store.enroll("alice", sample)
    assert store.forget("alice") is True
    assert store.forget("alice") is False


def test_list_users(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    a = _wav(tmp_path / "a.wav", seconds=6.0)
    b = _wav(tmp_path / "b.wav", seconds=6.0)
    store = VoiceCloneStore(backend=_FakeXtts(), encryption_key=b"k" * 32, storage_dir=tmp_path)
    store.enroll("alice", a)
    store.enroll("bob", b)
    assert store.list_users() == ["alice", "bob"]
