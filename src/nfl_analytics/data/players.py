"""Player identities and reports: joins use season/team/ID, never names."""

from datetime import date

import polars as pl

from .games import as_date, require_columns


def normalize_injuries(frame: pl.DataFrame) -> pl.DataFrame:
    require_columns(frame, {"season", "week", "team", "gsis_id"})
    mapping = {"gsis_id": "player_id", "full_name": "player", "report_primary_injury": "injury",
               "report_status": "report_status", "practice_status": "practice_status",
               "position": "position", "date_modified": "reported_at", "game_type": "season_type"}
    expressions = [pl.col(c).cast(pl.Int32) for c in ("season", "week")] + [pl.col("team")]
    for source, target in mapping.items():
        value = pl.col(source) if source in frame.columns else pl.lit(None)
        dtype = pl.Datetime("us", "UTC") if target == "reported_at" else pl.String
        expressions.append(value.cast(dtype, strict=False).alias(target))
    return frame.select(expressions)


def injury_reports(frame: pl.DataFrame, team: str, week: int, *, as_of: date | str | None = None) -> pl.DataFrame:
    if type(week) is not int or not 1 <= week <= 22:
        raise ValueError("week must be between 1 and 22")
    selected = normalize_injuries(frame).filter((pl.col("team") == team) & (pl.col("week") == week))
    if as_of is not None:
        # Undated reports cannot be claimed to have been known at a historical cutoff.
        selected = selected.filter(pl.col("reported_at").dt.date() <= as_date(as_of))
    return selected.sort(["reported_at", "player"], descending=[True, False], nulls_last=True)


def player_directory(rosters: pl.DataFrame) -> pl.DataFrame:
    require_columns(rosters, {"season", "team", "gsis_id"})
    columns = {"full_name": "player", "position": "position"}
    result = rosters.select("season", "team", pl.col("gsis_id").alias("player_id"),
                            *[(pl.col(c) if c in rosters.columns else pl.lit(None, dtype=pl.String)).alias(n) for c, n in columns.items()])
    # Exclude null IDs from identity joins; keep them in the original dataset.
    return result.filter(pl.col("player_id").is_not_null()).unique(subset=["season", "team", "player_id"], keep="last")


def attach_players(frame: pl.DataFrame, rosters: pl.DataFrame) -> pl.DataFrame:
    require_columns(frame, {"season", "team", "player_id"})
    return frame.join(player_directory(rosters), on=["season", "team", "player_id"], how="left", suffix="_roster", validate="m:1")
