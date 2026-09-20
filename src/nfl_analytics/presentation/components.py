"""Streamlit view components. All inputs are already analyzed data."""

from html import escape

import polars as pl
import streamlit as st

from .formatting import METRICS, DEFENSE_LABELS, value, record
from .identity import team_badge


def brand() -> None:
    st.html("""<style>
    :root {color-scheme:dark}
    .identity-avatar {position:relative;display:inline-grid;place-items:center;width:58px;height:58px;flex-shrink:0;background:#142d47;border-radius:16px;overflow:hidden;color:#bddcff;font-weight:800}
    .identity-avatar img {position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#13243a}
    .portrait {width:70px;height:70px;border-radius:50%;background:#203e5b}
    .portrait img {object-fit:cover}
    .team-identity {display:flex;align-items:center;gap:12px;border-left:3px solid var(--team-accent);padding-left:10px}
    .team-identity strong {font-size:24px;color:#f5f8ff}
    .team-identity small,.player-spotlight small {display:block;color:#acbfd5;font-size:11px}
    .player-spotlight {display:flex;align-items:center;gap:16px;padding:12px 16px;margin-bottom:10px;border:1px solid #31465e;border-left:3px solid var(--team-accent);border-radius:16px;background:linear-gradient(115deg,color-mix(in srgb,var(--team-accent) 24%,#101e31),#0c1929 80%)}
    .player-spotlight strong {color:#f5f8ff;font-size:17px}
    [class*="st-key-fixture_"] {background:radial-gradient(ellipse at top right,#1685ff26,transparent 65%),linear-gradient(145deg,#15283e,#0b1728);border-radius:14px;box-shadow:0 12px 30px #02081035}
    [data-testid=stVerticalBlockBorderWrapper] {background:radial-gradient(ellipse at top right,#1685ff19,transparent 65%),linear-gradient(145deg,#15283e,#0b1728)!important;box-shadow:0 12px 30px #02081035}
    .signal {background:radial-gradient(ellipse at top right,#1685ff22,transparent 65%),linear-gradient(145deg,#15283e,#0b1728)!important;box-shadow:0 10px 30px #02081035}
    [data-testid=stMetric] {background:linear-gradient(130deg,#173654,#101e31)!important;border-top:2px solid #358de0!important}
    @media(prefers-reduced-motion:reduce) {.signal {transition:none!important}}
    .stApp {background:linear-gradient(135deg,#07111f,#0a1625 55%,#07111f);color:#eaf2ff}
    .block-container {max-width:1500px;padding-top:4.5rem;padding-bottom:2.5rem}
    h1,h2,h3 {letter-spacing:-.035em;color:#f4f8ff}
    [data-testid=stSidebar] {background:#0b1728;border-right:1px solid #23374b}
    [data-testid=stMetric], [data-testid=stVerticalBlockBorderWrapper] {background:#101e31;border:1px solid #263b51;border-radius:13px;padding:8px}
    [data-testid=stMetricLabel] {color:#a8bbce}
    [data-testid=stMetricValue] {color:#f4f8ff}
    [data-testid=stDataFrame] {border:1px solid #263b51;border-radius:12px;overflow:hidden}
    button[kind=primary] {background:#1685ff;border-color:#1685ff;color:white}
    button:hover {border-color:#67b1ff!important;color:white!important}
    .hub-brand {display:flex;align-items:center;gap:12px;padding:7px 2px 10px;border-bottom:1px solid #213347;margin-bottom:7px}
    .hub-mark {height:36px;width:36px;display:grid;place-items:center;border-radius:10px;background:#1685ff;color:white;font-size:22px;font-weight:900;box-shadow:0 0 28px #1685ff50}
    .hub-brand strong {font-size:17px;letter-spacing:-.04em;color:#f4f8ff}
    .hub-brand small {display:block;color:#9aafc5;font-size:11px}
    .hero {position:relative;isolation:isolate;overflow:hidden;min-height:260px;background:radial-gradient(circle at 74% 42%,#153c68,transparent 37%),linear-gradient(105deg,#101e31,#0b1828 58%,#081321);border:1px solid #253d57;border-radius:17px;padding:42px 44px;margin:15px 0 16px}
    .hero:after {content:'';position:absolute;right:-35px;top:-62px;width:460px;height:360px;border:2px solid #4385cf4a;border-radius:50%;box-shadow:0 0 0 50px #2d68ad19,0 0 0 101px #2d68ad14;transform:rotate(-25deg);z-index:-1}
    .hero:before {content:'GRIDIRON';position:absolute;right:65px;bottom:23px;color:#9fc7f13a;font-size:56px;font-weight:900;font-style:italic;letter-spacing:-.08em}
    .hero-ball {position:absolute;right:13%;top:24%;width:205px;height:116px;border:3px solid #a8d7ff99;border-radius:50%;background:linear-gradient(145deg,#2a6093,#123454 65%,#0c233f);box-shadow:0 20px 55px #020c1f88,0 0 45px #1685ff44;transform:rotate(-28deg)}
    .hero-ball:before {content:'';position:absolute;left:36px;right:36px;top:53px;border-top:4px solid #cee8ffb0}
    .hero-ball:after {content:'╪╪╪╪';position:absolute;left:75px;top:33px;color:#d4efff;font-size:27px;letter-spacing:-6px;transform:rotate(90deg)}
    .hero h1 {font-size:clamp(32px,4vw,56px);color:white;line-height:1.06;margin:0 0 16px;max-width:700px}
    .hero p {max-width:600px;color:#b5c7d9;font-size:17px;line-height:1.55;margin:0}
    .eyebrow {color:#53a9ff;font-size:11px;letter-spacing:.2em;font-weight:800;margin-bottom:20px}
    .section-title {font-size:23px;font-weight:750;letter-spacing:-.03em;color:#f0f6ff;margin:18px 0 5px}
    .section-note {color:#95a9bf;font-size:13px;margin:0 0 13px}
    .game-line {display:flex;justify-content:space-between;align-items:center;padding:9px 0}
    .team-code {font-weight:800;font-size:28px;letter-spacing:-.04em;color:#f5f8ff}
    .score {font-weight:650;font-size:23px;color:#bdd4ed}
    .small-label {font-size:11px;letter-spacing:.09em;color:#9cb2c8;text-transform:uppercase}
    .chip {display:inline-block;background:#183759;padding:5px 10px;border-radius:20px;font-size:11px;color:#8fc4ff}
    .signal {background:#101e31;border:1px solid #29435b;border-radius:14px;padding:18px;min-height:195px;margin:7px 0 10px;transition:transform .15s,border-color .15s}
    .signal:hover {transform:translateY(-2px);border-color:#3770a9}
    .signal .label {color:#8db0d0;font-size:11px;letter-spacing:.12em;text-transform:uppercase}
    .signal h3 {margin:8px 0;font-size:21px}
    .signal .lean {color:#f3f8ff;font-weight:700;font-size:17px}
    .signal .level {font-size:11px;color:#9ce1c1;border:1px solid #43846b;padding:3px 7px;border-radius:10px}
    .signal ul {margin:10px 0 0;padding-left:17px;color:#aec3d5;font-size:12px;line-height:1.7}
    .empty-note {color:#98acc0;font-size:13px;line-height:1.5}
    .hub-footer {border-top:1px solid #23384d;padding:26px 0 5px;margin-top:35px;color:#9db0c6;font-size:12px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .hub-footer strong {color:#edf5ff}.hub-footer a {color:#59a9ff}
    @media(max-width:700px) {
      [data-testid="stHorizontalBlock"] {flex-direction:column!important;gap:12px!important}
      [data-testid="stColumn"] {width:100%!important;min-width:0!important;flex:1 1 auto!important}
      .hero {padding:25px;min-height:215px}.hero:before,.hero-ball {display:none}.hero h1 {font-size:34px}.hero p {font-size:14px}
      .signal {min-height:0}.block-container {padding-left:1rem;padding-right:1rem}
    }
    </style><div class="hub-brand"><span class="hub-mark">N</span><span><strong>NFL Analytics Hub</strong><small>Powered by nflreadpy · Gridiron Data Lab</small></span></div>""")


