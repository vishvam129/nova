"""Tests for nova.voice.cloud_stt."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nova.voice.cloud_stt import AssemblyAISTT, CloudStt, DeepgramSTT, is_online


class _Local:
    def __init__(self, text: str = "local") -> None:
        self.text = text
        self.calls = 0

    def transcribe(self, pcm: bytes) -> str:
        self.calls += 1
        return self.text


def test_offline_uses_local() -> None:
    local = _Local("offline-text")
    cloud = CloudStt(local=local, deepgram=DeepgramSTT(api_key="x"))
    with patch("nova.voice.cloud_stt.is_online", return_value=False):
        assert cloud.transcribe(b"\x00") == "offline-text"
    assert cloud.last_backend == "local"


def test_deepgram_success() -> None:
    local = _Local()
    dg = DeepgramSTT(api_key="x")
    cloud = CloudStt(local=local, deepgram=dg)
    with (
        patch("nova.voice.cloud_stt.is_online", return_value=True),
        patch.object(DeepgramSTT, "transcribe", return_value="cloud-result"),
    ):
        assert cloud.transcribe(b"\x00") == "cloud-result"
    assert cloud.last_backend == "deepgram"


def test_deepgram_fails_then_assemblyai() -> None:
    local = _Local()
    cloud = CloudStt(
        local=local,
        deepgram=DeepgramSTT(api_key="x"),
        assemblyai=AssemblyAISTT(api_key="y"),
    )
    with (
        patch("nova.voice.cloud_stt.is_online", return_value=True),
        patch.object(DeepgramSTT, "transcribe", side_effect=RuntimeError("fail")),
        patch.object(AssemblyAISTT, "transcribe", return_value="assembly-text"),
    ):
        assert cloud.transcribe(b"\x00") == "assembly-text"
    assert cloud.last_backend == "assemblyai"


def test_all_cloud_fail_falls_back_to_local() -> None:
    local = _Local("fallback")
    cloud = CloudStt(
        local=local,
        deepgram=DeepgramSTT(api_key="x"),
        assemblyai=AssemblyAISTT(api_key="y"),
    )
    with (
        patch("nova.voice.cloud_stt.is_online", return_value=True),
        patch.object(DeepgramSTT, "transcribe", side_effect=RuntimeError),
        patch.object(AssemblyAISTT, "transcribe", side_effect=OSError),
    ):
        assert cloud.transcribe(b"\x00") == "fallback"
    assert cloud.last_backend == "local"


def test_no_cloud_configured_uses_local() -> None:
    local = _Local("only-local")
    cloud = CloudStt(local=local)
    with patch("nova.voice.cloud_stt.is_online", return_value=True):
        assert cloud.transcribe(b"\x00") == "only-local"


def test_is_online_handles_socket_error() -> None:
    with patch("nova.voice.cloud_stt.socket.create_connection", side_effect=OSError):
        assert is_online() is False


def test_deepgram_parses_response() -> None:
    dg = DeepgramSTT(api_key="x")
    fake_resp = MagicMock()
    fake_resp.read.return_value = (
        b'{"results":{"channels":[{"alternatives":[{"transcript":"hello"}]}]}}'
    )
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)
    with patch("nova.voice.cloud_stt.urllib.request.urlopen", return_value=fake_resp):
        assert dg.transcribe(b"\x00") == "hello"
