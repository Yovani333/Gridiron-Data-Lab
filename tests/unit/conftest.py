"""Offline fixtures shared by domain and presentation tests."""

from datetime import date, datetime, timezone
import socket

import polars as pl
import pytest

from nfl_analytics.data.datasets import Dataset, SeasonData
from nfl_analytics.data.games import normalize_games


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    original = socket.socket.connect
    def denied(sock, address, *args, **kwargs):
        # asyncio's Windows socketpair requires loopback, never external traffic.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original(sock, address, *args, **kwargs)
        pytest.fail("Unit tests must not use network connections")
    monkeypatch.setattr(socket.socket, "connect", denied)


@pytest.fixture
def games():
    return normalize_games(pl.DataFrame({
        "game_id": ["a", "b", "c", "d", "e", "f"], "season": [2024] * 6,
        "week": [1, 2, 3, 4, 5, 6], "game_type": ["REG"] * 6,
        "gameday": [f"2024-09-{d:02}" for d in (1, 8, 15, 22, 25, 29)],
        "home_team": ["BUF", "MIA", "BUF", "KC", "BUF", "BUF"],
        "away_team": ["MIA", "BUF", "KC", "BUF", "MIA", "MIA"],
        "home_score": [30, 21, 17, 35, None, 40], "away_score": [20, 21, 24, 14, None, 10],
        "location": ["Home", "Home", "Home", "Neutral", "Home", "Home"],
        "div_game": [1, 1, 0, 0, 1, 1],
    }), today=date(2024, 9, 26))


@pytest.fixture
def bundle(games):
    stats = pl.DataFrame({"game_id": ["a", "a", "b", "b", "c", "c"],
                          "team": ["BUF", "MIA", "BUF", "MIA", "BUF", "KC"],
                          "passing_yards": [250, 200, 200, 180, 150, 300],
                          "rushing_yards": [100] * 6, "sack_yards_lost": [10] * 6,
                          "attempts": [30] * 6, "carries": [20] * 6, "sacks_suffered": [2] * 6,
                          "passing_tds": [2] * 6, "rushing_tds": [1] * 6,
                          "passing_interceptions": [1] * 6, "fumbles_lost_total": [0] * 6,
                          "completions": [20] * 6})
    teams = pl.DataFrame({"team_abbr": ["BUF", "MIA", "KC"], "team_name": ["Buffalo Bills", "Miami Dolphins", "Kansas City Chiefs"],
                          "team_conf": ["AFC"] * 3, "team_division": ["AFC East", "AFC East", "AFC West"]})
    missing = Dataset(None, "unavailable", "not published")
    return SeasonData(2024, games, Dataset(teams, "available", ""), Dataset(stats, "available", ""), missing, missing,
                      Dataset(None, "not_loaded", ""), datetime(2024, 9, 26, tzinfo=timezone.utc))


@pytest.fixture
def pbp():
    return pl.DataFrame({"game_id": ["a"] * 8, "play_id": list(range(8)), "posteam": ["BUF"] * 7 + ["MIA"],
                         "defteam": ["MIA"] * 7 + ["BUF"],
                         "play_type": ["pass", "run", "pass", "qb_kneel", "no_play", "pass", "run", "pass"],
                         "qb_kneel": [0, 0, 0, 1, 0, 0, 0, 0], "qb_spike": [0] * 8,
                         "two_point_attempt": [0, 0, 0, 0, 0, 1, 0, 0], "qb_dropback": [1, 0, 1, 0, 0, 1, 0, 1],
                         "epa": [1.0, -0.5, 0.0, -1.0, 3.0, 9.0, None, -2.0],
                         "yards_gained": [20, 10, -5, -1, 0, 2, 2, 0],
                         "third_down_converted": [1, 0, 0, 0, 1, 0, 0, 0],
                         "third_down_failed": [0, 0, 1, 0, 0, 0, 0, 1],
                         "first_down": [1, 1, 0, 0, 1, 0, 0, 0],
                         "fixed_drive": [1, 1, 2, 3, 4, 1, 2, 1],
                         "yardline_100": [20, 5, 40, 20, 50, 2, 35, 10],
                         "touchdown": [0, 1, 0, 0, 0, 1, 0, 0],
                         "td_team": [None, "BUF", None, None, None, "BUF", None, None]})
