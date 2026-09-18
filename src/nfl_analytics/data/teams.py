"""Franchise identity derived from provider IDs, without a hardcoded team map."""

import polars as pl


def franchise_aliases(team: str, catalog: pl.DataFrame | None) -> list[str]:
    if catalog is None or not {"team_abbr", "team_id"} <= set(catalog.columns):
        return [team]
    row = catalog.filter(pl.col("team_abbr") == team)
    if row.is_empty() or row["team_id"][0] is None:
        return [team]
    return catalog.filter(pl.col("team_id") == row["team_id"][0])["team_abbr"].drop_nulls().unique().sort().to_list()
