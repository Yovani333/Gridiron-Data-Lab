"""Temporary Python UI. Acquisition and analysis are delegated to service."""

from datetime import date

import streamlit as st

from . import service
from .components import brand, game_card, hero
from .matchup_view import render_matchup


@st.cache_data(ttl=900, show_spinner=False)
def available_seasons():
    return service.seasons()


@st.cache_data(ttl=900, show_spinner=False)
def calendar(season):
    return service.calendar(season)


@st.cache_data(ttl=900, max_entries=4, show_spinner=False)
def analysis_data(season, include_pbp):
    return service.load_analysis(season, include_pbp)


def main() -> None:
    st.set_page_config(page_title="Gridiron · NFL Analytics", page_icon="🏈", layout="wide")
    brand()
    service.initialize()
    with st.sidebar:
        st.markdown("### Tu laboratorio NFL")
        st.caption("Explora resultados. Contrasta equipos. Comprueba la muestra.")
        if st.button("Actualizar vista", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption("Los datos descargados se reutilizan hasta 24 h. La fuente puede tardar en publicar resultados.")
    try:
        with st.spinner("Consultando temporadas y calendario…"):
            years = available_seasons()
            if not years:
                st.info("No hay temporadas disponibles.")
                return
            season = st.sidebar.selectbox("Temporada", years, index=len(years) - 1)
            games = calendar(season)
        mode = st.sidebar.radio("Explorar", ["Partidos", "Comparar equipos"])
        window_label = st.sidebar.selectbox("Ventana de análisis", ["Último partido", "Últimos 3", "Últimos 5", "Personalizada", "Temporada completa"], index=2)
        window = {"Último partido": 1, "Últimos 3": 3, "Últimos 5": 5, "Temporada completa": None}.get(window_label)
        if window_label == "Personalizada":
            window = st.sidebar.number_input("Número de partidos", min_value=1, max_value=100, value=5, step=1)
        season_type = st.sidebar.selectbox("Tipo de temporada", ["REG", "POST", "all"], format_func=lambda x: {"REG": "Regular", "POST": "Playoffs", "all": "Regular + playoffs"}[x])
        h2h_label = st.sidebar.selectbox("Enfrentamientos anteriores", ["3", "5", "10", "Todos"], index=1)
        h2h_count = None if h2h_label == "Todos" else int(h2h_label)
        include_pbp = st.sidebar.checkbox("Incluir métricas avanzadas", help="Consulta una temporada de play-by-play; la primera carga es más lenta.")
        st.sidebar.caption("Fuente única: nflverse mediante nflreadpy. Sin predicciones ni recomendaciones.")
        if mode == "Comparar equipos":
            _comparison(games, season, window, season_type, h2h_count, include_pbp)
            return
        selected = st.session_state.get("selected_game")
        if selected and selected in games["game_id"].to_list():
            if st.button("← Volver a partidos"):
                st.session_state.pop("selected_game", None)
                st.rerun()
            with st.spinner("Preparando comparación y verificando cobertura…"):
                data = analysis_data(season, include_pbp)
                result = service.matchup(data, selected, games=window, season_type=season_type, h2h_games=h2h_count)
            render_matchup(result)
            return
        hero("El juego, en perspectiva.", "Resultados, rendimiento reciente y contexto para entender cada enfrentamiento.")
        filter_mode = st.radio("Consultar por", ["Semana", "Fecha", "Temporada"], horizontal=True)
        day, week = None, None
        if filter_mode == "Fecha":
            day = st.date_input("Fecha del calendario NFL", value=date.today())
        elif filter_mode == "Semana":
            weeks = games["week"].drop_nulls().unique().sort().to_list()
            if weeks:
                nearest = min(games.to_dicts(), key=lambda row: abs((row["date"] - date.today()).days))["week"]
                week = st.selectbox("Semana", weeks, index=weeks.index(nearest))
        visible = service.filter_calendar(games, day=day, week=week)
        cols = st.columns(3)
        cols[0].metric("Partidos en la selección", visible.height)
        cols[1].metric("Temporada", str(season))
        cols[2].metric("Ventana", str(window) + " partidos" if window else "Temporada")
        st.markdown("### Cartelera")
        st.caption("Fechas y horarios del calendario NFL (ET). Un resultado pendiente puede indicar demora de publicación; no es seguimiento en vivo.")
        if visible.is_empty():
            st.info("No hay partidos en esta selección. Prueba otra fecha, semana o temporada.")
        cards = st.columns(3)
        for index, game in enumerate(visible.to_dicts()):
            with cards[index % 3]:
                if game_card(game):
                    st.session_state["selected_game"] = game["game_id"]
                    st.rerun()
    except (RuntimeError, ValueError, OSError) as exc:
        st.error("La fuente de datos no está disponible o todavía no publicó esta selección.")
        with st.expander("Detalle para diagnóstico"):
            st.code(str(exc))


def _comparison(schedule, season, window, season_type, h2h_count, include_pbp):
    hero("Dos equipos. Una misma ventana.", "Compara su rendimiento con una fecha de corte y criterios visibles.")
    teams = sorted(set(schedule["home_team"]) | set(schedule["away_team"]))
    if len(teams) < 2:
        st.info("No hay suficientes equipos disponibles.")
        return
    left, right = st.columns(2)
    team_a = left.selectbox("Equipo A", teams)
    team_b = right.selectbox("Equipo B", [t for t in teams if t != team_a])
    cutoff = st.date_input("Incluir partidos anteriores al", value=date.today())
    week = st.selectbox("Semana para reportes de lesiones", schedule["week"].unique().sort().to_list())
    with st.spinner("Preparando comparación…"):
        data = analysis_data(season, include_pbp)
        result = service.comparison(data, team_a, team_b, before=cutoff, games=window, season_type=season_type,
                                    injury_week=week, h2h_games=h2h_count)
    render_matchup(result)
