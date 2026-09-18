"""Normalize schedules and query them without provider or UI dependencies."""

from datetime import date
from typing import Literal

import polars as pl

type Venue = Literal["all", "home", "away"]


def require_columns(frame: pl.DataFrame, columns: set[str]) -> None:
    if not isinstance(frame, pl.DataFrame):
        raise ValueError("Expected a Polars DataFrame")
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")


def as_date(value: date | str) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError("Expected a date or ISO date string (YYYY-MM-DD)")


def positive_count(value: int | None) -> None:
    if value is not None and (type(value) is not int or value < 1):
        raise ValueError("games must be a positive integer or None for all games")


def normalize_games(frame: pl.DataFrame, *, today: date | None = None) -> pl.DataFrame:
    """Scores imply a published result, not a live-clock or official status feed."""
    require_columns(frame, {"game_id", "season", "week", "game_type", "gameday", "home_team", "away_team", "home_score", "away_score"})
    today = today or date.today()
    optional = {"gametime": pl.String, "location": pl.String, "div_game": pl.Int32,
                "stadium": pl.String}
    frame = frame.with_columns([pl.lit(None, dtype=t).alias(c) for c, t in optional.items() if c not in frame.columns])
    result = frame.select(
        "game_id", pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
        pl.col("game_type").alias("season_type"),
        pl.col("gameday").cast(pl.String).str.to_date(strict=True).alias("date"),
        "gametime", "stadium", "home_team", "away_team",
        pl.col("home_score").cast(pl.Int32), pl.col("away_score").cast(pl.Int32),
        (pl.col("location").str.to_lowercase() == "neutral").fill_null(False).alias("neutral_site"),
        pl.col("div_game").cast(pl.Boolean).alias("divisional"),
    )
    if result.get_column("game_id").null_count() or result.get_column("game_id").n_unique() != result.height:
        raise ValueError("game_id must be non-null and unique")
    if result.select(pl.any_horizontal(pl.col("date").is_null(), pl.col("home_team").is_null(), pl.col("away_team").is_null(), pl.col("home_team") == pl.col("away_team")).any()).item():
        raise ValueError("Invalid game date or teams")
    scored = pl.col("home_score").is_not_null() & pl.col("away_score").is_not_null()
    margin = pl.col("home_score") - pl.col("away_score")
    return result.with_columns(
        pl.when(scored).then(pl.lit("result_available"))
        .when(pl.col("date") <= today).then(pl.lit("awaiting_update"))
        .otherwise(pl.lit("scheduled")).alias("status"),
        pl.when(scored & (margin > 0)).then(pl.col("home_team"))
        .when(scored & (margin < 0)).then(pl.col("away_team")).otherwise(None).alias("winner"),
        pl.when(scored & (margin > 0)).then(pl.col("away_team"))
        .when(scored & (margin < 0)).then(pl.col("home_team")).otherwise(None).alias("loser"),
        margin.abs().alias("margin"),
    ).sort(["date", "gametime", "game_id"])


def games_by_date(frame: pl.DataFrame, day: date | str) -> pl.DataFrame:
    return frame.filter(pl.col("date") == as_date(day))


def games_by_week(frame: pl.DataFrame, week: int) -> pl.DataFrame:
    if type(week) is not int or not 1 <= week <= 22:
        raise ValueError("week must be an integer from 1 to 22")
    return frame.filter(pl.col("week") == week)


def validate_team(team: str, frame: pl.DataFrame) -> str:
    if not isinstance(team, str) or not team.strip():
        raise ValueError("team must be a non-empty abbreviation")
    team = team.strip().upper()
    known = set(frame.get_column("home_team")) | set(frame.get_column("away_team"))
    if team not in known:
        raise ValueError(f"Unknown team in selected schedule: {team}")
    return team


def team_games(frame: pl.DataFrame, team: str, *, venue: Venue = "all", before: date | str | None = None,
               completed_only: bool = False, season_type: str = "all") -> pl.DataFrame:
    """One row per game from the team's perspective; opponent keys are retained."""
    team = validate_team(team, frame)
    if venue not in ("all", "home", "away"):
        raise ValueError("venue must be all, home or away")
    if season_type not in ("all", "REG", "POST"):
        raise ValueError("season_type must be all, REG or POST")
    home = pl.col("home_team") == team
    selected = frame.filter(home | (pl.col("away_team") == team)).with_columns(
        pl.lit(team).alias("team"), home.alias("is_home"),
        pl.when(home).then(pl.col("away_team")).otherwise(pl.col("home_team")).alias("opponent"),
        pl.when(home).then(pl.col("home_score")).otherwise(pl.col("away_score")).alias("points_for"),
        pl.when(home).then(pl.col("away_score")).otherwise(pl.col("home_score")).alias("points_against"),
    )
    if venue != "all":
        selected = selected.filter((pl.col("is_home") == (venue == "home")) & ~pl.col("neutral_site"))
    if before is not None:
        selected = selected.filter(pl.col("date") < as_date(before))
    if completed_only:
        selected = selected.filter(pl.col("status") == "result_available")
    if season_type != "all":
        selected = selected.filter(pl.col("season_type") == "REG" if season_type == "REG" else pl.col("season_type").is_in(["WC", "DIV", "CON", "SB", "POST"]))
    return selected.with_columns((pl.col("points_for") - pl.col("points_against")).alias("point_diff")).sort(["date", "game_id"], descending=True)


def recent_games(frame: pl.DataFrame, team: str, games: int | None = 5, **filters) -> pl.DataFrame:
    positive_count(games)
    selected = team_games(frame, team, completed_only=True, **filters)
    return selected if games is None else selected.head(games)
