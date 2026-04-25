"""Tests for nova.mobile.protocol — mobile WebSocket message contracts."""

from __future__ import annotations

import base64

import pytest

from nova.mobile.protocol import (
    AudioChunk,
    MobileMessageType,
    PairRequest,
    PairResponse,
    ReplyEvent,
    StatusEvent,
    TranscriptEvent,
    decode_message,
    encode_message,
)


def test_audio_chunk_roundtrip() -> None:
    pcm = b"\x00\x01\x02\x03"
    msg = AudioChunk(pcm=pcm, sequence=7)
    wire = encode_message(msg)
    recovered = decode_message(wire)
    assert isinstance(recovered, AudioChunk)
    assert recovered.pcm == pcm
    assert recovered.sequence == 7


def test_audio_chunk_type_field() -> None:
    msg = AudioChunk(pcm=b"x")
    d = msg.to_dict()
    assert d["type"] == MobileMessageType.AUDIO_CHUNK
    assert "pcm_b64" in d
    assert base64.b64decode(d["pcm_b64"]) == b"x"


def test_transcript_event_roundtrip() -> None:
    msg = TranscriptEvent(text="hello world", is_final=True)
    recovered = decode_message(encode_message(msg))
    assert isinstance(recovered, TranscriptEvent)
    assert recovered.text == "hello world"
    assert recovered.is_final is True


def test_transcript_event_partial() -> None:
    msg = TranscriptEvent(text="hel")
    assert msg.is_final is False


def test_reply_event_with_audio() -> None:
    audio = base64.b64encode(b"fakeaudio").decode()
    msg = ReplyEvent(text="Hi!", audio_b64=audio, is_final=True)
    d = msg.to_dict()
    assert d["audio_b64"] == audio
    recovered = decode_message(encode_message(msg))
    assert isinstance(recovered, ReplyEvent)
    assert recovered.audio_b64 == audio


def test_reply_event_without_audio() -> None:
    msg = ReplyEvent(text="Hi!")
    d = msg.to_dict()
    assert "audio_b64" not in d


def test_status_event_roundtrip() -> None:
    msg = StatusEvent(status="listening", detail="mic open")
    recovered = decode_message(encode_message(msg))
    assert isinstance(recovered, StatusEvent)
    assert recovered.status == "listening"
    assert recovered.detail == "mic open"


def test_pair_request_roundtrip() -> None:
    msg = PairRequest(token="abc123", device_name="Pixel 8")
    recovered = decode_message(encode_message(msg))
    assert isinstance(recovered, PairRequest)
    assert recovered.token == "abc123"
    assert recovered.device_name == "Pixel 8"


def test_pair_response_ok() -> None:
    msg = PairResponse(ok=True, device_id="dev-42")
    recovered = decode_message(encode_message(msg))
    assert isinstance(recovered, PairResponse)
    assert recovered.ok is True
    assert recovered.device_id == "dev-42"
    assert recovered.error == ""


def test_pair_response_rejected() -> None:
    msg = PairResponse(ok=False, error="token expired")
    recovered = decode_message(encode_message(msg))
    assert isinstance(recovered, PairResponse)
    assert recovered.ok is False
    assert recovered.error == "token expired"


def test_decode_unknown_type_raises() -> None:
    with pytest.raises(ValueError, match="unknown mobile message type"):
        decode_message('{"type": "bogus"}')
