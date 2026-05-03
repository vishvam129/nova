"""Tests for nova.quality.tau2_voice."""

from __future__ import annotations

from nova.quality.tau2_voice import (
    Tau2VoiceCase,
    Tau2VoiceRunner,
    default_voice_suite,
    grade_case,
)


class _ScriptedPipeline:
    def __init__(self, transcript: str, reply: str) -> None:
        self.transcript = transcript
        self.reply = reply

    def respond(self, audio: bytes) -> tuple[str, str, bytes]:
        return self.transcript, self.reply, b"audio"


class _BoomPipeline:
    def respond(self, audio: bytes) -> tuple[str, str, bytes]:
        raise RuntimeError("oops")


def test_grade_case_both_pass() -> None:
    case = Tau2VoiceCase(
        id="x",
        audio=b"",
        expect_transcript_contains=("hey",),
        expect_reply_contains=("hello",),
    )
    asr, reply = grade_case(case, "hey nova", "hello there")
    assert asr is True
    assert reply is True


def test_grade_case_asr_fails() -> None:
    case = Tau2VoiceCase(id="x", audio=b"", expect_transcript_contains=("xyz",))
    asr, _ = grade_case(case, "no match", "")
    assert asr is False


def test_grade_case_negative_blocks_reply() -> None:
    case = Tau2VoiceCase(
        id="x",
        audio=b"",
        expect_reply_contains=("ok",),
        expect_reply_not_contains=("error",),
    )
    _, reply = grade_case(case, "", "ok but error")
    assert reply is False


def test_runner_records_outcomes() -> None:
    runner = Tau2VoiceRunner()
    runner.add(
        Tau2VoiceCase(
            id="t1",
            audio=b"x",
            expect_transcript_contains=("hi",),
            expect_reply_contains=("hello",),
        )
    )
    report = runner.run(_ScriptedPipeline("hi nova", "hello there"))
    assert report.total == 1
    assert report.asr_pass_rate == 1.0
    assert report.reply_pass_rate == 1.0


def test_runner_handles_pipeline_exception() -> None:
    runner = Tau2VoiceRunner()
    runner.add(Tau2VoiceCase(id="t1", audio=b"x"))
    report = runner.run(_BoomPipeline())
    assert report.outcomes[0].asr_pass is False


def test_default_suite_non_empty() -> None:
    suite = default_voice_suite()
    assert len(suite) >= 2
    assert all(isinstance(c, Tau2VoiceCase) for c in suite)


def test_summary_line() -> None:
    runner = Tau2VoiceRunner()
    runner.add(Tau2VoiceCase(id="t", audio=b"x"))
    report = runner.run(_ScriptedPipeline("anything", "ok"))
    line = report.summary_line()
    assert "ASR" in line
    assert "Reply" in line


def test_pass_rates_zero_when_empty() -> None:
    runner = Tau2VoiceRunner()
    report = runner.run(_ScriptedPipeline("", ""))
    assert report.asr_pass_rate == 0.0
    assert report.reply_pass_rate == 0.0
