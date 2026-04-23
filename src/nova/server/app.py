"""FastAPI ASGI application wrapping the DeviceHub.

Only the factory ``build_app`` is exported. FastAPI is imported
lazily — tests that need to exercise the app create it with a mocked
hub; the hub itself is covered without importing FastAPI at all.
"""

from __future__ import annotations

from typing import Any

from nova.server.hub import DeviceHub, Envelope


def build_app(hub: DeviceHub | None = None) -> Any:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect

    hub = hub or DeviceHub()
    app = FastAPI(title="nova-brain")

    @app.get("/health")  # type: ignore[misc]
    async def health() -> dict[str, Any]:  # pragma: no cover
        return {"ok": True, "devices": hub.device_count}

    @app.websocket("/ws/{name}/{platform}")  # type: ignore[misc]
    async def device_ws(websocket: WebSocket, name: str, platform: str) -> None:  # pragma: no cover
        await websocket.accept()

        async def send(payload: dict[str, Any]) -> None:
            await websocket.send_json(payload)

        device = await hub.register(name=name, platform=platform, sender=send)
        await websocket.send_json({"kind": "hello", "payload": {"device_id": device.id}})
        try:
            while True:
                msg = await websocket.receive_json()
                env = Envelope(
                    kind=msg.get("kind", "unknown"),
                    payload=msg.get("payload", {}),
                    from_device=device.id,
                    to_device=msg.get("to"),
                )
                if env.to_device:
                    await hub.send(env.to_device, env)
                else:
                    await hub.broadcast(env, skip=device.id)
        except WebSocketDisconnect:
            pass
        finally:
            await hub.unregister(device.id)

    return app


__all__ = ["build_app"]
