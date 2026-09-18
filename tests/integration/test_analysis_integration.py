"""Small real consistency check; no play-by-play download in this test."""

from pathlib import Path

import polars as pl
import pytest

from nfl_analytics.analysis.form import recent_form
from nfl_analytics.analysis.team_stats import box_score_summary
from nfl_analytics.data import nfl_data
from nfl_analytics.data.games import recent_games


@pytest.mark.integration
def test_real_stats_join_and_normalization():
    nfl_data.configure_cache(Path(__file__).resolve().parents[2] / ".cache/nflreadpy")
    games = nfl_data.get_games(2024)
    stats = nfl_data.get_team_stats(2024)
    team = games.get_column("home_team")[0]
    selected = recent_games(games, team, 5, before="2025-01-01", season_type="REG")
    metrics = box_score_summary(selected, stats)
    assert metrics["offense"]["games_with_stats"] == selected.height
    assert metrics["defense"]["games_with_stats"] == selected.height
    assert stats.get_column("sack_yards_lost").min() >= 0
    form = recent_form(games, team, 5, before="2025-01-01", season_type="REG")
    assert form["wins"] + form["losses"] + form["ties"] == form["games"]
    assert selected.filter(pl.col("date") >= pl.date(2025, 1, 1)).is_empty()
