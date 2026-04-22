"""Voice pipeline: wake word, VAD, STT, TTS."""

from nova.voice import mic as _mic
from nova.voice import vad as _vad
from nova.voice import wake_word as _wake_word

WakeEvent = _wake_word.WakeEvent
WakeWordEngine = _wake_word.WakeWordEngine
create_engine = _wake_word.create_engine
available_backends = _wake_word.available_backends
register_backend = _wake_word.register_backend

AudioChunk = _mic.AudioChunk
MicStream = _mic.MicStream

AdaptiveVad = _vad.AdaptiveVad
EnergyVad = _vad.EnergyVad
SileroVad = _vad.SileroVad
Vad = _vad.Vad
VadFrame = _vad.VadFrame
available_vads = _vad.available_vads
create_vad = _vad.create_vad

__all__ = [
    "AdaptiveVad",
    "AudioChunk",
    "EnergyVad",
    "MicStream",
    "SileroVad",
    "Vad",
    "VadFrame",
    "WakeEvent",
    "WakeWordEngine",
    "available_backends",
    "available_vads",
    "create_engine",
    "create_vad",
    "register_backend",
]
