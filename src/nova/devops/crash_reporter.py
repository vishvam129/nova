"""Crash reporter: opt-in, sanitised, local-first dump with upload toggle.

Default behaviour:
    - off entirely
    - if enabled, write to ~/.local/share/nova/crashes/<ts>.json
    - never upload unless ``upload`` is also enabled
    - even when uploading, strip secrets via nova.safety.redaction first

Designed so a user can run ``nova crashes show`` and read the dump locally
to decide whether to share it with maintainers.
"""

from __future__ import annotations

import json
import platform
import sys
import traceback
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_DEFAULT_DIR = Path("~/.local/share/nova/crashes").expanduser()


def _redact(text: str) -> str:
    """Best-effort redaction without importing nova.safety to avoid cycles."""
    import re

    patterns = (
        (re.compile(r"sk-[A-Za-z0-9]{20,}"), "sk-***"),
        (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA***"),
        (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***"),
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "***-**-****"),
    )
    for pat, repl in patterns:
        text = pat.sub(repl, text)
    return text


@dataclass(frozen=True, slots=True)
class CrashReport:
    timestamp: datetime
    platform: str
    python_version: str
    nova_version: str
    exception_type: str
    exception_message: str
    traceback_text: str
    extras: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "platform": self.platform,
            "python_version": self.python_version,
            "nova_version": self.nova_version,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "traceback": self.traceback_text,
            "extras": dict(self.extras),
        }

    def encode(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def sanitized(self) -> CrashReport:
        return CrashReport(
            timestamp=self.timestamp,
            platform=self.platform,
            python_version=self.python_version,
            nova_version=self.nova_version,
            exception_type=self.exception_type,
            exception_message=_redact(self.exception_message),
            traceback_text=_redact(self.traceback_text),
            extras={k: _redact(v) for k, v in self.extras.items()},
        )


@dataclass
class CrashReporter:
    """Opt-in crash dump store + optional uploader."""

    enabled: bool = False
    upload: bool = False
    nova_version: str = "0.1.0"
    output_dir: Path = field(default_factory=lambda: _DEFAULT_DIR)
    upload_url: str = ""
    timeout_s: float = 5.0

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture(
        self,
        exc: BaseException,
        *,
        extras: dict[str, str] | None = None,
    ) -> Path | None:
        if not self.enabled:
            return None
        report = CrashReport(
            timestamp=datetime.now(),
            platform=platform.platform(),
            python_version=sys.version.split()[0],
            nova_version=self.nova_version,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            traceback_text="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            extras=dict(extras or {}),
        )
        sanitized = report.sanitized()
        ts = sanitized.timestamp.strftime("%Y%m%dT%H%M%S")
        path = self.output_dir / f"crash-{ts}.json"
        path.write_text(sanitized.encode())
        if self.upload and self.upload_url:
            self._upload(sanitized)
        return path

    def list_local(self) -> list[Path]:
        return sorted(self.output_dir.glob("crash-*.json"))

    def clear(self) -> int:
        items = self.list_local()
        for p in items:
            p.unlink(missing_ok=True)
        return len(items)

    def _upload(self, report: CrashReport) -> bool:
        try:
            req = urllib.request.Request(
                self.upload_url,
                data=report.encode().encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.status in (200, 201, 202)
        except (urllib.error.URLError, OSError):
            return False


def summarise(reports: Iterable[CrashReport]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in reports:
        counts[r.exception_type] = counts.get(r.exception_type, 0) + 1
    return counts


__all__ = ["CrashReport", "CrashReporter", "summarise"]
