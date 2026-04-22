"""Text-to-speech engine abstraction.

Uniform ``synth(text) -> AudioBytes`` API across backends. Builders for
real engines (Piper, Kokoro, StyleTTS2, XTTS-v2, ElevenLabs) import
their native deps lazily so tests and runtime only pay for what's
actually selected.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AudioBytes:
    """A chunk of synthesized audio as PCM-16 mono."""

    pcm16: bytes
    sample_rate: int


@runtime_checkable
class TtsEngine(Protocol):
    sample_rate: int

    def synth(self, text: str) -> AudioBytes: ...

    def stream(self, text: str) -> Iterable[AudioBytes]: ...


# --- Registry ---------------------------------------------------------------


class _TtsRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., TtsEngine]] = {}

    def register(self, name: str, builder: Callable[..., TtsEngine]) -> None:
        self._builders[name] = builder

    def build(self, name: str, **kwargs: object) -> TtsEngine:
        if name not in self._builders:
            raise ValueError(f"unknown TTS backend: {name!r}")
        return self._builders[name](**kwargs)

    def names(self) -> Iterable[str]:
        return tuple(self._builders)


_registry = _TtsRegistry()


def register_tts(name: str, builder: Callable[..., TtsEngine]) -> None:
    _registry.register(name, builder)


def available_ttses() -> tuple[str, ...]:
    return tuple(_registry.names())


def create_tts(backend: str = "kokoro", **kwargs: object) -> TtsEngine:
    return _registry.build(backend, **kwargs)


# --- Sentence chunking ------------------------------------------------------

_SENTENCE_RE = re.compile(r"([^.!?\n]+[.!?\n]?)")


def split_sentences(text: str) -> list[str]:
    """Rough sentence splitter good enough for TTS chunking."""
    return [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]


# --- Streaming synthesis ----------------------------------------------------


_SENTENCE_END_RE = re.compile(r"[.!?\n]")


class StreamingSynthesizer:
    """Synthesize audio from an LLM token stream sentence-by-sentence.

    Buffers incoming text chunks until a sentence boundary (``. ? !
    \\n``) is seen, then hands the complete sentence to the underlying
    ``TtsEngine`` and yields the resulting audio. The tail (any text
    after the last boundary) is flushed when the input iterator is
    exhausted. This keeps playback latency bounded by the time it takes
    the LLM to emit the *first sentence*, not the full response.
    """

    def __init__(self, engine: TtsEngine, min_chars: int = 4) -> None:
        self.engine = engine
        self.min_chars = min_chars

    def stream(self, tokens: Iterable[str]) -> Iterable[AudioBytes]:
        buf: list[str] = []

        def _flush() -> Iterable[AudioBytes]:
            text = "".join(buf).strip()
            buf.clear()
            if text:
                yield self.engine.synth(text)

        for token in tokens:
            buf.append(token)
            combined = "".join(buf)
            m = _SENTENCE_END_RE.search(combined)
            if m and len(combined.strip()) >= self.min_chars:
                # emit everything up to and including the boundary
                head = combined[: m.end()]
                tail = combined[m.end() :]
                buf.clear()
                buf.append(tail)
                text = head.strip()
                if text:
                    yield self.engine.synth(text)
        yield from _flush()


# --- Benchmarking -----------------------------------------------------------


def time_to_first_sound_ms(engine: TtsEngine, text: str = "Hello, this is a test.") -> float:
    """Measure time from calling ``stream`` to receiving the first audio chunk.

    Used to gate TTS backend choice against the configured TTFS budget
    (default 300ms for Kokoro on a 16GB laptop).
    """
    start = time.perf_counter()
    first = next(iter(engine.stream(text)))
    assert first.pcm16  # first chunk must contain audio
    return (time.perf_counter() - start) * 1000


# --- Built-in backends ------------------------------------------------------


class _PiperEngine:
    """Edge-friendly TTS (~30ms TTFS, ~20M params)."""

    def __init__(self, voice: str = "en_US-lessac-medium", sample_rate: int = 22050) -> None:
        self.voice = voice
        self.sample_rate = sample_rate
        self._voice: Any | None = None

    def _ensure(self) -> Any:
        if self._voice is None:
            from piper import PiperVoice

            self._voice = PiperVoice.load(self.voice)
        return self._voice

    def synth(self, text: str) -> AudioBytes:
        voice = self._ensure()
        pcm = b"".join(voice.synthesize_stream_raw(text))
        return AudioBytes(pcm16=pcm, sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        for sentence in split_sentences(text):
            yield self.synth(sentence)


class _KokoroEngine:
    """Kokoro-82M (TTS Arena #1, StyleTTS2-based)."""

    def __init__(self, voice: str = "af_sky", sample_rate: int = 24000) -> None:
        self.voice = voice
        self.sample_rate = sample_rate
        self._pipeline: Any | None = None

    def _ensure(self) -> Any:
        if self._pipeline is None:
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code="a")
        return self._pipeline

    def synth(self, text: str) -> AudioBytes:
        import numpy as np

        pipeline = self._ensure()
        audio_chunks: list[bytes] = []
        for _gs, _ps, audio in pipeline(text, voice=self.voice):
            pcm = (np.asarray(audio) * 32767).astype(np.int16).tobytes()
            audio_chunks.append(pcm)
        return AudioBytes(pcm16=b"".join(audio_chunks), sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        for sentence in split_sentences(text):
            yield self.synth(sentence)


class _StyleTts2Engine:
    """StyleTTS2 — architecture Kokoro is built on; useful for custom training."""

    def __init__(self, model_path: str = "styletts2/default", sample_rate: int = 24000) -> None:
        self.model_path = model_path
        self.sample_rate = sample_rate
        self._model: Any | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            import styletts2

            self._model = styletts2.load_model(self.model_path)
        return self._model

    def synth(self, text: str) -> AudioBytes:
        import numpy as np

        model = self._ensure()
        audio = model.inference(text)
        pcm = (np.asarray(audio) * 32767).astype(np.int16).tobytes()
        return AudioBytes(pcm16=pcm, sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        for sentence in split_sentences(text):
            yield self.synth(sentence)


class _XttsEngine:
    """XTTS-v2 — zero-shot voice cloning from ~6s of reference audio."""

    def __init__(
        self,
        speaker_wav: str | None = None,
        language: str = "en",
        sample_rate: int = 24000,
    ) -> None:
        self.speaker_wav = speaker_wav
        self.language = language
        self.sample_rate = sample_rate
        self._model: Any | None = None

    def _ensure(self) -> Any:
        if self._model is None:
            from TTS.api import TTS

            self._model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        return self._model

    def synth(self, text: str) -> AudioBytes:
        import numpy as np

        model = self._ensure()
        audio = model.tts(text=text, speaker_wav=self.speaker_wav, language=self.language)
        pcm = (np.asarray(audio) * 32767).astype(np.int16).tobytes()
        return AudioBytes(pcm16=pcm, sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        for sentence in split_sentences(text):
            yield self.synth(sentence)


class _ElevenLabsEngine:
    """Cloud TTS: ElevenLabs."""

    def __init__(
        self,
        voice_id: str = "Rachel",
        api_key: str | None = None,
        sample_rate: int = 24000,
        model: str = "eleven_turbo_v2_5",
    ) -> None:
        self.voice_id = voice_id
        self.api_key = api_key
        self.sample_rate = sample_rate
        self.model = model
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is None:
            from elevenlabs.client import ElevenLabs

            self._client = ElevenLabs(api_key=self.api_key)
        return self._client

    def synth(self, text: str) -> AudioBytes:
        client = self._ensure()
        audio_iter = client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model,
            text=text,
            output_format="pcm_24000",
        )
        pcm = b"".join(audio_iter)
        return AudioBytes(pcm16=pcm, sample_rate=self.sample_rate)

    def stream(self, text: str) -> Iterable[AudioBytes]:
        for sentence in split_sentences(text):
            yield self.synth(sentence)


_registry.register("piper", lambda **kw: _PiperEngine(**kw))
_registry.register("kokoro", lambda **kw: _KokoroEngine(**kw))
_registry.register("styletts2", lambda **kw: _StyleTts2Engine(**kw))
_registry.register("xtts", lambda **kw: _XttsEngine(**kw))
_registry.register("elevenlabs", lambda **kw: _ElevenLabsEngine(**kw))
