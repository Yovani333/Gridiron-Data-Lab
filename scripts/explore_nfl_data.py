"""Manual exploration; default downloads only the small schedules dataset."""

import argparse
from pathlib import Path

import polars as pl

from nfl_analytics.data import nfl_data as data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["schedules", "rosters", "player_stats", "team_stats", "injuries", "teams", "play_by_play"], default="schedules")
    parser.add_argument("--season", type=int, default=2024, help="Default: historical 2024 season")
    parser.add_argument("--allow-pbp", action="store_true", help="Allow downloading a full season of play-by-play")
    parser.add_argument("--full-schema", action="store_true")
    parser.add_argument("--context", action="store_true", help="Also inspect current season/week and schedule inventory")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached age for this invocation")
    args = parser.parse_args()
    if args.dataset == "play_by_play" and not args.allow_pbp:
        parser.error("play-by-play downloads a complete season; explicitly pass --allow-pbp")
    data.configure_cache(Path(__file__).resolve().parents[1] / ".cache" / "nflreadpy", duration=0 if args.refresh else 86400)
    try:
        loader = getattr(data, f"load_{args.dataset}")
        frame = loader() if args.dataset == "teams" else loader(args.season)
        print(f"Dataset: {args.dataset}; requested season: {args.season}")
        print(f"Type: {type(frame).__module__}.{type(frame).__name__}; rows: {frame.height}; columns: {frame.width}")
        columns = frame.columns if args.full_schema else frame.columns[:20]
        print(f"Schema ({len(columns)}/{frame.width} columns):", {col: str(frame.schema[col]) for col in columns})
        with pl.Config(tbl_cols=8, tbl_width_chars=120, tbl_formatting="ASCII_FULL"):
            print(frame.select(columns[:8]).head(5))
        for column in ("season", "week", "team", "home_team", "away_team", "recent_team"):
            if column in frame.columns:
                values = frame.get_column(column).drop_nulls().unique().sort().to_list()
                print(f"{column}: {values[:40]}")
        relevant = [c for c in ("game_id", "season", "week", "home_score", "away_score", "player_id", "gsis_id", "team") if c in frame.columns]
        print("Relevant null counts:", frame.select(relevant).null_count().to_dicts())
        if args.context:
            print("Current season:", data.get_current_season())
            print("Current week (schedule convention):", data.get_current_week())
            print("Schedule seasons:", data.get_schedule_seasons())
            print("Latest week with results:", data.get_latest_completed_week(args.season))
    except (data.NFLDataError, ValueError) as exc:
        parser.exit(1, f"Data exploration failed: {exc}\n")


if __name__ == "__main__":
    main()
