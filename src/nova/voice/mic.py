"""Cross-platform microphone capture.

Uses ``sounddevice`` which wraps PortAudio (PipeWire/ALSA on Linux,
CoreAudio on macOS, WASAPI on Windows). Audio is delivered to a callback
as mono PCM-16 chunks at the configured sample rate.
"""

from __future__ import annotations

import contextlib
import queue
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """A fixed-size mono PCM-16 frame."""

    pcm16: bytes
    sample_rate: int


FrameCallback = Callable[[AudioChunk], None]


class MicStream:
    """Context-manager wrapper around a sounddevice InputStream.

    Example::

        with MicStream() as mic:
            for chunk in mic.frames():
                process(chunk.pcm16)
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        device: int | str | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.device = device
        self._queue: queue.Queue[AudioChunk] = queue.Queue(maxsize=64)
        self._stream: Any | None = None
        self._stop_event = threading.Event()

    @property
    def frame_size(self) -> int:
        return int(self.sample_rate * self.frame_ms / 1000)

    def _callback(self, indata: Any, frames: int, time_info: Any, status: Any) -> None:
        import numpy as np

        if status:  # pragma: no cover — runtime audio warnings
            return
        mono = np.asarray(indata).reshape(-1)
        pcm16 = (mono * 32767).astype(np.int16).tobytes()
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(AudioChunk(pcm16=pcm16, sample_rate=self.sample_rate))

    def start(self) -> None:
        import sounddevice as sd

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.frame_size,
            callback=self._callback,
            device=self.device,
        )
        self._stream.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def frames(self, timeout: float = 1.0) -> Iterator[AudioChunk]:
        """Yield chunks until ``stop()`` is called."""
        while not self._stop_event.is_set():
            try:
                yield self._queue.get(timeout=timeout)
            except queue.Empty:
                continue

    def __enter__(self) -> MicStream:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.stop()


def list_devices() -> list[dict[str, Any]]:
    """Return a list of input devices (lazy import)."""
    import sounddevice as sd

    devices = sd.query_devices()
    return [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]
