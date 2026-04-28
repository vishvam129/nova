"""Remote access via Tailscale or built-in WireGuard helper.

Tailscale is the recommended path (zero-config mesh).  When unavailable,
``WireGuardConfig`` generates a peer config the user can drop into wg0.

Both helpers are thin wrappers around their CLIs / file outputs — no
network state lives here.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# ---------------- Tailscale ----------------


def tailscale_available() -> bool:
    return shutil.which("tailscale") is not None


@dataclass
class TailscaleStatus:
    online: bool
    self_ip: str = ""
    peers: dict[str, str] = field(default_factory=dict)  # hostname → ip


def tailscale_status() -> TailscaleStatus:
    """Parse ``tailscale status`` output."""
    if not tailscale_available():
        return TailscaleStatus(online=False)
    try:
        r = subprocess.run(["tailscale", "status", "--json=false"], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return TailscaleStatus(online=False)
    if r.returncode != 0:
        return TailscaleStatus(online=False)

    self_ip = ""
    peers: dict[str, str] = {}
    for line in r.stdout.decode(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        ip, host = parts[0], parts[1]
        if "you" in line.lower() or "self" in line.lower():
            self_ip = ip
        else:
            peers[host] = ip
    return TailscaleStatus(online=bool(self_ip or peers), self_ip=self_ip, peers=peers)


def tailscale_up(*, hostname: str | None = None, advertise_routes: list[str] | None = None) -> bool:
    """Bring tailscale up. Returns True on success."""
    if not tailscale_available():
        return False
    cmd = ["tailscale", "up"]
    if hostname:
        cmd += ["--hostname", hostname]
    if advertise_routes:
        cmd += ["--advertise-routes", ",".join(advertise_routes)]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


# ---------------- WireGuard ----------------


@dataclass
class WireGuardConfig:
    """Build a wg-quick compatible config."""

    private_key: str
    address: str  # e.g. "10.0.0.2/24"
    listen_port: int = 51_820
    dns: str = ""
    peers: list[WireGuardPeer] = field(default_factory=list)

    def render(self) -> str:
        lines = ["[Interface]"]
        lines.append(f"PrivateKey = {self.private_key}")
        lines.append(f"Address = {self.address}")
        if self.listen_port:
            lines.append(f"ListenPort = {self.listen_port}")
        if self.dns:
            lines.append(f"DNS = {self.dns}")
        for peer in self.peers:
            lines.append("")
            lines.append("[Peer]")
            lines.append(f"PublicKey = {peer.public_key}")
            lines.append(f"AllowedIPs = {peer.allowed_ips}")
            if peer.endpoint:
                lines.append(f"Endpoint = {peer.endpoint}")
            if peer.persistent_keepalive:
                lines.append(f"PersistentKeepalive = {peer.persistent_keepalive}")
        return "\n".join(lines) + "\n"

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path


@dataclass
class WireGuardPeer:
    public_key: str
    allowed_ips: str  # e.g. "10.0.0.1/32"
    endpoint: str = ""  # e.g. "vpn.example.com:51820"
    persistent_keepalive: int = 0


def wg_genkey() -> str:
    """Generate a base64 WireGuard private key via ``wg genkey``."""
    if not shutil.which("wg"):
        raise RuntimeError("wg binary not on PATH")
    r = subprocess.run(["wg", "genkey"], capture_output=True, timeout=5, check=True)
    return r.stdout.decode().strip()


def wg_pubkey(private_key: str) -> str:
    """Derive the public key from a private key via ``wg pubkey``."""
    if not shutil.which("wg"):
        raise RuntimeError("wg binary not on PATH")
    r = subprocess.run(
        ["wg", "pubkey"], input=private_key.encode(), capture_output=True, timeout=5, check=True
    )
    return r.stdout.decode().strip()


__all__ = [
    "TailscaleStatus",
    "WireGuardConfig",
    "WireGuardPeer",
    "tailscale_available",
    "tailscale_status",
    "tailscale_up",
    "wg_genkey",
    "wg_pubkey",
]
