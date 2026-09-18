"""Deterministic, regularized logistic model; training never fetches data."""

from dataclasses import asdict, dataclass
from datetime import date
import json
from math import exp, isfinite
from pathlib import Path

from .model_config import FEATURE_NAMES, MODEL_VERSION, ModelConfig


def logistic(value: float) -> float:
    if value >= 0:
        return 1 / (1 + exp(-value))
    tail = exp(value)
    return tail / (1 + tail)


@dataclass(frozen=True)
class Example:
    game_id: str
    season: int
    week: int
    date: date
    features: dict[str, float]
    home_win: int
    home_record: float | None = None
    away_record: float | None = None
    home_margin: float | None = None
    away_margin: float | None = None
    home_metrics: dict[str, float] | None = None
    away_metrics: dict[str, float] | None = None


@dataclass(frozen=True)
class FittedModel:
    version: str
    features: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    trained_games: int
    seasons: tuple[int, ...]
    trained_through: date
    config: ModelConfig
    rating_reference: dict[str, float]

    def probability(self, row: dict[str, float]) -> float:
        if any(row.get(name) is None or not isfinite(row[name]) for name in self.features):
            raise ValueError("Missing or nonfinite model feature")
        score = self.intercept + sum(weight * (row[name] - mean) / scale
                                     for name, mean, scale, weight in zip(
                                         self.features, self.means, self.scales, self.coefficients))
        return logistic(score)

    def rating(self, team: dict) -> float | None:
        """Team-only log-odds contribution relative to a training reference."""
        fields = {"win_pct_diff": "win_pct", "point_diff_diff": "point_diff",
                  "yards_per_play_diff": "yards_per_play", "turnover_margin_diff": "turnover_margin",
                  "opponent_strength_diff": "opponent_strength"}
        values = [team.get(fields[name]) for name in self.features if name in fields]
        if any(v is None or not isfinite(v) for v in values):
            return None
        return sum(self.coefficients[i] * (team[fields[name]] - self.rating_reference[name]) / self.scales[i]
                   for i, name in enumerate(self.features) if name in fields)

    def as_dict(self) -> dict:
        return {**asdict(self), "trained_through": self.trained_through.isoformat()}


def load_model(path: str | Path) -> FittedModel:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload["version"] != MODEL_VERSION or tuple(payload["features"]) != FEATURE_NAMES:
        raise ValueError("Unsupported model artifact or feature schema")
    return FittedModel(payload["version"], tuple(payload["features"]), tuple(payload["means"]),
                       tuple(payload["scales"]), tuple(payload["coefficients"]), payload["intercept"],
                       payload["trained_games"], tuple(payload["seasons"]),
                       date.fromisoformat(payload["trained_through"]), ModelConfig(**payload["config"]),
                       payload["rating_reference"])


def fit_model(examples: list[Example], config: ModelConfig = ModelConfig(),
              features: tuple[str, ...] = FEATURE_NAMES) -> FittedModel:
    if len(examples) < config.min_training_games:
        raise ValueError(f"Insufficient training games: {len(examples)}/{config.min_training_games}")
    if not features or any(name not in FEATURE_NAMES for name in features):
        raise ValueError("Unknown or empty feature set")
    if any(e.home_win not in (0, 1) or any(e.features.get(k) is None or
           not isfinite(e.features[k]) for k in features) for e in examples):
        raise ValueError("Invalid training example")
    if len({e.home_win for e in examples}) < 2:
        raise ValueError("Both outcomes are needed to fit a model")
    # Each result is represented twice during fitting, once from each team's
    # perspective. This makes home_field identifiable and enforces P(A)+P(B)=1.
    training = [(e.features, e.home_win) for e in examples] + [
        ({k: -v for k, v in e.features.items()}, 1-e.home_win) for e in examples]
    n = len(training)
    means = tuple(sum(row[k] for row, _ in training) / n for k in features)
    scales = tuple(max((sum((row[k] - m) ** 2 for row, _ in training) / n) ** 0.5, 1e-8)
                   for k, m in zip(features, means))
    rows = [tuple((row[k] - m) / s for k, m, s in zip(features, means, scales)) for row, _ in training]
    weights = [0.0] * len(features)
    intercept = 0.0
    for _ in range(config.iterations):
        grad = [0.0] * len(features)
        bias = 0.0
        for (_, outcome), row in zip(training, rows):
            error = logistic(intercept + sum(w * x for w, x in zip(weights, row))) - outcome
            bias += error
            for i, x in enumerate(row):
                grad[i] += error * x
        intercept -= config.learning_rate * bias / n
        for i in range(len(weights)):
            weights[i] -= config.learning_rate * (grad[i] / n + config.regularization * weights[i])
    reference = {}
    for key in features:
        if key == "home_field":
            continue
        metric = key.removesuffix("_diff")
        values = [row[metric] for e in examples for row in (e.home_metrics, e.away_metrics)
                  if row is not None and row.get(metric) is not None]
        reference[key] = sum(values) / len(values) if values else 0.0
    return FittedModel(MODEL_VERSION, features, means, scales, tuple(weights), intercept,
                       len(examples), tuple(sorted({e.season for e in examples})), max(e.date for e in examples), config,
                       reference)


def evaluate_matchup(model: FittedModel, features: dict, *, as_of_date: date | str) -> dict:
    cutoff = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date
    if features["as_of_date"] != cutoff or model.trained_through >= cutoff:
        raise ValueError("Model training or feature cutoff overlaps the evaluated game")
    if not features["model_ready"]:
        return {"status": "insufficient_data", "model_version": model.version}
    probability = model.probability(features["values"])
    factors = sorted(((name, model.coefficients[i] *
                       (features["values"][name] - model.means[i]) / model.scales[i])
                      for i, name in enumerate(model.features)), key=lambda item: abs(item[1]), reverse=True)
    return {"status": "retrospective_estimate", "model_version": model.version,
            "team_a_probability": probability, "team_b_probability": 1 - probability,
            "factors_a": [name for name, impact in factors if impact > 0],
            "factors_b": [name for name, impact in factors if impact < 0],
            "feature_contributions": dict(factors), "trained_games": model.trained_games,
            "trained_through": model.trained_through}
