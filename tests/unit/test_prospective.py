from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone

import polars as pl
import pytest

from nfl_analytics.analysis import prospective


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 9, 24, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(prospective, "datetime", Clock)


def test_capture_excludes_future_results_and_preserves_original(bundle, clock, tmp_path):
    snapshot = prospective.capture(bundle, "e", history=bundle.games)
    report = snapshot["payload"]["report"]
    assert "f" not in report["league_game_ids"]
    assert "e" not in report["league_game_ids"]
    path = prospective.save_snapshot(snapshot, tmp_path)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        prospective.save_snapshot(snapshot, tmp_path)
    assert path.read_bytes() == original
    changed = deepcopy(snapshot)
    changed["payload"]["report"]["version"] = "changed"
    with pytest.raises(ValueError, match="integrity"):
        prospective.verify(changed)


def test_capture_rejects_past_and_published_results(bundle, clock):
    for game_id in ("a", "f"):
        with pytest.raises(ValueError, match="future date"):
            prospective.capture(bundle, game_id, history=bundle.games)
    today = replace(bundle, games=bundle.games.with_columns(
        pl.when(pl.col("game_id") == "e").then(pl.lit(datetime(2024, 9, 24).date())).otherwise(pl.col("date")).alias("date")))
    with pytest.raises(ValueError, match="future date"):
        prospective.capture(today, "e", history=today.games)


def test_settlement_uses_frozen_report_and_tracks_pending(bundle, clock, monkeypatch):
    snapshot = prospective.capture(bundle, "e", history=bundle.games)
    assert prospective.evaluate_snapshots([snapshot], bundle.games)["games"][0]["state"] == "pending"
    original = deepcopy(snapshot)
    def forbidden(*args, **kwargs):
        pytest.fail("Settlement must not regenerate picks")
    monkeypatch.setattr(prospective, "analyze_picks", forbidden)
    results = bundle.games.with_columns(
        pl.when(pl.col("game_id") == "e").then(30).otherwise(pl.col("home_score")).alias("home_score"),
        pl.when(pl.col("game_id") == "e").then(17).otherwise(pl.col("away_score")).alias("away_score"),
        pl.when(pl.col("game_id") == "e").then(pl.lit("result_available")).otherwise(pl.col("status")).alias("status"))
    evaluation = prospective.evaluate_snapshots([snapshot], results)
    assert evaluation["games"][0]["state"] == "settled"
    assert len(evaluation["decisions"]) == 5
    assert snapshot == original
    with pytest.raises(ValueError, match="Duplicate"):
        prospective.evaluate_snapshots([snapshot, snapshot], results)
    moved = results.with_columns(pl.lit(datetime(2024, 9, 23).date()).alias("date"))
    assert prospective.evaluate_snapshots([snapshot], moved)["games"][0]["state"] == "schedule_changed_requires_review"
