"""Tests for nova.mobile.accessibility — AccessibilityEvent protocol."""

from __future__ import annotations

from nova.mobile.accessibility import POLICY_DISCLOSURE_TEXT, AccessibilityEvent


def test_roundtrip_encode_decode() -> None:
    evt = AccessibilityEvent(
        event_type="TYPE_WINDOW_STATE_CHANGED",
        package_name="com.example.app",
        class_name="android.app.Activity",
        text=["Hello", "World"],
        window_title="Main Screen",
    )
    recovered = AccessibilityEvent.decode(evt.encode())
    assert recovered.event_type == evt.event_type
    assert recovered.package_name == evt.package_name
    assert recovered.text == evt.text
    assert recovered.window_title == evt.window_title


def test_to_dict_has_type_field() -> None:
    evt = AccessibilityEvent(
        event_type="TYPE_VIEW_FOCUSED",
        package_name="com.example.app",
        class_name="android.widget.EditText",
    )
    d = evt.to_dict()
    assert d["type"] == "accessibility_event"
    assert d["event_type"] == "TYPE_VIEW_FOCUSED"


def test_from_dict_defaults() -> None:
    data = {"event_type": "TYPE_VIEW_CLICKED", "package_name": "com.foo"}
    evt = AccessibilityEvent.from_dict(data)
    assert evt.class_name == ""
    assert evt.text == []
    assert evt.content_description == ""
    assert evt.window_title == ""


def test_screen_summary_with_all_fields() -> None:
    evt = AccessibilityEvent(
        event_type="TYPE_WINDOW_STATE_CHANGED",
        package_name="com.google.maps",
        class_name="Activity",
        text=["Turn left", "200m"],
        window_title="Navigation",
    )
    summary = evt.screen_summary()
    assert "com.google.maps" in summary
    assert "Navigation" in summary
    assert "Turn left" in summary


def test_screen_summary_minimal() -> None:
    evt = AccessibilityEvent(
        event_type="TYPE_VIEW_FOCUSED",
        package_name="com.twitter.android",
        class_name="View",
    )
    summary = evt.screen_summary()
    assert "com.twitter.android" in summary
    assert "Window" not in summary


def test_policy_disclosure_text_non_empty() -> None:
    assert len(POLICY_DISCLOSURE_TEXT) > 50
    assert "accessibility" in POLICY_DISCLOSURE_TEXT.lower()
