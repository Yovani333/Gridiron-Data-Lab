"""UI interaction tests use real domain logic and controlled, offline frames."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from nfl_analytics.presentation import dashboard, service
from nfl_analytics.data.datasets import Dataset


@pytest.fixture
def app(monkeypatch, bundle):
    monkeypatch.setattr(service, "initialize", lambda: None)
    monkeypatch.setattr(dashboard, "available_seasons", lambda: [2024])
    monkeypatch.setattr(dashboard, "calendar", lambda season: bundle.games)
    monkeypatch.setattr(dashboard, "analysis_data", lambda season, include_pbp: bundle)
    monkeypatch.setattr(dashboard, "player_data", lambda season: None)
    monkeypatch.setattr(service, "history", lambda: bundle.games)
    path = Path(__file__).resolve().parents[2] / "scripts/run_dashboard.py"
    return AppTest.from_file(str(path), default_timeout=30)


def test_dashboard_and_matchup(app):
    app.run()
    assert not app.exception
    app.session_state["selected_game"] = "c"
    app.run()
    assert not app.exception
    assert len(app.tabs) == 8
    assert any("no disponibles" in item.value.lower() for item in app.info)
    assert len(app.dataframe) >= 4


def test_date_with_no_games(app):
    app.run()
    next(r for r in app.radio if r.label == "Navegación").set_value("Partidos").run()
    next(r for r in app.radio if r.label == "Consultar por").set_value("Fecha").run()
    app.date_input[0].set_value(date(2024, 9, 16)).run()
    assert not app.exception
    assert any("No hay partidos" in item.value for item in app.info)


def test_direct_comparison(app):
    app.run()
    next(r for r in app.radio if r.label == "Navegación").set_value("Equipos").run()
    assert not app.exception
    assert len(app.tabs) == 8


def test_model_diagnostics_are_separate_from_game_view(app):
    app.run()
    next(r for r in app.radio if r.label == "Navegación").set_value("Datos").run()
    assert not app.exception
    assert any("benchmark" in item.value.lower() for item in app.warning)
    assert any("Brier" == item.label for item in app.metric)


def test_source_failure(app, monkeypatch):
    def unavailable():
        raise RuntimeError("source offline")
    monkeypatch.setattr(dashboard, "available_seasons", unavailable)
    app.run()
    assert not app.exception
    assert any("fuente de datos" in item.value for item in app.error)


def test_advanced_view_and_back(app, bundle, pbp):
    bundle.pbp = Dataset(pbp, "available", "")
    app.session_state["selected_game"] = "c"
    app.run()
    assert not app.exception
    assert any("con EPA válido" in item.value for item in app.caption)
    next(b for b in app.button if b.label == "← Volver a partidos").click().run()
    assert not app.exception
    assert any(r.label == "Navegación" for r in app.radio)
    assert not any(b.label == "← Volver a partidos" for b in app.button)
