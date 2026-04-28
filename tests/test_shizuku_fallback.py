"""Tests for nova.mobile.shizuku_fallback."""

from __future__ import annotations

from nova.mobile.shizuku_fallback import (
    ChannelStatus,
    ControlChannel,
    pick_channel,
    tools_for_channel,
)


def test_pick_accessibility_when_unblocked() -> None:
    c = pick_channel(accessibility_blocked=False, shizuku_running=False, adb_authorized=False)
    assert c is ControlChannel.ACCESSIBILITY


def test_pick_shizuku_when_blocked_and_running() -> None:
    c = pick_channel(accessibility_blocked=True, shizuku_running=True, adb_authorized=False)
    assert c is ControlChannel.SHIZUKU


def test_pick_adb_when_only_adb() -> None:
    c = pick_channel(accessibility_blocked=True, shizuku_running=False, adb_authorized=True)
    assert c is ControlChannel.ADB


def test_pick_none_when_nothing_available() -> None:
    c = pick_channel(accessibility_blocked=True, shizuku_running=False, adb_authorized=False)
    assert c is ControlChannel.NONE


def test_tools_accessibility_includes_automate_ui() -> None:
    tools = tools_for_channel(ControlChannel.ACCESSIBILITY)
    assert "automate_ui" in tools
    assert "send_sms" in tools


def test_tools_shell_uses_automate_ui_shell() -> None:
    tools = tools_for_channel(ControlChannel.SHIZUKU)
    assert "automate_ui_shell" in tools
    assert "automate_ui" not in tools


def test_tools_none_is_empty() -> None:
    assert tools_for_channel(ControlChannel.NONE) == set()


def test_channel_status_roundtrip() -> None:
    s = ChannelStatus(
        active=ControlChannel.SHIZUKU,
        accessibility_blocked=True,
        shizuku_running=True,
        advanced_protection_on=True,
    )
    recovered = ChannelStatus.decode(s.encode())
    assert recovered.active is ControlChannel.SHIZUKU
    assert recovered.accessibility_blocked is True
    assert recovered.advanced_protection_on is True


def test_channel_status_message_type() -> None:
    s = ChannelStatus(active=ControlChannel.ACCESSIBILITY)
    assert s.to_dict()["type"] == "control_channel_status"
