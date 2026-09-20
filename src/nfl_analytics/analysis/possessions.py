"""Possession production: offensive TD (6) and FG (3), excluding conversions.

Uses provider fixed_drive_result only for drives containing pass/run/kneel/spike.
Return touchdowns, safeties and conversions are not offensive production here.
"""
import polars as pl


def drive_summary(frame: pl.DataFrame) -> dict:
    empty = {"drives": None, "drive_points": None, "points_per_drive": None,
             "drives_per_game": None, "drive_games": 0}
    required = {"game_id", "fixed_drive", "posteam", "play_type", "fixed_drive_result"}
    if frame.is_empty() or not required <= set(frame.columns):
        return empty
    snaps = frame.filter(pl.col("play_type").is_in(["pass", "run", "qb_kneel", "qb_spike"]))
    if snaps.is_empty() or snaps["fixed_drive"].null_count():
        return empty
    drives = snaps.group_by("game_id", "fixed_drive", "posteam").agg(
        pl.col("fixed_drive_result").drop_nulls().unique().alias("results"))
    valid = {"Touchdown": 6, "Field goal": 3, "Punt": 0, "End of half": 0,
             "Safety": 0, "Opp touchdown": 0, "Turnover": 0,
             "Missed field goal": 0, "Turnover on downs": 0}
    results = drives["results"].to_list()
    if any(len(items) != 1 or items[0] not in valid for items in results):
        return empty
    points = sum(valid[items[0]] for items in results)
    games = drives["game_id"].n_unique()
    return {"drives": drives.height, "drive_points": points, "points_per_drive": points / drives.height,
            "drives_per_game": drives.height / games, "drive_games": games}
