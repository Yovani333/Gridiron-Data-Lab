"""Public NFL data access; consumers need not import nflreadpy."""

from .nfl_data import (
    NFLDataError,
    configure_cache,
    get_current_season,
    get_current_week,
    get_latest_completed_week,
    get_schedule_seasons,
    load_injuries,
    load_play_by_play,
    load_player_stats,
    load_rosters,
    load_schedules,
    load_team_stats,
    load_teams,
    get_games,
    get_games_by_date,
    get_games_by_week,
    get_team_games,
    get_recent_games,
    get_team_stats,
)

__all__ = [
    "NFLDataError", "configure_cache", "get_current_season", "get_current_week",
    "get_latest_completed_week", "get_schedule_seasons", "load_injuries",
    "load_play_by_play", "load_player_stats", "load_rosters", "load_schedules",
    "load_team_stats", "load_teams",
    "get_games", "get_games_by_date", "get_games_by_week", "get_team_games",
    "get_recent_games", "get_team_stats",
]
