"""Render a completed comparison; no data acquisition or metric calculations."""

import polars as pl
import streamlit as st

from .components import form_cards, games_table, hero, metric_table
from .formatting import value


def render_matchup(result: dict) -> None:
    a, b = result["team_a"], result["team_b"]
    ta, tb = a["team"], b["team"]
    context = result["context"]
    names = [context[key].get("name") or context[key]["abbreviation"] for key in ("team_a", "team_b")]
    window = f"últimos {result['window']} partidos" if result["window"] else "temporada completa"
    hero(f"{names[0]}  /  {names[1]}", f"{result['season']} · {window} · {result['season_type']} · partidos anteriores al {result['before']}", "MATCHUP LAB · DATOS, CONTEXTO Y CONTRASTES")
    relation = {"divisional": "Enfrentamiento divisional", "same_conference": "Misma conferencia", "interconference": "Interconferencia",
                "unknown": "Conferencia no disponible", "historical_alignment_unavailable": "Alineación histórica no disponible"}
    st.caption(relation[context["relationship"]] + " · " + " / ".join(context[k].get("division") or "División no disponible" for k in ("team_a", "team_b")))
    if "game" in result:
        game = result["game"]
        st.caption(f"{ta} local · {tb} visitante" + (" · Sede neutral: se excluye de los splits local/visitante" if game["neutral_site"] else ""))
    st.caption("Las divisiones del catálogo describen la alineación actual; no se reconstruyen cambios históricos de conferencia.")
    if result.get("history_warning"):
        st.warning(result["history_warning"])
    for name, label in (("stats", "Estadísticas"), ("injuries", "Lesiones"), ("teams", "Metadatos de equipos")):
        if result["availability"][name]["status"] == "unavailable":
            st.warning(f"{label}: fuente temporalmente no disponible. Las demás secciones siguen disponibles.")
    tabs = st.tabs(["Resumen", "Forma reciente", "Ofensiva", "Defensiva", "Local / visitante", "Historial", "Lesiones", "Avanzadas"])
    with tabs[0]:
        form_cards(a, b)
        st.markdown("#### Cobertura de la comparación")
        st.caption("Los promedios de puntos usan el calendario. Las estadísticas y el PBP pueden cubrir menos partidos; no se rellenan faltantes con cero.")
        for profile in (a, b):
            st.write(f"**{profile['team']}** · {profile['form']['games']} resultados · {profile['offense']['games_with_stats']} box scores ofensivos · {profile['defense']['games_with_stats']} box scores rivales")
    with tabs[1]:
        for col, profile in zip(st.columns(2), (a, b)):
            with col:
                st.subheader(profile["team"])
                games_table(profile["games"])
                if profile["games"].height:
                    st.line_chart(profile["games"].sort("date").select("date", "points_for", "points_against"), x="date", y=["points_for", "points_against"], color=["#527d9f", "#bf9356"])
        st.caption("La ventana cuenta partidos, no semanas; los descansos no se consideran derrotas ni partidos con cero puntos.")
    with tabs[2]:
        st.caption(f"Box scores disponibles: {ta} {a['offense']['games_with_stats']}/{a['form']['games']} · {tb} {b['offense']['games_with_stats']}/{b['form']['games']}. Las métricas PBP requieren la carga avanzada.")
        if not a["offense"]["games_with_stats"] or not b["offense"]["games_with_stats"]:
            st.info("Estadísticas aún no disponibles para uno o ambos equipos en esta ventana.")
        metric_table(a["offense"], b["offense"], ta, tb)
    with tabs[3]:
        st.caption(f"Box scores rivales disponibles: {ta} {a['defense']['games_with_stats']}/{a['form']['games']} · {tb} {b['defense']['games_with_stats']}/{b['form']['games']}.")
        metric_table(a["defense"], b["defense"], ta, tb, defense=True)
    with tabs[4]:
        st.caption("Cada split toma los últimos N partidos de esa condición. Se excluyen sedes neutrales.")
        venue_a = st.selectbox(f"Condición de {ta}", ["home", "away"], format_func=lambda x: "Local" if x == "home" else "Visitante", key="venue_a")
        venue_b = st.selectbox(f"Condición de {tb}", ["away", "home"], format_func=lambda x: "Local" if x == "home" else "Visitante", key="venue_b")
        sa, sb = result["home_away"][ta][venue_a], result["home_away"][tb][venue_b]
        form_cards(sa, sb)
        metric_table(sa["offense"], sb["offense"], ta, tb)
        st.markdown("#### Defensiva por condición")
        metric_table(sa["defense"], sb["defense"], ta, tb, defense=True)
        if sa["advanced"] is not None and sb["advanced"] is not None:
            st.markdown("#### EPA y éxito por condición")
            metric_table(sa["advanced"]["offense"], sb["advanced"]["offense"], ta, tb, advanced=True)
            metric_table(sa["advanced"]["defense"], sb["advanced"]["defense"], ta, tb, advanced=True, defense=True)
    with tabs[5]:
        history = result["head_to_head"]
        cols = st.columns(3)
        cols[0].metric(f"Victorias {ta}", history["team_a_wins"])
        cols[1].metric("Empates", history["ties"])
        cols[2].metric(f"Victorias {tb}", history["team_b_wins"])
        st.caption(f"Puntos promedio: {ta} {value(history['team_a_avg_points'])} / {tb} {value(history['team_b_avg_points'])} · Margen medio de {ta}: {value(history['team_a_avg_margin'])}")
        cols_to_show = ["date", "home_team", "away_team", "home_score", "away_score", "winner", "margin"]
        st.dataframe(history["games"].select(cols_to_show), hide_index=True, width="stretch")
        st.caption(f"Temporadas consultadas: {history['scope_seasons']}. Historial descriptivo; no estima un ganador.")
        st.caption(f"Abreviaturas relacionadas por ID de franquicia: {history['aliases']}")
    with tabs[6]:
        st.caption(f"Semana {result['injury_week'] or 'no seleccionada'} · Solo informes con fecha registrada hasta {result['before']}. No son un archivo completo de lo conocido antes del kickoff.")
        for col, team in zip(st.columns(2), (ta, tb)):
            with col:
                st.subheader(team)
                reports = result["injuries"][team]
                if reports is None:
                    st.info("Datos de lesiones no disponibles o semana sin seleccionar.")
                elif reports.is_empty():
                    st.info("Sin informes verificables en esta selección. No implica que todos estén sanos.")
                else:
                    st.dataframe(reports.select("player", "player_id", "position", "injury", "report_status", "practice_status", "reported_at"), hide_index=True, width="stretch")
        st.caption("El estado de práctica no confirma participación en el partido. Las relaciones con roster usan temporada, equipo e ID; no se asignan pesos a lesiones.")
    with tabs[7]:
        if a["advanced"] is None or b["advanced"] is None:
            st.info("Métricas avanzadas no disponibles. Activa su carga en el panel lateral; la primera consulta puede tardar.")
        else:
            for profile in (a, b):
                side = profile["advanced"]["offense"]
                st.caption(f"{profile['team']}: {side['games_with_pbp']} partidos PBP · {side['plays']} jugadas elegibles · {side['epa_plays']} con EPA válido")
            st.markdown("#### Ofensiva")
            metric_table(a["advanced"]["offense"], b["advanced"]["offense"], ta, tb, advanced=True)
            st.markdown("#### Defensiva · permitido al rival")
            metric_table(a["advanced"]["defense"], b["advanced"]["defense"], ta, tb, advanced=True, defense=True)
            st.caption("Éxito = EPA > 0. Explosiva = dropback de ≥20 yardas o carrera diseñada de ≥10. Se excluyen kneels, spikes y conversiones de dos puntos. EPA es el valor publicado por nflverse.")
    st.caption(f"Lectura de datos: {result['read_at'].strftime('%Y-%m-%d %H:%M UTC')} · Caché de origen: hasta 24 h. Esta hora no es la última actualización del proveedor.")
