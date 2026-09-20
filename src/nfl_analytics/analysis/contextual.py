"""Descriptive cross-matchup comparisons, without extra scoring weights."""


def contextual_metrics(matchup: dict) -> dict:
    game = matchup.get("game") or {}
    rest_a, rest_b = game.get("home_rest"), game.get("away_rest")
    result = {"rest_days": {"home": rest_a, "away": rest_b,
                           "difference": rest_a - rest_b if rest_a is not None and rest_b is not None else None},
              "efficiency": []}
    a, b = matchup["team_a"], matchup["team_b"]
    for own, opponent in ((a, b), (b, a)):
        for metric in ("epa_per_play", "success_rate", "points_per_drive"):
            attack = (own.get("advanced") or {}).get("offense", {})
            defense = (opponent.get("advanced") or {}).get("defense", {})
            x, y = attack.get(metric), defense.get(metric)
            full = all(p.get("requested_games", 0) > 0 and p.get("games_with_pbp") == p.get("requested_games") for p in (attack, defense))
            result["efficiency"].append({"team": own["team"], "opponent": opponent["team"], "metric": metric,
                                         "offense": x, "opponent_allowed": y,
                                         "difference": x - y if full and x is not None and y is not None else None,
                                         "complete_game_coverage": full})
    return result
