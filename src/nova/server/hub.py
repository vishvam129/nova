"""In-memory device hub for the brain service.

Tracks connected devices and fan-outs ``Envelope`` messages to
subscribers. The networking layer (FastAPI WebSocket, WebRTC) plugs in
by calling ``register`` on connect and ``send`` / ``broadcast`` while
active. The hub itself is transport-agnostic and easy to unit-test.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

Sender = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class Envelope:
    kind: str
    payload: dict[str, Any]
    from_device: str | None = None
    to_device: str | None = None


@dataclass
class RegisteredDevice:
    id: str
    name: str
    platform: str
    sender: Sender


@dataclass
class DeviceHub:
    _devices: dict[str, RegisteredDevice] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    async def register(self, name: str, platform: str, sender: Sender) -> RegisteredDevice:
        device = RegisteredDevice(id=str(uuid.uuid4()), name=name, platform=platform, sender=sender)
        async with self._lock:
            self._devices[device.id] = device
        return device

    async def unregister(self, device_id: str) -> None:
        async with self._lock:
            self._devices.pop(device_id, None)

    async def send(self, device_id: str, envelope: Envelope) -> bool:
        device = self._devices.get(device_id)
        if device is None:
            return False
        await device.sender(_to_dict(envelope))
        return True

    async def broadcast(self, envelope: Envelope, skip: str | None = None) -> int:
        targets = [d for d in self._devices.values() if d.id != skip]
        for d in targets:
            await d.sender(_to_dict(envelope))
        return len(targets)

    @property
    def device_count(self) -> int:
        return len(self._devices)

    def devices(self) -> list[RegisteredDevice]:
        return list(self._devices.values())


def _to_dict(envelope: Envelope) -> dict[str, Any]:
    return {
        "kind": envelope.kind,
        "payload": envelope.payload,
        "from": envelope.from_device,
        "to": envelope.to_device,
    }


__all__ = ["DeviceHub", "Envelope", "RegisteredDevice", "Sender"]
