"""Record future regular-season games, then settle their frozen signals."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import polars as pl

from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import model_season_data
from nfl_analytics.analysis.prospective import capture, save_snapshot, evaluate_snapshots
from nfl_analytics.analysis.pick_backtest import save_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["record", "settle"])
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--directory", type=Path, default=Path("records/prospective"))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.days < 1:
        parser.error("days must be positive")
    if args.action == "settle" and (args.output is None or args.output.exists()):
        parser.error("settle requires a new --output path")
    nfl_data.configure_cache(".cache/nflreadpy", duration=0)
    if args.action == "record":
        data = model_season_data(args.season)
        history = nfl_data.get_games(nfl_data.get_schedule_seasons())
        today = datetime.now(timezone.utc).date()
        future = data.games.filter((pl.col("date") > today) & (pl.col("date") <= today + timedelta(days=args.days)) &
                                   (pl.col("season_type") == "REG") & pl.col("home_score").is_null() & pl.col("away_score").is_null())
        saved = 0
        for game_id in future["game_id"]:
            snapshot = capture(data, game_id, history=history)
            try:
                path = save_snapshot(snapshot, args.directory)
                print(f"Recorded {game_id}: {path}")
                saved += 1
            except FileExistsError:
                print(f"Already recorded {game_id}; preserved original")
        print(f"New snapshots: {saved}; eligible games: {future.height}")
    else:
        snapshots = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(args.directory.glob("*.json"))]
        snapshots = [s for s in snapshots if s["payload"]["season"] == args.season]
        result = evaluate_snapshots(snapshots, nfl_data.get_games(args.season))
        save_report(result, args.output)
        print(json.dumps(result["games"], indent=2))


if __name__ == "__main__":
    main()
