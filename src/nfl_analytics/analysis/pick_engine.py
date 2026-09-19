"""Rank market-specific statistical leans with optional timestamped market lines."""

from dataclasses import asdict

import polars as pl

from .market_analysis import moneyline_factors, points_factors, score_factors
from .market_lines import MarketLine
from .matchup_evidence import build_evidence
from .pick_config import PICK_VERSION, PickConfig


def analyze_picks(matchup: dict, schedule: pl.DataFrame, *, config: PickConfig = PickConfig(),
                  lines: tuple[MarketLine, ...] = ()) -> dict:
    """Snapshot is deterministic for the same cutoff, data, window and config.

    Spread value is the signed handicap applied to quote.team (e.g. -3.5).
    No line is inferred from point references or historical closing odds.
    """
    evidence = build_evidence(matchup, schedule, config)
    a, b = evidence["team_a"], evidence["team_b"]
    teams = (a["team"], b["team"])
    game_id = matchup.get("game", {}).get("game_id")
    sample = min(a["form"]["games"], b["form"]["games"])
    report = {"version": PICK_VERSION, "game_id": game_id, "as_of_date": matchup["before"].isoformat(),
              "window": matchup["window"], "config": asdict(config), "teams": teams,
              "samples": {p["team"]: p["form"]["games"] for p in (a, b)},
              "input_game_ids": {p["team"]: p["game_ids"] for p in (a, b)},
              "league_games": evidence["league_games"], "league_ppg": evidence["league_ppg"],
              "league_game_ids": evidence["league_game_ids"], "h2h_game_ids": evidence["h2h"]["game_id"].to_list(),
              "point_references": evidence["point_references"], "context": evidence["context"],
              "injuries": evidence["injuries"], "candidates": [], "best": None,
              "context_note": "División, conferencia y lesiones son contexto; no suman puntos sin una metodología validada."}
    quotes = {}
    for quote in lines:
        quote.validate_for(game_id, teams, matchup["before"])
        key = (quote.market, quote.team if quote.market == "team_total" else None)
        if key in quotes:
            raise ValueError("Only one quote per market/team is supported")
        quotes[key] = quote
    for market, team in (("moneyline", None), ("spread", None), ("game_total", None),
                         ("team_total", teams[0]), ("team_total", teams[1])):
        quote = quotes.get((market, team))
        candidate = _candidate(evidence, market, team, quote, sample, config)
        if matchup["season_type"] != "REG" or matchup.get("game", {}).get("season_type", "REG") != "REG":
            candidate.update(status="unsupported_season_type", selection=None)
        report["candidates"].append(candidate)
    ranked = sorted((c for c in report["candidates"] if c["status"] in ("statistical_lean", "market_candidate")),
                    key=lambda c: (-c["score"], c["id"]))
    report["ranking"] = [c["id"] for c in ranked]
    report["best"] = ranked[0]["id"] if ranked else None
    return report


def _candidate(e: dict, market: str, team: str | None, quote: MarketLine | None,
               sample: int, config: PickConfig) -> dict:
    ta, tb = e["team_a"]["team"], e["team_b"]["team"]
    pa, pb = e["point_references"][ta], e["point_references"][tb]
    expected = None
    if pa is not None and pb is not None:
        expected = pa - pb if market in ("moneyline", "spread") else pa + pb if market == "game_total" else e["point_references"][team]
    baseline = 0.0 if market in ("moneyline", "spread") else (
        None if e["league_ppg"] is None else e["league_ppg"] * (2 if market == "game_total" else 1))
    baseline_kind = "zero_margin" if market in ("moneyline", "spread") else "pregame_league_average"
    if quote and market != "moneyline":
        baseline = (-quote.value if quote.team == ta else quote.value) if market == "spread" else quote.value
        baseline_kind = "market_line"
    factors = moneyline_factors(e, config) if market == "moneyline" else points_factors(e, market, baseline, config, team=team)
    scored = score_factors(factors, config.side_weights if market == "moneyline" else config.points_weights, sample, config)
    direction = scored["direction"]
    selected_team = ta if direction > 0 else tb if direction < 0 else None
    selection = selected_team if market in ("moneyline", "spread") else (
        (f"{team} · " if team else "") + ("Over" if direction > 0 else "Under")) if direction else None
    status = "statistical_lean" if scored["eligible"] else "no_strong_signal"
    if sample < config.min_games:
        status = "insufficient_data"
    elif baseline is None:
        status = "missing_reference"
    # The scoring direction must agree with the point reference for points markets.
    if market != "moneyline" and status == "statistical_lean":
        if expected is None or (expected - baseline) * direction < config.line_buffer:
            status = "no_strong_signal"
    if status != "statistical_lean":
        selection = None
    elif quote:
        if market == "moneyline" and selected_team != quote.team:
            # A quote for the other team does not supply a price for the lean.
            baseline_kind = "opposite_team_quote"
        else:
            status = "market_candidate"
            if market == "moneyline":
                selection = f"{selected_team} ML @ {quote.decimal_price:g}"
            elif market == "spread":
                handicap = quote.value if selected_team == quote.team else -quote.value
                selection = f"{selected_team} {handicap:+g}"
            else:
                selection = f"{selection} {quote.value:g}"
    if status == "statistical_lean":
        selection += " side" if market == "spread" else " lean"
    return {**scored, "id": market + (f":{team}" if team else ""), "market": market,
            "team": team, "selection": selection, "status": status,
            "point_reference": expected, "baseline": baseline, "baseline_kind": baseline_kind,
            "line": quote.snapshot() if quote else None,
            "difference_points": None if expected is None or baseline is None else expected - baseline,
            "price_edge": None, "probability": None}
