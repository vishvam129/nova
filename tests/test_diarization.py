"""Tests for nova.safety.diarization."""

from __future__ import annotations

from nova.safety.diarization import Segment, TrustGate, VerifierDiarizer
from nova.safety.speaker_verify import HashEmbedder, SpeakerVerifier


def _audio_for(token: bytes, repeats: int = 50) -> bytes:
    return token * repeats


def test_segment_dataclass() -> None:
    s = Segment(pcm=b"x", speaker="alice", start_s=0.0, end_s=1.0)
    assert s.speaker == "alice"


def test_verifier_diarizer_assigns_speakers() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder(), threshold=0.0)
    sv.enroll("alice", _audio_for(b"alice-token-12345678"))

    dia = VerifierDiarizer(verifier=sv, window_s=0.1, min_score=0.0)
    segments = dia.diarize(_audio_for(b"alice-token-12345678"), sample_rate=16_000)
    assert len(segments) > 0
    assert all(s.speaker == "alice" for s in segments)


def test_verifier_diarizer_unknown_when_below_min_score() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder(), threshold=0.0)
    sv.enroll("alice", _audio_for(b"alice-voice-pattern-aaaa"))

    dia = VerifierDiarizer(verifier=sv, window_s=0.1, min_score=2.0)  # impossible
    segments = dia.diarize(_audio_for(b"bob-voice-pattern-bbbb"), sample_rate=16_000)
    assert all(s.speaker == "unknown" for s in segments)


def test_trust_gate_filter_keeps_only_trusted() -> None:
    gate = TrustGate(trusted_users={"alice"})
    segs = [
        Segment(pcm=b"a", speaker="alice", start_s=0, end_s=1),
        Segment(pcm=b"b", speaker="bob", start_s=1, end_s=2),
        Segment(pcm=b"c", speaker="unknown", start_s=2, end_s=3),
    ]
    out = gate.filter(segs)
    assert len(out) == 1
    assert out[0].speaker == "alice"


def test_has_trusted_speech() -> None:
    gate = TrustGate(trusted_users={"alice"})
    segs = [Segment(pcm=b"a", speaker="alice", start_s=0, end_s=1)]
    assert gate.has_trusted_speech(segs) is True
    assert gate.has_trusted_speech([]) is False


def test_trust_gate_add_remove() -> None:
    gate = TrustGate()
    gate.add("alice")
    assert "alice" in gate.trusted_users
    gate.remove("alice")
    assert "alice" not in gate.trusted_users


def test_diarize_empty_audio() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder())
    dia = VerifierDiarizer(verifier=sv)
    assert dia.diarize(b"") == []


def test_diarize_zero_window_returns_empty() -> None:
    sv = SpeakerVerifier(embedder=HashEmbedder())
    dia = VerifierDiarizer(verifier=sv, window_s=0.0)
    assert dia.diarize(b"\x00" * 100) == []
