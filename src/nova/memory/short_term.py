"""Short-term rolling conversation buffer.

Keeps the last N turns in a deque and, once the total estimated token
count exceeds a threshold, folds the oldest turns into a single
summary turn so the recent context stays cheap to reason over.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from time import time

from nova.brain.context import estimate_tokens


@dataclass(frozen=True, slots=True)
class MemoryTurn:
    role: str
    content: str
    ts: float


Summarizer = Callable[[list[MemoryTurn]], str]


def _naive_summary(turns: list[MemoryTurn]) -> str:
    pieces: list[str] = []
    for t in turns:
        trimmed = t.content.strip().splitlines()[0][:120]
        pieces.append(f"{t.role}: {trimmed}")
    return "; ".join(pieces)


@dataclass
class RollingBuffer:
    capacity: int = 40
    token_budget: int = 3000
    summarizer: Summarizer = field(default=_naive_summary)
    _turns: deque[MemoryTurn] = field(default_factory=deque, init=False)
    _summary: str = field(default="", init=False)

    def append(self, role: str, content: str) -> MemoryTurn:
        turn = MemoryTurn(role=role, content=content, ts=time())
        self._turns.append(turn)
        self._enforce_capacity()
        self._maybe_fold()
        return turn

    def _enforce_capacity(self) -> None:
        while len(self._turns) > self.capacity:
            self._turns.popleft()

    def _tokens(self) -> int:
        return sum(estimate_tokens(t.content) for t in self._turns)

    def _maybe_fold(self) -> None:
        if self._tokens() <= self.token_budget:
            return
        cut = max(1, len(self._turns) // 2)
        old = [self._turns.popleft() for _ in range(cut)]
        folded = self.summarizer(old)
        self._summary = f"{self._summary}\n{folded}".strip() if self._summary else folded.strip()

    @property
    def summary(self) -> str:
        return self._summary

    def turns(self) -> list[MemoryTurn]:
        return list(self._turns)

    def __len__(self) -> int:
        return len(self._turns)

    def __iter__(self) -> Iterable[MemoryTurn]:
        return iter(self._turns)


__all__ = ["MemoryTurn", "RollingBuffer", "Summarizer"]
