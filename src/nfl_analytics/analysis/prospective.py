"""Freeze prospective evidence; settle later without regenerating selections."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import polars as pl

from .matchup import analyze_matchup
from .pick_engine import analyze_picks
from .pick_benchmarks import benchmark_directions, benchmark_report, settle_benchmarks
from .pick_validation import settle_report
from nfl_analytics.data.datasets import Dataset


def _digest(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def capture(data, game_id: str, *, history: pl.DataFrame, window: int = 5) -> dict:
    """Use the actual UTC clock; reject today, past games and published scores.

    Same-day games are deliberately excluded because schedules lack a verified
    kickoff timestamp. No caller-supplied historical capture timestamp is allowed.
    """
    started = datetime.now(timezone.utc)
    target = data.games.filter(pl.col("game_id") == game_id)
    if target.height != 1:
        raise ValueError("Expected exactly one scheduled game")
    game = target.row(0, named=True)
    if game["date"] <= started.date() or game["home_score"] is not None or game["away_score"] is not None:
        raise ValueError("Prospective capture requires a future date and no scores")
    if game["season_type"] != "REG":
        raise ValueError("Only regular season is supported")
    # Keep the target for context; all evidence ends before today's UTC date.
    past = data.games.filter(pl.col("date") < started.date())
    absent = Dataset(None, "not_loaded", "Not used by prospective_v1")
    frozen_data = replace(data, games=pl.concat([past, target]), injuries=absent, rosters=absent, pbp=absent)
    frozen_history = history.filter(pl.col("date") < started.date())
    matchup = analyze_matchup(frozen_data, game_id, history=frozen_history, games=window)
    report = analyze_picks(matchup, frozen_data.games)
    payload = {
        "schema": "prospective_v1", "captured_at": datetime.now(timezone.utc).isoformat(),
        "evidence_before": started.date().isoformat(), "source_read_at": data.read_at.isoformat(),
        "season": data.season, "scheduled_date": game["date"].isoformat(),
        "report": report,
        "benchmarks": {c["id"]: benchmark_directions(matchup, c["market"]) for c in report["candidates"]},
        "inputs": {"games": frozen_data.games.write_json(), "history": frozen_history.write_json(),
                   **{name: getattr(frozen_data, name).frame.write_json() if getattr(frozen_data, name).frame is not None else None
                      for name in ("stats", "teams", "injuries", "rosters", "pbp")}},
    }
    if datetime.fromisoformat(payload["captured_at"]).date() != started.date():
        raise ValueError("UTC day changed during capture; retry")
    return {"sha256": _digest(payload), "payload": payload}


def save_snapshot(snapshot: dict, directory: Path) -> Path:
    """One observation per game/version; exclusive creation forbids replacement."""
    payload = verify(snapshot)
    report = payload["report"]
    key = sha256(f'{report["version"]}:{report["game_id"]}'.encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{key}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=True, allow_nan=False)
    return path


def verify(snapshot: dict) -> dict:
    payload = snapshot["payload"]
    if payload["schema"] != "prospective_v1" or snapshot["sha256"] != _digest(payload):
        raise ValueError("Snapshot integrity check failed")
    return payload


def evaluate_snapshots(snapshots: list[dict], results: pl.DataFrame) -> dict:
    """Keep pending/abstained games; compare only frozen signals and benchmarks."""
    rows, states, seen = [], [], set()
    for snapshot in snapshots:
        payload = verify(snapshot)
        report = payload["report"]
        key = (report["version"], report["game_id"])
        if key in seen:
            raise ValueError("Duplicate game/version would bias evaluation")
        seen.add(key)
        found = results.filter(pl.col("game_id") == report["game_id"])
        if found.height > 1:
            raise ValueError("Duplicate game result")
        game = found.row(0, named=True) if found.height else None
        state = "pending"
        outcomes = {}
        if game is not None:
            if game["date"].isoformat() <= payload["captured_at"][:10]:
                state = "schedule_changed_requires_review"
            elif game["status"] == "result_available":
                outcomes = {r["id"]: r for r in settle_report(report, game)}
                state = "settled" if game["home_score"] is not None and game["away_score"] is not None else "pending"
        states.append({"game_id": report["game_id"], "state": state, "snapshot_sha256": snapshot["sha256"]})
        if state != "settled":
            continue
        for candidate in report["candidates"]:
            rows.append({"game_id": report["game_id"], "market": candidate["market"],
                         "candidate": candidate["id"], "score": candidate["score"],
                         "outcome": outcomes.get(candidate["id"], {}).get("outcome"),
                         "benchmark_outcomes": settle_benchmarks(payload["benchmarks"][candidate["id"]], game, candidate)})
    versions = {key[0] for key in seen}
    if len(versions) > 1:
        raise ValueError("Evaluate model versions separately")
    return {"evaluated_at": datetime.now(timezone.utc).isoformat(), "versions": sorted(versions),
            "games": states, "decisions": rows, "benchmarks": benchmark_report(rows),
            "limitations": "Statistical references, not sportsbook lines or calibrated probabilities. Local timestamps are not external attestations."}
