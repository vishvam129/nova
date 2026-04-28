"""Tests for nova.server.remote_access."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nova.server.remote_access import (
    WireGuardConfig,
    WireGuardPeer,
    tailscale_available,
    tailscale_status,
    tailscale_up,
    wg_genkey,
    wg_pubkey,
)

# --- Tailscale ---


def test_tailscale_available_yes() -> None:
    with patch("nova.server.remote_access.shutil.which", return_value="/usr/bin/tailscale"):
        assert tailscale_available() is True


def test_tailscale_available_no() -> None:
    with patch("nova.server.remote_access.shutil.which", return_value=None):
        assert tailscale_available() is False


def test_tailscale_status_when_unavailable() -> None:
    with patch("nova.server.remote_access.tailscale_available", return_value=False):
        s = tailscale_status()
    assert s.online is False


def test_tailscale_up_runs_command() -> None:
    with (
        patch("nova.server.remote_access.tailscale_available", return_value=True),
        patch(
            "nova.server.remote_access.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as run,
    ):
        ok = tailscale_up(hostname="nova-laptop", advertise_routes=["10.0.0.0/24"])
    assert ok is True
    cmd = run.call_args[0][0]
    assert cmd[:2] == ["tailscale", "up"]
    assert "--hostname" in cmd
    assert "10.0.0.0/24" in cmd


def test_tailscale_up_unavailable_returns_false() -> None:
    with patch("nova.server.remote_access.tailscale_available", return_value=False):
        assert tailscale_up() is False


# --- WireGuard ---


def test_wireguard_config_render_minimal() -> None:
    cfg = WireGuardConfig(private_key="PRIV", address="10.0.0.2/24")
    out = cfg.render()
    assert "[Interface]" in out
    assert "PrivateKey = PRIV" in out
    assert "Address = 10.0.0.2/24" in out


def test_wireguard_config_with_peer() -> None:
    cfg = WireGuardConfig(
        private_key="PRIV",
        address="10.0.0.2/24",
        peers=[
            WireGuardPeer(
                public_key="PUB",
                allowed_ips="10.0.0.1/32",
                endpoint="vpn.example.com:51820",
                persistent_keepalive=25,
            )
        ],
    )
    out = cfg.render()
    assert "[Peer]" in out
    assert "PublicKey = PUB" in out
    assert "Endpoint = vpn.example.com:51820" in out
    assert "PersistentKeepalive = 25" in out


def test_wireguard_config_dns_optional() -> None:
    cfg = WireGuardConfig(private_key="PRIV", address="10.0.0.2/24", dns="1.1.1.1")
    assert "DNS = 1.1.1.1" in cfg.render()


def test_wireguard_config_write(tmp_path: Path) -> None:
    cfg = WireGuardConfig(private_key="PRIV", address="10.0.0.2/24")
    out = tmp_path / "wg0.conf"
    cfg.write(out)
    assert out.exists()
    assert "[Interface]" in out.read_text()


def test_wg_genkey_no_wg_raises() -> None:
    with (
        patch("nova.server.remote_access.shutil.which", return_value=None),
        pytest.raises(RuntimeError),
    ):
        wg_genkey()


def test_wg_genkey_returns_stdout() -> None:
    with (
        patch("nova.server.remote_access.shutil.which", return_value="/usr/bin/wg"),
        patch(
            "nova.server.remote_access.subprocess.run",
            return_value=MagicMock(stdout=b"abc==\n"),
        ),
    ):
        assert wg_genkey() == "abc=="


def test_wg_pubkey_returns_stdout() -> None:
    with (
        patch("nova.server.remote_access.shutil.which", return_value="/usr/bin/wg"),
        patch(
            "nova.server.remote_access.subprocess.run",
            return_value=MagicMock(stdout=b"pub==\n"),
        ),
    ):
        assert wg_pubkey("priv==") == "pub=="
