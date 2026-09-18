"""Descriptive records, configurable windows and head-to-head history."""

import polars as pl

from nfl_analytics.data.games import as_date, positive_count, recent_games, validate_team
from nfl_analytics.data.teams import franchise_aliases


def summarize_games(games: pl.DataFrame) -> dict:
    """Win percentage = wins / games; ties are reported separately."""
    n = games.height
    if not n:
        return {"games": 0, "wins": 0, "losses": 0, "ties": 0, "win_pct": None,
                "points_for": None, "points_against": None, "points_per_game": None,
                "points_allowed_per_game": None, "point_diff": None, "avg_margin": None}
    pf = games.get_column("points_for").sum()
    pa = games.get_column("points_against").sum()
    wins = games.filter(pl.col("point_diff") > 0).height
    losses = games.filter(pl.col("point_diff") < 0).height
    return {"games": n, "wins": wins, "losses": losses, "ties": n - wins - losses,
            "win_pct": wins / n, "points_for": pf, "points_against": pa,
            "points_per_game": pf / n, "points_allowed_per_game": pa / n,
            "point_diff": pf - pa, "avg_margin": (pf - pa) / n}


def recent_form(schedule: pl.DataFrame, team: str, games: int | None = 5, **filters) -> dict:
    return summarize_games(recent_games(schedule, team, games, **filters))


def head_to_head(schedule: pl.DataFrame, team_a: str, team_b: str, games: int | None = 5, *, before=None, catalog: pl.DataFrame | None = None) -> dict:
    positive_count(games)
    team_a, team_b = validate_team(team_a, schedule), validate_team(team_b, schedule)
    aliases_a, aliases_b = franchise_aliases(team_a, catalog), franchise_aliases(team_b, catalog)
    if set(aliases_a) & set(aliases_b):
        raise ValueError("Choose two different teams")
    home_a = pl.col("home_team").is_in(aliases_a)
    away_a = pl.col("away_team").is_in(aliases_a)
    history = schedule.filter(((home_a & pl.col("away_team").is_in(aliases_b)) |
                               (away_a & pl.col("home_team").is_in(aliases_b))) &
                              (pl.col("status") == "result_available"))
    if before is not None:
        history = history.filter(pl.col("date") < as_date(before))
    history = history.with_columns(
        pl.when(home_a).then(pl.col("home_score")).otherwise(pl.col("away_score")).alias("points_for"),
        pl.when(home_a).then(pl.col("away_score")).otherwise(pl.col("home_score")).alias("points_against"),
    ).with_columns((pl.col("points_for") - pl.col("points_against")).alias("point_diff")).sort(["date", "game_id"], descending=True)
    if games is not None:
        history = history.head(games)
    summary = summarize_games(history)
    return {"games": history, "team_a_wins": summary["wins"], "team_b_wins": summary["losses"],
            "ties": summary["ties"], "team_a_avg_points": summary["points_per_game"],
            "team_b_avg_points": summary["points_allowed_per_game"], "team_a_avg_margin": summary["avg_margin"],
            "scope_seasons": sorted(schedule.get_column("season").unique().to_list()),
            "aliases": {team_a: aliases_a, team_b: aliases_b}}
