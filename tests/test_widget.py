"""Tests for nova.mobile.widget."""

from __future__ import annotations

import json
from datetime import datetime

from nova.mobile.widget import RedoEvent, WidgetAction, WidgetState


def _action(i: int) -> WidgetAction:
    return WidgetAction(id=f"a{i}", label=f"action {i}", timestamp=datetime.now())


def test_push_and_actions_newest_first() -> None:
    s = WidgetState(capacity=5)
    s.push(_action(1))
    s.push(_action(2))
    s.push(_action(3))
    labels = [a.label for a in s.actions()]
    assert labels == ["action 3", "action 2", "action 1"]


def test_capacity_evicts_oldest() -> None:
    s = WidgetState(capacity=3)
    s.push_many([_action(i) for i in range(5)])
    ids = [a.id for a in s.actions()]
    assert ids == ["a4", "a3", "a2"]


def test_find_returns_match() -> None:
    s = WidgetState()
    s.push(_action(1))
    found = s.find("a1")
    assert found is not None
    assert found.label == "action 1"


def test_find_unknown() -> None:
    s = WidgetState()
    assert s.find("ghost") is None


def test_widget_state_encode_is_json() -> None:
    s = WidgetState()
    s.push(_action(1))
    parsed = json.loads(s.encode())
    assert parsed["type"] == "widget_state"
    assert len(parsed["actions"]) == 1


def test_action_dict_roundtrip() -> None:
    a = WidgetAction(id="x", label="open spotify", timestamp=datetime(2026, 4, 28))
    assert WidgetAction.from_dict(a.to_dict()) == a


def test_redo_event_roundtrip() -> None:
    e = RedoEvent(action_id="a1", timestamp=datetime(2026, 4, 28, 10))
    out = RedoEvent.from_dict(e.to_dict())
    assert out.action_id == "a1"
    assert out.timestamp == e.timestamp


def test_redo_event_message_type() -> None:
    e = RedoEvent(action_id="a1")
    assert e.to_dict()["type"] == "widget_redo"
