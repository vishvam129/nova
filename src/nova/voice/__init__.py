"""Voice pipeline: wake word, VAD, STT, TTS."""

from nova.voice import wake_word as _wake_word

WakeEvent = _wake_word.WakeEvent
WakeWordEngine = _wake_word.WakeWordEngine
create_engine = _wake_word.create_engine
available_backends = _wake_word.available_backends
register_backend = _wake_word.register_backend

__all__ = [
    "WakeEvent",
    "WakeWordEngine",
    "available_backends",
    "create_engine",
    "register_backend",
]
