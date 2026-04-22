"""Tests for microphone capture (hardware-free)."""

from __future__ import annotations

import numpy as np

from nova.voice.mic import AudioChunk, MicStream


def test_frame_size_30ms_at_16k() -> None:
    mic = MicStream(sample_rate=16000, frame_ms=30)
    assert mic.frame_size == 480


def test_frame_size_20ms_at_48k() -> None:
    mic = MicStream(sample_rate=48000, frame_ms=20)
    assert mic.frame_size == 960


def test_callback_produces_pcm16_chunks() -> None:
    mic = MicStream(sample_rate=16000, frame_ms=30)
    tone = np.sin(np.linspace(0, 2 * np.pi, mic.frame_size)).astype(np.float32)
    mic._callback(tone.reshape(-1, 1), mic.frame_size, None, None)  # type: ignore[arg-type]
    chunk = mic._queue.get_nowait()
    assert isinstance(chunk, AudioChunk)
    assert chunk.sample_rate == 16000
    assert len(chunk.pcm16) == mic.frame_size * 2  # int16 = 2 bytes/sample


def test_callback_drops_when_queue_full() -> None:
    mic = MicStream(sample_rate=16000, frame_ms=30)
    # fill the queue
    dummy = AudioChunk(pcm16=b"\x00\x00" * mic.frame_size, sample_rate=16000)
    for _ in range(mic._queue.maxsize):
        mic._queue.put_nowait(dummy)
    # this should not raise
    tone = np.zeros(mic.frame_size, dtype=np.float32)
    mic._callback(tone.reshape(-1, 1), mic.frame_size, None, None)  # type: ignore[arg-type]
