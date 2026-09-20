"""Build pregame evidence from the existing comparison; never downloads data."""

from math import isfinite

import polars as pl

from .form import summarize_games
from .pick_config import PickConfig


def finite(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) else None


def _team_evidence(profile: dict, split: dict | None, cutoff, config: PickConfig) -> dict:
    rows = profile["games"].filter((pl.col("date") < cutoff) & (pl.col("season_type") == "REG"))
    rows = rows.sort(["date", "game_id"], descending=True)
    form = summarize_games(rows)
    latest = rows.row(0, named=True) if rows.height else None
    split_form = split["form"] if split is not None and split["form"]["games"] >= config.min_split_games else None
    trend = None
    if rows.height >= config.trend_recent_games + config.trend_older_games:
        trend = rows.head(config.trend_recent_games)["point_diff"].mean() - rows.slice(config.trend_recent_games)["point_diff"].mean()
    # A partial box-score sample is never treated as the whole selected window.
    efficiency = None
    if rows.height and all(profile[side]["games_with_stats"] == rows.height for side in ("offense", "defense")):
        own = finite(profile["offense"].get("yards_per_play"))
        allowed = finite(profile["defense"].get("yards_per_play"))
        if own is not None and allowed is not None:
            efficiency = own - allowed
    return {"team": profile["team"], "form": form, "split": split_form,
            "last": latest, "trend": trend, "net_yards_per_play": efficiency,
            "game_ids": rows["game_id"].to_list()}


def build_evidence(matchup: dict, schedule: pl.DataFrame, config: PickConfig) -> dict:
    """All league references use same-season completed REG games before cutoff."""
    cutoff = matchup["before"]
    a, b = matchup["team_a"], matchup["team_b"]
    game = matchup.get("game")
    splits = matchup["home_away"]
    venue_known = bool(game and not game["neutral_site"])
    profiles = []
    for profile in (a, b):
        venue = "home" if game and profile["team"] == game["home_team"] else "away"
        profiles.append(_team_evidence(profile, splits[profile["team"]][venue] if venue_known else None, cutoff, config))
    prior = schedule.filter((pl.col("date") < cutoff) & (pl.col("season") == matchup["season"]) &
                            (pl.col("season_type") == "REG") & (pl.col("status") == "result_available"))
    league_ppg = None
    if prior.height >= config.min_league_games:
        league_ppg = finite(prior.select(((pl.col("home_score") + pl.col("away_score")) / 2).mean()).item())
    h2h = matchup["head_to_head"]["games"].filter(
        (pl.col("date") < cutoff) & (pl.col("season_type") == "REG") &
        (pl.col("season") >= matchup["season"] - config.h2h_seasons + 1)
    ).sort(["date", "game_id"], descending=True).head(config.h2h_games)
    injuries = {}
    for profile in profiles:
        reports = matchup["injuries"].get(profile["team"])
        # Date-only cutoff cannot establish that a same-day report preceded kickoff.
        known = None if reports is None else reports.filter(pl.col("reported_at").dt.date() < cutoff)
        injuries[profile["team"]] = {"status": matchup.get("injury_quality", {}).get(profile["team"], "unavailable" if known is None else "dated_reports_only"),
                                     "reports": None if known is None else known.height,
                                     "positions": [] if known is None else known["position"].drop_nulls().unique().sort().to_list(),
                                     "scored": False}
    references = {}
    for own, opponent in ((profiles[0], profiles[1]), (profiles[1], profiles[0])):
        pf, pa = finite(own["form"]["points_per_game"]), finite(opponent["form"]["points_allowed_per_game"])
        points = None if pf is None or pa is None else (pf + pa) / 2
        if points is not None and own["split"] and opponent["split"]:
            venue_points = (own["split"]["points_per_game"] + opponent["split"]["points_allowed_per_game"]) / 2
            points = (1 - config.venue_share) * points + config.venue_share * venue_points
        references[own["team"]] = points
    return {"team_a": profiles[0], "team_b": profiles[1], "league_ppg": league_ppg,
            "league_games": prior.height, "league_game_ids": prior["game_id"].to_list(),
            "h2h": h2h, "context": matchup["context"], "injuries": injuries,
            "point_references": references, "cutoff": cutoff, "venue_known": venue_known}
