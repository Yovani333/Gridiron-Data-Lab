"""Evaluate heuristic picks without training a model or requesting PBP."""
import argparse
import json
from pathlib import Path

from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import model_season_data
from nfl_analytics.analysis.pick_backtest import evaluate_picks, save_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new versioned path")
    nfl_data.configure_cache(".cache/nflreadpy")
    history = nfl_data.get_games(nfl_data.get_schedule_seasons())
    reports = [evaluate_picks(model_season_data(year), history=history, window=args.games)
               for year in sorted(set(args.seasons))]
    save_report({"reports": reports}, args.output)
    print(json.dumps([{k: v for k, v in report.items() if k not in ("decisions", "config")}
                      for report in reports], indent=2))


if __name__ == "__main__":
    main()
