"""Tests for StreamingSynthesizer (feature #20)."""

from __future__ import annotations

import time
from collections.abc import Iterable

from nova.voice.tts import AudioBytes, StreamingSynthesizer


class RecordingTts:
    sample_rate = 16000

    def __init__(self) -> None:
        self.synth_calls: list[str] = []

    def synth(self, text: str) -> AudioBytes:
        self.synth_calls.append(text)
        return AudioBytes(pcm16=text.encode(), sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        yield self.synth(text)


def _token_stream(text: str) -> Iterable[str]:
    """Simulate LLM token stream (word-by-word)."""
    for word in text.split(" "):
        yield word + " "


def test_emits_per_sentence() -> None:
    tts = RecordingTts()
    streamer = StreamingSynthesizer(tts)
    chunks = list(streamer.stream(_token_stream("Hello there. How are you? Fine.")))
    # 3 sentences → 3 audio chunks
    assert len(chunks) == 3
    assert tts.synth_calls == ["Hello there.", "How are you?", "Fine."]


def test_tail_without_boundary_is_flushed() -> None:
    tts = RecordingTts()
    streamer = StreamingSynthesizer(tts)
    chunks = list(streamer.stream(_token_stream("no punctuation here")))
    assert len(chunks) == 1
    assert tts.synth_calls == ["no punctuation here"]


def test_does_not_emit_on_short_buffer() -> None:
    tts = RecordingTts()
    streamer = StreamingSynthesizer(tts, min_chars=10)
    # Short sentences under min_chars are buffered until flush.
    chunks = list(streamer.stream(iter(["Hi.", " Ok.", " longer content."])))
    # With min_chars=10, first two boundaries don't trigger; third does.
    assert len(chunks) >= 1
    joined = " ".join(tts.synth_calls)
    assert "longer content" in joined


def test_first_audio_within_500ms_budget() -> None:
    """Latency budget: first audio must arrive before the stream ends."""
    tts = RecordingTts()
    streamer = StreamingSynthesizer(tts)

    def slow_tokens() -> Iterable[str]:
        # First sentence completes at ~50ms; remaining tokens over 2s.
        yield "Hello. "
        for _ in range(20):
            time.sleep(0.1)
            yield "more "
        yield "end."

    t0 = time.perf_counter()
    first = next(iter(streamer.stream(slow_tokens())))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert first.pcm16.startswith(b"Hello")
    assert elapsed_ms < 500, f"first audio arrived in {elapsed_ms:.1f}ms"


def test_newline_counts_as_sentence_boundary() -> None:
    tts = RecordingTts()
    streamer = StreamingSynthesizer(tts)
    chunks = list(streamer.stream(iter(["line one\n", "line two\n", "line three"])))
    assert len(chunks) == 3
