"""Application orchestration. The Streamlit view consumes this interface only."""

from pathlib import Path
import json

import polars as pl

from nfl_analytics.analysis.matchup import analyze_matchup, compare_teams
from nfl_analytics.analysis.engine import analyze_probability
from nfl_analytics.analysis.probability import load_model
from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import SeasonData, season_data
from nfl_analytics.data.games import games_by_date, games_by_week


def initialize(cache_dir: str | Path = ".cache/nflreadpy") -> None:
    nfl_data.configure_cache(cache_dir)


def seasons() -> list[int]:
    return nfl_data.get_schedule_seasons()


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
