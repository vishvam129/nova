"""Acoustic echo cancellation.

Prevents the assistant's own TTS output from triggering wake-word or
VAD events by subtracting the far-end reference (what we played) from
the near-end capture (what the mic heard).

Backends:
  * ``null``   — identity pass-through; for tests and environments
    without hardware echo (headphones).
  * ``webrtc`` — WebRTC AEC3 via ``webrtc-audio-processing`` (lazy).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EchoCanceller(Protocol):
    sample_rate: int

    def process(self, near_pcm16: bytes, far_pcm16: bytes) -> bytes: ...

    def close(self) -> None: ...


class NullEchoCanceller:
    """Pass-through AEC; useful in tests or for headphone setups."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def process(self, near_pcm16: bytes, far_pcm16: bytes) -> bytes:
        return near_pcm16

    def close(self) -> None:
        pass


class WebRtcAec:
    """WebRTC AEC3 adapter. Requires the ``webrtc-audio-processing`` package."""

    def __init__(self, sample_rate: int = 16000, frame_ms: int = 10) -> None:
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self._ap: Any | None = None

    def _ensure(self) -> Any:
        if self._ap is None:
            from webrtc_audio_processing import AudioProcessingModule

            ap = AudioProcessingModule(aec_type=2, enable_ns=False)
            ap.set_stream_format(self.sample_rate, 1)
            ap.set_reverse_stream_format(self.sample_rate, 1)
            self._ap = ap
        return self._ap

    def process(self, near_pcm16: bytes, far_pcm16: bytes) -> bytes:
        ap = self._ensure()
        ap.process_reverse_stream(far_pcm16)
        result: bytes = ap.process_stream(near_pcm16)
        return result

    def close(self) -> None:
        self._ap = None


_BACKENDS: dict[str, Callable[..., EchoCanceller]] = {
    "null": lambda **kw: NullEchoCanceller(**kw),
    "webrtc": lambda **kw: WebRtcAec(**kw),
}


def create_aec(backend: str = "webrtc", **kwargs: object) -> EchoCanceller:
    if backend not in _BACKENDS:
        raise ValueError(f"unknown AEC backend: {backend!r}")
    return _BACKENDS[backend](**kwargs)


def available_aecs() -> tuple[str, ...]:
    return tuple(_BACKENDS)


def apply_aec(
    aec: EchoCanceller,
    near_frames: Iterable[bytes],
    far_frames: Iterable[bytes],
) -> Iterable[bytes]:
    """Process paired near/far frame streams lock-step."""
    far_iter = iter(far_frames)
    for near in near_frames:
        far = next(far_iter, b"\x00" * len(near))
        yield aec.process(near, far)
