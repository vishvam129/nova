"""Tests for nova.safety.speaker_verify."""

from __future__ import annotations

from pathlib import Path

from nova.safety.speaker_verify import (
    HashEmbedder,
    SpeakerVerifier,
    cosine,
)


def test_cosine_identical_vectors() -> None:
    a = [1.0, 0.0, 0.0]
    assert cosine(a, a) == 1.0


def test_cosine_orthogonal() -> None:
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_zero_vector_returns_zero() -> None:
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_mismatched_lengths() -> None:
    assert cosine([1.0], [1.0, 2.0]) == 0.0


def test_hash_embedder_deterministic() -> None:
    e = HashEmbedder()
    pcm = b"hello world this is some audio bytes"
    assert list(e.embed(pcm)) == list(e.embed(pcm))


def test_hash_embedder_different_inputs() -> None:
    e = HashEmbedder()
    a = e.embed(b"speaker A speaks 0123456789ABCDEF")
    b = e.embed(b"speaker B has very different audio bytes go here")
    assert list(a) != list(b)


def test_verify_no_enrollments() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder())
    matched, name, score = sv.verify(b"abc")
    assert matched is False
    assert name == ""
    assert score == 0.0


def test_verify_matches_enrolled_speaker() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder(), threshold=0.5)
    audio = b"voice sample of vishvam speaking nova" * 10
    sv.enroll("vishvam", audio)
    matched, name, score = sv.verify(audio)
    assert matched is True
    assert name == "vishvam"
    assert score > 0.99


def test_verify_threshold_blocks_different_voice() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder(), threshold=0.99)
    sv.enroll("alice", b"alice speaking 0123456789" * 50)
    matched, _, _ = sv.verify(b"bob speaking xyz" * 50)
    assert matched is False


def test_save_and_load(tmp_path: Path) -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder())
    sv.enroll("a", b"sample audio bytes" * 20)
    sv.save(tmp_path / "voices.json")

    sv2 = SpeakerVerifier(embedder=HashEmbedder())
    sv2.load(tmp_path / "voices.json")
    assert "a" in sv2.enrollments
    assert sv2.enrollments["a"] == sv.enrollments["a"]


def test_load_missing_file_is_noop(tmp_path: Path) -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder())
    sv.load(tmp_path / "ghost.json")
    assert sv.enrollments == {}
