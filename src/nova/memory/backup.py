"""Memory backup + restore (encrypted tarball) with scheduled auto-backup.

Tar a directory tree, optionally encrypt with NaCl SecretBox, and write
a timestamped archive.  Restore reverses it.

A tiny scheduler is included for periodic auto-backup; callers wire it
into their event loop / cron.
"""

from __future__ import annotations

import contextlib
import io
import tarfile
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


def make_tarball(source_dir: Path) -> bytes:
    """Tar+gzip the directory and return bytes (in-memory)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(source_dir, arcname=source_dir.name)
    return buf.getvalue()


def extract_tarball(blob: bytes, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        tar.extractall(dest_dir, filter="data")


def encrypt(blob: bytes, key: bytes) -> bytes:
    """Encrypt with NaCl SecretBox (key must be 32 bytes)."""
    from nacl.secret import SecretBox
    from nacl.utils import random as nacl_random

    box = SecretBox(key)
    nonce = nacl_random(SecretBox.NONCE_SIZE)
    return nonce + box.encrypt(blob, nonce).ciphertext


def decrypt(blob: bytes, key: bytes) -> bytes:
    from nacl.secret import SecretBox

    box = SecretBox(key)
    nonce = blob[: SecretBox.NONCE_SIZE]
    ciphertext = blob[SecretBox.NONCE_SIZE :]
    return bytes(box.decrypt(ciphertext, nonce))


@dataclass
class BackupManager:
    """Backup ``source_dir`` to ``backup_dir`` with optional encryption."""

    source_dir: Path
    backup_dir: Path
    key: bytes | None = None  # 32 bytes for NaCl SecretBox
    keep_last: int = 7

    def backup(self) -> Path:
        """Create a single backup. Returns the file path written."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        blob = make_tarball(self.source_dir)
        if self.key is not None:
            blob = encrypt(blob, self.key)
            ext = ".tar.gz.enc"
        else:
            ext = ".tar.gz"
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        out = self.backup_dir / f"backup-{ts}{ext}"
        out.write_bytes(blob)
        self._rotate()
        return out

    def restore(self, archive: Path, dest: Path | None = None) -> Path:
        """Restore *archive* into ``dest`` (defaults to source_dir)."""
        target = dest or self.source_dir
        blob = archive.read_bytes()
        if archive.suffix == ".enc":
            if self.key is None:
                raise ValueError("encryption key required to decrypt .enc archive")
            blob = decrypt(blob, self.key)
        extract_tarball(blob, target.parent)
        return target

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(self.backup_dir.glob("backup-*"))

    def _rotate(self) -> None:
        backups = self.list_backups()
        overflow = len(backups) - self.keep_last
        for old in backups[:overflow] if overflow > 0 else []:
            old.unlink(missing_ok=True)


@dataclass
class AutoBackupScheduler:
    """Runs ``manager.backup()`` every ``interval_s`` seconds."""

    manager: BackupManager
    interval_s: float = 86_400.0
    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            with contextlib.suppress(Exception):
                self.manager.backup()
            self._stop.wait(self.interval_s)


def iter_backups(backup_dir: Path) -> Iterator[Path]:
    yield from sorted(backup_dir.glob("backup-*"))


def trim_old_backups(backup_dir: Path, keep_last: int) -> int:
    """Helper to delete all but the most recent ``keep_last`` backups."""
    backups = sorted(backup_dir.glob("backup-*"))
    overflow = len(backups) - keep_last
    if overflow <= 0:
        return 0
    for old in backups[:overflow]:
        old.unlink(missing_ok=True)
    return overflow


def _wait_for_backup(scheduler: AutoBackupScheduler, timeout: float = 1.0) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if scheduler.manager.list_backups():
            return
        time.sleep(0.05)


__all__ = [
    "AutoBackupScheduler",
    "BackupManager",
    "decrypt",
    "encrypt",
    "extract_tarball",
    "iter_backups",
    "make_tarball",
    "trim_old_backups",
]
