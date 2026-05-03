"""E2E golden demo: laptop listens to meeting → phone gets action items.

Stitches MeetingSession (laptop) → ReplyEvent over the mobile protocol
(phone) and asserts the phone-bound payload contains the extracted
action items.
"""

from __future__ import annotations

import base64
import json

from nova.context.meeting import MeetingSession
from nova.mobile.protocol import ReplyEvent, decode_message, encode_message


class _ScriptedSummarizer:
    def summarize(self, text: str) -> str:
        return f"Meeting summary: {len(text.split())} words discussed."


def _build_phone_payload(session: MeetingSession) -> str:
    summary = session.summary()
    items = session.action_items()
    body = summary + "\n\nAction items:\n" + "\n".join(f"- {it}" for it in items)
    audio = base64.b64encode(b"fake-tts-audio").decode()
    msg = ReplyEvent(text=body, audio_b64=audio, is_final=True)
    return encode_message(msg)


def test_golden_meeting_to_phone_summary() -> None:
    laptop = MeetingSession(summarizer=_ScriptedSummarizer())
    laptop.add("Welcome everyone.", speaker="Alice")
    laptop.add("Bob will draft the proposal by Friday.", speaker="Alice")
    laptop.add("Carol will review the metrics dashboard next week.", speaker="Bob")
    laptop.add("Thanks, see you next Monday.", speaker="Alice")

    wire = _build_phone_payload(laptop)

    msg = decode_message(wire)
    assert isinstance(msg, ReplyEvent)
    assert "Meeting summary" in msg.text
    assert "Bob" in msg.text  # action item with owner detected
    assert "draft" in msg.text  # the actual action verb
    assert msg.audio_b64 is not None  # TTS audio rides along

    # And the wire payload is valid JSON the Android client can parse
    parsed = json.loads(wire)
    assert parsed["type"] == "reply"
    assert parsed["is_final"] is True


def test_golden_meeting_extracts_multiple_action_items() -> None:
    session = MeetingSession()
    session.add("Alice will write the spec by Tuesday.")
    session.add("We'll deploy on Friday.")
    items = session.action_items()
    assert len(items) >= 2


def test_golden_phone_payload_no_audio_when_text_only() -> None:
    session = MeetingSession()
    session.add("Quick note.")
    summary = session.summary()
    msg = ReplyEvent(text=summary)  # no audio
    parsed = json.loads(encode_message(msg))
    assert "audio_b64" not in parsed
