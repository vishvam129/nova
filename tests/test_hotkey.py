"""Tests for nova.ui.hotkey."""

from __future__ import annotations

import pytest

from nova.ui.hotkey import Combo, PushToTalk


def test_parse_simple() -> None:
    c = Combo.parse("Ctrl+Space")
    assert c.modifiers == frozenset({"ctrl"})
    assert c.key == "space"


def test_parse_multi_modifier() -> None:
    c = Combo.parse("Ctrl+Shift+M")
    assert c.modifiers == frozenset({"ctrl", "shift"})
    assert c.key == "m"


def test_parse_unknown_modifier_raises() -> None:
    with pytest.raises(ValueError):
        Combo.parse("Hyper+Space")


def test_parse_empty_raises() -> None:
    with pytest.raises(ValueError):
        Combo.parse("")


def test_str_canonical_form() -> None:
    c = Combo.parse("ctrl+space")
    assert str(c) == "Ctrl+Space"


def test_default_is_ctrl_space() -> None:
    p = PushToTalk()
    assert p.combo.key == "space"
    assert "ctrl" in p.combo.modifiers


def test_press_release_callbacks() -> None:
    presses, releases = [], []
    p = PushToTalk(on_press=lambda: presses.append(1), on_release=lambda: releases.append(1))
    p.press()
    p.release()
    assert presses == [1]
    assert releases == [1]
    assert p.is_held is False


def test_press_idempotent() -> None:
    presses = []
    p = PushToTalk(on_press=lambda: presses.append(1))
    p.press()
    p.press()
    assert len(presses) == 1
    assert p.is_held is True


def test_release_when_not_held_noop() -> None:
    releases = []
    p = PushToTalk(on_release=lambda: releases.append(1))
    p.release()
    assert releases == []


def test_matches_correct_combo() -> None:
    p = PushToTalk()
    assert p.matches({"ctrl"}, "space") is True
    assert p.matches({"alt"}, "space") is False
    assert p.matches({"ctrl"}, "x") is False


def test_update_combo() -> None:
    p = PushToTalk()
    p.update_combo("Alt+Shift+N")
    assert p.combo.key == "n"
    assert p.combo.modifiers == frozenset({"alt", "shift"})
