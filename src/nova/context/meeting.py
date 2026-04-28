"""Meeting listen-along mode.

Streams loopback / mic audio through STT, accumulates a running transcript,
and on demand extracts action items + summary using a Summarizer protocol.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TranscriptChunk:
    text: str
    speaker: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, slots=True)
class ActionItem:
    text: str
    owner: str = ""
    due: str = ""

    def __str__(self) -> str:
        bits = [self.text]
        if self.owner:
            bits.append(f"(owner: {self.owner})")
        if self.due:
            bits.append(f"due {self.due}")
        return " ".join(bits)


_ACTION_VERBS = (
    "will ",
    "i'll ",
    "i will ",
    "we'll ",
    "we will ",
    "need to ",
    "should ",
    "let's ",
    "let us ",
    "todo:",
    "action:",
    "follow up",
)

_OWNER_PATTERN = re.compile(r"\b([A-Z][a-z]+) (?:will|should|to)\b")
_DUE_PATTERN = re.compile(r"\b(?:by|before|on|next)\s+(\w+(?:day)?|\d+(?:st|nd|rd|th)?)\b", re.I)


class Summarizer(Protocol):
    def summarize(self, text: str) -> str: ...


def extract_action_items(text: str) -> list[ActionItem]:
    """Pull action items from a transcript heuristically."""
    out: list[ActionItem] = []
    for raw in re.split(r"(?<=[.!?])\s+", text):
        sentence = raw.strip()
        low = sentence.lower()
        if not any(v in low for v in _ACTION_VERBS):
            continue
        owner_match = _OWNER_PATTERN.search(sentence)
        due_match = _DUE_PATTERN.search(sentence)
        out.append(
            ActionItem(
                text=sentence.rstrip(".!?"),
                owner=owner_match.group(1) if owner_match else "",
                due=due_match.group(1) if due_match else "",
            )
        )
    return out


@dataclass
class MeetingSession:
    """Live meeting transcript + on-demand summary/action extraction."""

    summarizer: Summarizer | None = None
    _chunks: list[TranscriptChunk] = field(default_factory=list, init=False)
    _started_at: datetime = field(default_factory=datetime.now, init=False)

    def add(self, text: str, speaker: str = "") -> TranscriptChunk:
        chunk = TranscriptChunk(text=text.strip(), speaker=speaker)
        if chunk.text:
            self._chunks.append(chunk)
        return chunk

    def add_chunks(self, chunks: Iterable[TranscriptChunk]) -> None:
        for c in chunks:
            if c.text:
                self._chunks.append(c)

    def transcript(self) -> str:
        return "\n".join(f"{c.speaker}: {c.text}" if c.speaker else c.text for c in self._chunks)

    def action_items(self) -> list[ActionItem]:
        return extract_action_items(self.transcript())

    def summary(self) -> str:
        if self.summarizer is None:
            return self.transcript()[:500]
        return self.summarizer.summarize(self.transcript())

    def duration_seconds(self) -> float:
        return (datetime.now() - self._started_at).total_seconds()

    def reset(self) -> None:
        self._chunks.clear()
        self._started_at = datetime.now()


__all__ = [
    "ActionItem",
    "MeetingSession",
    "Summarizer",
    "TranscriptChunk",
    "extract_action_items",
]
