"""``browser_control`` built-in tool — a thin Playwright wrapper.

Provides navigate / click / fill / extract / screenshot over a single
persistent browser page. Playwright itself is imported lazily so the
dependency is only required when the tool actually runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BrowserDriver(Protocol):
    def goto(self, url: str) -> None: ...

    def click(self, selector: str) -> None: ...

    def fill(self, selector: str, value: str) -> None: ...

    def extract_text(self, selector: str) -> str: ...

    def screenshot(self, path: str) -> None: ...

    def close(self) -> None: ...


@dataclass
class PlaywrightDriver:
    """Real driver over Playwright's sync API."""

    headless: bool = True
    _pw: Any = None
    _browser: Any = None
    _page: Any = None

    def _ensure(self) -> Any:
        if self._page is not None:
            return self._page
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        return self._page

    def goto(self, url: str) -> None:
        self._ensure().goto(url)

    def click(self, selector: str) -> None:
        self._ensure().click(selector)

    def fill(self, selector: str, value: str) -> None:
        self._ensure().fill(selector, value)

    def extract_text(self, selector: str) -> str:
        return str(self._ensure().inner_text(selector))

    def screenshot(self, path: str) -> None:
        self._ensure().screenshot(path=path)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._pw is not None:
            self._pw.stop()
            self._pw = None
        self._page = None


@dataclass
class BrowserSession:
    """High-level API used by the agent. Accepts any ``BrowserDriver``."""

    driver: BrowserDriver

    def navigate(self, url: str) -> None:
        self.driver.goto(url)

    def click(self, selector: str) -> None:
        self.driver.click(selector)

    def fill(self, selector: str, value: str) -> None:
        self.driver.fill(selector, value)

    def extract(self, selector: str) -> str:
        return self.driver.extract_text(selector)

    def screenshot(self, path: str) -> None:
        self.driver.screenshot(path)

    def close(self) -> None:
        self.driver.close()


__all__ = ["BrowserDriver", "BrowserSession", "PlaywrightDriver"]
