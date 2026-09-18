"""Model inference from a caller-supplied data snapshot and trained artifact."""

from datetime import date

from nfl_analytics.data.datasets import SeasonData
from nfl_analytics.data.games import as_date

from .features import matchup_features
from .probability import FittedModel, evaluate_matchup


def analyze_probability(data: SeasonData, model: FittedModel, team_a: str, team_b: str,
                        *, as_of_date: date | str, home_team: str | None = None) -> dict:
    """Abstain on training overlap or insufficient same-season pregame history."""
    cutoff = as_date(as_of_date)
    if model.trained_through >= cutoff:
        return {"status": "training_overlap", "model_version": model.version}
    features = matchup_features(data, team_a, team_b, as_of_date=cutoff, home_team=home_team,
                                config=model.config)
    result = evaluate_matchup(model, features, as_of_date=cutoff)
    if result["status"] == "retrospective_estimate":
        result["power_rating_a"] = model.rating(features["team_a"])
        result["power_rating_b"] = model.rating(features["team_b"])
        result["context"] = features["context"]
        result["features"] = features["values"]
    return result
