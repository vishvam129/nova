"""Nova brain service: FastAPI + WebSocket hub."""

from nova.server import app as _app
from nova.server import hub as _hub
from nova.server import pairing as _pairing

DeviceHub = _hub.DeviceHub
Envelope = _hub.Envelope
RegisteredDevice = _hub.RegisteredDevice
build_app = _app.build_app

PairingCoordinator = _pairing.PairingCoordinator
PairingInvite = _pairing.PairingInvite
PairingResponse = _pairing.PairingResponse
build_response = _pairing.build_response

__all__ = [
    "DeviceHub",
    "Envelope",
    "PairingCoordinator",
    "PairingInvite",
    "PairingResponse",
    "RegisteredDevice",
    "build_app",
    "build_response",
]
