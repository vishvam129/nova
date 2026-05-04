"""Bundle default STT/TTS/wake word models into the installer.

A ``ModelBundle`` lists the models the installer must download + verify.
``download_all()`` fetches missing files; ``verify()`` checks SHA-256.
The result is a manifest the installer ships next to the binary.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelEntry:
    name: str
    kind: str  # 'stt' | 'tts' | 'wake'
    url: str
    sha256: str
    size_bytes: int = 0

    def filename(self) -> str:
        return self.name + Path(self.url).suffix


_DEFAULTS: tuple[ModelEntry, ...] = (
    ModelEntry(
        name="moonshine-base",
        kind="stt",
        url="https://huggingface.co/UsefulSensors/moonshine-base/resolve/main/model.onnx",
        sha256="0" * 64,
        size_bytes=190_000_000,
    ),
    ModelEntry(
        name="kokoro-en-female",
        kind="tts",
        url="https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v0_19.onnx",
        sha256="0" * 64,
        size_bytes=82_000_000,
    ),
    ModelEntry(
        name="hey-nova",
        kind="wake",
        url="https://example.com/openwakeword/hey_nova.tflite",
        sha256="0" * 64,
        size_bytes=2_000_000,
    ),
)


@dataclass
class ModelBundle:
    """Download + verify bundle of installer-shipped models."""

    target_dir: Path
    entries: list[ModelEntry] = field(default_factory=lambda: list(_DEFAULTS))

    def __post_init__(self) -> None:
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, entry: ModelEntry) -> Path:
        return self.target_dir / entry.filename()

    def is_present(self, entry: ModelEntry) -> bool:
        return self.path_for(entry).exists()

    def missing(self) -> list[ModelEntry]:
        return [e for e in self.entries if not self.is_present(e)]

    def total_bytes(self) -> int:
        return sum(e.size_bytes for e in self.entries)

    def download_all(self, *, fetcher: object | None = None) -> list[Path]:
        """Download every missing model. ``fetcher`` is for tests; defaults to urllib."""
        downloaded: list[Path] = []
        for entry in self.missing():
            target = self.path_for(entry)
            blob = self._fetch(entry.url, fetcher=fetcher)
            target.write_bytes(blob)
            downloaded.append(target)
        return downloaded

    def verify(self) -> dict[str, bool]:
        """Return {name: ok} for every present model.  Skips missing."""
        out: dict[str, bool] = {}
        for entry in self.entries:
            path = self.path_for(entry)
            if not path.exists():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            out[entry.name] = digest == entry.sha256
        return out

    def write_manifest(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "models": [
                {
                    "name": e.name,
                    "kind": e.kind,
                    "filename": e.filename(),
                    "sha256": e.sha256,
                    "size_bytes": e.size_bytes,
                }
                for e in self.entries
            ]
        }
        path.write_text(json.dumps(payload, indent=2))
        return path

    @staticmethod
    def _fetch(url: str, *, fetcher: object | None) -> bytes:
        if callable(fetcher):
            return bytes(fetcher(url))
        with urllib.request.urlopen(url, timeout=60) as resp:
            return bytes(resp.read())


def default_models() -> Iterable[ModelEntry]:
    return tuple(_DEFAULTS)


__all__ = ["ModelBundle", "ModelEntry", "default_models"]
