"""Versioned heuristic policy. All scores are indices, never probabilities."""

from dataclasses import dataclass
from math import isfinite

PICK_VERSION = "statistical_leans_v0_2"


@dataclass(frozen=True)
class PickConfig:
    min_games: int = 3
    full_sample: int = 5
    min_split_games: int = 2
    min_league_games: int = 16
    min_factors: int = 3
    min_h2h_games: int = 3
    h2h_games: int = 5
    h2h_seasons: int = 3
    trend_recent_games: int = 3
    trend_older_games: int = 2
    min_score: float = 20.0
    margin_scale: float = 14.0
    points_scale: float = 7.0
    win_rate_scale: float = 0.5
    yards_scale: float = 2.0
    venue_share: float = 0.25
    line_buffer: float = 2.0
    side_weights: tuple[tuple[str, float], ...] = (
        ("margin", 1.0), ("offense", 0.5), ("defense", 0.5),
        ("record", 0.75), ("venue", 0.5), ("h2h", 0.25),
        ("last_game", 0.25), ("trend", 0.5), ("efficiency", 0.5),
    )
    points_weights: tuple[tuple[str, float], ...] = (
        ("offense", 1.0), ("defense", 1.0), ("venue", 0.5),
        ("h2h", 0.25), ("last_game", 0.25),
    )

    def __post_init__(self) -> None:
        counts = (self.min_games, self.full_sample, self.min_split_games,
                  self.min_league_games, self.min_factors, self.min_h2h_games, self.h2h_games, self.h2h_seasons,
                  self.trend_recent_games, self.trend_older_games)
        if any(type(n) is not int or n < 1 for n in counts) or self.full_sample < self.min_games:
            raise ValueError("Sample sizes must be positive integers; full_sample >= min_games")
        for scale in (self.margin_scale, self.points_scale, self.win_rate_scale, self.yards_scale, self.line_buffer):
            if not isfinite(scale) or scale <= 0:
                raise ValueError("Scales and buffers must be finite and positive")
        if not 0 <= self.venue_share <= 1 or not 0 < self.min_score <= 100:
            raise ValueError("Invalid venue share or score threshold")
        for weights in (self.side_weights, self.points_weights):
            if len(dict(weights)) != len(weights) or any(not isfinite(w) or w <= 0 for _, w in weights):
                raise ValueError("Weights must have unique keys and finite positive values")
        if set(dict(self.side_weights)) != {"margin", "offense", "defense", "record", "venue", "h2h", "last_game", "trend", "efficiency"}:
            raise ValueError("Unexpected side factors")
        if set(dict(self.points_weights)) != {"offense", "defense", "venue", "h2h", "last_game"}:
            raise ValueError("Unexpected points factors")
