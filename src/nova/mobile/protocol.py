"""Mobile ↔ Nova WebSocket protocol.

Every frame is a JSON object with a ``type`` field.  The Android client
(Kotlin) and this Python module share the same message contracts so both
sides can be updated together.

Wire format::

    { "type": "<MobileMessageType>", ...fields }

Binary audio is base64-encoded inside an ``audio_chunk`` message so the
WebSocket channel stays text-only (simpler for OkHttp + FastAPI).
"""

from __future__ import annotations

import base64
import json
from enum import StrEnum
from typing import Any


class MobileMessageType(StrEnum):
    # Client → server
    AUDIO_CHUNK = "audio_chunk"
    PAIR_REQUEST = "pair_request"
    WAKE_WORD = "wake_word"
    CANCEL = "cancel"
    PING = "ping"

    # Server → client
    TRANSCRIPT = "transcript"
    REPLY = "reply"
    STATUS = "status"
    PAIR_RESPONSE = "pair_response"
    PONG = "pong"
    ERROR = "error"


class MobileMessage:
    """Base class; subclasses add typed fields."""

    type: MobileMessageType

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MobileMessage:
        raise NotImplementedError


class AudioChunk(MobileMessage):
    """Raw PCM audio (16-bit, 16 kHz, mono) from the device mic."""

    type = MobileMessageType.AUDIO_CHUNK

    def __init__(self, pcm: bytes, sequence: int = 0) -> None:
        self.pcm = pcm
        self.sequence = sequence

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "pcm_b64": base64.b64encode(self.pcm).decode(),
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioChunk:
        pcm = base64.b64decode(data["pcm_b64"])
        return cls(pcm=pcm, sequence=data.get("sequence", 0))


class TranscriptEvent(MobileMessage):
    """Partial or final STT transcript (server → client)."""

    type = MobileMessageType.TRANSCRIPT

    def __init__(self, text: str, *, is_final: bool = False) -> None:
        self.text = text
        self.is_final = is_final

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text, "is_final": self.is_final}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptEvent:
        return cls(text=data["text"], is_final=data.get("is_final", False))


class ReplyEvent(MobileMessage):
    """Nova's spoken reply text, optionally with audio (server → client)."""

    type = MobileMessageType.REPLY

    def __init__(
        self,
        text: str,
        *,
        audio_b64: str | None = None,
        is_final: bool = True,
    ) -> None:
        self.text = text
        self.audio_b64 = audio_b64
        self.is_final = is_final

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": self.type,
            "text": self.text,
            "is_final": self.is_final,
        }
        if self.audio_b64:
            d["audio_b64"] = self.audio_b64
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplyEvent:
        return cls(
            text=data["text"],
            audio_b64=data.get("audio_b64"),
            is_final=data.get("is_final", True),
        )


class StatusEvent(MobileMessage):
    """Nova status broadcast (idle/listening/thinking/speaking/error)."""

    type = MobileMessageType.STATUS

    def __init__(self, status: str, detail: str = "") -> None:
        self.status = status
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "status": self.status, "detail": self.detail}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusEvent:
        return cls(status=data["status"], detail=data.get("detail", ""))


class PairRequest(MobileMessage):
    """Client requests to pair using an invite token from QR code."""

    type = MobileMessageType.PAIR_REQUEST

    def __init__(self, token: str, device_name: str = "") -> None:
        self.token = token
        self.device_name = device_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "token": self.token,
            "device_name": self.device_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PairRequest:
        return cls(token=data["token"], device_name=data.get("device_name", ""))


class PairResponse(MobileMessage):
    """Server accepts or rejects a pair request."""

    type = MobileMessageType.PAIR_RESPONSE

    def __init__(self, *, ok: bool, device_id: str = "", error: str = "") -> None:
        self.ok = ok
        self.device_id = device_id
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "ok": self.ok,
            "device_id": self.device_id,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PairResponse:
        return cls(
            ok=data["ok"],
            device_id=data.get("device_id", ""),
            error=data.get("error", ""),
        )


_TYPE_MAP: dict[str, type[MobileMessage]] = {
    MobileMessageType.AUDIO_CHUNK: AudioChunk,
    MobileMessageType.TRANSCRIPT: TranscriptEvent,
    MobileMessageType.REPLY: ReplyEvent,
    MobileMessageType.STATUS: StatusEvent,
    MobileMessageType.PAIR_REQUEST: PairRequest,
    MobileMessageType.PAIR_RESPONSE: PairResponse,
}


def decode_message(raw: str | bytes) -> MobileMessage:
    """Parse a JSON WebSocket frame into a typed MobileMessage."""
    data: dict[str, Any] = json.loads(raw)
    msg_type = data.get("type", "")
    cls = _TYPE_MAP.get(msg_type)
    if cls is None:
        raise ValueError(f"unknown mobile message type: {msg_type!r}")
    return cls.from_dict(data)


def encode_message(msg: MobileMessage) -> str:
    """Serialize a MobileMessage to a JSON string for the WebSocket."""
    return json.dumps(msg.to_dict())


__all__ = [
    "AudioChunk",
    "MobileMessage",
    "MobileMessageType",
    "PairRequest",
    "PairResponse",
    "ReplyEvent",
    "StatusEvent",
    "TranscriptEvent",
    "decode_message",
    "encode_message",
]
