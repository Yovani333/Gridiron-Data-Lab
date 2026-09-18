"""Transparent matchup contrasts; a signal is descriptive, never a pick."""

from datetime import date

import polars as pl

from nfl_analytics.data.datasets import SeasonData
from nfl_analytics.data.games import recent_games

from .form import head_to_head, summarize_games
from .signal_config import SignalConfig


_FACTORS = (
    ("recent_form", "Mejor porcentaje de victorias recientes", "win_pct", False),
    ("point_differential", "Mejor diferencial reciente", "avg_margin", False),
    ("offense", "Más puntos anotados por partido", "points_per_game", False),
    ("defense", "Menos puntos permitidos por partido", "points_allowed_per_game", True),
)


def analyze_signal(data: SeasonData, game: dict, *, config: SignalConfig = SignalConfig(),
                   history: pl.DataFrame | None = None) -> dict:
    """Use only finalized REG games dated before the matchup; tie => no lean."""
    cutoff: date = game["date"]
    home, away = game["home_team"], game["away_team"]
    selected = {team: recent_games(data.games, team, config.recent_games, before=cutoff,
                                   season_type="REG") for team in (home, away)}
    forms = {team: summarize_games(rows) for team, rows in selected.items()}
    result = {"game_id": game["game_id"], "home": home, "away": away,
              "samples": {team: forms[team]["games"] for team in (home, away)},
              "factors": [], "score": 0.0, "lean": None, "level": None}
    if min(result["samples"].values()) < config.min_games:
        result["status"] = "insufficient_data"
        return result
    score = 0.0

    def add(key: str, label: str, advantage: str) -> None:
        nonlocal score
        points = config.weights[key] * (1 if advantage == home else -1)
        score += points
        result["factors"].append({"key": key, "label": label, "team": advantage, "points": points})

    for key, label, metric, lower_is_better in _FACTORS:
        a, b = forms[home][metric], forms[away][metric]
        if a is not None and b is not None and a != b:
            add(key, label, home if (a < b if lower_is_better else a > b) else away)

    home_split = summarize_games(recent_games(data.games, home, config.recent_games,
                                               before=cutoff, season_type="REG", venue="home"))
    away_split = summarize_games(recent_games(data.games, away, config.recent_games,
                                               before=cutoff, season_type="REG", venue="away"))
    if min(home_split["games"], away_split["games"]) >= config.min_split_games:
        a, b = home_split["win_pct"], away_split["win_pct"]
        if a != b:
            add("home_away", "Mejor récord local/visitante en la muestra", home if a > b else away)

    h2h = head_to_head(history if history is not None else data.games, home, away, config.recent_games,
                       before=cutoff, catalog=data.teams.frame)
    if h2h["games"].height >= config.min_h2h_games and h2h["team_a_wins"] != h2h["team_b_wins"]:
        add("head_to_head", "Más triunfos en los últimos enfrentamientos", home if h2h["team_a_wins"] > h2h["team_b_wins"] else away)

    result["score"] = score
    result["status"] = "descriptive_only"
    if score:
        result["lean"] = home if score > 0 else away
        magnitude = abs(score)
        result["level"] = ("Alta" if magnitude >= config.high_threshold else
                           "Media" if magnitude >= config.medium_threshold else "Baja")
    return result
