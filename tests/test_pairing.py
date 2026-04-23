"""Tests for device pairing."""

from __future__ import annotations

import time

from nova.server.pairing import (
    PairingCoordinator,
    PairingInvite,
    build_response,
)


def test_invite_qr_roundtrip() -> None:
    coord = PairingCoordinator()
    invite = coord.invite("ws://laptop.local:8765")
    qr = invite.to_qr_text()
    decoded = PairingInvite.from_qr_text(qr)
    assert decoded.nonce == invite.nonce
    assert decoded.hub_url == invite.hub_url
    assert decoded.laptop_public_key == invite.laptop_public_key


def test_invalid_qr_text_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        PairingInvite.from_qr_text("https://example.com")


def test_valid_handshake_verifies() -> None:
    coord = PairingCoordinator()
    invite = coord.invite("ws://host:1234")
    response, _ = build_response(invite, "phone", "android")
    assert coord.verify(response, invite.nonce) is True


def test_invite_is_one_shot() -> None:
    coord = PairingCoordinator()
    invite = coord.invite("ws://h:1")
    response, _ = build_response(invite, "phone", "android")
    assert coord.verify(response, invite.nonce) is True
    assert coord.verify(response, invite.nonce) is False


def test_tampered_signature_rejected() -> None:
    coord = PairingCoordinator()
    invite = coord.invite("ws://h:1")
    response, _ = build_response(invite, "phone", "android")
    broken = response.__class__(
        device_name=response.device_name,
        platform=response.platform,
        device_public_key=response.device_public_key,
        signature="AAAA" + response.signature[4:],
    )
    assert coord.verify(broken, invite.nonce) is False


def test_expired_invite_rejected() -> None:
    coord = PairingCoordinator(ttl_seconds=0)
    invite = coord.invite("ws://h:1")
    response, _ = build_response(invite, "phone", "android")
    time.sleep(0.01)
    assert coord.verify(response, invite.nonce) is False


def test_unknown_nonce_rejected() -> None:
    coord = PairingCoordinator()
    invite = coord.invite("ws://h:1")
    response, _ = build_response(invite, "phone", "android")
    assert coord.verify(response, "some-other-nonce") is False
