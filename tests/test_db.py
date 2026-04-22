"""Tests for nova.db."""

from __future__ import annotations

from pathlib import Path

from nova.db import MIGRATIONS, migrate, open_store


def test_migration_creates_tables(tmp_path: Path) -> None:
    conn = open_store(tmp_path / "nova.db")
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    for expected in {"conversations", "messages", "events", "devices", "tasks", "schema_version"}:
        assert expected in tables
    version = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()["v"]
    assert version == MIGRATIONS[-1][0]


def test_wal_mode_enabled(tmp_path: Path) -> None:
    conn = open_store(tmp_path / "nova.db")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "nova.db"
    conn1 = open_store(db)
    v1 = migrate(conn1)
    conn1.close()
    conn2 = open_store(db)
    v2 = migrate(conn2)
    assert v1 == v2 == MIGRATIONS[-1][0]


def test_foreign_keys_enforced(tmp_path: Path) -> None:
    conn = open_store(tmp_path / "nova.db")
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
