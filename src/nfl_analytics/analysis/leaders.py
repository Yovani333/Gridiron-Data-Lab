"""Season leaderboards from weekly nflverse player statistics."""

import polars as pl

from nfl_analytics.data.games import require_columns


LEADER_CATEGORIES = {
    "Passing": ("passing_yards", "passing_tds", "passing_interceptions"),
    "Rushing": ("rushing_yards", "rushing_tds", "carries"),
    "Receiving": ("receiving_yards", "receiving_tds", "receptions"),
    "Defense": ("def_tackles_solo", "def_sacks", "def_interceptions"),
}


def season_leaders(frame: pl.DataFrame, category: str, *, limit: int = 10) -> pl.DataFrame:
    """Aggregate REG weekly rows once per player; missing columns remain unavailable."""
    if category not in LEADER_CATEGORIES or type(limit) is not int or limit < 1:
        raise ValueError("Invalid leaderboard category or limit")
    require_columns(frame, {"player_id", "season_type", "team"})
    metrics = LEADER_CATEGORIES[category]
    if metrics[0] not in frame.columns:
        return pl.DataFrame()
    name = "player_display_name" if "player_display_name" in frame.columns else "player_name"
    require_columns(frame, {name})
    selected = frame.filter((pl.col("season_type") == "REG") & pl.col("player_id").is_not_null())
    if selected.is_empty():
        return pl.DataFrame()
    aggregations = [pl.col(name).drop_nulls().last().alias("player"),
                    pl.col("team").drop_nulls().last().alias("team")]
    if "headshot_url" in frame.columns:
        aggregations.append(pl.col("headshot_url").drop_nulls().last())
    for metric in metrics:
        if metric in frame.columns:
            # null-only player metrics are not converted into a fabricated zero.
            aggregations.append(pl.when(pl.col(metric).is_not_null().any())
                                .then(pl.col(metric).sum()).otherwise(None).alias(metric))
    return (selected.group_by("player_id").agg(aggregations)
            .filter(pl.col(metrics[0]).is_not_null() & (pl.col(metrics[0]) > 0))
            .sort(metrics[0], descending=True).head(limit)
            .select("player", "team", *(["headshot_url"] if "headshot_url" in frame.columns else []),
                    *[m for m in metrics if m in frame.columns]))
