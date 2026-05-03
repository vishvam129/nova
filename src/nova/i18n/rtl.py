"""Right-to-left language rendering helpers.

Pure data — every UI surface (tray, overlay HUD, command palette, text
chat) consults ``is_rtl(lang)`` and ``direction(lang)`` to set its
text-direction attribute / CSS rule.  Mixed-direction text gets wrapped
with Unicode bidi controls via ``wrap_bidi``.
"""

from __future__ import annotations

_RTL_LANGUAGES: frozenset[str] = frozenset(
    {
        "ar",  # Arabic
        "fa",  # Persian / Farsi
        "he",  # Hebrew
        "ur",  # Urdu
        "ps",  # Pashto
        "sd",  # Sindhi
        "yi",  # Yiddish
        "dv",  # Dhivehi
        "ckb",  # Sorani Kurdish
    }
)

_RLE = "‫"  # right-to-left embedding
_LRE = "‪"  # left-to-right embedding
_PDF = "‬"  # pop directional formatting


def is_rtl(language_code: str) -> bool:
    """Return True if *language_code* is a right-to-left script."""
    if not language_code:
        return False
    primary = language_code.split("-")[0].split("_")[0].lower()
    return primary in _RTL_LANGUAGES


def direction(language_code: str) -> str:
    """Return CSS-style direction: 'rtl' or 'ltr'."""
    return "rtl" if is_rtl(language_code) else "ltr"


def html_dir_attr(language_code: str) -> str:
    """Return the dir="…" attribute fragment for HTML/Compose surfaces."""
    return f'dir="{direction(language_code)}"'


def wrap_bidi(text: str, language_code: str) -> str:
    """Wrap *text* in Unicode bidi controls so neighbouring opposite-script
    text doesn't visually merge with it."""
    if is_rtl(language_code):
        return f"{_RLE}{text}{_PDF}"
    return f"{_LRE}{text}{_PDF}"


def supported_rtl_languages() -> list[str]:
    return sorted(_RTL_LANGUAGES)


__all__ = [
    "direction",
    "html_dir_attr",
    "is_rtl",
    "supported_rtl_languages",
    "wrap_bidi",
]
