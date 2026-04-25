"""Tests for nova.mobile.android_tools — Android MCP tool protocol."""

from __future__ import annotations

from nova.mobile.android_tools import (
    ANDROID_TOOL_SCHEMAS,
    AndroidToolCall,
    AndroidToolResult,
    automate_ui,
    make_call,
    open_app,
    read_notifications,
    send_sms,
)


def test_send_sms_encode_decode() -> None:
    call = send_sms(to="+1234567890", body="Hello!", call_id="c1")
    recovered = AndroidToolCall.decode(call.encode())
    assert recovered.tool == "send_sms"
    assert recovered.args["to"] == "+1234567890"
    assert recovered.args["body"] == "Hello!"
    assert recovered.call_id == "c1"


def test_make_call_encode_decode() -> None:
    call = make_call(number="+0987654321", call_id="c2")
    recovered = AndroidToolCall.decode(call.encode())
    assert recovered.tool == "make_call"
    assert recovered.args["number"] == "+0987654321"


def test_read_notifications_default_limit() -> None:
    call = read_notifications()
    assert call.args["limit"] == 10


def test_open_app_encode_decode() -> None:
    call = open_app(package="com.spotify.music", call_id="c3")
    recovered = AndroidToolCall.decode(call.encode())
    assert recovered.tool == "open_app"
    assert recovered.args["package"] == "com.spotify.music"


def test_automate_ui_tap() -> None:
    call = automate_ui(action="tap", target="com.foo:id/btn_ok")
    assert call.tool == "automate_ui"
    assert call.args["action"] == "tap"
    assert call.args["target"] == "com.foo:id/btn_ok"


def test_automate_ui_type_text() -> None:
    call = automate_ui(action="type", text="nova rocks")
    recovered = AndroidToolCall.decode(call.encode())
    assert recovered.args["text"] == "nova rocks"


def test_tool_call_wire_type() -> None:
    import json

    call = send_sms(to="123", body="hi")
    frame = json.loads(call.encode())
    assert frame["type"] == "android_tool_call"


def test_tool_result_ok() -> None:
    result = AndroidToolResult(call_id="c1", ok=True, data={"sms_id": "42"})
    recovered = AndroidToolResult.decode(result.encode())
    assert recovered.ok is True
    assert recovered.data["sms_id"] == "42"
    assert recovered.error == ""


def test_tool_result_error() -> None:
    result = AndroidToolResult(call_id="c2", ok=False, error="permission denied")
    recovered = AndroidToolResult.decode(result.encode())
    assert recovered.ok is False
    assert recovered.error == "permission denied"


def test_schemas_cover_all_tools() -> None:
    names = {s["name"] for s in ANDROID_TOOL_SCHEMAS}
    assert names == {"send_sms", "make_call", "read_notifications", "open_app", "automate_ui"}


def test_schemas_have_required_fields() -> None:
    for schema in ANDROID_TOOL_SCHEMAS:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
