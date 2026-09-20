"""Chronological evaluation and calibration of strictly pregame feature rows."""

from collections import defaultdict
from math import log

from nfl_analytics.data.datasets import SeasonData

from .features import matchup_features
from .model_config import FEATURE_NAMES, ModelConfig
from .probability import Example, fit_model


def examples_from_season(data: SeasonData, config: ModelConfig = ModelConfig()) -> list[Example]:
    """Build completed REG home-team rows from information dated before each game."""
    rows = data.games.filter((data.games["status"] == "result_available") &
                             (data.games["season_type"] == "REG")).sort(["date", "game_id"])
    result = []
    for game in rows.iter_rows(named=True):
        if game["home_score"] == game["away_score"]:
            continue
        features = matchup_features(data, game["home_team"], game["away_team"],
                                    as_of_date=game["date"], home_team=None if game["neutral_site"] else game["home_team"], config=config)
        if not features["model_ready"]:
            continue
        a, b = features["team_a"], features["team_b"]
        result.append(Example(game["game_id"], game["season"], game["week"], game["date"],
                              {k: features["values"][k] for k in FEATURE_NAMES},
                              int(game["home_score"] > game["away_score"]),
                              a["win_pct"], b["win_pct"], a["point_diff"], b["point_diff"],
                              {key: a[key] for key in ("win_pct", "point_diff", "yards_per_play", "turnover_margin", "opponent_strength")},
                              {key: b[key] for key in ("win_pct", "point_diff", "yards_per_play", "turnover_margin", "opponent_strength")}))
    return result


def calibration(predictions: list[dict]) -> list[dict]:
    buckets = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70),
               (0.70, 0.75), (0.75, 1.01)]
    result = []
    for low, high in buckets:
        selected = [row for row in predictions if low <= max(row["probability"], 1-row["probability"]) < high]
        result.append({"bucket": f"{int(low*100)}-{int(high*100) if high <= 1 else '100'}%",
                       "games": len(selected),
                       "mean_predicted": sum(max(r["probability"], 1-r["probability"]) for r in selected) / len(selected) if selected else None,
                       "actual_win_rate": sum(int((r["probability"] >= .5) == bool(r["home_win"])) for r in selected) / len(selected) if selected else None})
    return result


def scores(predictions: list[dict]) -> dict:
    if not predictions:
        return {"games": 0, "accuracy": None, "brier": None, "log_loss": None, "calibration": calibration([])}
    n = len(predictions)
    return {"games": n,
            "accuracy": sum(int((r["probability"] >= .5) == bool(r["home_win"])) for r in predictions) / n,
            "brier": sum((r["probability"] - r["home_win"]) ** 2 for r in predictions) / n,
            "log_loss": -sum(r["home_win"] * log(max(r["probability"], 1e-15)) +
                             (1-r["home_win"]) * log(max(1-r["probability"], 1e-15)) for r in predictions) / n,
            "calibration": calibration(predictions)}


def walk_forward(examples: list[Example], config: ModelConfig = ModelConfig(),
                 features: tuple[str, ...] = FEATURE_NAMES) -> dict:
    """Refit by week; exclude the entire evaluated week from training."""
    ordered = sorted(examples, key=lambda e: (e.date, e.game_id))
    if len({e.game_id for e in ordered}) != len(ordered):
        raise ValueError("Duplicate game_id")
    groups = defaultdict(list)
    for row in ordered:
        groups[(row.season, row.week)].append(row)
    predictions = []
    for _, games in sorted(groups.items(), key=lambda item: min(e.date for e in item[1])):
        day = min(e.date for e in games)
        training = [e for e in ordered if e.date < day]
        if len(training) < config.min_training_games or len({e.home_win for e in training}) < 2:
            continue
        model = fit_model(training, config, features)
        for game in games:
            p = model.probability(game.features)
            predictions.append({"game_id": game.game_id, "date": game.date.isoformat(),
                                "probability": p, "home_win": game.home_win,
                                "trained_through": model.trained_through.isoformat(),
                                "home_record_pick": (game.home_record or 0) >= (game.away_record or 0),
                                "home_margin_pick": (game.home_margin or 0) >= (game.away_margin or 0)})
    summary = scores(predictions)
    summary.update(model_version="model_v0_1", seasons=sorted({e.season for e in ordered}),
                   features=list(features), eligible_games=len(ordered), predictions=predictions,
                   benchmarks={name: sum(int(r[key] == bool(r["home_win"])) for r in predictions)/len(predictions) if predictions else None
                               for name, key in (("better_record", "home_record_pick"), ("better_point_diff", "home_margin_pick"))} |
                   {"always_home": sum(r["home_win"] for r in predictions)/len(predictions) if predictions else None})
    return summary


def ablation(examples: list[Example], config: ModelConfig = ModelConfig()) -> dict:
    """Evaluate each removable component on identical chronological examples."""
    return {"full": {k: v for k, v in walk_forward(examples, config).items() if k in ("games", "brier", "accuracy", "log_loss")},
            **{f"without_{name}": {k: v for k, v in walk_forward(examples, config, tuple(x for x in FEATURE_NAMES if x != name)).items()
                                       if k in ("games", "brier", "accuracy", "log_loss")}
               for name in FEATURE_NAMES}}
