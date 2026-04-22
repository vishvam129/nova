"""Tests for AuditLog."""

from __future__ import annotations

from pathlib import Path

from nova.safety.audit import AuditLog


def test_write_and_tail_roundtrip(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.write("run_shell", {"cmd": "ls"}, outcome="ok")
    log.write("open_app", {"target": "firefox"}, outcome="ok")
    entries = log.tail(n=10)
    assert len(entries) == 2
    assert entries[0].tool == "run_shell"
    assert entries[1].tool == "open_app"
    assert entries[0].arguments == {"cmd": "ls"}


def test_redacts_secret_in_arguments(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.jsonl")
    ant = "sk" + "-ant-" + "A" * 25
    log.write("set_env", {"value": f"token={ant}"})
    entry = log.tail()[0]
    assert "sk-ant-" not in entry.arguments["value"]


def test_redacts_nested_dict_arguments(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.write("send_email", {"to": "alice@example.com", "body": "hi"})
    entry = log.tail()[0]
    assert "alice@example.com" not in entry.arguments["to"]


def test_error_field_redacted(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.write("api_call", {}, outcome="fail", error="bad key sk-ant-" + "Z" * 25)
    entry = log.tail()[0]
    assert "sk-ant-" not in (entry.error or "")


def test_append_only(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log1 = AuditLog(path=path)
    log1.write("a", {})
    log2 = AuditLog(path=path)
    log2.write("b", {})
    lines = path.read_text().splitlines()
    assert len(lines) == 2


def test_tail_empty_when_no_file(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "missing.jsonl")
    assert log.tail() == []


def test_iter_all_yields_all(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.jsonl")
    for i in range(5):
        log.write("t", {"i": i})
    entries = list(log.iter_all())
    assert len(entries) == 5
    assert [e.arguments["i"] for e in entries] == [0, 1, 2, 3, 4]
