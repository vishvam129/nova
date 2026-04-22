"""Append-only audit log.

Every tool invocation — arguments, outcome, caller — is serialized to
a JSONL file under the user data directory. Lines are flushed + fsynced
so a crash can't lose recent records. Arguments pass through the
redactor before being written so secrets never hit disk.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nova.safety.redaction import Redactor


@dataclass(frozen=True, slots=True)
class AuditEntry:
    ts: float
    tool: str
    arguments: dict[str, Any]
    outcome: str
    error: str | None = None
    actor: str | None = None


@dataclass
class AuditLog:
    path: Path
    redactor: Redactor = field(default_factory=Redactor)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def write(
        self,
        tool: str,
        arguments: dict[str, Any],
        outcome: str = "ok",
        error: str | None = None,
        actor: str | None = None,
    ) -> AuditEntry:
        redacted_args = {k: self._redact_value(v) for k, v in arguments.items()}
        entry = AuditEntry(
            ts=time.time(),
            tool=tool,
            arguments=redacted_args,
            outcome=outcome,
            error=self._redact_value(error) if error else None,
            actor=actor,
        )
        self._append(entry)
        return entry

    def _redact_value(self, v: Any) -> Any:
        if isinstance(v, str):
            return self.redactor.redact(v).text
        if isinstance(v, dict):
            return {k: self._redact_value(x) for k, x in v.items()}
        if isinstance(v, list):
            return [self._redact_value(x) for x in v]
        return v

    def _append(self, entry: AuditEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "ts": entry.ts,
                "tool": entry.tool,
                "arguments": entry.arguments,
                "outcome": entry.outcome,
                "error": entry.error,
                "actor": entry.actor,
            }
        )
        with self._lock, open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def tail(self, n: int = 50) -> list[AuditEntry]:
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [_parse(line) for line in lines[-n:]]

    def iter_all(self) -> Iterator[AuditEntry]:
        if not self.path.is_file():
            return
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield _parse(line)


def _parse(line: str) -> AuditEntry:
    data = json.loads(line)
    return AuditEntry(
        ts=float(data["ts"]),
        tool=str(data["tool"]),
        arguments=dict(data.get("arguments", {})),
        outcome=str(data.get("outcome", "ok")),
        error=data.get("error"),
        actor=data.get("actor"),
    )


__all__ = ["AuditEntry", "AuditLog"]
