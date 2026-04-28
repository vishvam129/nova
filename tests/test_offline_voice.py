"""Tests for nova.mobile.offline_voice."""

from __future__ import annotations

from nova.mobile.offline_voice import (
    OfflineVoiceCapabilities,
    OnDeviceModel,
    VoiceMode,
    pick_voice_mode,
)


def test_default_capabilities_have_models() -> None:
    caps = OfflineVoiceCapabilities()
    assert caps.stt is not None
    assert caps.tts is not None
    assert caps.can_stt_offline is True
    assert caps.can_tts_offline is True


def test_capabilities_dict_roundtrip() -> None:
    caps = OfflineVoiceCapabilities(mode=VoiceMode.OFFLINE)
    d = caps.to_dict()
    assert d["type"] == "offline_voice_caps"
    out = OfflineVoiceCapabilities.from_dict(d)
    assert out.mode is VoiceMode.OFFLINE
    assert out.stt is not None
    assert out.stt.name == caps.stt.name  # type: ignore[union-attr]


def test_capabilities_with_no_tts() -> None:
    caps = OfflineVoiceCapabilities(stt=OnDeviceModel("w", "stt", 75.0), tts=None)
    out = OfflineVoiceCapabilities.from_dict(caps.to_dict())
    assert out.tts is None
    assert out.can_tts_offline is False


def test_pick_mode_auto_online() -> None:
    caps = OfflineVoiceCapabilities(mode=VoiceMode.AUTO)
    assert pick_voice_mode(online=True, caps=caps) is VoiceMode.ONLINE


def test_pick_mode_auto_offline_when_no_net() -> None:
    caps = OfflineVoiceCapabilities(mode=VoiceMode.AUTO)
    assert pick_voice_mode(online=False, caps=caps) is VoiceMode.OFFLINE


def test_pick_mode_forced_online_falls_back_when_offline() -> None:
    caps = OfflineVoiceCapabilities(mode=VoiceMode.ONLINE)
    assert pick_voice_mode(online=False, caps=caps) is VoiceMode.OFFLINE


def test_pick_mode_forced_offline() -> None:
    caps = OfflineVoiceCapabilities(mode=VoiceMode.OFFLINE)
    assert pick_voice_mode(online=True, caps=caps) is VoiceMode.OFFLINE


def test_pick_mode_no_offline_stt_uses_online() -> None:
    caps = OfflineVoiceCapabilities(stt=None, tts=None, mode=VoiceMode.AUTO)
    assert pick_voice_mode(online=False, caps=caps) is VoiceMode.ONLINE
