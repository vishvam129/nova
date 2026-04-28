"""Streaming LLM response with token-level cancellation on barge-in.

When the user starts speaking mid-reply, the voice pipeline calls
``StreamingResponse.cancel()``.  The next token tick checks the cancel
flag and stops yielding tokens (and tells the LLM client to abort).
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field


@dataclass
class StreamingResponse:
    """Wraps a token iterator with a thread-safe cancel flag."""

    token_source: Iterable[str]
    on_cancel: object | None = None  # callable[[], None] — abort the LLM client

    _cancelled: threading.Event = field(default_factory=threading.Event, init=False)
    _emitted: list[str] = field(default_factory=list, init=False)

    def cancel(self) -> None:
        if self._cancelled.is_set():
            return
        self._cancelled.set()
        cb = self.on_cancel
        if callable(cb):
            with contextlib.suppress(Exception):
                cb()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def emitted_text(self) -> str:
        return "".join(self._emitted)

    def __iter__(self) -> Iterator[str]:
        for token in self.token_source:
            if self._cancelled.is_set():
                break
            self._emitted.append(token)
            yield token


__all__ = ["StreamingResponse"]
