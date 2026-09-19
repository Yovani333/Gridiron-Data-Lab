"""Controlled pregame snapshots; no network, invented production data or closing-line leakage."""

from dataclasses import replace
from datetime import date, datetime, timezone

import polars as pl
import pytest

from nfl_analytics.analysis.market_analysis import factor, score_factors
from nfl_analytics.analysis.market_lines import MarketLine
from nfl_analytics.analysis.matchup import analyze_matchup
from nfl_analytics.analysis.pick_config import PickConfig
from nfl_analytics.analysis.pick_engine import analyze_picks
from nfl_analytics.analysis.pick_validation import settle_report
from nfl_analytics.data.datasets import Dataset, SeasonData
from nfl_analytics.data.games import normalize_games


@pytest.fixture
def pick_data():
    rows = []
    for i, day in enumerate(("09-01", "09-08", "09-15", "09-22", "09-29", "10-06")):
        home, away = ("BUF", "MIA") if i % 2 == 0 else ("MIA", "BUF")
        rows.append(dict(game_id=f"ab{i}", season=2024, week=i + 1, game_type="REG", gameday=f"2024-{day}",
                         home_team=home, away_team=away, home_score=30 if home == "BUF" else 10,
                         away_score=10 if home == "BUF" else 30, location="Home", div_game=1))
    for i in range(16):
        rows.append(dict(game_id=f"league{i}", season=2024, week=1, game_type="REG", gameday="2024-09-01",
                         home_team="KC", away_team="NYJ", home_score=13, away_score=7, location="Home", div_game=0))
    rows.append(dict(game_id="target", season=2024, week=8, game_type="REG", gameday="2024-10-20",
                     home_team="BUF", away_team="MIA", home_score=None, away_score=None, location="Home", div_game=1))
    schedule = normalize_games(pl.DataFrame(rows), today=date(2024, 10, 19))
    absent = Dataset(None, "unavailable", "No data")
    return SeasonData(2024, schedule, absent, absent, absent, absent, absent, datetime(2024, 10, 19, tzinfo=timezone.utc))


def report(data, **kwargs):
    matchup = analyze_matchup(data, "target")
    return analyze_picks(matchup, data.games, **kwargs)


def by_id(result, market):
    return next(c for c in result["candidates"] if c["id"] == market)


def test_four_markets_ranked_without_fake_quotes(pick_data):
    result = report(pick_data)
    assert len(result["candidates"]) == 5  # two separate team totals
    assert {c["market"] for c in result["candidates"]} == {"moneyline", "spread", "game_total", "team_total"}
    assert by_id(result, "moneyline")["selection"] == "BUF lean"
    assert by_id(result, "spread")["selection"] == "BUF side"
    assert by_id(result, "game_total")["selection"] == "Over lean"
    assert by_id(result, "team_total:BUF")["selection"] == "BUF · Over lean"
    assert result["best"] == result["ranking"][0]
    scores = [by_id(result, key)["score"] for key in result["ranking"]]
    assert scores == sorted(scores, reverse=True)
    for candidate in result["candidates"]:
        assert candidate["line"] is None and candidate["probability"] is None
        assert candidate["price_edge"] is None
        assert 0 <= candidate["score"] <= 100
        assert candidate["signed_score"] == pytest.approx(sum(f["contribution"] or 0 for f in candidate["factors"]))


def test_future_and_same_day_results_cannot_change_report(pick_data):
    before = report(pick_data)
    raw_future = pick_data.games.filter(pl.col("game_id") == "target").with_columns(
        pl.lit(99).alias("home_score"), pl.lit(0).alias("away_score"),
        pl.lit("result_available").alias("status"), pl.lit("future").alias("game_id"))
    updated = replace(pick_data, games=pl.concat([pick_data.games, raw_future], how="vertical_relaxed"))
    assert report(updated) == before


def test_early_season_empty_and_missing_reference(pick_data):
    small = replace(pick_data, games=pick_data.games.filter(pl.col("game_id").is_in(["ab0", "target"])))
    result = report(small)
    assert result["best"] is None
    assert all(c["status"] == "insufficient_data" and c["selection"] is None for c in result["candidates"])
    empty = replace(pick_data, games=pick_data.games.filter(pl.col("game_id") == "target"))
    assert all(c["status"] == "insufficient_data" for c in report(empty)["candidates"])
    no_league = report(pick_data, config=PickConfig(min_league_games=100))
    assert by_id(no_league, "game_total")["status"] == "missing_reference"
    assert by_id(no_league, "moneyline")["selection"] == "BUF lean"


def test_missing_factors_reduce_score_instead_of_inflating_it():
    config = PickConfig()
    weights = (("a", 1.0), ("b", 1.0), ("c", 1.0))
    full = [factor(k, k, 1, 0, 1) for k in ("a", "b", "c")]
    missing = [full[0], full[1], factor("c", "c", None, 0, 1)]
    assert score_factors(full, weights, 5, config)["score"] == 100
    assert score_factors(missing, weights, 5, config)["score"] == pytest.approx(66.7)
    assert score_factors(full, weights, 3, config)["score"] == 60


def test_neutral_site_does_not_award_home_away_points(pick_data):
    neutral = replace(pick_data, games=pick_data.games.with_columns(
        pl.when(pl.col("game_id") == "target").then(True).otherwise(pl.col("neutral_site")).alias("neutral_site")))
    result = report(neutral)
    for candidate in result["candidates"]:
        venue = next(f for f in candidate["factors"] if f["key"] == "venue")
        assert venue["contribution"] is None


def quote(market, team=None, value=None, **kwargs):
    return MarketLine("target", market, "test fixture", datetime(2024, 10, 19, tzinfo=timezone.utc), team, value, **kwargs)


