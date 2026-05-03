"""Multi-user support: profiles, memory namespaces, voice-print routing.

Each user gets:
    - a unique profile (display name, locale)
    - an isolated memory directory (~/.local/share/nova/users/<id>)
    - a voice-print enrolment in the SpeakerVerifier (delegated)

UserRouter resolves an incoming utterance → User by speaker verification,
falling back to an explicit ``current_user`` for text-only sessions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

_DEFAULT_ROOT = Path("~/.local/share/nova/users").expanduser()


@dataclass(frozen=True, slots=True)
class UserProfile:
    id: str
    display_name: str
    locale: str = "en-US"
    is_admin: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "locale": self.locale,
            "is_admin": self.is_admin,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> UserProfile:
        return cls(
            id=str(d["id"]),
            display_name=str(d["display_name"]),
            locale=str(d.get("locale", "en-US")),
            is_admin=bool(d.get("is_admin", False)),
        )


@dataclass
class UserStore:
    """JSON-backed user directory + per-user memory dirs."""

    root: Path = field(default_factory=lambda: _DEFAULT_ROOT)
    _users: dict[str, UserProfile] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        index = self.root / "users.json"
        if index.exists():
            for entry in json.loads(index.read_text() or "[]"):
                profile = UserProfile.from_dict(entry)
                self._users[profile.id] = profile

    def create(
        self, display_name: str, *, locale: str = "en-US", is_admin: bool = False
    ) -> UserProfile:
        profile = UserProfile(
            id=uuid4().hex[:12],
            display_name=display_name,
            locale=locale,
            is_admin=is_admin,
        )
        self._users[profile.id] = profile
        self.user_dir(profile.id).mkdir(parents=True, exist_ok=True)
        self._save()
        return profile

    def get(self, user_id: str) -> UserProfile | None:
        return self._users.get(user_id)

    def list(self) -> list[UserProfile]:
        return list(self._users.values())

    def by_name(self, name: str) -> UserProfile | None:
        n = name.lower().strip()
        for u in self._users.values():
            if u.display_name.lower() == n:
                return u
        return None

    def user_dir(self, user_id: str) -> Path:
        return self.root / user_id

    def memory_dir(self, user_id: str) -> Path:
        path = self.user_dir(user_id) / "memory"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def delete(self, user_id: str) -> bool:
        if user_id not in self._users:
            return False
        del self._users[user_id]
        self._save()
        return True

    def _save(self) -> None:
        (self.root / "users.json").write_text(
            json.dumps([u.to_dict() for u in self._users.values()], indent=2)
        )


@dataclass
class UserRouter:
    """Resolve incoming audio / text to a UserProfile."""

    store: UserStore
    voice_user_map: dict[str, str] = field(default_factory=dict)
    current_user_id: str = ""

    def map_voice_print(self, voice_id: str, user_id: str) -> None:
        self.voice_user_map[voice_id] = user_id

    def for_voice(self, voice_id: str) -> UserProfile | None:
        uid = self.voice_user_map.get(voice_id)
        return self.store.get(uid) if uid else None

    def for_text(self) -> UserProfile | None:
        return self.store.get(self.current_user_id) if self.current_user_id else None

    def resolve(self, *, voice_id: str | None = None) -> UserProfile | None:
        if voice_id:
            via_voice = self.for_voice(voice_id)
            if via_voice:
                return via_voice
        return self.for_text()


__all__ = ["UserProfile", "UserRouter", "UserStore"]
