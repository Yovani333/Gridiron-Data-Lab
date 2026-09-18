"""Descriptive PBP metrics; definitions and denominators are explicit."""

import polars as pl

from nfl_analytics.data.games import require_columns
from .team_stats import complete_sum, ratio


def _mean(frame: pl.DataFrame, column: str) -> float | None:
    if column not in frame.columns:
        return None
    values = frame.get_column(column).drop_nulls()
    values = values.filter(values.is_finite())
    return values.mean() if len(values) else None


def _scrimmage(frame: pl.DataFrame) -> pl.DataFrame:
    # Dropbacks include sacks and scrambles; two-point plays are excluded by type.
    return frame.filter(pl.col("play_type").is_in(["pass", "run"]) &
                        (pl.col("qb_kneel").fill_null(0) == 0) &
                        (pl.col("qb_spike").fill_null(0) == 0) &
                        (pl.col("two_point_attempt").fill_null(0) == 0))


def _red_zone(frame: pl.DataFrame) -> tuple[int | None, float | None]:
    required = {"fixed_drive", "yardline_100", "touchdown", "td_team", "posteam"}
    if not required <= set(frame.columns) or frame.is_empty():
        return None, None
    # One opportunity per possession with a scrimmage snap at/opponent 20 or closer.
    eligible = frame.filter(pl.col("fixed_drive").is_not_null())
    if eligible.is_empty():
        return None, None
    if eligible.select(pl.any_horizontal(pl.col("yardline_100").is_null(), pl.col("touchdown").is_null()).any()).item():
        return None, None
    drives = eligible.group_by("game_id", "fixed_drive", "posteam").agg(
        (pl.col("yardline_100") <= 20).any().alias("entered"),
        ((pl.col("touchdown") == 1) & (pl.col("td_team") == pl.col("posteam"))).any().alias("td"),
    ).filter(pl.col("entered"))
    return drives.height, ratio(drives.filter(pl.col("td")).height, drives.height)


def _side(frame: pl.DataFrame) -> dict:
    count = frame.height
    passes = frame.filter(pl.col("qb_dropback") == 1)
    rushes = frame.filter(pl.col("qb_dropback") == 0)
    epa_n = frame.filter(pl.col("epa").is_not_null() & pl.col("epa").is_finite()).height
    explosive_known = frame.filter(pl.col("yards_gained").is_not_null() & pl.col("qb_dropback").is_not_null())
    explosive = explosive_known.filter(((pl.col("qb_dropback") == 1) & (pl.col("yards_gained") >= 20)) |
                                       ((pl.col("qb_dropback") == 0) & (pl.col("yards_gained") >= 10)))
    rz_count, rz_rate = _red_zone(frame)
    return {"plays": count, "games_with_pbp": frame.get_column("game_id").n_unique(), "epa_plays": epa_n,
            "epa_per_play": _mean(frame, "epa"), "total_epa": complete_sum(frame, "epa"),
            "passing_epa_per_play": _mean(passes, "epa"), "rushing_epa_per_play": _mean(rushes, "epa"),
            "passing_epa_total": complete_sum(passes, "epa"), "rushing_epa_total": complete_sum(rushes, "epa"),
            "success_rate": ratio(frame.filter(pl.col("epa").is_finite() & (pl.col("epa") > 0)).height, epa_n),
            "explosive_play_rate": ratio(explosive.height, explosive_known.height),
            "first_downs": None, "third_down_rate": None,
            "red_zone_trips": rz_count, "red_zone_td_rate": rz_rate}


def advanced_summary(pbp: pl.DataFrame | None, selected_games: pl.DataFrame, team: str) -> dict | None:
    """Defense values are opponent EPA/success ALLOWED, without sign inversion."""
    if pbp is None:
        return None
    required = {"game_id", "posteam", "defteam", "play_type", "qb_kneel", "qb_spike", "two_point_attempt", "qb_dropback", "epa", "yards_gained"}
    require_columns(pbp, required)
    eligible = pbp.join(selected_games.select("game_id"), on="game_id", how="semi")
    result = {}
    for side, column in (("offense", "posteam"), ("defense", "defteam")):
        all_plays = eligible.filter(pl.col(column) == team)
        result[side] = _side(_scrimmage(all_plays))
        # Provider conversion flags include accepted-penalty first downs. Not only scrimmage plays.
        if {"third_down_converted", "third_down_failed"} <= set(all_plays.columns):
            thirds = all_plays.filter((pl.col("third_down_converted") == 1) | (pl.col("third_down_failed") == 1))
            converted = thirds.filter(pl.col("third_down_converted") == 1).height
            result[side]["third_down_rate"] = ratio(converted, thirds.height)
        if "first_down" in all_plays.columns:
            known = all_plays.filter(pl.col("first_down").is_not_null())
            result[side]["first_downs"] = complete_sum(known, "first_down")
    return result
