"""Tests for nova.integrations.home_assistant."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from nova.integrations.home_assistant import (
    HaEntity,
    HomeAssistantRest,
    HomeAssistantToolHandler,
    ws_subscribe_frame,
)


class _FakeBackend:
    def __init__(self, entities: list[HaEntity]) -> None:
        self.entities = entities
        self.last_call: tuple[str, str, dict[str, object]] | None = None

    def list_entities(self):
        return self.entities

    def get_state(self, entity_id: str):
        for e in self.entities:
            if e.entity_id == entity_id:
                return e
        return None

    def call_service(self, domain, service, data):
        self.last_call = (domain, service, dict(data))
        return True


def _entity(eid: str, state: str = "on", **attrs: object) -> HaEntity:
    return HaEntity(entity_id=eid, state=state, attributes=dict(attrs))


def test_entity_domain() -> None:
    e = _entity("light.kitchen")
    assert e.domain == "light"


def test_entity_to_dict() -> None:
    e = _entity("light.kitchen", brightness=200)
    d = e.to_dict()
    assert d["entity_id"] == "light.kitchen"
    assert d["attributes"]["brightness"] == 200


def test_handler_list_entities() -> None:
    backend = _FakeBackend([_entity("light.kitchen"), _entity("switch.kettle")])
    h = HomeAssistantToolHandler(backend=backend)
    out = h.call("home.list_entities")
    assert isinstance(out, list)
    assert len(out) == 2


def test_handler_get_state_known() -> None:
    backend = _FakeBackend([_entity("light.kitchen", state="off")])
    h = HomeAssistantToolHandler(backend=backend)
    out = h.call("home.get_state", entity_id="light.kitchen")
    assert isinstance(out, dict)
    assert out["state"] == "off"


def test_handler_get_state_unknown() -> None:
    h = HomeAssistantToolHandler(backend=_FakeBackend([]))
    assert h.call("home.get_state", entity_id="ghost.nope") is None


def test_handler_call_service() -> None:
    backend = _FakeBackend([])
    h = HomeAssistantToolHandler(backend=backend)
    out = h.call(
        "home.call_service",
        domain="light",
        service="turn_on",
        data={"entity_id": "light.kitchen"},
    )
    assert out == {"ok": True}
    assert backend.last_call == ("light", "turn_on", {"entity_id": "light.kitchen"})


def test_handler_subscribe_events_returns_frame() -> None:
    h = HomeAssistantToolHandler(backend=_FakeBackend([]))
    raw = h.call("home.subscribe_events", message_id=7)
    parsed = json.loads(str(raw))
    assert parsed["id"] == 7
    assert parsed["type"] == "subscribe_events"


def test_handler_unknown_tool() -> None:
    h = HomeAssistantToolHandler(backend=_FakeBackend([]))
    with pytest.raises(ValueError):
        h.call("home.bogus")


def test_ws_subscribe_frame_default_event_type() -> None:
    parsed = json.loads(ws_subscribe_frame(message_id=1))
    assert parsed["event_type"] == "state_changed"


def test_rest_get_handles_network_error() -> None:
    rest = HomeAssistantRest(base_url="https://x", bearer_token="t")
    with patch("nova.integrations.home_assistant.urllib.request.urlopen", side_effect=OSError):
        assert rest.list_entities() == []


def test_rest_call_service_success() -> None:
    rest = HomeAssistantRest(base_url="https://x", bearer_token="t")
    fake = MagicMock()
    fake.status = 200
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("nova.integrations.home_assistant.urllib.request.urlopen", return_value=fake):
        assert rest.call_service("light", "turn_on", {}) is True
