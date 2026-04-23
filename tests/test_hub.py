"""Tests for DeviceHub (transport-free async)."""

from __future__ import annotations

import asyncio
from typing import Any

from nova.server.hub import DeviceHub, Envelope


def _make_recorder() -> tuple[list[dict[str, Any]], Any]:
    inbox: list[dict[str, Any]] = []

    async def sender(payload: dict[str, Any]) -> None:
        inbox.append(payload)

    return inbox, sender


def test_register_and_count() -> None:
    async def go() -> None:
        hub = DeviceHub()
        _inbox, sender = _make_recorder()
        device = await hub.register("phone", "android", sender)
        assert hub.device_count == 1
        assert device.name == "phone"
        assert device.platform == "android"

    asyncio.run(go())


def test_unregister_removes_device() -> None:
    async def go() -> None:
        hub = DeviceHub()
        _, sender = _make_recorder()
        d = await hub.register("laptop", "linux", sender)
        await hub.unregister(d.id)
        assert hub.device_count == 0

    asyncio.run(go())


def test_send_delivers_to_single_device() -> None:
    async def go() -> None:
        hub = DeviceHub()
        inbox, sender = _make_recorder()
        d = await hub.register("phone", "android", sender)
        ok = await hub.send(d.id, Envelope(kind="ping", payload={"x": 1}))
        assert ok is True
        assert inbox[0]["kind"] == "ping"
        assert inbox[0]["payload"] == {"x": 1}

    asyncio.run(go())


def test_send_unknown_device_returns_false() -> None:
    async def go() -> None:
        hub = DeviceHub()
        ok = await hub.send("ghost", Envelope(kind="x", payload={}))
        assert ok is False

    asyncio.run(go())


def test_broadcast_skips_source() -> None:
    async def go() -> None:
        hub = DeviceHub()
        inboxes = []
        ids = []
        for name in ("a", "b", "c"):
            inbox, sender = _make_recorder()
            inboxes.append(inbox)
            d = await hub.register(name, "linux", sender)
            ids.append(d.id)
        n = await hub.broadcast(Envelope(kind="hi", payload={}), skip=ids[0])
        assert n == 2
        assert len(inboxes[0]) == 0
        assert len(inboxes[1]) == 1
        assert len(inboxes[2]) == 1

    asyncio.run(go())


def test_devices_list_snapshot() -> None:
    async def go() -> None:
        hub = DeviceHub()
        _, sender = _make_recorder()
        await hub.register("a", "linux", sender)
        await hub.register("b", "android", sender)
        names = sorted(d.name for d in hub.devices())
        assert names == ["a", "b"]

    asyncio.run(go())
