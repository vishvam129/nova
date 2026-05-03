"""Tests for nova.ui.command_palette."""

from __future__ import annotations

from nova.ui.command_palette import Command, CommandPalette


def test_register_and_query_exact_name() -> None:
    p = CommandPalette()
    p.register(Command(name="settings", description="Open settings", action=lambda x: x))
    out = p.query("settings")
    assert out[0][0] == "settings"


def test_query_prefix_match() -> None:
    p = CommandPalette()
    p.register(Command(name="settings", description="x", action=lambda x: x))
    p.register(Command(name="search", description="x", action=lambda x: x))
    out = [name for name, _ in p.query("set")]
    assert out[0] == "settings"


def test_query_substring_match() -> None:
    p = CommandPalette()
    p.register(Command(name="quit", description="exit", action=lambda x: x))
    out = [name for name, _ in p.query("qui")]
    assert "quit" in out


def test_query_keyword_match() -> None:
    p = CommandPalette()
    p.register(
        Command(
            name="memory.export", description="x", action=lambda x: x, keywords=("download", "json")
        )
    )
    out = [name for name, _ in p.query("download")]
    assert "memory.export" in out


def test_query_limit() -> None:
    p = CommandPalette()
    for i in range(20):
        p.register(Command(name=f"cmd-{i}", description="x", action=lambda x: x))
    assert len(p.query("cmd", limit=5)) == 5


def test_remember_and_recent_match() -> None:
    p = CommandPalette()
    p.remember("draft an email to alice")
    out = [name for name, _ in p.query("draft")]
    assert "draft an email to alice" in out


def test_remember_dedupes() -> None:
    p = CommandPalette()
    p.remember("hi")
    p.remember("hi")
    assert p.recent == ["hi"]


def test_remember_capped() -> None:
    p = CommandPalette(max_recent=3)
    for i in range(5):
        p.remember(f"prompt-{i}")
    assert len(p.recent) == 3


def test_execute_known_command() -> None:
    fired: list[str] = []
    p = CommandPalette()
    p.register(Command(name="play", description="x", action=fired.append))
    p.execute("play")
    assert fired == ["play"]


def test_execute_unknown_falls_back_to_free_prompt() -> None:
    fired: list[str] = []
    p = CommandPalette()
    p.register(
        Command(name="ask", description="ask brain", action=fired.append, keywords=("free_prompt",))
    )
    p.execute("what is 2+2?")
    assert fired == ["what is 2+2?"]


def test_execute_no_handler_just_remembers() -> None:
    p = CommandPalette()
    p.execute("never seen")
    assert p.recent[0] == "never seen"
