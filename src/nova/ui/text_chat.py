"""Text chat UI backend.

Backend for a text chat surface (terminal / web / native).  Holds the
shared conversation history that voice and text modes both append to,
emits events to subscribed renderers.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    via: str = "text"  # "text" or "voice"

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "via": self.via,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> ChatMessage:
        return cls(
            role=ChatRole(d["role"]),
            content=str(d["content"]),
            timestamp=datetime.fromisoformat(str(d["timestamp"])),
            via=str(d.get("via", "text")),
        )


@dataclass
class TextChat:
    """Shared chat history with pub/sub for renderers."""

    history_path: Path | None = None
    _messages: list[ChatMessage] = field(default_factory=list, init=False)
    _observers: list[Callable[[ChatMessage], None]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.history_path and self.history_path.exists():
            for line in self.history_path.read_text().splitlines():
                if line.strip():
                    self._messages.append(ChatMessage.from_dict(json.loads(line)))

    def send(self, text: str, *, via: str = "text") -> ChatMessage:
        return self._append(ChatMessage(role=ChatRole.USER, content=text, via=via))

    def receive(self, text: str, *, via: str = "text") -> ChatMessage:
        return self._append(ChatMessage(role=ChatRole.ASSISTANT, content=text, via=via))

    def system(self, text: str) -> ChatMessage:
        return self._append(ChatMessage(role=ChatRole.SYSTEM, content=text))

    def tool(self, text: str) -> ChatMessage:
        return self._append(ChatMessage(role=ChatRole.TOOL, content=text))

    def messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def filter_role(self, role: ChatRole) -> list[ChatMessage]:
        return [m for m in self._messages if m.role is role]

    def subscribe(self, observer: Callable[[ChatMessage], None]) -> None:
        self._observers.append(observer)

    def clear(self) -> None:
        self._messages.clear()
        if self.history_path and self.history_path.exists():
            self.history_path.write_text("")

    def __len__(self) -> int:
        return len(self._messages)

    def _append(self, msg: ChatMessage) -> ChatMessage:
        self._messages.append(msg)
        if self.history_path:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with self.history_path.open("a") as f:
                f.write(json.dumps(msg.to_dict()) + "\n")
        for obs in list(self._observers):
            obs(msg)
        return msg


__all__ = ["ChatMessage", "ChatRole", "TextChat"]
