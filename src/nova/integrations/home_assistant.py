"""Home Assistant MCP: REST + WebSocket client contracts.

REST is used for one-shot calls (call_service, list states); WebSocket
is the live event stream so Nova can react to motion sensors etc.

Both backends share ``HomeAssistantBackend`` and the MCP-facing
``HomeAssistantToolHandler`` exposes:
    home.list_entities
    home.get_state
    home.call_service
    home.subscribe_events  (returns a frame template the WS subscriber uses)
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class HaEntity:
    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "state": self.state,
            "attributes": dict(self.attributes),
        }


class HomeAssistantBackend(Protocol):
    def list_entities(self) -> Iterable[HaEntity]: ...
    def get_state(self, entity_id: str) -> HaEntity | None: ...
    def call_service(self, domain: str, service: str, data: dict[str, Any]) -> bool: ...


@dataclass
class HomeAssistantRest:
    """REST client for Home Assistant /api endpoints."""

    base_url: str
    bearer_token: str
    timeout_s: float = 5.0

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> Any:
        req = urllib.request.Request(f"{self.base_url.rstrip('/')}{path}", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return None

    def _post(self, path: str, payload: dict[str, Any]) -> bool:
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}{path}",
            data=json.dumps(payload).encode(),
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.status in (200, 201)
        except (urllib.error.URLError, OSError):
            return False

    def list_entities(self) -> list[HaEntity]:
        data = self._get("/api/states") or []
        return [
            HaEntity(
                entity_id=str(e.get("entity_id", "")),
                state=str(e.get("state", "")),
                attributes=dict(e.get("attributes") or {}),
            )
            for e in data
            if isinstance(e, dict)
        ]

    def get_state(self, entity_id: str) -> HaEntity | None:
        data = self._get(f"/api/states/{entity_id}")
        if not isinstance(data, dict):
            return None
        return HaEntity(
            entity_id=str(data.get("entity_id", "")),
            state=str(data.get("state", "")),
            attributes=dict(data.get("attributes") or {}),
        )

    def call_service(self, domain: str, service: str, data: dict[str, Any]) -> bool:
        return self._post(f"/api/services/{domain}/{service}", data)


def ws_subscribe_frame(*, message_id: int, event_type: str = "state_changed") -> str:
    """Return the JSON the WS subscriber sends to start receiving events."""
    return json.dumps({"id": message_id, "type": "subscribe_events", "event_type": event_type})


@dataclass
class HomeAssistantToolHandler:
    backend: HomeAssistantBackend

    def call(self, tool: str, **kwargs: Any) -> object:
        if tool == "home.list_entities":
            return [e.to_dict() for e in self.backend.list_entities()]
        if tool == "home.get_state":
            ent = self.backend.get_state(str(kwargs["entity_id"]))
            return ent.to_dict() if ent else None
        if tool == "home.call_service":
            domain = str(kwargs["domain"])
            service = str(kwargs["service"])
            data = dict(kwargs.get("data") or {})
            return {"ok": self.backend.call_service(domain, service, data)}
        if tool == "home.subscribe_events":
            return ws_subscribe_frame(
                message_id=int(kwargs.get("message_id", 1)),
                event_type=str(kwargs.get("event_type", "state_changed")),
            )
        raise ValueError(f"unknown home.* tool: {tool!r}")


__all__ = [
    "HaEntity",
    "HomeAssistantBackend",
    "HomeAssistantRest",
    "HomeAssistantToolHandler",
    "ws_subscribe_frame",
]
