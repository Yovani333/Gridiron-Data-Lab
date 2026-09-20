"""Pregame measurements from published results, with an exclusive date cutoff.

The schedule has dates rather than verified publication timestamps. Excluding
the whole game day is conservative; revised historical files cannot establish
exactly what was published at a past kickoff.
"""

from datetime import date
from math import isfinite

import polars as pl

from nfl_analytics.data.datasets import SeasonData
from nfl_analytics.data.games import as_date, recent_games, validate_team

from .form import head_to_head, summarize_games
from .model_config import FEATURE_NAMES, ModelConfig
from .play_by_play import advanced_summary
from .team_stats import box_score_summary


def _opponent_strength(schedule: pl.DataFrame, selected: pl.DataFrame) -> float | None:
    """Mean opponent pregame point differential per game, as known before each meeting."""
    known = []
    for played in selected.iter_rows(named=True):
        prior = recent_games(schedule, played["opponent"], None, before=played["date"], season_type="REG")
        if prior.height:
            known.append(summarize_games(prior)["avg_margin"])
    return sum(known) / len(known) if known else None


def team_features(data: SeasonData, team: str, *, as_of_date: date | str,
                  config: ModelConfig = ModelConfig(), venue: str = "all") -> dict:
    cutoff = as_date(as_of_date)
    team = validate_team(team, data.games)
    selected = recent_games(data.games, team, config.recent_games, before=cutoff,
                            season_type="REG", venue=venue)
    form = summarize_games(selected)
    box = box_score_summary(selected, data.stats.frame)
    advanced = advanced_summary(data.pbp.frame, selected, team) if data.pbp.frame is not None else None
    offense, defense = box["offense"], box["defense"]
    return {
        "team": team, "as_of_date": cutoff, "games": form["games"],
        "win_pct": form["win_pct"], "points_per_game": form["points_per_game"],
        "points_allowed_per_game": form["points_allowed_per_game"],
        "point_diff": form["avg_margin"],
        "yards_per_game": offense["yards_per_game"],
        "yards_per_play": offense["yards_per_play"],
        "passing_yards_per_game": offense["passing_yards_per_game"],
        "rushing_yards_per_game": offense["rushing_yards_per_game"],
        "touchdowns": offense["touchdowns"], "sacks_allowed": offense["sacks"],
        "yards_allowed_per_game": defense["yards_per_game"],
        "yards_per_play_allowed": defense["yards_per_play"],
        "turnovers": offense["turnovers"], "turnovers_generated": defense["turnovers"],
        "turnover_margin": (defense["turnovers"] - offense["turnovers"]
                            if defense["turnovers"] is not None and offense["turnovers"] is not None else None),
        "opponent_strength": _opponent_strength(data.games, selected),
        "offensive_epa": advanced["offense"]["epa_per_play"] if advanced else None,
        "defensive_epa_allowed": advanced["defense"]["epa_per_play"] if advanced else None,
        "passing_epa": advanced["offense"]["passing_epa_per_play"] if advanced else None,
        "rushing_epa": advanced["offense"]["rushing_epa_per_play"] if advanced else None,
        "success_rate": advanced["offense"]["success_rate"] if advanced else None,
        "success_rate_allowed": advanced["defense"]["success_rate"] if advanced else None,
        "explosive_play_rate": advanced["offense"]["explosive_play_rate"] if advanced else None,
        "box_games": offense["games_with_stats"],
        "defense_box_games": defense["games_with_stats"],
    }


def matchup_features(data: SeasonData, team_a: str, team_b: str, *, as_of_date: date | str,
                     home_team: str | None = None, config: ModelConfig = ModelConfig(),
                     history: pl.DataFrame | None = None) -> dict:
    """All differences are A minus B; positive means more of that measurement.

    Defensive EPA allowed is reversed so a positive difference favors A.
    A reported injury is not a point-in-time archive and is not a model input.
    """
    cutoff = as_date(as_of_date)
    if team_a == team_b:
        raise ValueError("Teams must differ")
    if home_team not in (None, team_a, team_b):
        raise ValueError("home_team must be one of the selected teams or None")
    a = team_features(data, team_a, as_of_date=cutoff, config=config)
    b = team_features(data, team_b, as_of_date=cutoff, config=config)
    def diff(key: str, reverse: bool = False) -> float | None:
        x, y = a[key], b[key]
        if x is None or y is None or not isfinite(x) or not isfinite(y):
            return None
        return (y - x) if reverse else (x - y)
    row = {
        "win_pct_diff": diff("win_pct"), "point_diff_diff": diff("point_diff"),
        "yards_per_play_diff": diff("yards_per_play"),
        "turnover_margin_diff": diff("turnover_margin"),
        "opponent_strength_diff": diff("opponent_strength"),
        "home_field": 1.0 if home_team == team_a else -1.0 if home_team == team_b else 0.0,
        "offensive_epa_diff": diff("offensive_epa"),
        "defensive_epa_diff": diff("defensive_epa_allowed", reverse=True),
        "success_rate_diff": diff("success_rate"),
    }
    matchup = data.games.filter((pl.col("date") == cutoff) &
                                (((pl.col("home_team") == team_a) & (pl.col("away_team") == team_b)) |
                                 ((pl.col("home_team") == team_b) & (pl.col("away_team") == team_a))))
    divisional = matchup.row(0, named=True)["divisional"] if matchup.height else None
    meta = data.teams.frame
    conf_a = meta.filter(pl.col("team_abbr") == team_a)["team_conf"].to_list() if meta is not None else []
    conf_b = meta.filter(pl.col("team_abbr") == team_b)["team_conf"].to_list() if meta is not None else []
    h2h = head_to_head(history if history is not None else data.games, team_a, team_b, 5,
                       before=cutoff, catalog=meta)
    return {"team_a": a, "team_b": b, "as_of_date": cutoff, "values": row,
            "model_ready": all(row[k] is not None for k in FEATURE_NAMES) and
                           min(a["games"], b["games"]) >= config.min_games and
                           all(p["box_games"] == p["defense_box_games"] == p["games"] for p in (a, b)),
            "context": {"divisional": divisional, "same_conference": conf_a[0] == conf_b[0] if conf_a and conf_b else None,
                        "interconference": conf_a[0] != conf_b[0] if conf_a and conf_b else None,
                        "h2h_a_wins": h2h["team_a_wins"], "h2h_b_wins": h2h["team_b_wins"],
                        "h2h_a_margin": h2h["team_a_avg_margin"], "h2h_a_points": h2h["team_a_avg_points"],
                        "injuries": "not_point_in_time_verified"}}
