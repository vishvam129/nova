"""Tests for BrowserSession using a FakeDriver."""

from __future__ import annotations

from dataclasses import dataclass, field

from nova.tools.builtin.browser import BrowserDriver, BrowserSession


@dataclass
class FakeDriver:
    actions: list[tuple[str, ...]] = field(default_factory=list)
    texts: dict[str, str] = field(default_factory=dict)
    closed: bool = False

    def goto(self, url: str) -> None:
        self.actions.append(("goto", url))

    def click(self, selector: str) -> None:
        self.actions.append(("click", selector))

    def fill(self, selector: str, value: str) -> None:
        self.actions.append(("fill", selector, value))

    def extract_text(self, selector: str) -> str:
        self.actions.append(("extract", selector))
        return self.texts.get(selector, "")

    def screenshot(self, path: str) -> None:
        self.actions.append(("screenshot", path))

    def close(self) -> None:
        self.closed = True


def test_driver_is_browser_driver_protocol() -> None:
    assert isinstance(FakeDriver(), BrowserDriver)


def test_navigate_calls_goto() -> None:
    d = FakeDriver()
    BrowserSession(driver=d).navigate("https://example.com")
    assert d.actions == [("goto", "https://example.com")]


def test_click_and_fill_forward() -> None:
    d = FakeDriver()
    s = BrowserSession(driver=d)
    s.click("#btn")
    s.fill("input[name=q]", "nova")
    assert d.actions == [("click", "#btn"), ("fill", "input[name=q]", "nova")]


def test_extract_returns_text() -> None:
    d = FakeDriver(texts={"h1": "Welcome"})
    assert BrowserSession(driver=d).extract("h1") == "Welcome"


def test_screenshot_and_close() -> None:
    d = FakeDriver()
    s = BrowserSession(driver=d)
    s.screenshot("/tmp/shot.png")
    s.close()
    assert ("screenshot", "/tmp/shot.png") in d.actions
    assert d.closed is True
