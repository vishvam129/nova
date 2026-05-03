"""Music playback MCP: Spotify + YouTube Music.

Both backends share ``MusicBackend`` and the MCP-facing
``MusicToolHandler`` exposes:
    music.play          { query, service }
    music.pause
    music.resume
    music.next / .prev
    music.volume        { level }
    music.now_playing
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Track:
    title: str
    artist: str = ""
    album: str = ""
    uri: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "uri": self.uri,
        }


class MusicBackend(Protocol):
    def play(self, query: str) -> Track | None: ...
    def pause(self) -> bool: ...
    def resume(self) -> bool: ...
    def skip(self, *, forward: bool = True) -> bool: ...
    def set_volume(self, level: int) -> bool: ...
    def now_playing(self) -> Track | None: ...


@dataclass
class SpotifyBackend:
    """Web-API client; assumes a fresh user OAuth token."""

    access_token: str
    timeout_s: float = 5.0
    base_url: str = "https://api.spotify.com/v1"

    def _post(self, path: str, payload: dict[str, object] | None = None) -> bool:
        body = json.dumps(payload).encode() if payload else None
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Authorization": f"Bearer {self.access_token}"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.status in (200, 204)
        except (urllib.error.URLError, OSError):
            return False

    def play(self, query: str) -> Track | None:
        # Real impl would search via /search; tested via play() return None
        return None if not self._post("/me/player/play") else Track(title=query)

    def pause(self) -> bool:
        return self._post("/me/player/pause")

    def resume(self) -> bool:
        return self._post("/me/player/play")

    def skip(self, *, forward: bool = True) -> bool:
        path = "/me/player/next" if forward else "/me/player/previous"
        return self._post(path)

    def set_volume(self, level: int) -> bool:
        level = max(0, min(100, level))
        return self._post(f"/me/player/volume?volume_percent={level}")

    def now_playing(self) -> Track | None:
        return None


@dataclass
class YouTubeMusicBackend:
    """ytmusicapi-style client; methods left for adapter to fill in."""

    cookie_header: str
    state: dict[str, object] = field(default_factory=dict)

    def play(self, query: str) -> Track | None:
        return Track(title=query, artist="(youtube)")

    def pause(self) -> bool:
        self.state["paused"] = True
        return True

    def resume(self) -> bool:
        self.state["paused"] = False
        return True

    def skip(self, *, forward: bool = True) -> bool:
        return True

    def set_volume(self, level: int) -> bool:
        self.state["volume"] = max(0, min(100, level))
        return True

    def now_playing(self) -> Track | None:
        return None


def list_supported_services() -> Iterable[str]:
    return ("spotify", "youtube_music")


@dataclass
class MusicToolHandler:
    backend: MusicBackend

    def call(self, tool: str, **kwargs: object) -> object:
        if tool == "music.play":
            track = self.backend.play(str(kwargs.get("query", "")))
            return track.to_dict() if track else {"ok": False}
        if tool == "music.pause":
            return {"ok": self.backend.pause()}
        if tool == "music.resume":
            return {"ok": self.backend.resume()}
        if tool == "music.next":
            return {"ok": self.backend.skip(forward=True)}
        if tool == "music.prev":
            return {"ok": self.backend.skip(forward=False)}
        if tool == "music.volume":
            return {"ok": self.backend.set_volume(int(kwargs["level"]))}  # type: ignore[arg-type]
        if tool == "music.now_playing":
            t = self.backend.now_playing()
            return t.to_dict() if t else None
        raise ValueError(f"unknown music.* tool: {tool!r}")


__all__ = [
    "MusicBackend",
    "MusicToolHandler",
    "SpotifyBackend",
    "Track",
    "YouTubeMusicBackend",
    "list_supported_services",
]
