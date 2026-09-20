"""Render market reports only; no statistical calculations or source access."""

from html import escape

import streamlit as st

from .components import heading

MARKETS = {"moneyline": "Moneyline", "spread": "Spread", "game_total": "Game Total", "team_total": "Team Total"}
STATUSES = {"insufficient_data": "Muestra insuficiente", "missing_reference": "Referencia NFL aún insuficiente",
            "no_strong_signal": "Sin señal fuerte", "unsupported_season_type": "Disponible solo para temporada regular"}


def _reason(factor: dict) -> str:
    return f"{factor['label']}: {factor['value']:.2f} frente a {factor['reference']:.2f}"


def pick_summary(report: dict) -> None:
    """Compact dashboard card, linked to the existing matchup view by its caller."""
    a, b = report["teams"]
    best = next((c for c in report["candidates"] if c["id"] == report["best"]), None)
    if best:
        body = (f'<div class="lean">{escape(best["selection"])}</div>'
                f'<p class="empty-note">{MARKETS[best["market"]]} · Pick Score {best["score"]:.1f}/100</p>'
                f'<p class="empty-note">{escape(_reason(best["supporting"][0]))}</p>')
    else:
        reason = "Muestra insuficiente" if any(c["status"] == "insufficient_data" for c in report["candidates"]) else "Sin señal fuerte en los mercados disponibles"
        body = f'<p class="empty-note">{reason}</p><p class="empty-note">Partidos previos: {a} {report["samples"][a]} · {b} {report["samples"][b]}</p>'
    st.html(f'<article class="signal"><span class="label">POTENTIAL PICKS · STATISTICAL LEANS</span><h3>{escape(a)} vs {escape(b)}</h3>{body}</article>')


def render_picks(report: dict) -> None:
    heading("Potential Picks / Posibles Picks", "Cuatro mercados · factores verificables · candidatos ordenados por fuerza de señal")
    st.caption(f"{report['version']} · Corte: antes del {report['as_of_date']} · Muestra: " +
               " / ".join(f"{team} {n} partidos" for team, n in report["samples"].items()))
    st.info("Pick Score es un índice de 0 a 100, no un porcentaje de acierto. Sin línea real verificada se muestra un Statistical Lean; no un Market Pick.")
    if report["best"]:
        best = next(c for c in report["candidates"] if c["id"] == report["best"])
        st.markdown(f"**Mejor coincidencia estadística:** {best['selection']} · {MARKETS[best['market']]} · {best['score']:.1f}/100")
    else:
        st.caption("No hay un candidato destacado con los mínimos actuales.")
    ordered = sorted(report["candidates"], key=lambda c: report["ranking"].index(c["id"]) if c["id"] in report["ranking"] else len(report["ranking"]))
    for index in range(0, len(ordered), 2):
        for col, candidate in zip(st.columns(2), ordered[index:index + 2]):
            with col, st.container(border=True):
                st.markdown(f"**{MARKETS[candidate['market']]}**" + (f" · {candidate['team']}" if candidate["team"] else ""))
                st.subheader(candidate["selection"] or STATUSES[candidate["status"]])
                if candidate["status"] in ("statistical_lean", "market_candidate", "no_strong_signal"):
                    st.caption(f"Pick Score {candidate['score']:.1f}/100 · cobertura de factores {candidate['coverage']:.0%}")
                if candidate["line"]:
                    st.caption(f"Línea: {candidate['line']['source']} · observada {candidate['line']['observed_at']}")
                else:
                    st.caption("Línea de mercado: no disponible/verificada")
                if candidate["baseline_kind"] == "pregame_league_average" and candidate["baseline"] is not None:
                    st.caption(f"Referencia NFL previa: {candidate['baseline']:.2f} puntos. No es una línea de apuesta.")
                if candidate["market"] == "spread" and candidate["line"] is None:
                    st.caption("Preferencia de lado; no afirma que cubrirá un handicap desconocido.")
                if candidate["selection"]:
                    for item in candidate["supporting"][:3]:
                        st.write("• " + _reason(item))
                    if candidate["opposing"]:
                        st.caption("Contrapeso: " + _reason(candidate["opposing"][0]))
                with st.expander("Ver contribuciones y cobertura"):
                    st.caption(f"Signo positivo favorece a {report['teams'][0]} en Moneyline/Spread, o a Over en totales. Los faltantes permanecen en el denominador.")
                    st.dataframe([{"Factor": f["label"], "Valor": f["value"], "Referencia": f["reference"],
                                   "Escala": f["scale"], "Peso": f["weight"], "Contribución": f["contribution"]}
                                  for f in candidate["factors"]], hide_index=True, width="stretch")
    with st.expander("Metodología y contexto"):
        st.write("Cada diferencia se divide por su escala y se limita a −1…1. Se suman contribuciones ponderadas, se divide entre todos los pesos previstos y se multiplica por la cobertura de muestra y por 100. El mínimo de señal es " + str(report["config"]["min_score"]) + "/100.")
        st.write("Los puntos de referencia combinan anotación propia y puntos permitidos por el rival, con un componente local/visitante cuando hay muestra. Son estimaciones heurísticas sin calibrar.")
        st.write(report["context_note"])
        st.caption(f"Relación entre equipos: {report['context']['relationship']} · promedio NFL basado en {report['league_games']} partidos previos.")
        for team, injuries in report["injuries"].items():
            if injuries["status"] == "unverifiable_timestamp":
                st.caption(f"Lesiones {team}: existen datos de origen, pero sin fecha verificable. Excluidos del contexto histórico y del score.")
                continue
            st.caption(f"Lesiones {team}: " + ("no disponibles" if injuries["reports"] is None else f"{injuries['reports']} informes fechados antes del corte; posiciones: {', '.join(injuries['positions']) or 'sin información'}") + ". Sin ponderación de impacto.")
        st.caption("Los mercados comparten factores y no son independientes. Ni el score ni la comparación con una línea calculan rentabilidad esperada. El historial puede incluir revisiones posteriores del proveedor.")
