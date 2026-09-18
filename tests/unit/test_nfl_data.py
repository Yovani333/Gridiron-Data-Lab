"""Offline contracts; upstream calls are replaced with small Polars fixtures."""

import polars as pl
import pytest
import socket

from nfl_analytics.data import nfl_data as data


@pytest.fixture(autouse=True)
def fixed_season(monkeypatch):
    monkeypatch.setattr(data.nfl, "get_current_season", lambda **kwargs: 2026)
    def offline(*args, **kwargs):
        pytest.fail("unit tests must not open network connections")
    monkeypatch.setattr(socket.socket, "connect", offline)


@pytest.fixture
def schedule():
    return pl.DataFrame({"game_id": ["a", "b", "c"], "season": [2024] * 3,
                         "week": [1, 2, 3], "home_team": ["KC", "BUF", "KC"],
                         "away_team": ["BAL", "MIA", "BUF"],
                         "home_score": [27, 20, None], "away_score": [20, 17, None]})


@pytest.mark.parametrize("seasons", [True, False, None, [], "2024", 2024.0, [True], [2024, "2025"], 1919, 2027])
def test_invalid_seasons_never_call_provider(monkeypatch, seasons):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid input reached the provider")
    monkeypatch.setattr(data.nfl, "load_schedules", unexpected)
    with pytest.raises(ValueError):
        data.load_schedules(seasons)


def test_schedules_and_polars_filter(monkeypatch, schedule):
    calls = []
    def provider(years):
        calls.append(years)
        return schedule
    monkeypatch.setattr(data.nfl, "load_schedules", provider)
    result = data.load_schedules([2024, 2024])
    assert calls == [[2024]]
    assert result is schedule
    assert result.filter(pl.col("home_team") == "KC").height == 2


@pytest.mark.parametrize("bad", [None, [], pl.DataFrame({"season": [2024]})])
def test_broken_contract(monkeypatch, bad):
    monkeypatch.setattr(data.nfl, "load_schedules", lambda _: bad)
    with pytest.raises(data.NFLDataError):
        data.load_schedules(2024)


def test_empty_schedule(monkeypatch, schedule):
    monkeypatch.setattr(data.nfl, "load_schedules", lambda _: schedule.head(0))
    with pytest.raises(data.NFLDataError, match="no rows"):
        data.load_schedules(2024)


def test_provider_error_preserves_cause(monkeypatch):
    error = ConnectionError("offline")
    def fail(_):
        raise error
    monkeypatch.setattr(data.nfl, "load_schedules", fail)
    with pytest.raises(data.NFLDataError, match="schedules") as caught:
        data.load_schedules(2024)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("name,columns", [
    ("player_stats", {"season": [2024], "player_id": ["p1"]}),
    ("team_stats", {"season": [2024], "team": ["KC"]}),
    ("rosters", {"season": [2024], "team": ["KC"], "gsis_id": ["p1"]}),
    ("injuries", {"season": [2024], "week": [1], "team": ["KC"]}),
])
def test_loaders(monkeypatch, name, columns):
    def provider(years, **kwargs):
        assert years == [2024]
        if name.endswith("stats"):
            assert kwargs == {"summary_level": "week"}
        return pl.DataFrame(columns)
    monkeypatch.setattr(data.nfl, f"load_{name}", provider)
    assert isinstance(getattr(data, f"load_{name}")(2024), pl.DataFrame)


@pytest.mark.parametrize("loader", [data.load_player_stats, data.load_team_stats])
def test_invalid_summary(loader):
    with pytest.raises(ValueError, match="summary_level"):
        loader(2024, summary_level="bad")


def test_pbp_single_season(monkeypatch):
    def provider(year):
        assert year == 2024
        return pl.DataFrame({"game_id": ["a"], "play_id": [1], "season": [2024], "week": [1]})
    monkeypatch.setattr(data.nfl, "load_pbp", provider)
    assert data.load_play_by_play(2024).height == 1
    for invalid in ([2024], True, 1998):
        with pytest.raises(ValueError):
            data.load_play_by_play(invalid)


def test_week_context(monkeypatch, schedule):
    monkeypatch.setattr(data.nfl, "load_schedules", lambda _: schedule)
    assert data.get_current_week() == 3
    assert data.get_latest_completed_week(2024) == 2
    monkeypatch.setattr(data.nfl, "load_schedules", lambda _: schedule.head(2))
    assert data.get_current_week() == 2
    monkeypatch.setattr(data.nfl, "load_schedules", lambda _: schedule.tail(1))
    assert data.get_latest_completed_week(2024) is None


def test_inventory(monkeypatch):
    monkeypatch.setattr(data.nfl, "load_schedules", lambda _: pl.DataFrame({"season": [2024, 2023, 2024]}))
    assert data.get_schedule_seasons() == [2023, 2024]


def test_cache_configuration(monkeypatch, tmp_path):
    settings = {}
    monkeypatch.setattr(data, "update_config", lambda **kwargs: settings.update(kwargs))
    data.configure_cache(tmp_path, duration=60)
    assert settings == {"cache_mode": "filesystem", "cache_dir": tmp_path.resolve(), "cache_duration": 60}
    for invalid in (-1, True, 1.5):
        with pytest.raises(ValueError):
            data.configure_cache(tmp_path, duration=invalid)


@pytest.mark.parametrize("today,roster,expected", [
    ("2026-01-15", False, 2025),
    ("2026-02-08", False, 2025),
    ("2026-09-10", False, 2026),
    ("2026-03-14", True, 2025),
    ("2026-03-15", True, 2026),
])
def test_provider_season_convention(monkeypatch, today, roster, expected):
    # Diagnostic contract test for the installed provider's date convention.
    from datetime import date
    from importlib import import_module
    dates = import_module("nflreadpy.utils_date")
    class FixedDate(date):
        @classmethod
        def today(cls):
            return date.fromisoformat(today)
    monkeypatch.setattr(dates, "date", FixedDate)
    monkeypatch.setattr(data.nfl, "get_current_season", dates.get_current_season)
    assert data.get_current_season(roster=roster) == expected
