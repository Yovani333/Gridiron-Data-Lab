"""Versioned, explicit policy for the first retrospective probability model."""

from dataclasses import dataclass

MODEL_VERSION = "model_v0_1"

# Every training and inference row must have these measurements. Optional
# PBP/H2H/injury context is reported separately, never silently imputed.
FEATURE_NAMES = (
    "win_pct_diff", "point_diff_diff", "yards_per_play_diff",
    "turnover_margin_diff", "opponent_strength_diff", "home_field",
)


@dataclass(frozen=True)
class ModelConfig:
    recent_games: int = 5
    min_games: int = 3
    min_training_games: int = 40
    regularization: float = 0.05
    iterations: int = 200
    learning_rate: float = 0.15

    def __post_init__(self) -> None:
        if self.recent_games < 1 or self.min_games < 1 or self.min_training_games < 1:
            raise ValueError("Game counts must be positive")
        if self.regularization < 0 or self.iterations < 1 or self.learning_rate <= 0:
            raise ValueError("Invalid optimizer parameters")
