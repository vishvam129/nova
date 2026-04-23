"""Device pairing: QR code + Ed25519 handshake.

Flow:
  1. Laptop generates a short-lived ``PairingInvite`` containing the hub
     URL + laptop's public key + a nonce. It's rendered as a QR the
     phone scans.
  2. Phone generates its own keypair, signs the nonce with its secret
     key, and POSTs ``PairingResponse`` back.
  3. Laptop verifies the signature and records the phone's public key
     as a trusted device.
"""

from __future__ import annotations

import base64
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from nacl.signing import SigningKey, VerifyKey


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _ub64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


@dataclass(frozen=True, slots=True)
class PairingInvite:
    hub_url: str
    nonce: str
    laptop_public_key: str
    expires_at: float

    def to_qr_text(self) -> str:
        return "nova-pair://" + _b64(
            json.dumps(
                {
                    "u": self.hub_url,
                    "n": self.nonce,
                    "k": self.laptop_public_key,
                    "e": self.expires_at,
                }
            ).encode()
        )

    @classmethod
    def from_qr_text(cls, text: str) -> PairingInvite:
        if not text.startswith("nova-pair://"):
            raise ValueError("not a nova pairing QR")
        raw = _ub64(text.removeprefix("nova-pair://"))
        data = json.loads(raw)
        return cls(
            hub_url=str(data["u"]),
            nonce=str(data["n"]),
            laptop_public_key=str(data["k"]),
            expires_at=float(data["e"]),
        )


@dataclass(frozen=True, slots=True)
class PairingResponse:
    device_name: str
    platform: str
    device_public_key: str
    signature: str


@dataclass
class PairingCoordinator:
    """Holds pending invites and verifies responses."""

    ttl_seconds: int = 300
    _invites: dict[str, PairingInvite] = field(default_factory=dict)
    _signing: SigningKey = field(default_factory=SigningKey.generate)

    @property
    def public_key(self) -> str:
        return _b64(self._signing.verify_key.encode())

    def invite(self, hub_url: str) -> PairingInvite:
        nonce = _b64(secrets.token_bytes(24))
        invite = PairingInvite(
            hub_url=hub_url,
            nonce=nonce,
            laptop_public_key=self.public_key,
            expires_at=time.time() + self.ttl_seconds,
        )
        self._invites[nonce] = invite
        return invite

    def verify(self, response: PairingResponse, nonce: str) -> bool:
        invite = self._invites.get(nonce)
        if invite is None:
            return False
        if time.time() > invite.expires_at:
            self._invites.pop(nonce, None)
            return False
        try:
            verify_key = VerifyKey(_ub64(response.device_public_key))
            verify_key.verify(nonce.encode(), _ub64(response.signature))
        except Exception:
            return False
        self._invites.pop(nonce, None)
        return True


def sign_invite(invite: PairingInvite, device_signing_key: SigningKey) -> bytes:
    return bytes(device_signing_key.sign(invite.nonce.encode()).signature)


def build_response(
    invite: PairingInvite,
    device_name: str,
    platform: str,
    signing_key: SigningKey | None = None,
) -> tuple[PairingResponse, SigningKey]:
    key = signing_key or SigningKey.generate()
    sig = sign_invite(invite, key)
    return (
        PairingResponse(
            device_name=device_name,
            platform=platform,
            device_public_key=_b64(bytes(key.verify_key)),
            signature=_b64(sig),
        ),
        key,
    )


__all__: list[Any] = [
    "PairingCoordinator",
    "PairingInvite",
    "PairingResponse",
    "build_response",
    "sign_invite",
]
