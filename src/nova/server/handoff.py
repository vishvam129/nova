"""Device handoff: move an active session from one device to another mid-turn.

Usage::

    coord = HandoffCoordinator(sessions=session_registry, devices=device_hub)
    handoff_id = coord.initiate(
        session_id=current.id, from_device="phone", to_device="laptop"
    )
    # Receiving device calls coord.accept(handoff_id) to take over.

The transfer is a fire-and-forget message: the source device pauses its
loop, the destination device replays the session's CRDT state to catch up.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class HandoffState(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REJECTED = "rejected"


@dataclass
class Handoff:
    id: str
    session_id: str
    from_device: str
    to_device: str
    state: HandoffState = HandoffState.PENDING
    created_at: float = field(default_factory=time.monotonic)


@dataclass
class HandoffCoordinator:
    """Tracks pending session handoffs between devices."""

    ttl_s: float = 30.0
    on_transfer: Callable[[Handoff], None] | None = None
    _pending: dict[str, Handoff] = field(default_factory=dict, init=False)

    def initiate(self, *, session_id: str, from_device: str, to_device: str) -> str:
        if from_device == to_device:
            raise ValueError("from_device and to_device must differ")
        h = Handoff(
            id=uuid4().hex[:12],
            session_id=session_id,
            from_device=from_device,
            to_device=to_device,
        )
        self._pending[h.id] = h
        return h.id

    def get(self, handoff_id: str) -> Handoff | None:
        return self._pending.get(handoff_id)

    def accept(self, handoff_id: str) -> Handoff | None:
        h = self._pending.get(handoff_id)
        if h is None:
            return None
        if self._is_expired(h):
            h.state = HandoffState.EXPIRED
            return None
        h.state = HandoffState.ACCEPTED
        if self.on_transfer:
            self.on_transfer(h)
        return h

    def reject(self, handoff_id: str) -> bool:
        h = self._pending.get(handoff_id)
        if h is None:
            return False
        h.state = HandoffState.REJECTED
        return True

    def pending_for(self, device: str) -> list[Handoff]:
        return [
            h
            for h in self._pending.values()
            if h.to_device == device and h.state is HandoffState.PENDING and not self._is_expired(h)
        ]

    def expire_old(self) -> int:
        expired = 0
        for h in self._pending.values():
            if h.state is HandoffState.PENDING and self._is_expired(h):
                h.state = HandoffState.EXPIRED
                expired += 1
        return expired

    def _is_expired(self, handoff: Handoff) -> bool:
        return (time.monotonic() - handoff.created_at) > self.ttl_s


__all__ = ["Handoff", "HandoffCoordinator", "HandoffState"]
