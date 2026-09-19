"""Temporary Python UI. Acquisition and analysis are delegated to service."""

from datetime import date

import polars as pl
import streamlit as st

from . import service
from .components import brand, footer, game_card, heading, hero
from .matchup_view import render_matchup
from .picks_view import pick_summary


@st.cache_data(ttl=900, show_spinner=False)
def available_seasons():
    return service.seasons()


@st.cache_data(ttl=900, show_spinner=False)
def calendar(season):
    return service.calendar(season)


@st.cache_data(ttl=900, max_entries=4, show_spinner=False)
def analysis_data(season, include_pbp):
    return service.load_analysis(season, include_pbp)


@st.cache_data(ttl=900, max_entries=3, show_spinner=False)
def player_data(season):
    return service.player_stats(season)


def main() -> None:
    st.set_page_config(page_title="Gridiron · NFL Analytics", page_icon="🏈", layout="wide", initial_sidebar_state="collapsed")
    brand()
    service.initialize()
    nav_col, search_col = st.columns([5, 2], vertical_alignment="center")
    with nav_col:
        section = st.radio("Navegación", ["Inicio", "Partidos", "Equipos", "Jugadores", "Análisis", "Estadísticas", "Datos"],
                           horizontal=True, label_visibility="collapsed", key="nav", on_change=_clear_selection)
    with search_col:
        query = st.text_input("Buscar jugador, equipo...", placeholder="Buscar jugador, equipo...", label_visibility="collapsed")
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
        window_label = st.sidebar.selectbox("Ventana de análisis", ["Último partido", "Últimos 3", "Últimos 5", "Personalizada", "Temporada completa"], index=2)
        window = {"Último partido": 1, "Últimos 3": 3, "Últimos 5": 5, "Temporada completa": None}.get(window_label)
        if window_label == "Personalizada":
            window = st.sidebar.number_input("Número de partidos", min_value=1, max_value=100, value=5, step=1)
        season_type = st.sidebar.selectbox("Tipo de temporada", ["REG", "POST", "all"], format_func=lambda x: {"REG": "Regular", "POST": "Playoffs", "all": "Regular + playoffs"}[x])
        h2h_label = st.sidebar.selectbox("Enfrentamientos anteriores", ["3", "5", "10", "Todos"], index=1)
        h2h_count = None if h2h_label == "Todos" else int(h2h_label)
        include_pbp = st.sidebar.checkbox("Incluir métricas avanzadas", help="Consulta una temporada de play-by-play; la primera carga es más lenta.")
        st.sidebar.caption("Fuente única: nflverse mediante nflreadpy. Modelo experimental sin recomendaciones.")
        if section == "Equipos":
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
            footer()
            return
        if section == "Inicio":
            _home(games, season, years, query)
            footer()
            return
        if section in ("Jugadores", "Estadísticas"):
            _statistics(games, season, years, query, section)
            footer()
            return
        if section == "Análisis":
            _analysis_page(games, season, include_pbp)
            footer()
            return
        if section == "Datos":
            _diagnostics()
            footer()
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
        footer()
    except (RuntimeError, ValueError, OSError) as exc:
        st.error("La fuente de datos no está disponible o todavía no publicó esta selección.")
        with st.expander("Detalle para diagnóstico"):
            st.code(str(exc))


