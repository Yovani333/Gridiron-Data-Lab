"""Future quote boundary. No network, odds provider, or fabricated default lines."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from math import isfinite
from typing import Literal

type Market = Literal["moneyline", "spread", "game_total", "team_total"]


@dataclass(frozen=True)
class MarketLine:
    game_id: str
    market: Market
    source: str
    observed_at: datetime
    team: str | None = None
    value: float | None = None
    decimal_price: float | None = None

    def __post_init__(self) -> None:
        if self.market not in ("moneyline", "spread", "game_total", "team_total"):
            raise ValueError("Unsupported market")
        if (not isinstance(self.game_id, str) or not self.game_id.strip() or
            not isinstance(self.source, str) or not self.source.strip() or
            not isinstance(self.observed_at, datetime) or self.observed_at.utcoffset() is None):
            raise ValueError("A quote needs game ID, source and timezone-aware observation time")
        for value in (self.value, self.decimal_price):
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)):
                raise ValueError("Quote values must be finite numbers")
        if self.market != "game_total" and not self.team:
            raise ValueError("This market requires an explicit team")
        if self.market == "game_total" and self.team is not None:
            raise ValueError("Game totals are not team-specific")
        if self.market == "moneyline":
            if self.decimal_price is None or self.decimal_price <= 1 or self.value is not None:
                raise ValueError("Moneyline requires a decimal price > 1, without a points line")
        elif self.value is None or (self.market != "spread" and self.value <= 0):
            raise ValueError("Spread needs a handicap; totals must be positive")
        if self.decimal_price is not None and self.decimal_price <= 1:
            raise ValueError("Decimal price must exceed 1")

    def validate_for(self, game_id: str, teams: tuple[str, str], cutoff: date) -> None:
        if self.game_id != game_id or self.team is not None and self.team not in teams:
            raise ValueError("Quote does not belong to this matchup")
        # No intraday inference without a timestamped feature cutoff.
        if self.observed_at.astimezone(timezone.utc).date() >= cutoff:
            raise ValueError("Quote was not observed before the analysis cutoff date")

    def snapshot(self) -> dict:
        result = asdict(self)
        result["observed_at"] = self.observed_at.isoformat()
        return result
