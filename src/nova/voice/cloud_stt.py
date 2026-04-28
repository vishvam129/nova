"""Cloud STT backends with auto-fallback to local STT.

Two cloud providers wired in:
    - Deepgram Nova-2 (HTTP /v1/listen)
    - AssemblyAI (HTTP /v2/transcript)

When the API key is missing, the network is unreachable, or the request
fails, ``CloudStt`` silently falls back to a local ``Transcriber``.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


class _LocalTranscriber(Protocol):
    def transcribe(self, pcm: bytes) -> str: ...


@dataclass
class DeepgramSTT:
    api_key: str
    model: str = "nova-2"
    timeout_s: float = 5.0

    def transcribe(self, pcm: bytes, sample_rate: int = 16_000) -> str:
        url = f"https://api.deepgram.com/v1/listen?model={self.model}&encoding=linear16&sample_rate={sample_rate}"
        req = urllib.request.Request(
            url,
            data=pcm,
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/raw",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            data = json.loads(resp.read().decode())
        try:
            return str(data["results"]["channels"][0]["alternatives"][0]["transcript"])
        except (KeyError, IndexError):
            return ""


@dataclass
class AssemblyAISTT:
    api_key: str
    timeout_s: float = 10.0

    def transcribe(self, pcm: bytes, sample_rate: int = 16_000) -> str:
        upload = urllib.request.Request(
            "https://api.assemblyai.com/v2/upload",
            data=pcm,
            headers={"authorization": self.api_key},
        )
        with urllib.request.urlopen(upload, timeout=self.timeout_s) as resp:
            audio_url = json.loads(resp.read())["upload_url"]

        body = json.dumps({"audio_url": audio_url}).encode()
        create = urllib.request.Request(
            "https://api.assemblyai.com/v2/transcript",
            data=body,
            headers={"authorization": self.api_key, "content-type": "application/json"},
        )
        with urllib.request.urlopen(create, timeout=self.timeout_s) as resp:
            transcript_id = json.loads(resp.read())["id"]

        poll_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        for _ in range(30):
            poll = urllib.request.Request(poll_url, headers={"authorization": self.api_key})
            with urllib.request.urlopen(poll, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read())
            if data["status"] == "completed":
                return str(data.get("text", ""))
            if data["status"] == "error":
                raise RuntimeError(data.get("error", "AssemblyAI failed"))
        raise TimeoutError("AssemblyAI transcription polling timed out")


def is_online(host: str = "8.8.8.8", port: int = 53, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@dataclass
class CloudStt:
    """Tries cloud STT first, falls back to local on failure / offline."""

    local: _LocalTranscriber
    deepgram: DeepgramSTT | None = None
    assemblyai: AssemblyAISTT | None = None
    last_backend: str = field(default="", init=False)

    def transcribe(self, pcm: bytes, sample_rate: int = 16_000) -> str:
        if not is_online():
            self.last_backend = "local"
            return self.local.transcribe(pcm)
        for name, backend in (("deepgram", self.deepgram), ("assemblyai", self.assemblyai)):
            if backend is None:
                continue
            try:
                text = backend.transcribe(pcm, sample_rate=sample_rate)
                self.last_backend = name
                return text
            except (urllib.error.URLError, OSError, RuntimeError, TimeoutError):
                continue
        self.last_backend = "local"
        return self.local.transcribe(pcm)


__all__ = ["AssemblyAISTT", "CloudStt", "DeepgramSTT", "is_online"]