def _home(games: pl.DataFrame, season: int, years: list[int], query: str) -> None:
    hero("La NFL en tus datos", "Explora partidos, equipos, estadísticas y análisis utilizando datos históricos y actuales de NFL.",
         "GRIDIRON DATA LAB · NFL ANALYTICS HUB")
    actions = st.columns([1.5, 1.5, 4])
    actions[0].button("Explorar partidos", type="primary", width="stretch", on_click=_navigate, args=("Partidos",))
    actions[1].button("Ver estadísticas", width="stretch", on_click=_navigate, args=("Estadísticas",))
    upcoming = service.upcoming(games)
    if query:
        upcoming = [g for g in upcoming if query.upper() in (g["home_team"] + " " + g["away_team"]).upper()]
    heading("Próximos partidos", f"Calendario {season} · horarios ET · resultados sujetos a publicación de nflverse")
    if upcoming:
        cards = st.columns(4)
        for index, game in enumerate(upcoming):
            with cards[index % 4]:
                if game_card(game):
                    st.session_state["selected_game"] = game["game_id"]
                    st.rerun()
    else:
        st.info("No hay próximos partidos disponibles en esta temporada o para esta búsqueda.")
    st.button("Ver todos los partidos →", on_click=_navigate, args=("Partidos",))

    heading("Potential Picks / Posibles Picks", "Moneyline · Spread · Game Total · Team Total. Abre un matchup para revisar factores y cobertura.")
    if upcoming:
        try:
            data = analysis_data(season, False)
            signals = service.featured_picks(data, upcoming)
            cols = st.columns(min(3, len(signals)))
            for index, signal in enumerate(signals):
                with cols[index % len(cols)]:
                    pick_summary(signal)
                    if st.button("Ver análisis completo →", key=f"signal_{signal['game_id']}", width="stretch"):
                        st.session_state["selected_game"] = signal["game_id"]
                        st.rerun()
        except (RuntimeError, ValueError, OSError):
            st.info("El análisis temporalmente no está disponible; los partidos siguen visibles.")
    else:
        st.info("No hay partidos próximos para analizar en esta selección.")

    stats_year, players = _latest_player_data(years, season)
    overview = service.overview(games, seasons_available=years, players=players)
    heading("Datos en perspectiva", f"Partidos de {season}; jugadores de {stats_year if stats_year else 'temporada sin datos'}")
    cards = st.columns(4)
    cards[0].metric("Equipos en calendario", overview["teams"])
    cards[1].metric("Jugadores con estadísticas", overview["players"] if overview["players"] is not None else "N/A")
    cards[2].metric("Partidos en calendario", overview["games"])
    cards[3].metric("Temporadas en calendario", f"{overview['seasons'][0]}–{overview['seasons'][1]}" if overview["seasons"] else "N/A")
    _stats_panels(games, players, stats_year)


def _clear_selection() -> None:
    st.session_state.pop("selected_game", None)


def _navigate(section: str) -> None:
    st.session_state["nav"] = section
    _clear_selection()


def _latest_player_data(years: list[int], season: int) -> tuple[int | None, pl.DataFrame | None]:
    # Current season may not yet have weekly player data. Keep fallback bounded.
    for year in [s for s in sorted(years, reverse=True) if s <= season and s >= 1999][:3]:
        players = player_data(year)
        if players is not None and not players.is_empty():
            return year, players
    return None, None


def _stats_panels(games: pl.DataFrame, players: pl.DataFrame | None, stats_year: int | None) -> None:
    heading("Líderes de la temporada", f"Estadísticas semanales de temporada regular · {stats_year or 'sin publicación'}")
    category = st.radio("Categoría de líderes", ["Passing", "Rushing", "Receiving", "Defense"], horizontal=True)
    board = service.leaders(players, category)
    left, right = st.columns([1.2, 1])
    with left:
        if board.is_empty():
            st.info("Estadísticas de jugadores aún no disponibles.")
        else:
            st.dataframe(board.rename({"player": "Jugador", "team": "Equipo"}), hide_index=True, width="stretch")
    with right:
        if not board.is_empty():
            key = {"Passing": "passing_yards", "Rushing": "rushing_yards", "Receiving": "receiving_yards", "Defense": "def_tackles_solo"}[category]
            st.caption(f"{key.replace('_', ' ').title()} · Top {board.height} ({stats_year})")
            st.bar_chart(board.select("player", key), x="player", y=key, color="#1685ff", horizontal=True)
        counts = service.result_distribution(games)
        total = sum(counts.values())
        st.caption(f"Distribución de resultados · {games['season'][0]} · {total} partidos REG finalizados")
        if total:
            result_chart = pl.DataFrame({"Resultado": ["Local", "Visitante", "Empate"], "Partidos": list(counts.values())})
            st.bar_chart(result_chart, x="Resultado", y="Partidos", color="#1685ff")
        else:
            st.info("Aún no hay resultados finales de temporada regular.")


