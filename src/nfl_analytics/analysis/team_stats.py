"""Box-score metrics with explicit coverage; incomplete sums are not zero."""

import polars as pl

from nfl_analytics.data.games import require_columns


def complete_sum(frame: pl.DataFrame, column: str) -> float | None:
    if frame.is_empty() or column not in frame.columns:
        return None
    series = frame.get_column(column)
    if series.null_count() or (series.dtype.is_float() and not series.is_finite().all()):
        return None
    return series.sum()


def add_values(*values) -> float | None:
    return None if any(v is None for v in values) else sum(values)


def ratio(numerator, denominator) -> float | None:
    return numerator / denominator if numerator is not None and denominator is not None and denominator > 0 else None


def _metrics(frame: pl.DataFrame) -> dict:
    totals = {name: complete_sum(frame, name) for name in (
        "passing_yards", "rushing_yards", "sack_yards_lost", "passing_tds", "rushing_tds",
        "passing_interceptions", "fumbles_lost_total", "completions", "attempts", "carries", "sacks_suffered")}
    passing, rushing, sack_yards = (totals[k] for k in ("passing_yards", "rushing_yards", "sack_yards_lost"))
    yards = add_values(passing, rushing, -sack_yards if sack_yards is not None else None)
    plays = add_values(totals["attempts"], totals["carries"], totals["sacks_suffered"])
    return {"games_with_stats": frame.height, "total_yards": yards,
            "yards_per_game": ratio(yards, frame.height), "yards_per_play": ratio(yards, plays),
            "passing_yards": passing, "rushing_yards": rushing,
            "passing_yards_per_game": ratio(passing, frame.height),
            "rushing_yards_per_game": ratio(rushing, frame.height),
            "touchdowns": add_values(totals["passing_tds"], totals["rushing_tds"]),
            "turnovers": add_values(totals["passing_interceptions"], totals["fumbles_lost_total"]),
            "completions": totals["completions"], "attempts": totals["attempts"],
            "sacks": totals["sacks_suffered"], "plays": plays,
            # Full first downs require penalty first downs; computed from PBP instead.
            "first_downs": None, "third_down_rate": None, "red_zone_td_rate": None}


def box_score_summary(selected_games: pl.DataFrame, stats: pl.DataFrame | None) -> dict:
    """Join opponents per game, not season totals; preserves future adjustment keys."""
    empty = _metrics(pl.DataFrame())
    if stats is None or stats.is_empty():
        return {"offense": empty.copy(), "defense": empty.copy(), "requested_games": selected_games.height}
    require_columns(stats, {"game_id", "team"})
    if stats.select(pl.struct("game_id", "team").n_unique()).item() != stats.height:
        raise ValueError("Team stats must contain one row per game/team")
    keys = selected_games.select("game_id", "team", "opponent")
    own = keys.select("game_id", "team").join(stats, on=["game_id", "team"], how="inner", validate="1:1")
    opponents = keys.select("game_id", pl.col("opponent").alias("team")).join(stats, on=["game_id", "team"], how="inner", validate="1:1")
    return {"offense": _metrics(own), "defense": _metrics(opponents), "requested_games": selected_games.height}
