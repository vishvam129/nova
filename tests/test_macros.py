"""Tests for nova.context.macros."""

from __future__ import annotations

from pathlib import Path

from nova.context.macros import Macro, MacroLibrary, MacroStep


def _morning() -> Macro:
    return Macro(
        name="morning routine",
        steps=[
            MacroStep("set lights to 80%"),
            MacroStep("play news briefing"),
            MacroStep("read calendar today", delay_ms=2000),
        ],
        aliases=["good morning", "wake up"],
    )


def test_macro_matches_name_and_alias() -> None:
    m = _morning()
    assert m.matches("morning routine") is True
    assert m.matches("good morning") is True
    assert m.matches("WAKE UP") is True
    assert m.matches("nope") is False


def test_macro_dict_roundtrip() -> None:
    m = _morning()
    out = Macro.from_dict(m.to_dict())
    assert out.name == m.name
    assert len(out.steps) == 3
    assert out.steps[2].delay_ms == 2000


def test_library_add_and_find() -> None:
    lib = MacroLibrary()
    lib.add(_morning())
    found = lib.find("good morning")
    assert found is not None
    assert found.name == "morning routine"


def test_library_find_unknown() -> None:
    assert MacroLibrary().find("ghost") is None


def test_library_remove() -> None:
    lib = MacroLibrary()
    lib.add(_morning())
    assert lib.remove("morning routine") is True
    assert lib.remove("morning routine") is False


def test_library_run_dispatches_each_step() -> None:
    lib = MacroLibrary()
    lib.add(_morning())
    seen: list[str] = []
    lib.run("good morning", lambda step: seen.append(step.description))
    assert len(seen) == 3
    assert seen[0] == "set lights to 80%"


def test_library_run_unknown_returns_empty() -> None:
    lib = MacroLibrary()
    assert lib.run("ghost", lambda step: step) == []


def test_library_persistence(tmp_path: Path) -> None:
    p = tmp_path / "macros.json"
    lib1 = MacroLibrary(path=p)
    lib1.add(_morning())

    lib2 = MacroLibrary(path=p)
    found = lib2.find("good morning")
    assert found is not None
    assert len(found.steps) == 3


def test_library_list() -> None:
    lib = MacroLibrary()
    lib.add(_morning())
    lib.add(Macro(name="evening routine", steps=[MacroStep("dim lights")]))
    assert len(lib.list()) == 2
