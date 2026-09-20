"""Hand-computed fixtures cover the meaning of metrics, not just their shape."""

from datetime import date, datetime, timezone

import polars as pl
import pytest

from nfl_analytics.analysis.form import recent_form, head_to_head
from nfl_analytics.analysis.matchup import analyze_matchup, compare_teams
from nfl_analytics.analysis.play_by_play import advanced_summary
from nfl_analytics.analysis.team_stats import box_score_summary
from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import optional_dataset
from nfl_analytics.data.games import games_by_date, games_by_week, normalize_games, recent_games, team_games
from nfl_analytics.data.players import attach_players, injury_reports
from nfl_analytics.data.stats import normalize_team_stats


def test_date_week_and_empty(games):
    assert games_by_date(games, "2024-09-08").get_column("game_id").to_list() == ["b"]
    assert games_by_week(games, 3).get_column("game_id").to_list() == ["c"]
    assert games_by_date(games, "2024-09-16").is_empty()
    with pytest.raises(ValueError):
        games_by_date(games, "not-a-date")
    for invalid in (True, 0, 23, "3"):
        with pytest.raises(ValueError):
            games_by_week(games, invalid)


def test_scores_ties_pending(games):
    rows = {r["game_id"]: r for r in games.to_dicts()}
    assert rows["a"]["winner"] == "BUF" and rows["a"]["margin"] == 10
    assert rows["b"]["winner"] is None and rows["b"]["margin"] == 0
    assert rows["e"]["status"] == "awaiting_update" and rows["e"]["margin"] is None


def test_form_and_cutoff(games):
    form = recent_form(games, "buf", 3, before="2024-09-22")
    assert form == {"games": 3, "wins": 1, "losses": 1, "ties": 1, "win_pct": 1 / 3, "standings_pct": .5,
                    "points_for": 68, "points_against": 65, "points_per_game": 68 / 3,
                    "points_allowed_per_game": 65 / 3, "point_diff": 3, "avg_margin": 1.0}
    assert recent_games(games, "BUF", 1, before="2024-09-22")["game_id"].to_list() == ["c"]
    assert recent_form(games, "BUF", None, before="2024-09-01")["points_per_game"] is None
    assert recent_form(games, "BUF", 1, before="2024-09-22")["losses"] == 1
    for invalid in (True, 0, -1, "5"):
        with pytest.raises(ValueError):
            recent_games(games, "BUF", invalid)
    with pytest.raises(ValueError):
        team_games(games, "INVALID")


def test_splits_exclude_neutral(games):
    assert recent_games(games, "BUF", None, venue="home", before="2024-09-29")["game_id"].to_list() == ["c", "a"]
    assert recent_games(games, "BUF", None, venue="away", before="2024-09-29")["game_id"].to_list() == ["b"]
    assert recent_games(games, "BUF", None, before="2024-09-29").height == 4


def test_h2h(games):
    result = head_to_head(games, "BUF", "MIA", None, before="2024-09-29")
    assert result["team_a_wins"] == 1 and result["team_b_wins"] == 0 and result["ties"] == 1
    assert result["team_a_avg_margin"] == 5
    assert head_to_head(games, "BUF", "MIA", 1, before="2024-09-29")["games"]["game_id"].to_list() == ["b"]
    with pytest.raises(ValueError):
        head_to_head(games, "BUF", "BUF")


def test_stats_opponents_and_denominators(bundle):
    selected = recent_games(bundle.games, "BUF", 3, before="2024-09-22")
    summary = box_score_summary(selected, bundle.stats.frame)
    assert summary["offense"]["total_yards"] == 870
    assert summary["offense"]["yards_per_play"] == 870 / 156
    assert summary["defense"]["total_yards"] == 950
    assert summary["offense"]["touchdowns"] == 9
    assert summary["offense"]["turnovers"] == 3
    partial = bundle.stats.frame.filter(pl.col("game_id") != "b")
    assert box_score_summary(selected, partial)["offense"]["games_with_stats"] == 2
    nulls = bundle.stats.frame.with_columns(pl.lit(None, dtype=pl.Int32).alias("passing_yards"))
    assert box_score_summary(selected, nulls)["offense"]["total_yards"] is None
    assert box_score_summary(selected, None)["offense"]["turnovers"] is None


