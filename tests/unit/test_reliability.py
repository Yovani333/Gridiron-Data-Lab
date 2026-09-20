from dataclasses import replace
from datetime import datetime, timezone

import polars as pl
import pytest

from nfl_analytics.analysis.form import head_to_head
from nfl_analytics.analysis.matchup import analyze_matchup
from nfl_analytics.analysis.play_by_play import advanced_summary
from nfl_analytics.analysis.possessions import drive_summary
from nfl_analytics.analysis.pick_backtest import evaluate_picks, save_report
from nfl_analytics.data.games import recent_games
from nfl_analytics.data.players import injury_reports


def test_same_day_injury_is_never_historical():
    frame = pl.DataFrame({"season": [2024], "week": [1], "team": ["BUF"], "gsis_id": ["p"],
                          "date_modified": [datetime(2024, 9, 8, 23, 59, tzinfo=timezone.utc)]})
    assert injury_reports(frame, "BUF", 1, as_of="2024-09-08").is_empty()


def test_h2h_filters_season_type_before_limit(games):
    frame = games.with_columns(pl.when(pl.col("game_id") == "f").then(pl.lit("POST")).otherwise(pl.col("season_type")).alias("season_type"))
    result = head_to_head(frame, "BUF", "MIA", 1, before="2024-10-01", season_type="REG")
    assert result["games"]["game_id"].to_list() == ["b"]


def test_duplicate_pbp_is_rejected(games, pbp):
    with pytest.raises(ValueError, match="unique"):
        advanced_summary(pl.concat([pbp, pbp.head(1)]), recent_games(games, "BUF", 1, before="2024-09-08"), "BUF")


def test_drive_points_and_unknown_results():
    frame = pl.DataFrame({"game_id": ["a"] * 5, "posteam": ["BUF"] * 5,
                          "fixed_drive": [1, 1, 2, 3, 4], "play_type": ["pass"] * 5,
                          "fixed_drive_result": ["Touchdown", "Touchdown", "Field goal", "Opp touchdown", "Punt"]})
    result = drive_summary(frame)
    assert result["drives"] == 4
    assert result["drive_points"] == 9
    assert result["points_per_drive"] == 2.25
    assert drive_summary(frame.with_columns(pl.lit(None).alias("fixed_drive_result")))["points_per_drive"] is None


def test_context_rest_and_missing_efficiency(bundle):
    data = replace(bundle, games=bundle.games.with_columns(pl.lit(10).alias("home_rest"), pl.lit(7).alias("away_rest")))
    report = analyze_matchup(data, "c")
    assert report["contextual_metrics"]["rest_days"]["difference"] == 3
    assert all(row["difference"] is None for row in report["contextual_metrics"]["efficiency"])


def test_neutral_site_training_does_not_set_home_advantage(bundle, monkeypatch):
    from nfl_analytics.analysis import validation
    captured = {}
    def features(data, a, b, **kwargs):
        captured[kwargs["as_of_date"].isoformat()] = kwargs["home_team"]
        return {"model_ready": False}
    monkeypatch.setattr(validation, "matchup_features", features)
    validation.examples_from_season(bundle)
    assert captured["2024-09-22"] is None
    assert captured["2024-09-01"] == "BUF"


def test_backtest_accounts_for_abstentions_and_no_future_inputs(bundle, tmp_path):
    report = evaluate_picks(bundle)
    dates = dict(zip(bundle.games["game_id"], bundle.games["date"]))
    for row in report["decisions"]:
        assert all(dates[key].isoformat() < row["date"] for ids in row["input_game_ids"].values() for key in ids)
    for row in report["summaries"]:
        assert row["opportunities"] == row["issued"] + row["abstentions"]
        assert row["issued"] == row["favorable"] + row["unfavorable"] + row["pushes"]
    altered = replace(bundle, games=bundle.games.with_columns(pl.when(pl.col("game_id") == "f").then(999).otherwise(pl.col("home_score")).alias("home_score")))
    replay = evaluate_picks(altered)
    assert [{k:v for k,v in r.items() if k not in ("outcome", "benchmark_outcomes")} for r in report["decisions"]] == [{k:v for k,v in r.items() if k not in ("outcome", "benchmark_outcomes")} for r in replay["decisions"]]
    path = tmp_path / "report.json"
    save_report(report, path)
    with pytest.raises(FileExistsError):
        save_report(report, path)
