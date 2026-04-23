"""Tests for TrayController (display-free)."""

from __future__ import annotations

from nova.ui.tray import MenuItem, TrayController, TrayStatus


def test_default_status_is_idle() -> None:
    t = TrayController()
    assert t.status is TrayStatus.IDLE


def test_set_status_notifies_observers() -> None:
    t = TrayController()
    seen: list[TrayStatus] = []
    t.subscribe(lambda s: seen.append(s))
    t.set_status(TrayStatus.LISTENING)
    t.set_status(TrayStatus.THINKING)
    assert seen == [TrayStatus.LISTENING, TrayStatus.THINKING]


def test_tooltip_reflects_status_and_last_action() -> None:
    t = TrayController(title="Nova")
    t.set_status(TrayStatus.SPEAKING)
    t.note_action("said hello")
    tt = t.tooltip()
    assert "speaking" in tt
    assert "said hello" in tt


def test_add_item_and_menu() -> None:
    t = TrayController()
    fired: list[str] = []
    t.add_item(MenuItem("Quit", lambda: fired.append("q")))
    t.add_item(MenuItem("Settings", lambda: fired.append("s")))
    menu = t.menu()
    assert [m.label for m in menu] == ["Quit", "Settings"]
    menu[0].action()
    menu[1].action()
    assert fired == ["q", "s"]


def test_tooltip_without_action_uses_short_form() -> None:
    t = TrayController(title="Nova")
    assert t.tooltip() == "Nova — idle"
