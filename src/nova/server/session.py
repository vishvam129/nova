"""Unified conversation session across devices.

A single logical conversation spans phone + laptop. Each device sees
the same ordered transcript, the same active tool calls, and the same
"active device" hint. Backed by ``DictCrdt`` so offline edits
reconcile on reconnect.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field

from nova.memory.crdt import Crdt, DictCrdt


@dataclass(frozen=True, slots=True)
class SessionMessage:
    id: str
    role: str
    content: str
    ts: float
    origin_device: str | None = None


@dataclass
class UnifiedSession:
    session_id: str
    doc: Crdt = field(default_factory=DictCrdt)
    _clock: int = 0

    def _tick(self) -> int:
        self._clock += 1
        return self._clock

    def append(
        self,
        role: str,
        content: str,
        ts: float,
        origin_device: str | None = None,
    ) -> SessionMessage:
        msg = SessionMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            ts=ts,
            origin_device=origin_device,
        )
        self.doc.set(
            f"msg:{ts:.6f}:{msg.id}",
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "ts": msg.ts,
                "origin_device": msg.origin_device,
            },
            lamport=self._tick(),
        )
        return msg

    def set_active_device(self, device_id: str) -> None:
        self.doc.set("active_device", device_id, lamport=self._tick())

    @property
    def active_device(self) -> str | None:
        val = self.doc.get("active_device")
        return str(val) if val is not None else None

    def messages(self) -> list[SessionMessage]:
        items: list[SessionMessage] = []
        for key in self.doc.keys():  # noqa: SIM118 — Crdt protocol method, not dict
            if not key.startswith("msg:"):
                continue
            data = self.doc.get(key)
            if not isinstance(data, dict):
                continue
            items.append(
                SessionMessage(
                    id=str(data["id"]),
                    role=str(data["role"]),
                    content=str(data["content"]),
                    ts=float(data["ts"]),
                    origin_device=data.get("origin_device"),
                )
            )
        items.sort(key=lambda m: m.ts)
        return items


@dataclass
class SessionRegistry:
    _sessions: dict[str, UnifiedSession] = field(default_factory=dict)

    def create(self) -> UnifiedSession:
        sid = str(uuid.uuid4())
        session = UnifiedSession(session_id=sid)
        self._sessions[sid] = session
        return session

    def get(self, sid: str) -> UnifiedSession | None:
        return self._sessions.get(sid)

    def all(self) -> Iterable[UnifiedSession]:
        return tuple(self._sessions.values())


__all__ = ["SessionMessage", "SessionRegistry", "UnifiedSession"]
