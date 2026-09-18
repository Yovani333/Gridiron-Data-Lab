"""Compose descriptive comparisons from frames. No downloads or predictions."""

from datetime import date

import polars as pl

from nfl_analytics.data.datasets import SeasonData
from nfl_analytics.data.games import as_date, recent_games, validate_team
from nfl_analytics.data.players import attach_players, injury_reports
from .form import head_to_head, summarize_games
from .play_by_play import advanced_summary
from .team_stats import box_score_summary


def _profile(data: SeasonData, team: str, *, before: date, games: int | None, season_type: str, venue: str = "all") -> dict:
    selected = recent_games(data.games, team, games, before=before, season_type=season_type, venue=venue)
    basic = box_score_summary(selected, data.stats.frame)
    advanced = advanced_summary(data.pbp.frame, selected, team)
    form = summarize_games(selected)
    basic["offense"]["points_per_game"] = form["points_per_game"]
    basic["defense"]["points_per_game"] = form["points_allowed_per_game"]
    if advanced is not None:
        for side in ("offense", "defense"):
            for metric in ("first_downs", "third_down_rate", "red_zone_td_rate"):
                basic[side][metric] = advanced[side][metric]
    return {"team": team, "form": form, "games": selected, "offense": basic["offense"],
            "defense": basic["defense"], "advanced": advanced, "venue": venue}


def _context(teams: pl.DataFrame | None, team_a: str, team_b: str) -> dict:
    result = {"team_a": {"abbreviation": team_a}, "team_b": {"abbreviation": team_b}, "relationship": "unknown"}
    if teams is None:
        return result
    for key, team in (("team_a", team_a), ("team_b", team_b)):
        rows = teams.filter(pl.col("team_abbr") == team)
        if rows.height:
            row = rows.row(0, named=True)
            result[key].update(name=row.get("team_name"), conference=row.get("team_conf"), division=row.get("team_division"))
    a, b = result["team_a"], result["team_b"]
    if a.get("conference") and b.get("conference"):
        result["relationship"] = ("divisional" if a.get("division") and a.get("division") == b.get("division")
                                  else "same_conference" if a["conference"] == b["conference"] else "interconference")
    return result


def compare_teams(data: SeasonData, team_a: str, team_b: str, *, before: date | str,
                  games: int | None = 5, season_type: str = "REG", injury_week: int | None = None,
                  history: pl.DataFrame | None = None, h2h_games: int | None = 5) -> dict:
    """Exclude the cutoff date and everything after it; window is within this season."""
    before = as_date(before)
    team_a, team_b = validate_team(team_a, data.games), validate_team(team_b, data.games)
    if team_a == team_b:
        raise ValueError("Choose two different teams")
    profiles = {team: _profile(data, team, before=before, games=games, season_type=season_type) for team in (team_a, team_b)}
    splits = {team: {venue: _profile(data, team, before=before, games=games, season_type=season_type, venue=venue)
                     for venue in ("home", "away")} for team in (team_a, team_b)}
    injuries = {}
    for team in (team_a, team_b):
        reports = None
        if data.injuries.frame is not None and injury_week is not None:
            reports = injury_reports(data.injuries.frame, team, injury_week, as_of=before)
            if data.rosters.frame is not None:
                reports = attach_players(reports, data.rosters.frame)
        injuries[team] = reports
    return {"team_a": profiles[team_a], "team_b": profiles[team_b], "home_away": splits,
            "head_to_head": head_to_head(history if history is not None else data.games, team_a, team_b, h2h_games, before=before, catalog=data.teams.frame),
            "injuries": injuries, "context": _context(data.teams.frame, team_a, team_b),
            "before": before, "window": games, "season_type": season_type, "season": data.season,
            "read_at": data.read_at, "injury_week": injury_week,
            "availability": {name: {"status": getattr(data, name).status, "message": getattr(data, name).message}
                             for name in ("stats", "injuries", "rosters", "pbp", "teams")}}


def analyze_matchup(data: SeasonData, game_id: str, **options) -> dict:
    rows = data.games.filter(pl.col("game_id") == game_id)
    if rows.height != 1:
        raise ValueError(f"Unknown game_id: {game_id}")
    game = rows.row(0, named=True)
    comparison = compare_teams(data, game["home_team"], game["away_team"], before=game["date"], injury_week=game["week"], **options)
    comparison["game"] = game
    # Schedule flags are game-specific; metadata describes the current alignment.
    if game["divisional"] is True:
        comparison["context"]["relationship"] = "divisional"
    elif game["divisional"] is False and comparison["context"]["relationship"] == "divisional":
        comparison["context"]["relationship"] = "historical_alignment_unavailable"
    return comparison
