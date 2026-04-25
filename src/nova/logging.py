"""Structured logging for Nova services.

Call ``configure_logging()`` once at process start.  After that every
module gets a bound logger via ``get_logger(__name__)`` and all output
goes through structlog's processor chain.

Two output modes:
    json   — one JSON object per line, suitable for log aggregators
    pretty — coloured human-readable output for the terminal

A rotating file handler is always attached alongside stderr so logs
survive restarts.  The file always uses JSON format regardless of the
console mode.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog

_DEFAULT_LOG_FILE = Path("~/.local/share/nova/nova.log").expanduser()
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_DEFAULT_BACKUP_COUNT = 5
_configured = False


def configure_logging(
    *,
    level: str = "INFO",
    json_mode: bool = False,
    log_file: Path | None = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
) -> None:
    """Configure structlog + stdlib logging.  Safe to call multiple times."""
    global _configured  # noqa: PLW0603

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors for both file and console
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Console renderer
    if json_mode:
        console_renderer: Any = structlog.processors.JSONRenderer()
    else:
        console_renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # --- stdlib root logger ---
    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Clear any handlers pytest or the framework already added
    root.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                console_renderer,
            ],
            foreign_pre_chain=shared_processors,
        )
    )
    root.addHandler(console_handler)

    # Rotating file handler (always JSON)
    file_path = log_file or _DEFAULT_LOG_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        )
    )
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str = "") -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger, configuring defaults if not yet done."""
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
