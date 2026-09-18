"""Opt-in small real download through our own data boundary."""

from pathlib import Path

import polars as pl
import pytest

from nfl_analytics.data import configure_cache, load_schedules


@pytest.mark.integration
def test_real_2024_schedule():
    configure_cache(Path(__file__).resolve().parents[2] / ".cache" / "nflreadpy")
    frame = load_schedules(2024)
    assert isinstance(frame, pl.DataFrame)
    assert frame.height > 250
    assert {"game_id", "season", "week", "home_team", "away_team", "home_score", "away_score"} <= set(frame.columns)
    assert frame.get_column("season").unique().to_list() == [2024]
    assert frame.get_column("game_id").n_unique() == frame.height
    assert frame.filter(pl.col("week") == 1).height > 0
