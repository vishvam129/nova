"""tau2-bench voice eval runner for end-to-end voice pipeline.

Each Tau2VoiceCase ships a synthesized prompt audio (or a path to one),
expected transcript snippet, and expected reply snippet.  The runner
drives the full voice pipeline (STT → brain → TTS) and scores both
ASR accuracy and reply correctness.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


class VoicePipeline(Protocol):
    """End-to-end voice agent: bytes in, (transcript, reply, audio) out."""

    def respond(self, audio: bytes) -> tuple[str, str, bytes]: ...


@dataclass(frozen=True, slots=True)
class Tau2VoiceCase:
    id: str
    audio: bytes
    expect_transcript_contains: tuple[str, ...] = ()
    expect_reply_contains: tuple[str, ...] = ()
    expect_reply_not_contains: tuple[str, ...] = ()
    category: str = "general"


@dataclass(frozen=True, slots=True)
class Tau2Outcome:
    case_id: str
    transcript: str
    reply: str
    asr_pass: bool
    reply_pass: bool
    duration_s: float


@dataclass(frozen=True, slots=True)
class Tau2Report:
    outcomes: tuple[Tau2Outcome, ...]

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def asr_pass_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(1 for o in self.outcomes if o.asr_pass) / len(self.outcomes)

    @property
    def reply_pass_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(1 for o in self.outcomes if o.reply_pass) / len(self.outcomes)

    def summary_line(self) -> str:
        return (
            f"ASR {self.asr_pass_rate * 100:.1f}% | "
            f"Reply {self.reply_pass_rate * 100:.1f}% | "
            f"{self.total} cases"
        )


def _contains_all(text: str, needles: Iterable[str]) -> bool:
    low = text.lower()
    return all(n.lower() in low for n in needles)


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


def grade_case(case: Tau2VoiceCase, transcript: str, reply: str) -> tuple[bool, bool]:
    asr_ok = (not case.expect_transcript_contains) or _contains_all(
        transcript, case.expect_transcript_contains
    )
    reply_ok = (not case.expect_reply_contains) or _contains_all(reply, case.expect_reply_contains)
    if case.expect_reply_not_contains and _contains_any(reply, case.expect_reply_not_contains):
        reply_ok = False
    return asr_ok, reply_ok


@dataclass
class Tau2VoiceRunner:
    cases: list[Tau2VoiceCase] = field(default_factory=list)

    def add(self, case: Tau2VoiceCase) -> None:
        self.cases.append(case)

    def run(self, pipeline: VoicePipeline) -> Tau2Report:
        outcomes: list[Tau2Outcome] = []
        for case in self.cases:
            t0 = time.monotonic()
            try:
                transcript, reply, _audio = pipeline.respond(case.audio)
            except Exception:  # noqa: BLE001
                outcomes.append(
                    Tau2Outcome(
                        case_id=case.id,
                        transcript="",
                        reply="",
                        asr_pass=False,
                        reply_pass=False,
                        duration_s=time.monotonic() - t0,
                    )
                )
                continue
            asr_ok, reply_ok = grade_case(case, transcript, reply)
            outcomes.append(
                Tau2Outcome(
                    case_id=case.id,
                    transcript=transcript,
                    reply=reply,
                    asr_pass=asr_ok,
                    reply_pass=reply_ok,
                    duration_s=time.monotonic() - t0,
                )
            )
        return Tau2Report(outcomes=tuple(outcomes))


def default_voice_suite() -> list[Tau2VoiceCase]:
    """Synthetic-audio placeholder cases — real ones are sampled WAVs."""
    return [
        Tau2VoiceCase(
            id="tau2-greet",
            audio=b"\x00" * 1600,
            expect_transcript_contains=("hey nova",),
            expect_reply_contains=("hi", "hello"),
        ),
        Tau2VoiceCase(
            id="tau2-time",
            audio=b"\x00" * 1600,
            expect_transcript_contains=("time",),
            expect_reply_contains=(":",),
        ),
    ]


__all__ = [
    "Tau2Outcome",
    "Tau2Report",
    "Tau2VoiceCase",
    "Tau2VoiceRunner",
    "VoicePipeline",
    "default_voice_suite",
    "grade_case",
]
