"""Speech-to-text engine abstraction.

Uniform ``transcribe(pcm16) -> Transcript`` API across backends. Real
engines (Whisper, faster-whisper, Distil-Whisper, Moonshine, Parakeet)
are lazily imported by the registered builders, so tests and runtime
only pay for what's actually selected.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    language: str | None
    confidence: float | None = None


@runtime_checkable
class SttEngine(Protocol):
    sample_rate: int

    def transcribe(self, pcm16: bytes) -> Transcript: ...

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]: ...


# --- Registry ---------------------------------------------------------------


class _SttRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., SttEngine]] = {}

    def register(self, name: str, builder: Callable[..., SttEngine]) -> None:
        self._builders[name] = builder

    def build(self, name: str, **kwargs: object) -> SttEngine:
        if name not in self._builders:
            raise ValueError(f"unknown STT backend: {name!r}")
        return self._builders[name](**kwargs)

    def names(self) -> Iterable[str]:
        return tuple(self._builders)


_registry = _SttRegistry()


def register_stt(name: str, builder: Callable[..., SttEngine]) -> None:
    _registry.register(name, builder)


def available_stts() -> tuple[str, ...]:
    return tuple(_registry.names())


def create_stt(backend: str = "faster-whisper", **kwargs: object) -> SttEngine:
    return _registry.build(backend, **kwargs)


# --- Helpers ----------------------------------------------------------------


def _pcm16_to_float32(pcm16: bytes) -> Any:
    import numpy as np

    return np.frombuffer(pcm16, dtype=np.int16).astype("float32") / 32768.0


# --- Built-in backends ------------------------------------------------------


class _WhisperEngine:
    """openai-whisper reference implementation (slowest, most portable)."""

    def __init__(self, model: str = "base", sample_rate: int = 16000) -> None:
        self.model_name = model
        self.sample_rate = sample_rate
        self._model: Any | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            import whisper

            self._model = whisper.load_model(self.model_name)
        return self._model

    def transcribe(self, pcm16: bytes) -> Transcript:
        model = self._ensure()
        audio = _pcm16_to_float32(pcm16)
        result = model.transcribe(audio)
        return Transcript(
            text=str(result.get("text", "")).strip(),
            language=str(result.get("language")) if result.get("language") else None,
        )

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        buffer = bytearray()
        for frame in frames:
            buffer.extend(frame)
        yield self.transcribe(bytes(buffer))


class _FasterWhisperEngine:
    """CTranslate2-backed Whisper; default choice on CPU/GPU."""

    def __init__(
        self,
        model: str = "base",
        compute_type: str = "int8",
        sample_rate: int = 16000,
    ) -> None:
        self.model_name = model
        self.compute_type = compute_type
        self.sample_rate = sample_rate
        self._model: Any | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, compute_type=self.compute_type)
        return self._model

    def transcribe(self, pcm16: bytes) -> Transcript:
        model = self._ensure()
        audio = _pcm16_to_float32(pcm16)
        segments, info = model.transcribe(audio)
        text = " ".join(seg.text for seg in segments).strip()
        return Transcript(text=text, language=info.language, confidence=info.language_probability)

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        buffer = bytearray()
        for frame in frames:
            buffer.extend(frame)
            if len(buffer) >= self.sample_rate * 2:  # ~1s chunks
                yield self.transcribe(bytes(buffer))
                buffer.clear()
        if buffer:
            yield self.transcribe(bytes(buffer))


class _MoonshineEngine:
    """Sub-200ms streaming ASR for edge devices."""

    def __init__(self, model: str = "moonshine/tiny", sample_rate: int = 16000) -> None:
        self.model_name = model
        self.sample_rate = sample_rate
        self._tok: Any | None = None
        self._model: Any | None = None

    def _ensure(self) -> tuple[Any, Any]:
        if self._model is None:
            import moonshine

            self._model = moonshine.load_model(self.model_name)
            self._tok = moonshine.load_tokenizer(self.model_name)
        return self._model, self._tok

    def transcribe(self, pcm16: bytes) -> Transcript:
        model, tok = self._ensure()
        audio = _pcm16_to_float32(pcm16)
        tokens = model.generate(audio)
        return Transcript(text=tok.decode(tokens).strip(), language=None)

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        for frame in frames:
            yield self.transcribe(frame)


class _ParakeetEngine:
    """NVIDIA Parakeet via NeMo (highest throughput, multilingual)."""

    def __init__(self, model: str = "nvidia/parakeet-tdt-1.1b", sample_rate: int = 16000) -> None:
        self.model_name = model
        self.sample_rate = sample_rate
        self._model: Any | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            from nemo.collections.asr.models import EncDecRNNTBPEModel

            self._model = EncDecRNNTBPEModel.from_pretrained(self.model_name)
        return self._model

    def transcribe(self, pcm16: bytes) -> Transcript:
        model = self._ensure()
        audio = _pcm16_to_float32(pcm16)
        hyps = model.transcribe([audio])
        return Transcript(text=str(hyps[0]).strip(), language=None)

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        buffer = bytearray()
        for frame in frames:
            buffer.extend(frame)
        yield self.transcribe(bytes(buffer))


_registry.register("whisper", lambda **kw: _WhisperEngine(**kw))
_registry.register("faster-whisper", lambda **kw: _FasterWhisperEngine(**kw))
_registry.register(
    "distil-whisper", lambda **kw: _FasterWhisperEngine(model="distil-large-v3", **kw)
)
_registry.register("moonshine", lambda **kw: _MoonshineEngine(**kw))
_registry.register("parakeet", lambda **kw: _ParakeetEngine(**kw))
