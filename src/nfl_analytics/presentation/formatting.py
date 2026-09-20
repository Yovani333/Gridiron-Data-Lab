"""Presentation-only labels and formatting; no NFL calculations."""

METRICS = {
    "points_per_drive": "Puntos / drive (sin conversiones)", "drives_per_game": "Posesiones / partido",
    "points_per_game": "Puntos / partido",
    "yards_per_game": "Yardas netas / partido", "yards_per_play": "Yardas netas / jugada",
    "total_yards": "Yardas netas totales", "passing_yards_per_game": "Yardas pase / partido",
    "rushing_yards_per_game": "Yardas carrera / partido", "touchdowns": "Touchdowns ofensivos",
    "turnovers": "Pérdidas de balón", "completions": "Pases completos", "attempts": "Intentos de pase",
    "sacks": "Sacks permitidos", "first_downs": "Primeros downs (PBP)",
    "third_down_rate": "Conversión de tercer down", "red_zone_td_rate": "TD por posesión con snap en zona roja",
    "epa_per_play": "EPA / jugada", "passing_epa_per_play": "EPA / dropback",
    "rushing_epa_per_play": "EPA / carrera diseñada", "success_rate": "Success Rate",
    "explosive_play_rate": "Jugadas explosivas", "total_epa": "EPA total",
    "passing_epa_total": "EPA total de dropbacks", "rushing_epa_total": "EPA total de carreras",
}

DEFENSE_LABELS = {"points_per_game": "Puntos permitidos / partido", "turnovers": "Pérdidas del rival",
                  "sacks": "Sacks al rival", "touchdowns": "TD ofensivos permitidos",
                  "yards_per_game": "Yardas netas permitidas / partido", "yards_per_play": "Yardas permitidas / jugada"}


def value(number, key: str = "") -> str:
    if number is None:
        return "No disponible"
    if key.endswith("rate") or key == "win_pct":
        return f"{number:.1%}"
    if isinstance(number, int):
        return f"{number:,}"
    return f"{number:.3f}" if "epa" in key else f"{number:,.1f}"


def record(form: dict) -> str:
    return f"{form['wins']}–{form['losses']}–{form['ties']}" if form["games"] else "Sin partidos"
