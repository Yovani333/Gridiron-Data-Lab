"""Thin, typed boundary around nflreadpy; no analytics or implicit bulk loads."""

from collections.abc import Callable
from pathlib import Path
from typing import Literal

import nflreadpy as nfl
import polars as pl
from nflreadpy.config import update_config

type Seasons = int | list[int]
type SummaryLevel = Literal["week", "reg", "post", "reg+post"]


class NFLDataError(RuntimeError):
    """Provider failure, unavailable data or a broken DataFrame contract."""


def configure_cache(directory: str | Path, *, duration: int = 86400) -> None:
    """Opt into nflreadpy's persistent cache (global to the current process)."""
    if type(duration) is not int or duration < 0:
        raise ValueError("duration must be a non-negative integer in seconds")
    update_config(cache_mode="filesystem", cache_dir=Path(directory).expanduser().resolve(),
                  cache_duration=duration)


def get_current_season(*, roster: bool = False) -> int:
    """Provider season convention, including offseason and roster-year handling."""
    if type(roster) is not bool:
        raise ValueError("roster must be a boolean")
    return nfl.get_current_season(roster=roster)


def _seasons(seasons: Seasons, minimum: int = 1920, *, roster: bool = False) -> list[int]:
    values = [seasons] if type(seasons) is int else seasons
    if not isinstance(values, list) or not values:
        raise ValueError("seasons must be an integer or a non-empty list of integers")
    maximum = get_current_season(roster=roster)
    if any(type(year) is not int or not minimum <= year <= maximum for year in values):
        raise ValueError(f"seasons must contain integers between {minimum} and {maximum}")
    return list(dict.fromkeys(values))


def _frame(name: str, call: Callable[[], object], required: set[str]) -> pl.DataFrame:
    try:
        result = call()
    except Exception as exc:
        raise NFLDataError(f"{name}: nflreadpy failed; check network and dataset availability: {exc}") from exc
    if not isinstance(result, pl.DataFrame):
        raise NFLDataError(f"{name}: expected polars.DataFrame, got {type(result).__name__}")
    missing = required.difference(result.columns)
    if missing:
        raise NFLDataError(f"{name}: missing essential columns: {', '.join(sorted(missing))}")
    if result.is_empty():
        raise NFLDataError(f"{name}: no rows available for the requested selection")
    return result


_SCHEDULE_COLUMNS = {"game_id", "season", "week", "home_team", "away_team", "home_score", "away_score"}


def load_schedules(seasons: Seasons) -> pl.DataFrame:
    """Schedules/results; upstream downloads the full small games file then filters."""
    years = _seasons(seasons)
    return _frame("schedules", lambda: nfl.load_schedules(years), _SCHEDULE_COLUMNS)


def load_player_stats(seasons: Seasons, *, summary_level: SummaryLevel = "week") -> pl.DataFrame:
    """Player statistics, weekly by default; explicit seasons only."""
    years = _seasons(seasons, 1999)
    _summary(summary_level)
    return _frame("player_stats", lambda: nfl.load_player_stats(years, summary_level=summary_level), {"season", "player_id"})


def load_team_stats(seasons: Seasons, *, summary_level: SummaryLevel = "week") -> pl.DataFrame:
    """Team statistics, weekly by default."""
    years = _seasons(seasons, 1999)
    _summary(summary_level)
    return _frame("team_stats", lambda: nfl.load_team_stats(years, summary_level=summary_level), {"season", "team"})


def _summary(value: SummaryLevel) -> None:
    if value not in ("week", "reg", "post", "reg+post"):
        raise ValueError("summary_level must be week, reg, post or reg+post")


def load_rosters(seasons: Seasons) -> pl.DataFrame:
    """Season rosters; provider accepts years from 1920 (availability may vary)."""
    years = _seasons(seasons, roster=True)
    return _frame("rosters", lambda: nfl.load_rosters(years), {"season", "team", "gsis_id"})


def load_injuries(seasons: Seasons) -> pl.DataFrame:
    """Historical injury reports; recent seasons may not be published upstream."""
    years = _seasons(seasons, 2009)
    return _frame("injuries", lambda: nfl.load_injuries(years), {"season", "week", "team"})


def load_play_by_play(season: int) -> pl.DataFrame:
    """Explicit single-season download; no server-side week or column selection."""
    if type(season) is not int:
        raise ValueError("play-by-play requires a single integer season")
    year = _seasons(season, 1999)[0]
    return _frame("play_by_play", lambda: nfl.load_pbp(year), {"game_id", "play_id", "season", "week"})


def load_teams() -> pl.DataFrame:
    """Team metadata for future division/conference joins."""
    return _frame("teams", nfl.load_teams, {"team_abbr"})


def get_schedule_seasons() -> list[int]:
    """Seasons actually present in schedules, not a promise for other datasets."""
    frame = _frame("schedule inventory", lambda: nfl.load_schedules(True), {"season"})
    return frame.get_column("season").drop_nulls().unique().sort().to_list()


def get_current_week() -> int | None:
    """Earliest unscored week, or final scheduled week if all results exist.

    This is the provider's schedule-based convention, not a live game clock.
    """
    frame = load_schedules(get_current_season())
    pending = frame.filter(pl.col("home_score").is_null() | pl.col("away_score").is_null())
    return pending.get_column("week").min() if not pending.is_empty() else frame.get_column("week").max()


def get_latest_completed_week(season: int) -> int | None:
    """Latest week with at least one scored game; not necessarily fully completed."""
    frame = load_schedules(season)
    return frame.filter(pl.col("home_score").is_not_null() & pl.col("away_score").is_not_null()).get_column("week").max()
