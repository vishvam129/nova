"""Android on-device offline STT + TTS contract.

The Kotlin app ships:
    - whisper.cpp (ARM build) with whisper-tiny.en quantised model (~75 MB)
    - piper-tts (ARM build) with a single voice (~25 MB)

This module describes the model metadata + capability flags so the brain
knows what the phone can do offline and chooses backends accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class VoiceMode(StrEnum):
    ONLINE = "online"  # cloud STT/TTS via the laptop bridge
    OFFLINE = "offline"  # whisper.cpp + piper on the phone
    AUTO = "auto"  # online when reachable, offline otherwise


@dataclass(frozen=True, slots=True)
class OnDeviceModel:
    """Metadata for a model bundled in the APK."""

    name: str
    kind: str  # 'stt' | 'tts'
    size_mb: float
    sha256: str = ""
    sample_rate: int = 16_000


_DEFAULT_STT = OnDeviceModel(
    name="whisper-tiny.en-q5_1",
    kind="stt",
    size_mb=75.0,
    sample_rate=16_000,
)

_DEFAULT_TTS = OnDeviceModel(
    name="piper-en_US-amy-medium",
    kind="tts",
    size_mb=25.0,
    sample_rate=22_050,
)


@dataclass
class OfflineVoiceCapabilities:
    """Sent from Android → brain on connect so the router knows what's available."""

    stt: OnDeviceModel | None = field(default_factory=lambda: _DEFAULT_STT)
    tts: OnDeviceModel | None = field(default_factory=lambda: _DEFAULT_TTS)
    mode: VoiceMode = VoiceMode.AUTO

    MESSAGE_TYPE: str = field(default="offline_voice_caps", init=False, repr=False)

    @property
    def can_stt_offline(self) -> bool:
        return self.stt is not None

    @property
    def can_tts_offline(self) -> bool:
        return self.tts is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.MESSAGE_TYPE,
            "mode": self.mode.value,
            "stt": _model_to_dict(self.stt),
            "tts": _model_to_dict(self.tts),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> OfflineVoiceCapabilities:
        return cls(
            stt=_model_from_dict(d.get("stt")),
            tts=_model_from_dict(d.get("tts")),
            mode=VoiceMode(d.get("mode", VoiceMode.AUTO.value)),
        )


def _model_to_dict(m: OnDeviceModel | None) -> dict[str, object] | None:
    if m is None:
        return None
    return {
        "name": m.name,
        "kind": m.kind,
        "size_mb": m.size_mb,
        "sha256": m.sha256,
        "sample_rate": m.sample_rate,
    }


def _model_from_dict(d: object) -> OnDeviceModel | None:
    if not isinstance(d, dict):
        return None
    return OnDeviceModel(
        name=str(d["name"]),
        kind=str(d["kind"]),
        size_mb=float(d["size_mb"]),
        sha256=str(d.get("sha256", "")),
        sample_rate=int(d.get("sample_rate", 16_000)),
    )


def pick_voice_mode(*, online: bool, caps: OfflineVoiceCapabilities) -> VoiceMode:
    """Choose effective mode for this turn given current connectivity."""
    if caps.mode is VoiceMode.ONLINE:
        return VoiceMode.ONLINE if online else VoiceMode.OFFLINE
    if caps.mode is VoiceMode.OFFLINE:
        return VoiceMode.OFFLINE
    # AUTO
    if online:
        return VoiceMode.ONLINE
    return VoiceMode.OFFLINE if caps.can_stt_offline else VoiceMode.ONLINE


__all__ = [
    "OfflineVoiceCapabilities",
    "OnDeviceModel",
    "VoiceMode",
    "pick_voice_mode",
]
