"""Streaming STT pipeline: emit partial transcripts during speech.

Wraps any chunk-capable transcriber and emits ``Partial`` events as audio
arrives, plus a ``Final`` event when end-of-turn is signalled.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Protocol


class _ChunkTranscriber(Protocol):
    def transcribe(self, pcm: bytes) -> str: ...


@dataclass(frozen=True, slots=True)
class Partial:
    text: str


@dataclass(frozen=True, slots=True)
class Final:
    text: str


@dataclass
class StreamingPipeline:
    """Buffer audio, re-transcribe rolling window, emit partials + final."""

    transcriber: _ChunkTranscriber
    partial_every_ms: int = 300
    sample_rate: int = 16_000

    _buffer: bytearray = field(default_factory=bytearray, init=False)
    _bytes_since_partial: int = field(default=0, init=False)
    _last_partial: str = field(default="", init=False)

    def push(self, pcm: bytes) -> Partial | None:
        self._buffer.extend(pcm)
        self._bytes_since_partial += len(pcm)
        threshold = int(self.sample_rate * 2 * self.partial_every_ms / 1000)
        if self._bytes_since_partial >= threshold:
            self._bytes_since_partial = 0
            text = self.transcriber.transcribe(bytes(self._buffer))
            if text != self._last_partial:
                self._last_partial = text
                return Partial(text)
        return None

    def finalize(self) -> Final:
        text = self.transcriber.transcribe(bytes(self._buffer))
        self.reset()
        return Final(text)

    def reset(self) -> None:
        self._buffer.clear()
        self._bytes_since_partial = 0
        self._last_partial = ""


def stream(
    pipeline: StreamingPipeline,
    chunks: Iterator[bytes],
    on_event: Callable[[Partial | Final], None],
) -> None:
    """Drive *pipeline* over an iterator of PCM chunks, calling *on_event*."""
    for chunk in chunks:
        evt = pipeline.push(chunk)
        if evt is not None:
            on_event(evt)
    on_event(pipeline.finalize())


__all__ = ["Final", "Partial", "StreamingPipeline", "stream"]
