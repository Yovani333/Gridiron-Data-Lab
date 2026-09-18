"""Dataset availability belongs to data access, not to the user interface."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import polars as pl

from . import nfl_data


@dataclass
class Dataset:
    frame: pl.DataFrame | None
    status: str
    message: str


@dataclass
class SeasonData:
    season: int
    games: pl.DataFrame
    teams: Dataset
    stats: Dataset
    injuries: Dataset
    rosters: Dataset
    pbp: Dataset
    read_at: datetime


def optional_dataset(loader: Callable[[], pl.DataFrame]) -> Dataset:
    try:
        return Dataset(loader(), "available", "Datos disponibles; la cobertura se comprueba por partido.")
    except (nfl_data.NFLDataError, ValueError) as exc:
        return Dataset(None, "unavailable", str(exc))


def season_data(season: int, *, include_pbp: bool = False) -> SeasonData:
    """PBP is explicitly opt-in; failures in optional sources do not hide games."""
    games = nfl_data.get_games(season)
    return SeasonData(
        season=season, games=games,
        teams=optional_dataset(nfl_data.load_teams),
        stats=optional_dataset(lambda: nfl_data.get_team_stats(season)),
        injuries=optional_dataset(lambda: nfl_data.load_injuries(season)),
        rosters=optional_dataset(lambda: nfl_data.load_rosters(season)),
        pbp=optional_dataset(lambda: nfl_data.load_play_by_play(season)) if include_pbp else Dataset(None, "not_loaded", "Activa las métricas avanzadas para consultar EPA y Success Rate."),
        read_at=datetime.now(timezone.utc),
    )
