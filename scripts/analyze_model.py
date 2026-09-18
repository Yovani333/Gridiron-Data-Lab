"""Single matchup inference; example: --season 2026 --team-a BUF --team-b MIA --as-of-date 2026-10-01."""

import argparse
import json

from nfl_analytics.data.datasets import model_season_data
from nfl_analytics.presentation import service


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental pregame NFL model")
    parser.add_argument("--season", required=True, type=int)
    parser.add_argument("--team-a", required=True)
    parser.add_argument("--team-b", required=True)
    parser.add_argument("--as-of-date", required=True, help="YYYY-MM-DD; excludes the entire date")
    parser.add_argument("--home-team", help="Omit for a neutral hypothetical comparison")
    args = parser.parse_args()
    service.initialize()
    data = model_season_data(args.season)
    result = service.model_projection(data, args.team_a.upper(), args.team_b.upper(),
                                      as_of_date=args.as_of_date, home_team=args.home_team.upper() if args.home_team else None)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
