"""Chronological evaluation of heuristic indices, separate from logistic models."""
from dataclasses import asdict
from hashlib import sha256
import json

import polars as pl

from .matchup import analyze_matchup
from .pick_config import PickConfig, PICK_VERSION
from .pick_engine import analyze_picks
from .pick_validation import settle_report
from .pick_benchmarks import benchmark_directions, settle_benchmarks, benchmark_report, wilson_interval


def fingerprint(frame: pl.DataFrame | None) -> str | None:
    if frame is None:
        return None
    # Row ordering is part of the snapshot, including optional provider revisions.
    return sha256(frame.write_json().encode()).hexdigest()


def evaluate_picks(data, *, history=None, window=5, config=PickConfig()) -> dict:
    """Every report excludes the target date. Outcomes enter only settlement.

    Without market lines, spread is a winning-side proxy and totals compare
    against the prior league baseline. These are not ATS/ROI/probability tests.
    """
    historical = data.games if history is None else history
    rows = data.games.filter((pl.col("season_type") == "REG") &
                             (pl.col("status") == "result_available")).sort(["date", "game_id"])
    decisions = []
    for game in rows.iter_rows(named=True):
        matchup = analyze_matchup(data, game["game_id"], history=historical, games=window)
        report = analyze_picks(matchup, data.games, config=config)
        outcomes = {row["id"]: row for row in settle_report(report, game)}
        for candidate in report["candidates"]:
            directions = benchmark_directions(matchup, candidate["market"])
            decisions.append({"game_id": game["game_id"], "date": game["date"].isoformat(),
                              "market": candidate["market"], "candidate": candidate["id"],
                              "status": candidate["status"], "score": candidate["score"],
                              "outcome": outcomes.get(candidate["id"], {}).get("outcome"),
                              "baseline": candidate["baseline"], "selection": candidate["selection"],
                              "input_game_ids": report["input_game_ids"],
                              "benchmark_directions": directions,
                              "benchmark_outcomes": settle_benchmarks(directions, game, candidate)})
    summaries = []
    for market in ("moneyline", "spread", "game_total", "team_total"):
        subset = [r for r in decisions if r["market"] == market]
        for low, high in ((0, 101), (0, 20), (20, 40), (40, 60), (60, 80), (80, 101)):
            selected = [r for r in subset if low <= r["score"] < high]
            wins = sum(r["outcome"] == "favorable" for r in selected)
            losses = sum(r["outcome"] == "unfavorable" for r in selected)
            pushes = sum(r["outcome"] == "push" for r in selected)
            abstentions = sum(r["outcome"] is None for r in selected)
            lo, hi = wilson_interval(wins, wins + losses)
            summaries.append({"market": market, "score_bucket": "all" if high == 101 and low == 0 else f"{low}-{min(high,100)}",
                              "opportunities": len(selected), "issued": wins + losses + pushes,
                              "abstentions": abstentions, "favorable": wins, "unfavorable": losses, "pushes": pushes,
                              "favorable_rate_excluding_pushes": wins / (wins + losses) if wins + losses else None,
                              "wilson95_low": lo, "wilson95_high": hi,
                              "resolved_sample": wins + losses,
                              "small_sample": wins + losses < 30})
    return {"version": PICK_VERSION, "season": data.season, "games": rows.height,
            "window": window, "config": asdict(config), "summaries": summaries, "decisions": decisions,
            "evaluation_version": "paired_benchmarks_v1", "benchmarks": benchmark_report(decisions),
            "fingerprints": {"games": fingerprint(data.games), "stats": fingerprint(data.stats.frame),
                             "history": fingerprint(historical)},
            "limitations": "Retrospective revised data; date-exclusive cutoff. No market odds, ATS, ROI, or calibrated probabilities."}


def save_report(report, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=True, allow_nan=False, indent=2)
