"""Wake-word backend adapters. Native deps are imported lazily."""

from __future__ import annotations

import time
from typing import Any

from nova.voice.wake_word import WakeEvent


class OpenWakeWordEngine:
    """Thin adapter over the ``openwakeword`` package."""

    def __init__(self, phrase: str, threshold: float, sample_rate: int) -> None:
        self.phrase = phrase
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._model: Any | None = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            from openwakeword.model import Model

            self._model = Model(wakeword_models=[self.phrase])
        return self._model

    def feed(self, pcm16: bytes) -> WakeEvent | None:
        import numpy as np

        model = self._ensure_model()
        samples = np.frombuffer(pcm16, dtype=np.int16)
        scores = model.predict(samples)
        score = float(scores.get(self.phrase, 0.0))
        if score >= self.threshold:
            return WakeEvent(phrase=self.phrase, score=score, timestamp=time.time())
        return None

    def close(self) -> None:
        self._model = None


class PorcupineEngine:
    """Thin adapter over Picovoice's ``pvporcupine``."""

    def __init__(self, phrase: str, access_key: str | None, sample_rate: int) -> None:
        self.phrase = phrase
        self.access_key = access_key
        self.sample_rate = sample_rate
        self._porcupine: Any | None = None

    def _ensure(self) -> Any:
        if self._porcupine is None:
            import pvporcupine

            if not self.access_key:
                raise RuntimeError("porcupine backend requires access_key")
            self._porcupine = pvporcupine.create(access_key=self.access_key, keywords=[self.phrase])
        return self._porcupine

    def feed(self, pcm16: bytes) -> WakeEvent | None:
        import numpy as np

        engine = self._ensure()
        samples = np.frombuffer(pcm16, dtype=np.int16)
        result = engine.process(samples)
        if result >= 0:
            return WakeEvent(phrase=self.phrase, score=1.0, timestamp=time.time())
        return None

    def close(self) -> None:
        if self._porcupine is not None:
            self._porcupine.delete()
            self._porcupine = None
