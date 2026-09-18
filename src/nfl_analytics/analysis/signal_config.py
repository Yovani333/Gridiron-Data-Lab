"""Explicit heuristic weights; these are not fitted or calibrated probabilities."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SignalConfig:
    recent_games: int = 5
    min_games: int = 3
    min_split_games: int = 2
    min_h2h_games: int = 3
    weights: dict[str, float] = field(default_factory=lambda: {
        "recent_form": 1.0,
        "point_differential": 1.0,
        "offense": 1.0,
        "defense": 1.0,
        "home_away": 1.0,
        "head_to_head": 0.5,
    })
    medium_threshold: float = 2.0
    high_threshold: float = 3.5

    def __post_init__(self) -> None:
        if self.recent_games < 1 or self.min_games < 1 or self.min_split_games < 1:
            raise ValueError("Game minimums must be positive")
        if not 0 < self.medium_threshold < self.high_threshold:
            raise ValueError("Signal thresholds must be ordered and positive")
        if any(value <= 0 for value in self.weights.values()):
            raise ValueError("Signal weights must be positive")
