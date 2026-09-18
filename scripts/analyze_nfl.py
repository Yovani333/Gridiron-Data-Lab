"""Small examples of calendar queries, records, stats and descriptive comparisons."""

import argparse
from datetime import date
import json
from pathlib import Path

import polars as pl

from nfl_analytics.analysis.form import recent_form, head_to_head
from nfl_analytics.analysis.matchup import compare_teams, analyze_matchup
from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import season_data
from nfl_analytics.data.games import games_by_date, games_by_week, recent_games


def encode(value):
    if isinstance(value, pl.DataFrame):
        return value.to_dicts()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int)
    parser.add_argument("--team", required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--week", type=int)
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--pbp", action="store_true", help="Download one full season for advanced metrics")
    parser.add_argument("--matchup", help="Optional game_id; uses its date as the cutoff")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    nfl_data.configure_cache(Path(__file__).resolve().parents[1] / ".cache/nflreadpy")
    season = args.season or nfl_data.get_current_season()
    data = season_data(season, include_pbp=args.pbp)
    schedule = data.games
    historical = nfl_data.get_games(nfl_data.get_schedule_seasons())
    comparison = compare_teams(data, args.team, args.opponent, before=args.date, games=args.games,
                               injury_week=args.week, history=historical)
    report = {"by_date": games_by_date(schedule, args.date),
              "by_week": games_by_week(schedule, args.week) if args.week else None,
              "recent_games": recent_games(schedule, args.team, args.games, before=args.date),
              "recent_form": recent_form(schedule, args.team, args.games, before=args.date),
              "head_to_head": head_to_head(historical, args.team, args.opponent, before=args.date),
              "comparison": comparison}
    if args.matchup:
        report["matchup"] = analyze_matchup(data, args.matchup, games=args.games, history=historical)
    serialized = json.dumps(report, default=encode, ensure_ascii=True, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(f"Report saved: {args.output}")
        print(json.dumps({k: comparison["team_a"][k] for k in ("team", "form", "offense", "defense", "advanced")}, default=encode, indent=2))
    else:
        print(serialized)


if __name__ == "__main__":
    main()
