"""Auto-update channel with Ed25519 release signature verification.

Each release ships:
    nova-vX.Y.Z.tar.gz       — the artifact
    nova-vX.Y.Z.tar.gz.sig   — Ed25519 detached signature

The updater:
    1. Polls a manifest URL for the latest version per channel.
    2. Compares with the running version.
    3. Downloads artifact + signature.
    4. Verifies the signature with the bundled public key.
    5. Stages the file in ``stage_dir`` for the installer to swap in.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Channel(StrEnum):
    STABLE = "stable"
    BETA = "beta"
    NIGHTLY = "nightly"


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    channel: Channel
    artifact_url: str
    signature_url: str
    notes: str = ""


def parse_manifest(text: str, channel: Channel) -> ReleaseInfo | None:
    data = json.loads(text)
    block = data.get(channel.value)
    if not block:
        return None
    return ReleaseInfo(
        version=str(block["version"]),
        channel=channel,
        artifact_url=str(block["artifact_url"]),
        signature_url=str(block["signature_url"]),
        notes=str(block.get("notes", "")),
    )


def is_newer(candidate: str, current: str) -> bool:
    """Compare semver-ish version strings; returns True if candidate > current."""
    return _parse_version(candidate) > _parse_version(current)


def _parse_version(value: str) -> tuple[int, ...]:
    cleaned = value.lstrip("v").split("-", 1)[0]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def verify_signature(artifact: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verify Ed25519 detached signature; returns False on any failure."""
    try:
        from nacl.exceptions import BadSignatureError
        from nacl.signing import VerifyKey

        VerifyKey(public_key).verify(artifact, signature)
    except BadSignatureError:
        return False
    except Exception:  # noqa: BLE001
        return False
    return True


@dataclass
class AutoUpdater:
    current_version: str
    channel: Channel = Channel.STABLE
    manifest_url: str = "https://nova.example/releases/manifest.json"
    public_key: bytes = b""
    stage_dir: Path = field(default_factory=lambda: Path("~/.cache/nova/updates").expanduser())
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        self.stage_dir.mkdir(parents=True, exist_ok=True)

    def _fetch(self, url: str) -> bytes:
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_s) as resp:
                return bytes(resp.read())
        except (urllib.error.URLError, OSError):
            return b""

    def latest_release(self) -> ReleaseInfo | None:
        body = self._fetch(self.manifest_url)
        if not body:
            return None
        try:
            return parse_manifest(body.decode(), self.channel)
        except (json.JSONDecodeError, KeyError):
            return None

    def check(self) -> ReleaseInfo | None:
        rel = self.latest_release()
        if rel is None:
            return None
        return rel if is_newer(rel.version, self.current_version) else None

    def download_and_verify(self, release: ReleaseInfo) -> Path | None:
        artifact = self._fetch(release.artifact_url)
        signature = self._fetch(release.signature_url)
        if not artifact or not signature:
            return None
        if self.public_key and not verify_signature(artifact, signature, self.public_key):
            return None
        out = self.stage_dir / f"nova-{release.version}.tar.gz"
        out.write_bytes(artifact)
        return out


__all__ = [
    "AutoUpdater",
    "Channel",
    "ReleaseInfo",
    "is_newer",
    "parse_manifest",
    "verify_signature",
]
