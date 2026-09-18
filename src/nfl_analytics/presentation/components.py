"""Streamlit view components. All inputs are already analyzed data."""

from html import escape

import polars as pl
import streamlit as st

from .formatting import METRICS, DEFENSE_LABELS, value, record


def brand() -> None:
    st.html("""<style>
    .stApp {background:#f4f6f8;color:#172332}
    .block-container {max-width:1440px;padding-top:4.5rem;padding-bottom:4rem}
    h1,h2,h3 {letter-spacing:-.035em}
    [data-testid=stSidebar] {background:#eaf0f4;border-right:1px solid #dae2e9}
    [data-testid=stMetric] {background:white;border:1px solid #dfe6eb;border-radius:12px;padding:18px}
    [data-testid=stVerticalBlockBorderWrapper] {border-radius:14px}
    .brand {font-size:12px;font-weight:800;letter-spacing:.24em;color:#506576;margin-bottom:18px}
    .hero {background:#142536;border-radius:18px;padding:22px 28px;color:#f7f8fb;margin:4px 0 16px}
    .hero h1 {font-size:32px;color:#f7f8fb;margin:0 0 10px;line-height:1.1}
    .hero p {color:#bdccd9;margin:0;font-size:15px}
    .eyebrow {color:#e5ba71;font-size:11px;letter-spacing:.17em;font-weight:700;margin-bottom:12px}
    .game-line {display:flex;justify-content:space-between;align-items:center;padding:9px 0}
    .team-code {font-weight:750;font-size:28px;letter-spacing:-.04em}
    .score {font-weight:600;font-size:24px;color:#506576}
    .small-label {font-size:11px;letter-spacing:.09em;color:#647a8b;text-transform:uppercase}
    .chip {display:inline-block;background:#e8eef4;padding:4px 9px;border-radius:20px;font-size:11px;color:#354d61}
    @media(max-width:600px) {.hero {padding:22px}.hero h1 {font-size:28px}}
    </style><div class="brand">GRIDIRON <span style="color:#a07836">/</span> DATA LAB</div>""")


def hero(title: str, subtitle: str, eyebrow: str = "NFL · ANÁLISIS DESCRIPTIVO") -> None:
    st.html(f'<section class="hero"><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></section>')


def game_card(game: dict) -> bool:
    statuses = {"result_available": "Resultado publicado", "awaiting_update": "Resultado pendiente", "scheduled": "Programado"}
    with st.container(border=True):
        st.html(f'<span class="chip">{statuses[game["status"]]}</span><div class="small-label" style="margin-top:14px">SEMANA {game["week"]} · {game["season_type"]}</div>')
        for side, label in (("away", "Visitante"), ("home", "Local")):
            score = game[f"{side}_score"]
            st.html(f'<div class="game-line"><div><span class="team-code">{escape(game[f"{side}_team"])}</span> <span class="small-label">{label}</span></div><span class="score">{score if score is not None else "—"}</span></div>')
        st.caption(f"{game['date']} · {game['gametime'] or 'Hora por confirmar'} ET" + (" · Sede neutral" if game["neutral_site"] else ""))
        return st.button("Ver matchup →", key=f"game_{game['game_id']}", width="stretch")


def metric_table(a: dict, b: dict, team_a: str, team_b: str, *, defense: bool = False, advanced: bool = False) -> None:
    keys = (["epa_per_play", "passing_epa_per_play", "rushing_epa_per_play", "success_rate", "explosive_play_rate", "total_epa", "passing_epa_total", "rushing_epa_total"]
            if advanced else ["points_per_game", "yards_per_game", "yards_per_play", "total_yards", "passing_yards_per_game", "rushing_yards_per_game", "touchdowns", "turnovers", "completions", "attempts", "sacks", "first_downs", "third_down_rate", "red_zone_td_rate"])
    labels = METRICS | (DEFENSE_LABELS if defense else {})
    rows = [{"Métrica": labels[k], team_a: value(a.get(k), k), team_b: value(b.get(k), k)} for k in keys]
    st.dataframe(pl.DataFrame(rows), hide_index=True, width="stretch")
    if defense:
        st.caption("Valores de la ofensiva rival permitidos. EPA defensivo se muestra como EPA permitido, sin invertir el signo.")


def form_cards(a: dict, b: dict) -> None:
    for col, profile in zip(st.columns(2), (a, b)):
        with col:
            form = profile["form"]
            st.subheader(profile["team"])
            st.metric("Récord · V–D–E", record(form))
            st.caption(f"{form['games']} partidos · victorias: {value(form['win_pct'], 'win_pct')}")
            left, right = st.columns(2)
            left.metric("Puntos / partido", value(form["points_per_game"]))
            right.metric("Permitidos / partido", value(form["points_allowed_per_game"]))
            st.caption(f"Diferencial total: {value(form['point_diff'])} · Promedio: {value(form['avg_margin'])}")


def games_table(frame: pl.DataFrame) -> None:
    if frame.is_empty():
        st.info("No hay partidos finalizados en esta ventana.")
        return
    columns = [c for c in ("date", "week", "opponent", "is_home", "neutral_site", "points_for", "points_against", "point_diff") if c in frame.columns]
    st.dataframe(frame.select(columns), hide_index=True, width="stretch")
