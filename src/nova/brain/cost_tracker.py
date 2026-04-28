"""Daily cost/token tracker with cap enforcement.

When the daily cap is hit, ``check()`` returns False — the router should
then skip cloud backends and route everything to local models.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Approximate $/1k tokens for common models (input+output blended)
_DEFAULT_PRICES = {
    "claude-opus-4-7": 0.020,
    "claude-sonnet-4-6": 0.005,
    "gpt-4o": 0.010,
    "gemini-1.5-pro": 0.007,
    "deepgram": 0.0043,
    "assemblyai": 0.012,
}


@dataclass
class CostTracker:
    """Tracks per-day USD spend; blocks once daily_cap_usd is exceeded."""

    daily_cap_usd: float = 1.00
    state_path: Path = field(
        default_factory=lambda: Path("~/.local/share/nova/cost.json").expanduser()
    )
    prices: dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_PRICES))

    _today: str = field(default="", init=False)
    _spend: float = field(default=0.0, init=False)
    _tokens: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        self._today = date.today().isoformat()
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                if data.get("date") == self._today:
                    self._spend = float(data.get("spend_usd", 0.0))
                    self._tokens = int(data.get("tokens", 0))
                    return
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        self._spend = 0.0
        self._tokens = 0

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps({"date": self._today, "spend_usd": self._spend, "tokens": self._tokens})
        )

    def record(self, model: str, tokens: int) -> None:
        if date.today().isoformat() != self._today:
            self._load()
        price = self.prices.get(model, 0.0)
        self._spend += (tokens / 1000) * price
        self._tokens += tokens
        self._save()

    def check(self) -> bool:
        """Return True if more spend is allowed today, False if capped."""
        return self._spend < self.daily_cap_usd

    @property
    def spend_usd(self) -> float:
        return self._spend

    @property
    def tokens(self) -> int:
        return self._tokens

    def remaining_usd(self) -> float:
        return max(0.0, self.daily_cap_usd - self._spend)

    def reset(self) -> None:
        self._spend = 0.0
        self._tokens = 0
        self._save()


__all__ = ["CostTracker"]
