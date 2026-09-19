"""Settle frozen reports without fitting weights or interpreting scores as odds."""

from math import isfinite


def settle_report(report: dict, game: dict) -> list[dict]:
    """Totals without lines are measured against the stored statistical reference.

    This is not sportsbook backtesting, ROI, or probability calibration. Pushes
    and missing scores are explicit and must not be counted as wins or losses.
    """
    if report["game_id"] != game["game_id"]:
        raise ValueError("Report and result must describe the same game")
    teams = report["teams"]
    scores = {game["home_team"]: game["home_score"], game["away_team"]: game["away_score"]}
    if set(scores) != set(teams):
        raise ValueError("Report and result teams differ")
    if any(value is None for value in scores.values()):
        return []
    if any(not isinstance(value, (int, float)) or not isfinite(value) or value < 0 for value in scores.values()):
        raise ValueError("Scores must be finite nonnegative numbers")
    settled = []
    for candidate in report["candidates"]:
        if candidate["status"] not in ("statistical_lean", "market_candidate"):
            continue
        market = candidate["market"]
        if market in ("moneyline", "spread"):
            observed = scores[teams[0]] - scores[teams[1]]
        elif market == "game_total":
            observed = sum(scores.values())
        else:
            observed = scores[candidate["team"]]
        delta = (observed - candidate["baseline"]) * candidate["direction"]
        settled.append({"id": candidate["id"], "game_id": game["game_id"], "version": report["version"],
                        "score": candidate["score"], "observed": observed, "reference": candidate["baseline"],
                        "reference_kind": candidate["baseline_kind"],
                        "outcome": "favorable" if delta > 0 else "unfavorable" if delta < 0 else "push"})
    return settled