def hero(title: str, subtitle: str, eyebrow: str = "NFL · ANÁLISIS DESCRIPTIVO") -> None:
    st.html(f'<section class="hero"><div class="hero-ball" aria-hidden="true"></div><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></section>')


def heading(title: str, note: str = "") -> None:
    st.html(f'<div class="section-title">{escape(title)}</div><p class="section-note">{escape(note)}</p>')


def signal_card(signal: dict) -> None:
    home, away = escape(signal["home"]), escape(signal["away"])
    if signal["status"] == "insufficient_data":
        body = f'<p class="empty-note">Muestra insuficiente: {home} {signal["samples"][signal["home"]]} · {away} {signal["samples"][signal["away"]]} partidos previos. Se requieren al menos 3 por equipo.</p>'
    elif signal["lean"]:
        factors = [f for f in signal["factors"] if f["team"] == signal["lean"]]
        reasons = "".join(f'<li>+{abs(f["points"]):g} {escape(f["label"])}</li>' for f in factors[:4])
        body = f'<div class="lean">Lean {escape(signal["lean"])} <span class="level">Señal {escape(signal["level"])}</span></div><ul>{reasons}</ul>'
    else:
        body = '<p class="empty-note">Sin diferencia neta en los factores disponibles.</p>'
    st.html(f'<article class="signal"><span class="label">ANÁLISIS DESCRIPTIVO · {home} LOCAL</span><h3>{away} <span style="color:#68849e">vs</span> {home}</h3>{body}</article>')


def footer() -> None:
    st.html('<footer class="hub-footer"><span><strong>NFL Analytics Hub</strong><br>Datos mediante nflreadpy / nflverse · Análisis estadístico descriptivo</span><span><a href="https://github.com/Yovani333/Gridiron-Data-Lab">GitHub</a> · Sin recomendaciones de apuestas</span></footer>')


def game_card(game: dict) -> bool:
    statuses = {"result_available": "Resultado publicado", "awaiting_update": "Resultado pendiente", "scheduled": "Programado"}
    with st.container(border=True, key=f"fixture_{game['game_id']}"):
        st.html(f'<span class="chip">{statuses.get(game["status"], "Estado no disponible")}</span><div class="small-label" style="margin-top:14px">SEMANA {game["week"]} · {escape(game["season_type"])}</div>')
        for side, label in (("away", "Visitante"), ("home", "Local")):
            score = game[f"{side}_score"]
            team = game[f"{side}_team"]
            record_text = game.get("records", {}).get(team)
            display = f" · {record_text}" if record_text else ""
            st.html(f'<div class="game-line"><div>{team_badge(team)}<span class="small-label">{label}{escape(display)}</span></div><span class="score">{score if score is not None else "—"}</span></div>')
        st.caption(f"{game['date']} · {game['gametime'] or 'Hora por confirmar'} ET" + (f" · {game['stadium']}" if game.get("stadium") else ""))
        return st.button("Ver análisis completo →", key=f"game_{game['game_id']}", width="stretch")


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
            st.html(team_badge(profile["team"]))
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
