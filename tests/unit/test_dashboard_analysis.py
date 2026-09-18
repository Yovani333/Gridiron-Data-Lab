"""Offline assertions for the descriptive dashboard pipeline."""

from datetime import date

import polars as pl

from nfl_analytics.analysis.leaders import season_leaders
from nfl_analytics.analysis.signals import analyze_signal
from nfl_analytics.presentation import service


def test_leaderboard_aggregates_players_and_preserves_missing_values():
    weekly = pl.DataFrame({
        "player_id": ["one", "one", "two", "two"],
        "player_display_name": ["A", "A", "B", "B"],
        "team": ["BUF", "BUF", "MIA", "MIA"],
        "season_type": ["REG", "REG", "REG", "POST"],
        "passing_yards": [100, 150, 120, 999],
        "passing_tds": [None, None, 2, 8],
        "passing_interceptions": [1, 0, 0, 0],
    })
    leaders = season_leaders(weekly, "Passing")
    assert leaders["player"].to_list() == ["A", "B"]
    assert leaders["passing_yards"].to_list() == [250, 120]
    assert leaders["passing_tds"].to_list() == [None, 2]


def test_signal_uses_only_prior_results_and_requires_a_sample(bundle):
    scheduled = next(g for g in bundle.games.to_dicts() if g["game_id"] == "e")
    signal = analyze_signal(bundle, scheduled)
    assert signal["status"] == "insufficient_data"
    assert signal["samples"]["BUF"] == 4
    assert signal["samples"]["MIA"] == 2
    # Even if the game itself and a future blowout are in the frame, neither enters the sample.
    assert signal["samples"]["BUF"] < 5
    next_game = service.upcoming(bundle.games, today=date(2024, 9, 24))[0]
    assert next_game["game_id"] == "e"
    assert next_game["records"]["BUF"] == "1-2-1"


def test_signal_factors_and_scores_are_traceable(bundle):
    scheduled = next(g for g in bundle.games.to_dicts() if g["game_id"] == "f")
    # The future fixture becomes eligible only once each team has sufficient pregame history.
    from nfl_analytics.analysis.signal_config import SignalConfig
    signal = analyze_signal(bundle, scheduled, config=SignalConfig(min_games=2), history=bundle.games)
    assert signal["status"] == "descriptive_only"
    assert signal["samples"]["BUF"] == 4
    assert signal["samples"]["MIA"] == 2
    assert sum(f["points"] for f in signal["factors"]) == signal["score"]
    assert all(f["key"] in SignalConfig().weights for f in signal["factors"])


def test_overview_and_results_use_actual_frame(bundle):
    result = service.overview(bundle.games, seasons_available=[2023, 2024], players=None)
    assert result == {"teams": 3, "players": None, "games": 6, "seasons": (2023, 2024)}
    assert service.result_distribution(bundle.games) == {"home": 3, "away": 1, "ties": 1}
