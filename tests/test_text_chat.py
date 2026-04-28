"""Tests for nova.ui.text_chat."""

from __future__ import annotations

from pathlib import Path

from nova.ui.text_chat import ChatMessage, ChatRole, TextChat


def test_send_and_receive() -> None:
    chat = TextChat()
    user = chat.send("hi")
    bot = chat.receive("hello!")
    assert user.role is ChatRole.USER
    assert bot.role is ChatRole.ASSISTANT
    assert len(chat) == 2


def test_via_defaults_to_text() -> None:
    chat = TextChat()
    msg = chat.send("hi")
    assert msg.via == "text"


def test_via_voice() -> None:
    chat = TextChat()
    msg = chat.send("hi nova", via="voice")
    assert msg.via == "voice"


def test_filter_role() -> None:
    chat = TextChat()
    chat.send("a")
    chat.receive("b")
    chat.send("c")
    user_msgs = chat.filter_role(ChatRole.USER)
    assert len(user_msgs) == 2


def test_system_and_tool_messages() -> None:
    chat = TextChat()
    chat.system("warming up")
    chat.tool("ran open_app")
    assert chat.filter_role(ChatRole.SYSTEM)[0].content == "warming up"
    assert chat.filter_role(ChatRole.TOOL)[0].content == "ran open_app"


def test_subscribe_observer() -> None:
    chat = TextChat()
    seen: list[ChatMessage] = []
    chat.subscribe(seen.append)
    chat.send("x")
    chat.receive("y")
    assert len(seen) == 2


def test_persistence_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "chat.jsonl"
    c1 = TextChat(history_path=p)
    c1.send("hi")
    c1.receive("hello", via="voice")

    c2 = TextChat(history_path=p)
    msgs = c2.messages()
    assert len(msgs) == 2
    assert msgs[1].via == "voice"


def test_clear(tmp_path: Path) -> None:
    p = tmp_path / "chat.jsonl"
    chat = TextChat(history_path=p)
    chat.send("x")
    chat.clear()
    assert len(chat) == 0
    assert p.read_text() == ""


def test_message_dict_roundtrip() -> None:
    msg = ChatMessage(role=ChatRole.USER, content="hi")
    assert ChatMessage.from_dict(msg.to_dict()).content == "hi"
