"""Export one auditable pregame report using the same service as the application."""

import argparse
import json
from pathlib import Path

from nfl_analytics.presentation import service
from nfl_analytics.analysis.pick_validation import settle_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    service.initialize()
    data = service.load_analysis(args.season)
    result = service.matchup(data, args.game_id, games=args.games)
    report = result["potential_picks"]
    output = {"report": report, "retrospective_settlement": settle_report(report, result["game"])}
    text = json.dumps(output, indent=2, ensure_ascii=True, allow_nan=False)
    if args.output:
        # Preserve prior snapshots; evaluations must not be overwritten silently.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