def _statistics(games: pl.DataFrame, season: int, years: list[int], query: str, section: str) -> None:
    hero("Jugadores y estadísticas" if section == "Jugadores" else "La temporada en números",
         "Líderes y resultados publicados por nflverse; sin cifras simuladas.")
    choices = [year for year in years if year >= 1999]
    selected = st.selectbox("Temporada de jugadores", choices, index=choices.index(season) if season in choices else len(choices) - 1)
    players = player_data(selected)
    if players is None:
        st.info("Estadísticas no publicadas para esta temporada. Prueba una temporada anterior.")
    elif query:
        name = "player_display_name" if "player_display_name" in players.columns else "player_name"
        players = players.filter(pl.col(name).str.to_lowercase().str.contains(query.lower(), literal=True).fill_null(False) |
                                 pl.col("team").str.contains(query.upper(), literal=True).fill_null(False))
    _stats_panels(games, players, selected)


def _analysis_page(games: pl.DataFrame, season: int, include_pbp: bool) -> None:
    hero("Explora un matchup", "Selecciona un partido para comparar forma reciente, ofensiva, defensiva, historial y lesiones.")
    options = games.to_dicts()
    if not options:
        st.info("Sin partidos disponibles.")
        return
    selected = st.selectbox("Partido", options, format_func=lambda g: f"{g['date']} · {g['away_team']} vs {g['home_team']}")
    if st.button("Ver análisis completo", type="primary"):
        st.session_state["selected_game"] = selected["game_id"]
        st.rerun()


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


def _diagnostics():
    report = service.model_diagnostics()
    hero("Una hipótesis medible.", "Evaluación cronológica y límites de model_v0_1.", "LAB · VALIDACIÓN")
    if report["accuracy"] <= report["benchmarks"]["better_record"]:
        st.warning("Modelo experimental. Su accuracy no supera el benchmark de mejor récord; no usar como pick.")
    else:
        st.warning("Modelo experimental: una mejora en esta muestra no garantiza calibración ni rendimiento futuro; no usar como pick.")
    st.caption(f"Temporadas: {report['seasons']} · Partidos: {report['games']} · Variables: {', '.join(report['features'])}")
    cols = st.columns(3)
    cols[0].metric("Accuracy", f"{report['accuracy']:.1%}")
    cols[1].metric("Brier", f"{report['brier']:.3f}")
    cols[2].metric("Log loss", f"{report['log_loss']:.3f}")
    st.markdown("#### Benchmarks · accuracy")
    st.dataframe([{"Regla": k, "Accuracy": v} for k, v in report["benchmarks"].items()], hide_index=True)
    st.markdown("#### Calibración")
    st.dataframe(report["calibration"], hide_index=True)
    st.markdown("#### Coeficientes normalizados")
    st.dataframe([{"Variable": k, "Coeficiente": v} for k, v in report["coefficients"].items()], hide_index=True)
    if report.get("ablation"):
        st.markdown("#### Ablación · Brier menor es mejor")
        st.dataframe([{"Variante": k, "Brier": v["brier"], "Accuracy": v["accuracy"]}
                      for k, v in report["ablation"].items()], hide_index=True)
    st.caption(f"Artefacto entrenado con {report['trained_games']} partidos hasta {report['trained_through']}.")
    st.caption("Cada semana se evalúa con un modelo entrenado antes de su primer partido; la fuente histórica puede contener revisiones posteriores a los partidos.")
