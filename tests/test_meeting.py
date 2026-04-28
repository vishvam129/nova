"""Tests for nova.context.meeting."""

from __future__ import annotations

from nova.context.meeting import (
    ActionItem,
    MeetingSession,
    extract_action_items,
)


class _FakeSummarizer:
    def summarize(self, text: str) -> str:
        return f"SUMMARY({len(text)} chars)"


def test_extract_action_items_basic() -> None:
    text = "Alice will draft the proposal by Friday. Bob is fine. We'll review next week."
    items = extract_action_items(text)
    assert len(items) >= 2
    assert any("draft" in it.text for it in items)


def test_action_item_owner_detected() -> None:
    text = "Alice will write the report."
    items = extract_action_items(text)
    assert items[0].owner == "Alice"


def test_action_item_due_detected() -> None:
    text = "We'll ship the feature by Monday."
    items = extract_action_items(text)
    assert items[0].due.lower().startswith("monday")


def test_action_item_str() -> None:
    a = ActionItem(text="ship feature", owner="Alice", due="Monday")
    s = str(a)
    assert "ship feature" in s
    assert "Alice" in s
    assert "Monday" in s


def test_meeting_session_transcript() -> None:
    s = MeetingSession()
    s.add("Hi", speaker="Alice")
    s.add("Hello", speaker="Bob")
    out = s.transcript()
    assert "Alice: Hi" in out
    assert "Bob: Hello" in out


def test_meeting_session_skips_empty() -> None:
    s = MeetingSession()
    s.add("")
    s.add("   ")
    assert s.transcript() == ""


def test_meeting_session_action_items() -> None:
    s = MeetingSession()
    s.add("We will deploy by Friday")
    s.add("Bob will review the PR.")
    items = s.action_items()
    assert len(items) >= 1


def test_meeting_session_summary_with_summarizer() -> None:
    s = MeetingSession(summarizer=_FakeSummarizer())
    s.add("hello world")
    out = s.summary()
    assert out.startswith("SUMMARY(")


def test_meeting_session_summary_without_summarizer() -> None:
    s = MeetingSession()
    s.add("a" * 1000)
    assert len(s.summary()) <= 500


def test_meeting_session_reset() -> None:
    s = MeetingSession()
    s.add("x")
    s.reset()
    assert s.transcript() == ""


def test_no_action_words_returns_empty() -> None:
    items = extract_action_items("The weather is nice today. Hello world.")
    assert items == []
