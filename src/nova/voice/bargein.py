"""Barge-in: detect user speech while TTS plays, duck volume, then stop.

Run the TTS output through a ``BargeInPlayer``. Feed each inbound
mic frame to ``observe``. When the VAD reports sustained speech, the
player ducks audio (reduces amplitude) for a configurable hold window
and, if speech continues, halts playback entirely.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from nova.voice.tts import AudioBytes
from nova.voice.vad import AdaptiveVad


class PlaybackState(StrEnum):
    PLAYING = "playing"
    DUCKED = "ducked"
    STOPPED = "stopped"


@dataclass
class BargeInPlayer:
    """State machine around a TTS audio stream."""

    vad: AdaptiveVad
    duck_after_ms: int = 120
    stop_after_ms: int = 300
    duck_gain: float = 0.25
    _state: PlaybackState = field(default=PlaybackState.PLAYING, init=False)
    _speech_started_at: float | None = field(default=None, init=False)

    @property
    def state(self) -> PlaybackState:
        return self._state

    def observe(self, pcm16: bytes, now: Callable[[], float] = time.monotonic) -> PlaybackState:
        frame = self.vad.process(pcm16)
        t = now()
        if frame.is_speech:
            if self._speech_started_at is None:
                self._speech_started_at = t
            elapsed_ms = (t - self._speech_started_at) * 1000
            if elapsed_ms >= self.stop_after_ms:
                self._state = PlaybackState.STOPPED
            elif elapsed_ms >= self.duck_after_ms:
                self._state = PlaybackState.DUCKED
        else:
            self._speech_started_at = None
            if self._state == PlaybackState.DUCKED:
                self._state = PlaybackState.PLAYING
        return self._state

    def apply(self, audio: AudioBytes) -> AudioBytes | None:
        """Return the audio to actually play (possibly attenuated) or ``None``."""
        if self._state == PlaybackState.STOPPED:
            return None
        if self._state == PlaybackState.DUCKED:
            return _attenuate(audio, self.duck_gain)
        return audio

    def play(self, audio_stream: Iterable[AudioBytes]) -> Iterable[AudioBytes]:
        for chunk in audio_stream:
            out = self.apply(chunk)
            if out is None:
                break
            yield out


def _attenuate(audio: AudioBytes, gain: float) -> AudioBytes:
    import numpy as np

    samples = np.frombuffer(audio.pcm16, dtype=np.int16).astype(np.float32)
    scaled = (samples * gain).clip(-32768, 32767).astype(np.int16).tobytes()
    return AudioBytes(pcm16=scaled, sample_rate=audio.sample_rate)
