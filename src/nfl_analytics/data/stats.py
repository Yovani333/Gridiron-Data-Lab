"""Canonical box-score conventions verified against nflverse's signed sack yards."""

import polars as pl

from .games import require_columns


def normalize_team_stats(frame: pl.DataFrame) -> pl.DataFrame:
    require_columns(frame, {"game_id", "team", "season", "week"})
    if frame.select(pl.struct("game_id", "team").n_unique()).item() != frame.height:
        raise ValueError("Duplicate game/team statistics")
    # nflverse publishes sack yards lost as negative; our contract is a loss magnitude.
    if "sack_yards_lost" in frame.columns:
        frame = frame.with_columns(pl.col("sack_yards_lost").abs())
    return frame
