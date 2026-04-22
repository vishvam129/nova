"""Tests for StreamingTranscriber + Moonshine streaming semantics."""

from __future__ import annotations

import time
from collections.abc import Iterable

from nova.voice.stt import StreamingTranscriber, Transcript


class RecordingStt:
    sample_rate = 16000

    def __init__(self) -> None:
        self.seen_sizes: list[int] = []

    def transcribe(self, pcm16: bytes) -> Transcript:
        self.seen_sizes.append(len(pcm16))
        return Transcript(text=f"p{len(self.seen_sizes)}", language=None)

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        for f in frames:
            yield self.transcribe(f)


def _frame(ms: int, sample_rate: int = 16000) -> bytes:
    return b"\x00\x00" * (sample_rate * ms // 1000)


def test_emits_partial_every_n_ms() -> None:
    stt = RecordingStt()
    streamer = StreamingTranscriber(stt, window_ms=1000, partial_every_ms=150)
    # 5 x 150ms frames => 5 partials + 1 final flush
    frames = [_frame(150) for _ in range(5)]
    partials = list(streamer.stream(frames))
    assert len(partials) >= 5
    assert all(p.text.startswith("p") for p in partials)


def test_window_caps_buffer_size() -> None:
    stt = RecordingStt()
    streamer = StreamingTranscriber(stt, window_ms=1000, partial_every_ms=150)
    # Feed 3 seconds of audio — buffer should never exceed ~1s (32k bytes)
    list(streamer.stream([_frame(150) for _ in range(20)]))
    assert max(stt.seen_sizes) <= 16000 * 2  # window_bytes


def test_first_partial_arrives_under_200ms_budget() -> None:
    """Latency budget test: first partial fires after ~150ms of audio.

    Uses a no-op fake engine so wall-clock measures overhead of the
    streamer itself, not the model.
    """
    stt = RecordingStt()
    streamer = StreamingTranscriber(stt, window_ms=1000, partial_every_ms=150)
    frames = iter([_frame(150)])
    t0 = time.perf_counter()
    first = next(iter(streamer.stream(frames)))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert first.text == "p1"
    assert elapsed_ms < 200


def test_no_partial_until_threshold() -> None:
    stt = RecordingStt()
    streamer = StreamingTranscriber(stt, window_ms=1000, partial_every_ms=150)
    # Feed two tiny 50ms chunks — no partial should fire mid-stream,
    # only the flush at end.
    partials = list(streamer.stream([_frame(50), _frame(50)]))
    assert len(partials) == 1  # just the final flush
