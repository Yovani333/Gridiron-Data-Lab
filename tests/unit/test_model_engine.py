"""Point-in-time and numeric contracts; all fixtures are offline."""

from dataclasses import replace
from datetime import date

import pytest
import polars as pl

from nfl_analytics.analysis.features import matchup_features, team_features
from nfl_analytics.analysis.engine import analyze_probability
from nfl_analytics.analysis.model_config import FEATURE_NAMES, ModelConfig
from nfl_analytics.analysis.probability import Example, evaluate_matchup, fit_model
from nfl_analytics.analysis.validation import calibration, examples_from_season, scores, walk_forward


def test_future_and_same_day_results_never_enter_features(bundle):
    cutoff = date(2024, 9, 29)
    first = matchup_features(bundle, "BUF", "MIA", as_of_date=cutoff, home_team="BUF",
                             config=ModelConfig(min_games=1))
    changed = bundle.games.with_columns(
        # The September 29 final result exists in the fixture but must not be read.
        pl.when(pl.col("game_id") == "f").then(999)
        .otherwise(pl.col("home_score")).alias("home_score")
    )
    second = matchup_features(replace(bundle, games=changed), "BUF", "MIA", as_of_date=cutoff,
                              home_team="BUF", config=ModelConfig(min_games=1))
    assert first["values"] == second["values"]
    assert first["team_a"]["games"] == second["team_a"]["games"]


def test_missing_stats_and_early_season_abstain(bundle):
    first = matchup_features(bundle, "BUF", "MIA", as_of_date="2024-09-01", home_team="BUF")
    assert not first["model_ready"]
    assert first["team_a"]["win_pct"] is None
    missing = replace(bundle, stats=replace(bundle.stats, frame=None))
    later = matchup_features(missing, "BUF", "MIA", as_of_date="2024-09-29")
    assert later["values"]["yards_per_play_diff"] is None
    assert not later["model_ready"]


def test_opponent_strength_uses_opponent_pregame_results(bundle):
    info = team_features(bundle, "BUF", as_of_date="2024-09-29", config=ModelConfig(min_games=1))
    assert info["games"] == 4
    # The initial MIA meeting has no prior MIA result. Opponents are not scored
    # using their final-season record (which would include the game itself).
    assert info["opponent_strength"] is not None


def _examples(n=12):
    config = ModelConfig(min_games=1, min_training_games=3, iterations=60)
    examples = []
    for i in range(n):
        features = {name: float(((i * (j + 2)) % 7) - 3) for j, name in enumerate(FEATURE_NAMES)}
        examples.append(Example(str(i), 2024, i // 2 + 1, date(2024, 9, i + 1), features, i % 2,
                                float(i % 2), 0.5, float(i - 6), 0.0))
    return examples, config


def test_fit_normalization_probability_and_cutoff(bundle):
    examples, config = _examples()
    model = fit_model(examples[:8], config)
    p = model.probability(examples[9].features)
    assert 0 < p < 1
    reversed_features = {k: -v for k, v in examples[9].features.items()}
    assert p + model.probability(reversed_features) == pytest.approx(1)
    assert model.trained_games == 8
    assert len(model.coefficients) == len(FEATURE_NAMES)
    with pytest.raises(ValueError, match="overlaps"):
        evaluate_matchup(model, {"as_of_date": examples[7].date}, as_of_date=examples[7].date)
    with pytest.raises(ValueError, match="Missing"):
        model.probability({})


def test_engine_produces_complementary_probabilities_from_pregame_data(bundle):
    examples, config = _examples()
    model = fit_model(examples[:8], config)
    assert analyze_probability(bundle, model, "BUF", "MIA", as_of_date="2024-09-29", home_team="BUF")["status"] == "insufficient_data"
    result = analyze_probability(bundle, model, "BUF", "MIA", as_of_date="2024-09-22", home_team="BUF")
    assert result["status"] == "retrospective_estimate"
    assert result["team_a_probability"] + result["team_b_probability"] == pytest.approx(1)
    assert result["features"]["home_field"] == 1
    assert result["power_rating_a"] is not None
    assert analyze_probability(bundle, model, "BUF", "MIA", as_of_date="2024-09-08")["status"] == "training_overlap"


def test_walk_forward_excludes_same_day_and_future_training():
    examples, config = _examples()
    result = walk_forward(examples, config)
    assert result["games"] == 8
    assert all(row["trained_through"] < row["date"] for row in result["predictions"])
    assert 0 <= result["brier"] <= 1
    assert result["benchmarks"]["always_home"] == pytest.approx(4 / 8)
    modified = [replace(e, home_win=1-e.home_win) if e.date > date(2024, 9, 9) else e for e in examples]
    original = next(r for r in result["predictions"] if r["date"] == "2024-09-09")
    replay = next(r for r in walk_forward(modified, config)["predictions"] if r["date"] == "2024-09-09")
    assert original["probability"] == replay["probability"]


def test_scores_and_empty_calibration():
    assert scores([])["brier"] is None
    assert all(bucket["games"] == 0 for bucket in calibration([]))
    result = scores([{"probability": .6, "home_win": 1}, {"probability": .2, "home_win": 0}])
    assert result["brier"] == pytest.approx(.10)
    assert result["accuracy"] == 1


def test_examples_require_pregame_sample(bundle):
    assert examples_from_season(bundle) == []
