"""Voice activity detection with adaptive thresholding.

Backends:
  * ``energy``  — zero-dependency RMS-energy detector, useful as fallback
    and in tests.
  * ``silero``  — ML-based VAD (Silero); imported lazily so the ONNX
    runtime is only required when selected.

``AdaptiveVad`` wraps any backend with an online noise-floor estimator so
the speech/silence threshold tracks the current environment.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class VadFrame:
    is_speech: bool
    probability: float


@runtime_checkable
class Vad(Protocol):
    sample_rate: int

    def probability(self, pcm16: bytes) -> float: ...


class EnergyVad:
    """Tiny RMS-energy VAD. Accurate enough for a fallback."""

    def __init__(self, sample_rate: int = 16000, threshold: float = 500.0) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold

    def probability(self, pcm16: bytes) -> float:
        import numpy as np

        samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return 0.0
        rms = float(np.sqrt(np.mean(samples * samples)))
        # Map RMS to a 0..1 probability around the threshold.
        return max(0.0, min(1.0, rms / (self.threshold * 2.0)))


class SileroVad:
    """Lazy adapter around the ``silero-vad`` package."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self._model: Any | None = None
        self._get_speech_prob: Any | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            from silero_vad import load_silero_vad  # type: ignore[import-not-found]

            self._model = load_silero_vad()
        return self._model

    def probability(self, pcm16: bytes) -> float:
        import numpy as np
        import torch  # type: ignore[import-not-found]

        model = self._ensure()
        samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        tensor = torch.from_numpy(samples)
        return float(model(tensor, self.sample_rate).item())


class AdaptiveVad:
    """Wraps any VAD with an EMA noise-floor estimator.

    ``is_speech`` returns True whenever the backend probability exceeds
    ``noise_floor + margin``. The floor tracks the lowest recent
    probabilities so the threshold adapts to the room.
    """

    def __init__(
        self,
        backend: Vad,
        margin: float = 0.15,
        decay: float = 0.02,
        initial_floor: float = 0.05,
    ) -> None:
        self.backend = backend
        self.margin = margin
        self.decay = decay
        self.noise_floor = initial_floor

    @property
    def sample_rate(self) -> int:
        return self.backend.sample_rate

    def process(self, pcm16: bytes) -> VadFrame:
        prob = self.backend.probability(pcm16)
        speech = prob > self.noise_floor + self.margin
        if not speech:
            self.noise_floor = (1 - self.decay) * self.noise_floor + self.decay * prob
        return VadFrame(is_speech=speech, probability=prob)


_BACKENDS: dict[str, Callable[..., Vad]] = {
    "energy": lambda **kw: EnergyVad(**kw),
    "silero": lambda **kw: SileroVad(**kw),
}


def create_vad(
    backend: str = "silero", adaptive: bool = True, **kwargs: object
) -> Vad | AdaptiveVad:
    if backend not in _BACKENDS:
        raise ValueError(f"unknown VAD backend: {backend!r}")
    engine = _BACKENDS[backend](**kwargs)
    return AdaptiveVad(engine) if adaptive else engine


def available_vads() -> tuple[str, ...]:
    return tuple(_BACKENDS)