def test_pbp_rates_and_missing_epa(games, pbp):
    selected = recent_games(games, "BUF", None, before="2024-09-08")
    result = advanced_summary(pbp, selected, "BUF")
    offense, defense = result["offense"], result["defense"]
    assert offense["plays"] == 4 and offense["epa_plays"] == 3
    assert offense["epa_per_play"] == pytest.approx(0.5 / 3)
    assert offense["success_rate"] == pytest.approx(1 / 3)
    assert offense["total_epa"] is None  # Missing EPA cannot silently become zero.
    assert offense["passing_epa_per_play"] == 0.5
    assert offense["explosive_play_rate"] == 0.5
    assert offense["third_down_rate"] == pytest.approx(2 / 3)
    assert offense["red_zone_trips"] == 1 and offense["red_zone_td_rate"] == 1
    assert defense["epa_per_play"] == -2 and defense["success_rate"] == 0
    assert advanced_summary(None, selected, "BUF") is None
    empty = advanced_summary(pbp, selected.head(0), "BUF")
    assert empty["offense"]["epa_per_play"] is None


def test_matchup_excludes_target_result(bundle):
    result = analyze_matchup(bundle, "c", games=5)
    assert result["team_a"]["form"]["games"] == 2
    assert "c" not in result["team_a"]["games"]["game_id"].to_list()
    assert result["team_a"]["advanced"] is None
    assert result["injuries"]["BUF"] is None
    assert analyze_matchup(bundle, "b")["context"]["relationship"] == "divisional"
    assert compare_teams(bundle, "BUF", "KC", before=date(2024, 9, 22))["context"]["relationship"] == "same_conference"
    with pytest.raises(ValueError):
        analyze_matchup(bundle, "missing")


def test_network_failure_is_optional(monkeypatch):
    def fail():
        raise nfl_data.NFLDataError("connection unavailable")
    result = optional_dataset(fail)
    assert result.frame is None and result.status == "unavailable"


def test_injuries_cutoff_and_identity():
    reports = pl.DataFrame({"season": [2024] * 3, "week": [2] * 3, "team": ["BUF"] * 3,
                            "gsis_id": ["p1", "p2", None], "report_status": ["Questionable"] * 3,
                            "date_modified": [datetime(2024, 9, 7, tzinfo=timezone.utc), datetime(2024, 9, 9, tzinfo=timezone.utc), None]})
    selected = injury_reports(reports, "BUF", 2, as_of="2024-09-08")
    assert selected["player_id"].to_list() == ["p1"]
    roster = pl.DataFrame({"season": [2024, 2024], "team": ["BUF", "MIA"], "gsis_id": ["p1", "p1"], "full_name": ["Player", "Other team"]})
    assert attach_players(selected, roster)["player"].to_list() == [None]
    assert attach_players(selected, roster)["player_roster"].to_list() == ["Player"]


def test_signed_sack_yards_normalized():
    raw = pl.DataFrame({"game_id": ["a"], "team": ["BUF"], "season": [2024], "week": [1], "sack_yards_lost": [-27]})
    assert normalize_team_stats(raw)["sack_yards_lost"].item() == 27


def test_partial_score_is_not_a_result(games):
    partial = games.with_columns(pl.when(pl.col("game_id") == "a").then(None).otherwise(pl.col("away_score")).alias("away_score"))
    # Query works on normalized status; normalize again from a raw schedule.
    raw = partial.rename({"date": "gameday", "season_type": "game_type"})
    normalized = normalize_games(raw)
    assert normalized.filter(pl.col("game_id") == "a")["status"].item() == "awaiting_update"
    assert "a" not in recent_games(normalized, "BUF", None)["game_id"].to_list()


def test_empty_schedule_schema(games):
    raw = games.head(0).rename({"date": "gameday", "season_type": "game_type"})
    normalized = normalize_games(raw)
    assert games_by_date(normalized, "2024-09-01").is_empty()


def test_no_postseason_data(games):
    assert recent_form(games, "BUF", None, season_type="POST")["games"] == 0


def test_optional_unsupported_year():
    def unsupported():
        raise ValueError("injuries available since 2009")
    assert optional_dataset(unsupported).status == "unavailable"


def test_missing_red_zone_values_are_not_zero(games, pbp):
    selected = recent_games(games, "BUF", 1, before="2024-09-08")
    pbp = pbp.with_columns(pl.lit(None, dtype=pl.Float64).alias("touchdown"))
    assert advanced_summary(pbp, selected, "BUF")["offense"]["red_zone_td_rate"] is None


def test_h2h_franchise_identity_preserves_original_names(games):
    historical = games.with_columns(pl.when(pl.col("game_id") == "a").then(pl.lit("OLD")).otherwise(pl.col("home_team")).alias("home_team"))
    catalog = pl.DataFrame({"team_abbr": ["BUF", "OLD", "MIA"], "team_id": ["one", "one", "two"]})
    result = head_to_head(historical, "BUF", "MIA", None, before="2024-09-29", catalog=catalog)
    assert result["team_a_wins"] == 1
    assert "OLD" in result["games"]["home_team"].to_list()
