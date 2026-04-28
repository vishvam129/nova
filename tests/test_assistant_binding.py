"""Tests for nova.mobile.assistant_binding."""

from __future__ import annotations

from nova.mobile.assistant_binding import (
    ASSISTANT_INTENT_FILTER,
    ASSISTANT_ROLE_REQUEST_CODE,
    AssistantBindingConfig,
    AssistantLaunchEvent,
    is_supported_source,
)


def test_intent_filter_has_assist_action() -> None:
    assert "android.intent.action.ASSIST" in ASSISTANT_INTENT_FILTER
    assert "android.intent.action.VOICE_COMMAND" in ASSISTANT_INTENT_FILTER


def test_role_request_code_is_int() -> None:
    assert isinstance(ASSISTANT_ROLE_REQUEST_CODE, int)


def test_config_defaults() -> None:
    cfg = AssistantBindingConfig()
    assert cfg.enabled is True
    assert cfg.immediate_listen is True


def test_config_dict_roundtrip() -> None:
    cfg = AssistantBindingConfig(enabled=False, open_overlay=False, immediate_listen=False)
    out = AssistantBindingConfig.from_dict(cfg.to_dict())
    assert out == cfg


def test_launch_event_roundtrip() -> None:
    e = AssistantLaunchEvent(
        source="long_press_home",
        package_in_focus="com.spotify.music",
        extras={"foo": "bar"},
    )
    d = e.to_dict()
    assert d["type"] == "assistant_launch"
    out = AssistantLaunchEvent.from_dict(d)
    assert out.source == "long_press_home"
    assert out.package_in_focus == "com.spotify.music"
    assert out.extras == {"foo": "bar"}


def test_is_supported_source() -> None:
    assert is_supported_source("long_press_home") is True
    assert is_supported_source("power_button") is True
    assert is_supported_source("nope") is False
