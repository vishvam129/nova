"""Tests for nova.mobile.ios_bridge."""

from __future__ import annotations

import json

import pytest

from nova.mobile.ios_bridge import (
    URL_SCHEME,
    ApnsPayload,
    ShortcutAction,
    ShortcutInvocation,
    build_shortcut_url,
)


def test_url_scheme_constant() -> None:
    assert URL_SCHEME == "nova"


def test_parse_ask_url() -> None:
    inv = ShortcutInvocation.parse("nova://ask?q=hello")
    assert inv.action is ShortcutAction.ASK
    assert inv.params == {"q": "hello"}


def test_parse_handoff_url() -> None:
    inv = ShortcutInvocation.parse("nova://handoff?id=abc&from=laptop")
    assert inv.action is ShortcutAction.HANDOFF
    assert inv.params["id"] == "abc"


def test_parse_rejects_other_schemes() -> None:
    with pytest.raises(ValueError):
        ShortcutInvocation.parse("https://example.com/ask?q=hi")


def test_to_url_roundtrip() -> None:
    inv = ShortcutInvocation(action=ShortcutAction.NOTE, params={"text": "hello world"})
    url = inv.to_url()
    parsed = ShortcutInvocation.parse(url)
    assert parsed.action is ShortcutAction.NOTE
    assert parsed.params["text"] == "hello world"


def test_build_shortcut_url_helper() -> None:
    url = build_shortcut_url(ShortcutAction.REMIND, when="6pm", text="call mom")
    inv = ShortcutInvocation.parse(url)
    assert inv.action is ShortcutAction.REMIND
    assert inv.params["when"] == "6pm"


def test_apns_payload_basic() -> None:
    p = ApnsPayload(title="Nova", body="hi")
    parsed = json.loads(p.encode())
    assert parsed["aps"]["alert"]["title"] == "Nova"
    assert parsed["aps"]["alert"]["body"] == "hi"
    assert parsed["aps"]["sound"] == "default"


def test_apns_payload_handoff_id() -> None:
    p = ApnsPayload(title="t", body="b", handoff_id="abc")
    parsed = json.loads(p.encode())
    assert parsed["nova_handoff_id"] == "abc"


def test_apns_payload_extras() -> None:
    p = ApnsPayload(title="t", body="b", extras={"action": "open"})
    parsed = json.loads(p.encode())
    assert parsed["nova"]["action"] == "open"
