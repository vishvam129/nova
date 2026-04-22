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


# --- Streaming helpers ------------------------------------------------------


class StreamingTranscriber:
    """Sliding-window partial-transcript helper built on any ``SttEngine``.

    Audio frames are appended to a ring buffer up to ``window_ms``
    milliseconds; a partial transcript is emitted every
    ``partial_every_ms`` milliseconds of fresh audio. Useful for pushing
    ASR latency toward the 100–200ms range when paired with Moonshine or
    Distil-Whisper.
    """

    def __init__(
        self,
        engine: SttEngine,
        sample_rate: int = 16000,
        window_ms: int = 1000,
        partial_every_ms: int = 150,
    ) -> None:
        self.engine = engine
        self.sample_rate = sample_rate
        self.window_ms = window_ms
        self.partial_every_ms = partial_every_ms

    @property
    def _bytes_per_ms(self) -> int:
        return self.sample_rate // 500  # int16 -> 2 bytes per sample

    def stream(self, frames: Iterable[bytes]) -> Iterable[Transcript]:
        window_bytes = self.window_ms * self._bytes_per_ms
        emit_every = self.partial_every_ms * self._bytes_per_ms
        buffer = bytearray()
        since_emit = 0
        for frame in frames:
            buffer.extend(frame)
            since_emit += len(frame)
            if len(buffer) > window_bytes:
                del buffer[: len(buffer) - window_bytes]
            if since_emit >= emit_every and buffer:
                yield self.engine.transcribe(bytes(buffer))
                since_emit = 0
        if buffer:
            yield self.engine.transcribe(bytes(buffer))


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
    """Moonshine ASR — tuned for <200ms streaming on edge hardware.

    ``transcribe`` runs once on a full utterance. ``stream`` uses a
    sliding window (default 1s) that emits a partial every
    ``partial_every_ms`` milliseconds of new audio, matching Moonshine's
    design sweet spot for real-time voice applications.
    """

    def __init__(
        self,
        model: str = "moonshine/tiny",
        sample_rate: int = 16000,
        window_ms: int = 1000,
        partial_every_ms: int = 150,
    ) -> None:
        self.model_name = model
        self.sample_rate = sample_rate
        self.window_ms = window_ms
        self.partial_every_ms = partial_every_ms
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
        yield from StreamingTranscriber(
            self,
            sample_rate=self.sample_rate,
            window_ms=self.window_ms,
            partial_every_ms=self.partial_every_ms,
        ).stream(frames)


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
