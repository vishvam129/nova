"""Tests for nova.memory.backup."""

from __future__ import annotations

from pathlib import Path

import pytest

from nova.memory.backup import (
    BackupManager,
    decrypt,
    encrypt,
    extract_tarball,
    iter_backups,
    make_tarball,
    trim_old_backups,
)


def test_make_and_extract_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hello")
    (src / "b.txt").write_text("world")

    blob = make_tarball(src)
    out = tmp_path / "out"
    extract_tarball(blob, out)
    assert (out / "src" / "a.txt").read_text() == "hello"
    assert (out / "src" / "b.txt").read_text() == "world"


def test_encrypt_decrypt_roundtrip() -> None:
    pytest.importorskip("nacl")
    key = b"k" * 32
    blob = b"some secret data"
    enc = encrypt(blob, key)
    assert enc != blob
    assert decrypt(enc, key) == blob


def test_backup_manager_writes_archive(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("data")
    backups = tmp_path / "backups"

    mgr = BackupManager(source_dir=src, backup_dir=backups)
    out = mgr.backup()
    assert out.exists()
    assert out.suffix == ".gz"
    assert out.parent == backups


def test_backup_manager_encrypted(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("secret")
    backups = tmp_path / "backups"

    mgr = BackupManager(source_dir=src, backup_dir=backups, key=b"k" * 32)
    out = mgr.backup()
    assert out.suffix == ".enc"
    # Encrypted bytes should not contain plaintext
    assert b"secret" not in out.read_bytes()


def test_backup_manager_restore(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("v1")
    backups = tmp_path / "backups"

    mgr = BackupManager(source_dir=src, backup_dir=backups)
    archive = mgr.backup()

    # Modify, then restore
    (src / "a.txt").write_text("v2")
    mgr.restore(archive)
    assert (src / "a.txt").read_text() == "v1"


def test_backup_rotation(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.txt").write_text("x")
    backups = tmp_path / "backups"

    mgr = BackupManager(source_dir=src, backup_dir=backups, keep_last=2)
    a = mgr.backup()
    import time as _t

    _t.sleep(1.0)
    b = mgr.backup()
    _t.sleep(1.0)
    c = mgr.backup()

    remaining = mgr.list_backups()
    assert len(remaining) == 2
    assert a not in remaining
    assert b in remaining
    assert c in remaining


def test_iter_backups(tmp_path: Path) -> None:
    bdir = tmp_path / "b"
    bdir.mkdir()
    (bdir / "backup-1.tar.gz").write_bytes(b"x")
    (bdir / "backup-2.tar.gz").write_bytes(b"y")
    (bdir / "junk.txt").write_text("ignore")
    items = list(iter_backups(bdir))
    assert len(items) == 2


def test_trim_old_backups(tmp_path: Path) -> None:
    bdir = tmp_path / "b"
    bdir.mkdir()
    for i in range(5):
        (bdir / f"backup-{i}.tar.gz").write_bytes(b"x")
    removed = trim_old_backups(bdir, keep_last=2)
    assert removed == 3
    assert len(list(bdir.glob("backup-*"))) == 2


def test_restore_encrypted_requires_key(tmp_path: Path) -> None:
    pytest.importorskip("nacl")
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hi")
    backups = tmp_path / "backups"
    mgr_enc = BackupManager(source_dir=src, backup_dir=backups, key=b"k" * 32)
    archive = mgr_enc.backup()

    # Manager without a key cannot restore
    mgr_plain = BackupManager(source_dir=src, backup_dir=backups)
    with pytest.raises(ValueError):
        mgr_plain.restore(archive)
