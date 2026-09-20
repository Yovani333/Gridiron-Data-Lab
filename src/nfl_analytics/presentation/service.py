"""Application orchestration. The Streamlit view consumes this interface only."""

from datetime import date
from pathlib import Path
import json

import polars as pl

from nfl_analytics.analysis.matchup import analyze_matchup, compare_teams
from nfl_analytics.analysis.engine import analyze_probability
from nfl_analytics.analysis.probability import load_model
from nfl_analytics.analysis.leaders import season_leaders
from nfl_analytics.analysis.signals import analyze_signal
from nfl_analytics.analysis.form import recent_form
from nfl_analytics.analysis.pick_engine import analyze_picks
from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import SeasonData, season_data
from nfl_analytics.data.games import games_by_date, games_by_week


def initialize(cache_dir: str | Path = ".cache/nflreadpy") -> None:
    nfl_data.configure_cache(cache_dir)


def seasons() -> list[int]:
    return nfl_data.get_schedule_seasons()


def team_identities() -> dict:
    """Optional visual metadata, never required for statistical calculations."""
    try:
        return {row["team_abbr"]: row for row in nfl_data.load_teams().to_dicts()}
    except (nfl_data.NFLDataError, ValueError):
        return {}


def calendar(season: int) -> pl.DataFrame:
    return nfl_data.get_games(season)


def filter_calendar(games: pl.DataFrame, *, day=None, week: int | None = None) -> pl.DataFrame:
    if day is not None:
        games = games_by_date(games, day)
    if week is not None:
        games = games_by_week(games, week)
    return games


def load_analysis(season: int, include_pbp: bool = False) -> SeasonData:
    return season_data(season, include_pbp=include_pbp)


def history() -> pl.DataFrame:
    """Full schedule is a small single file already cached by nflreadpy."""
    return nfl_data.get_games(seasons())


def upcoming(schedule: pl.DataFrame, *, today: date | None = None, limit: int = 4) -> list[dict]:
    """Future unscored games; schedules are not a live status feed."""
    today = today or date.today()
    games = (schedule.filter((pl.col("date") >= today) & (pl.col("status") != "result_available"))
             .sort(["date", "gametime", "game_id"]).head(limit).to_dicts())
    for game in games:
        game["records"] = {}
        for team in (game["home_team"], game["away_team"]):
            form = recent_form(schedule, team, games=None, before=game["date"], season_type="REG")
            game["records"][team] = f"{form['wins']}-{form['losses']}-{form['ties']}" if form["games"] else None
    return games


def overview(schedule: pl.DataFrame, *, seasons_available: list[int], players: pl.DataFrame | None) -> dict:
    teams = set(schedule["home_team"].drop_nulls().to_list()) | set(schedule["away_team"].drop_nulls().to_list())
    return {"teams": len(teams), "players": players["player_id"].drop_nulls().n_unique() if players is not None else None,
            "games": schedule.height, "seasons": (min(seasons_available), max(seasons_available)) if seasons_available else None}


def player_stats(season: int) -> pl.DataFrame | None:
    """Optional weekly player data; a missing publication must not break schedules."""
    try:
        return nfl_data.load_player_stats(season)
    except (nfl_data.NFLDataError, ValueError):
        return None


def leaders(players: pl.DataFrame | None, category: str) -> pl.DataFrame:
    return season_leaders(players, category) if players is not None else pl.DataFrame()


def result_distribution(schedule: pl.DataFrame) -> dict:
    completed = schedule.filter((pl.col("status") == "result_available") & (pl.col("season_type") == "REG"))
    return {"home": completed.filter(pl.col("home_score") > pl.col("away_score")).height,
            "away": completed.filter(pl.col("home_score") < pl.col("away_score")).height,
            "ties": completed.filter(pl.col("home_score") == pl.col("away_score")).height}


def featured_signals(data: SeasonData, games: list[dict]) -> list[dict]:
    try:
        historical = history()
    except nfl_data.NFLDataError:
        historical = data.games
    return [analyze_signal(data, game, history=historical) for game in games]


def featured_picks(data: SeasonData, games: list[dict]) -> list[dict]:
    """Reuse the descriptive pipeline; no probability model or quote downloads."""
    try:
        historical = history()
    except nfl_data.NFLDataError:
        historical = data.games
    return [analyze_picks(analyze_matchup(data, game["game_id"], history=historical), data.games) for game in games]


def matchup(data: SeasonData, game_id: str, *, games: int | None = 5, season_type: str = "REG", h2h_games: int | None = 5) -> dict:
    try:
        historical = history()
        history_warning = None
    except nfl_data.NFLDataError:
        historical = data.games
        history_warning = "Historial completo no disponible: se muestra solo la temporada seleccionada."
    result = analyze_matchup(data, game_id, games=games, season_type=season_type, history=historical, h2h_games=h2h_games)
    result["history_warning"] = history_warning
    game = result["game"]
    result["signal"] = analyze_signal(data, game, history=historical)
    result["potential_picks"] = analyze_picks(result, data.games)
    result["model"] = model_projection(data, game["home_team"], game["away_team"],
                                       as_of_date=game["date"], home_team=game["home_team"])
    return result


def comparison(data: SeasonData, team_a: str, team_b: str, **options) -> dict:
    try:
        historical = history()
        warning = None
    except nfl_data.NFLDataError:
        historical = data.games
        warning = "Historial completo no disponible: se muestra solo la temporada seleccionada."
    result = compare_teams(data, team_a, team_b, history=historical, **options)
    result["history_warning"] = warning
    result["potential_picks"] = analyze_picks(result, data.games)
    result["model"] = model_projection(data, team_a, team_b, as_of_date=result["before"])
    return result


_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "config"


def model_diagnostics() -> dict:
    """Frozen walk-forward report shipped with this model version."""
    report = json.loads((_ARTIFACT_DIR / "model_v0_1_diagnostics.json").read_text(encoding="utf-8"))
    model = load_model(_ARTIFACT_DIR / "model_v0_1.json")
    report["coefficients"] = dict(zip(model.features, model.coefficients))
    report["trained_games"] = model.trained_games
    report["trained_through"] = model.trained_through.isoformat()
    return report


def model_projection(data: SeasonData, team_a: str, team_b: str, *, as_of_date, home_team=None) -> dict:
    model = load_model(_ARTIFACT_DIR / "model_v0_1.json")
    return analyze_probability(data, model, team_a, team_b, as_of_date=as_of_date, home_team=home_team)
