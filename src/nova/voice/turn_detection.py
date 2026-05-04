"""End-of-turn detection for the voice pipeline.

Traditional energy VAD introduces ~800 ms of silence before signalling
turn-end.  Model-based detectors trained on conversational prosody can
call end-of-turn in <250 ms by predicting whether the speaker has finished
a complete thought — even before the trailing silence is conclusive.

Architecture::

    TurnDetector (Protocol)
        ├── VadTurnDetector   — energy threshold, ~800 ms latency (fallback)
        ├── ModelTurnDetector — wraps LiveKit turn-detector ONNX model, <250 ms
        └── HybridTurnDetector — model primary, VAD fallback

The model backend is imported lazily so the module loads even without the
onnxruntime / livekit-agents package installed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TurnDetector(Protocol):
    """Protocol all turn detectors implement."""

    def push_audio(self, pcm: bytes) -> None:
        """Feed a chunk of raw PCM (16-bit, 16 kHz, mono)."""
        ...

    def is_turn_complete(self) -> bool:
        """Return True when the speaker has finished their turn."""
        ...

    def reset(self) -> None:
        """Reset internal state for a new utterance."""
        ...

    @property
    def latency_ms(self) -> float:
        """Estimated end-of-turn latency in milliseconds."""
        ...


@dataclass
class VadTurnDetector:
    """Energy-VAD-based turn detector (~800 ms latency).

    Signals end-of-turn after *silence_ms* milliseconds of audio whose
    RMS energy is below *energy_threshold*.
    """

    energy_threshold: float = 0.01
    silence_ms: float = 800.0
    sample_rate: int = 16_000

    _silence_start: float | None = field(default=None, init=False, repr=False)
    _complete: bool = field(default=False, init=False, repr=False)

    def push_audio(self, pcm: bytes) -> None:
        rms = _rms(pcm)
        if rms < self.energy_threshold:
            if self._silence_start is None:
                self._silence_start = time.monotonic()
            elapsed_ms = (time.monotonic() - self._silence_start) * 1000
            if elapsed_ms >= self.silence_ms:
                self._complete = True
        else:
            self._silence_start = None
            self._complete = False

    def is_turn_complete(self) -> bool:
        return self._complete

    def reset(self) -> None:
        self._silence_start = None
        self._complete = False

    @property
    def latency_ms(self) -> float:
        return self.silence_ms


@dataclass
class ModelTurnDetector:
    """LiveKit turn-detector ONNX model — <250 ms latency.

    The model scores each 20 ms frame with end-of-turn probability.
    A detection fires when the exponential moving average of the score
    crosses *threshold*.

    The ONNX model is loaded lazily on first ``push_audio`` call so import
    remains fast when onnxruntime is not installed.

    model_path: Path to the ``turn_detector.onnx`` file.  If None, the
                default model bundled with livekit-agents is used.
    """

    threshold: float = 0.55
    smoothing: float = 0.6
    model_path: str | None = None

    _session: Any = field(default=None, init=False, repr=False)
    _ema: float = field(default=0.0, init=False, repr=False)
    _complete: bool = field(default=False, init=False, repr=False)
    _frames: list[bytes] = field(default_factory=list, init=False, repr=False)

    def _ensure_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            import onnxruntime as ort

            path = self.model_path or _default_model_path()
            self._session = ort.InferenceSession(path)
        except Exception as exc:
            raise RuntimeError(
                "ModelTurnDetector requires onnxruntime and the LiveKit "
                "turn-detector model. Install with: "
                "pip install onnxruntime livekit-agents"
            ) from exc
        return self._session

    def push_audio(self, pcm: bytes) -> None:
        self._frames.append(pcm)
        try:
            session = self._ensure_session()
        except RuntimeError:
            return

        import numpy as np

        audio = np.frombuffer(b"".join(self._frames), dtype=np.int16).astype(np.float32)
        audio /= 32768.0
        inputs = {session.get_inputs()[0].name: audio[np.newaxis, :]}
        score: float = float(session.run(None, inputs)[0][0])
        self._ema = self.smoothing * self._ema + (1 - self.smoothing) * score
        self._complete = self._ema >= self.threshold

    def is_turn_complete(self) -> bool:
        return self._complete

    def reset(self) -> None:
        self._ema = 0.0
        self._complete = False
        self._frames.clear()

    @property
    def latency_ms(self) -> float:
        return 250.0


@dataclass
class HybridTurnDetector:
    """Uses ModelTurnDetector when available, falls back to VadTurnDetector.

    On first push_audio, tries to load the ONNX model.  If that fails,
    silently switches to the VAD detector for the rest of the session.
    """

    model_threshold: float = 0.55
    vad_silence_ms: float = 800.0
    energy_threshold: float = 0.01

    _detector: TurnDetector = field(init=False, repr=False)
    _tried_model: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self._detector = ModelTurnDetector(threshold=self.model_threshold)

    def _maybe_fallback(self) -> None:
        if self._tried_model:
            return
        self._tried_model = True
        # Probe by trying to load the ONNX session directly; push_audio
        # silently swallows the error so we must check availability here.
        model_det = self._detector
        if isinstance(model_det, ModelTurnDetector):
            try:
                model_det._ensure_session()
            except Exception:  # noqa: BLE001
                self._detector = VadTurnDetector(
                    energy_threshold=self.energy_threshold,
                    silence_ms=self.vad_silence_ms,
                )
                self._detector.reset()

    def push_audio(self, pcm: bytes) -> None:
        self._maybe_fallback()
        self._detector.push_audio(pcm)

    def is_turn_complete(self) -> bool:
        return self._detector.is_turn_complete()

    def reset(self) -> None:
        self._tried_model = False
        self._detector = ModelTurnDetector(threshold=self.model_threshold)

    @property
    def latency_ms(self) -> float:
        return self._detector.latency_ms

    @property
    def active_backend(self) -> str:
        return type(self._detector).__name__


def _rms(pcm: bytes) -> float:
    if not pcm:
        return 0.0
    import struct

    n = len(pcm) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm[: n * 2])
    rms = float((sum(s * s for s in samples) / n) ** 0.5 / 32768.0)
    return rms


def _default_model_path() -> str:
    try:
        from livekit.agents.turn_detector import _MODEL_PATH

        return str(_MODEL_PATH)
    except ImportError as exc:
        raise RuntimeError("livekit-agents not installed") from exc


__all__ = [
    "HybridTurnDetector",
    "ModelTurnDetector",
    "TurnDetector",
    "VadTurnDetector",
]
