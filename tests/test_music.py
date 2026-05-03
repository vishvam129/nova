"""Tests for nova.integrations.music."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nova.integrations.music import (
    MusicToolHandler,
    SpotifyBackend,
    Track,
    YouTubeMusicBackend,
    list_supported_services,
)


def test_supported_services() -> None:
    assert "spotify" in list_supported_services()
    assert "youtube_music" in list_supported_services()


def test_track_to_dict() -> None:
    t = Track(title="Lofi", artist="ChilledCow", album="L1")
    assert t.to_dict()["title"] == "Lofi"


def test_yt_music_play_returns_track() -> None:
    yt = YouTubeMusicBackend(cookie_header="x")
    out = yt.play("lofi beats")
    assert out is not None
    assert "youtube" in out.artist


def test_yt_music_pause_resume_volume() -> None:
    yt = YouTubeMusicBackend(cookie_header="x")
    assert yt.pause() is True
    assert yt.resume() is True
    yt.set_volume(150)  # clamped
    assert yt.state["volume"] == 100


def test_handler_play() -> None:
    h = MusicToolHandler(backend=YouTubeMusicBackend(cookie_header="x"))
    out = h.call("music.play", query="lofi")
    assert isinstance(out, dict)
    assert out["title"] == "lofi"


def test_handler_pause() -> None:
    h = MusicToolHandler(backend=YouTubeMusicBackend(cookie_header="x"))
    assert h.call("music.pause") == {"ok": True}


def test_handler_volume() -> None:
    yt = YouTubeMusicBackend(cookie_header="x")
    h = MusicToolHandler(backend=yt)
    h.call("music.volume", level=50)
    assert yt.state["volume"] == 50


def test_handler_next_prev() -> None:
    h = MusicToolHandler(backend=YouTubeMusicBackend(cookie_header="x"))
    assert h.call("music.next") == {"ok": True}
    assert h.call("music.prev") == {"ok": True}


def test_handler_now_playing_none() -> None:
    h = MusicToolHandler(backend=YouTubeMusicBackend(cookie_header="x"))
    assert h.call("music.now_playing") is None


def test_handler_unknown_tool() -> None:
    h = MusicToolHandler(backend=YouTubeMusicBackend(cookie_header="x"))
    with pytest.raises(ValueError):
        h.call("music.bogus")


def test_spotify_pause_handles_network_error() -> None:
    s = SpotifyBackend(access_token="t")
    with patch("nova.integrations.music.urllib.request.urlopen", side_effect=OSError):
        assert s.pause() is False


def test_spotify_resume_success() -> None:
    s = SpotifyBackend(access_token="t")
    fake = MagicMock(status=204)
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("nova.integrations.music.urllib.request.urlopen", return_value=fake):
        assert s.resume() is True
