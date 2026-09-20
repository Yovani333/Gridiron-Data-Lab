"""Fixed pregame rules and paired comparisons on identical issued candidates.

No fitting, score reweighting, probability calibration or odds are involved.
"""
from math import sqrt


BUCKETS = ((0, 20), (20, 40), (40, 60), (60, 80), (80, 101))


def benchmark_directions(matchup: dict, market: str) -> dict[str, int | None]:
    """Side rules use the same recent window as the score; ties choose home.

    Team A is home in game reports, including the administrative home at a
    neutral venue. Always-home is a benchmark convention, not a home bonus.
    Totals rules compare against the exact statistical baseline of the candidate.
    """
    if market in ("game_total", "team_total"):
        return {"always_over": 1, "always_under": -1}
    a, b = matchup["team_a"]["form"], matchup["team_b"]["form"]
    def choose(key):
        return None if a[key] is None or b[key] is None else 1 if a[key] >= b[key] else -1
    return {"always_home": 1, "better_recent_record": choose("win_pct"),
            "better_recent_margin": choose("avg_margin")}


def settle_benchmarks(directions: dict, game: dict, candidate: dict) -> dict:
    """Outcomes are computed only after directions have been generated."""
    market = candidate["market"]
    if market in ("moneyline", "spread"):
        observed = game["home_score"] - game["away_score"]
    elif market == "game_total":
        observed = game["home_score"] + game["away_score"]
    else:
        observed = game["home_score"] if candidate["team"] == game["home_team"] else game["away_score"]
    baseline = candidate["baseline"]
    return {name: None if direction is None or baseline is None else
            "push" if observed == baseline else
            "favorable" if (observed - baseline) * direction > 0 else "unfavorable"
            for name, direction in directions.items()}


def wilson_interval(wins: int, total: int) -> tuple[float | None, float | None]:
    """Descriptive 95% binomial interval; games/team totals are not independent."""
    if not total:
        return None, None
    z = 1.959963984540054
    p = wins / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * sqrt(p * (1-p) / total + z*z / (4*total*total)) / denominator
    return max(0.0, center-half), min(1.0, center+half)


def benchmark_report(decisions: list[dict]) -> list[dict]:
    """Only compare non-push predictions on the same game/candidate IDs.

    Abstentions never enter win rates. Missing benchmark values remove the same
    candidate from BOTH denominators. Bands are score indices, not probabilities.
    """
    result = []
    for market in ("moneyline", "spread", "game_total", "team_total"):
        rows = [r for r in decisions if r["market"] == market]
        names = sorted({key for r in rows for key in r["benchmark_outcomes"]})
        for bucket, low, high in [("all", 0, 101)] + [(f"{low}–{min(high,100)}", low, high) for low, high in BUCKETS]:
            band = [r for r in rows if low <= r["score"] < high]
            issued = [r for r in band if r["outcome"] is not None]
            for name in names:
                paired = [r for r in issued if r["outcome"] != "push" and
                          r["benchmark_outcomes"].get(name) in ("favorable", "unfavorable")]
                n = len(paired)
                ours = sum(r["outcome"] == "favorable" for r in paired)
                baseline = sum(r["benchmark_outcomes"][name] == "favorable" for r in paired)
                only_ours = sum(r["outcome"] == "favorable" and r["benchmark_outcomes"][name] == "unfavorable" for r in paired)
                only_baseline = sum(r["outcome"] == "unfavorable" and r["benchmark_outcomes"][name] == "favorable" for r in paired)
                lo, hi = wilson_interval(ours, n)
                result.append({"market": market, "score_bucket": bucket, "benchmark": name,
                               "opportunities": len(band), "issued": len(issued),
                               "abstentions": len(band)-len(issued), "paired_games": n,
                               "excluded_push_or_missing": len(issued)-n,
                               "score_wins": ours, "benchmark_wins": baseline,
                               "score_rate": ours/n if n else None,
                               "benchmark_rate": baseline/n if n else None,
                               "difference_percentage_points": 100*(ours-baseline)/n if n else None,
                               "only_score_wins": only_ours, "only_benchmark_wins": only_baseline,
                               "score_wilson95_low": lo, "score_wilson95_high": hi,
                               "sample_note": "no observations" if not n else "small sample (<30)" if n < 30 else "descriptive sample; dependence not adjusted"})
    return result