def test_real_handicap_is_compared_not_invented(pick_data):
    result = report(pick_data, lines=(quote("spread", "MIA", 3.5),))
    candidate = by_id(result, "spread")
    assert candidate["selection"] == "BUF -3.5"
    assert candidate["status"] == "market_candidate"
    assert candidate["baseline"] == 3.5
    assert candidate["point_reference"] == 20
    # Better winner conditions do not imply covering an arbitrarily large handicap.
    large = by_id(report(pick_data, lines=(quote("spread", "BUF", -40),)), "spread")
    assert large["selection"] == "MIA +40"


def test_line_changes_total_direction_and_no_edge_near_reference(pick_data):
    above = by_id(report(pick_data, lines=(quote("game_total", value=60),)), "game_total")
    assert above["selection"] == "Under 60"
    equal = by_id(report(pick_data, lines=(quote("game_total", value=40),)), "game_total")
    assert equal["selection"] is None and equal["status"] == "no_strong_signal"
    tt = by_id(report(pick_data, lines=(quote("team_total", "BUF", 20),)), "team_total:BUF")
    assert tt["selection"] == "BUF · Over 20"


def test_quote_provenance_validation(pick_data):
    with pytest.raises(ValueError, match="before"):
        report(pick_data, lines=(replace(quote("spread", "BUF", -3.5), observed_at=datetime(2024, 10, 20, tzinfo=timezone.utc)),))
    with pytest.raises(ValueError, match="matchup"):
        report(pick_data, lines=(replace(quote("spread", "BUF", -3.5), game_id="different"),))
    with pytest.raises(ValueError, match="Only one"):
        report(pick_data, lines=(quote("game_total", value=40), quote("game_total", value=41)))
    with pytest.raises(ValueError):
        quote("spread", "BUF", float("nan"))
    with pytest.raises(ValueError):
        quote("moneyline", "BUF", decimal_price=1)


def test_moneyline_price_does_not_create_a_probability(pick_data):
    candidate = by_id(report(pick_data, lines=(quote("moneyline", "BUF", decimal_price=1.8),)), "moneyline")
    assert candidate["selection"] == "BUF ML @ 1.8"
    assert candidate["probability"] is None and candidate["price_edge"] is None
    other = by_id(report(pick_data, lines=(quote("moneyline", "MIA", decimal_price=1.8),)), "moneyline")
    assert other["status"] == "statistical_lean" and other["selection"] == "BUF lean"


def test_postseason_does_not_implicitly_use_regular_policy(pick_data):
    post = replace(pick_data, games=pick_data.games.with_columns(
        pl.when(pl.col("game_id") == "target").then(pl.lit("POST")).otherwise(pl.col("season_type")).alias("season_type")))
    assert all(c["status"] == "unsupported_season_type" for c in report(post)["candidates"])


def test_same_day_injuries_are_context_only(pick_data):
    injuries = pl.DataFrame({"season": [2024, 2024], "week": [8, 8], "team": ["BUF", "BUF"],
                            "gsis_id": ["prior", "late"], "position": ["QB", "WR"],
                            "date_modified": [datetime(2024, 10, 19, tzinfo=timezone.utc), datetime(2024, 10, 20, tzinfo=timezone.utc)]})
    data = replace(pick_data, injuries=Dataset(injuries, "available", ""))
    result = report(data)
    assert result["injuries"]["BUF"] == {"status": "dated_reports_only", "reports": 1, "positions": ["QB"], "scored": False}
    assert result["candidates"] == report(pick_data)["candidates"]


def test_frozen_report_settlement_keeps_pushes_and_reference_types(pick_data):
    frozen = report(pick_data, lines=(quote("spread", "BUF", -3),))
    result = {"game_id": "target", "home_team": "BUF", "away_team": "MIA", "home_score": 23, "away_score": 20}
    settled = settle_report(frozen, result)
    spread = next(row for row in settled if row["id"] == "spread")
    assert spread["outcome"] == "push" and spread["reference_kind"] == "market_line"
    total = next(row for row in settled if row["id"] == "game_total")
    assert total["reference_kind"] == "pregame_league_average"
    assert settle_report(frozen, {**result, "home_score": None}) == []


def test_balanced_evidence_does_not_force_any_pick(pick_data):
    data = replace(pick_data, games=pick_data.games.with_columns(
        pl.when(pl.col("game_id") != "target").then(20).otherwise(pl.col("home_score")).alias("home_score"),
        pl.when(pl.col("game_id") != "target").then(20).otherwise(pl.col("away_score")).alias("away_score")))
    result = report(data)
    assert result["best"] is None and result["ranking"] == []
    assert all(c["status"] == "no_strong_signal" for c in result["candidates"])


def test_matchup_ui_renders_real_report_structure(monkeypatch, pick_data):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from nfl_analytics.presentation import dashboard, service
    monkeypatch.setattr(service, "initialize", lambda: None)
    monkeypatch.setattr(service, "history", lambda: pick_data.games)
    monkeypatch.setattr(dashboard, "available_seasons", lambda: [2024])
    monkeypatch.setattr(dashboard, "calendar", lambda season: pick_data.games)
    monkeypatch.setattr(dashboard, "analysis_data", lambda season, include_pbp: pick_data)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "scripts/run_dashboard.py"), default_timeout=30)
    app.session_state["selected_game"] = "target"
    app.run()
    assert not app.exception
    assert any(item.value == "BUF lean" for item in app.subheader)
    assert any(item.value == "BUF side" for item in app.subheader)
    assert any("Mejor coincidencia estadística" in item.value for item in app.markdown)
    assert sum(item.label == "Ver contribuciones y cobertura" for item in app.expander) == 5
