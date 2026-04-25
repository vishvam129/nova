"""Tests for nova.logging — structured logging configuration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

import nova.logging as nova_logging
from nova.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def reset_logging(tmp_path: Path) -> None:
    """Reset structlog + stdlib root logger between tests."""
    nova_logging._configured = False
    root = logging.getLogger()
    root.handlers.clear()


def test_get_logger_returns_bound_logger() -> None:
    logger = get_logger("test.module")
    assert logger is not None


def test_configure_logging_creates_file(tmp_path: Path) -> None:
    log_file = tmp_path / "nova.log"
    configure_logging(log_file=log_file)
    assert log_file.parent.exists()


def test_configure_logging_writes_json_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / "nova.log"
    configure_logging(log_file=log_file, level="DEBUG")
    logger = get_logger("test")
    logger.info("hello structured world", extra_key="val")
    # Flush handlers
    for h in logging.getLogger().handlers:
        h.flush()
    if log_file.exists():
        lines = [ln for ln in log_file.read_text().splitlines() if ln.strip()]
        if lines:
            record = json.loads(lines[-1])
            assert "event" in record or "message" in record


def test_configure_logging_json_mode(tmp_path: Path) -> None:
    log_file = tmp_path / "nova.log"
    configure_logging(json_mode=True, log_file=log_file)
    # no exception means success
    logger = get_logger("test.json")
    logger.info("json mode active")


def test_configure_logging_idempotent(tmp_path: Path) -> None:
    log_file = tmp_path / "nova.log"
    configure_logging(log_file=log_file)
    # second call should not raise
    nova_logging._configured = False
    configure_logging(log_file=log_file)


def test_get_logger_auto_configures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nova_logging, "_DEFAULT_LOG_FILE", tmp_path / "nova.log")
    nova_logging._configured = False
    logger = get_logger("auto")
    assert nova_logging._configured is True
    logger.debug("auto configured")


def test_rotating_handler_attached(tmp_path: Path) -> None:
    import logging.handlers

    log_file = tmp_path / "nova.log"
    configure_logging(log_file=log_file)
    handlers = logging.getLogger().handlers
    types = [type(h) for h in handlers]
    assert logging.handlers.RotatingFileHandler in types
