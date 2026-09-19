"""Directional evidence per market and auditable, uncalibrated 0–100 scoring."""

from .matchup_evidence import finite
from .pick_config import PickConfig


def factor(key: str, label: str, value: float | None, reference: float | None, scale: float) -> dict:
    value, reference = finite(value), finite(reference)
    strength = None if value is None or reference is None else max(-1.0, min(1.0, (value - reference) / scale))
    return {"key": key, "label": label, "value": value, "reference": reference,
            "scale": scale, "strength": strength}


def _difference(a, b):
    return None if finite(a) is None or finite(b) is None else a - b


def _mean(a, b):
    return None if finite(a) is None or finite(b) is None else (a + b) / 2


def moneyline_factors(evidence: dict, config: PickConfig) -> list[dict]:
    a, b = evidence["team_a"], evidence["team_b"]
    fa, fb = a["form"], b["form"]
    split = _difference(a["split"]["win_pct"], b["split"]["win_pct"]) if a["split"] and b["split"] else None
    h2h = evidence["h2h"]
    h2h_diff = None if h2h.height < config.min_h2h_games else (h2h.filter(h2h["point_diff"] > 0).height - h2h.filter(h2h["point_diff"] < 0).height) / h2h.height
    last = _difference(a["last"]["point_diff"], b["last"]["point_diff"]) if a["last"] and b["last"] else None
    return [
        factor("margin", "Diferencial medio A menos B (puntos)", _difference(fa["avg_margin"], fb["avg_margin"]), 0, config.margin_scale),
        factor("offense", "Puntos anotados por partido: A menos B", _difference(fa["points_per_game"], fb["points_per_game"]), 0, config.points_scale),
        factor("defense", "Puntos permitidos: B menos A", _difference(fb["points_allowed_per_game"], fa["points_allowed_per_game"]), 0, config.points_scale),
        factor("record", "Porcentaje de victorias: A menos B", _difference(fa["win_pct"], fb["win_pct"]), 0, config.win_rate_scale),
        factor("venue", "Récord en la condición del partido: A menos B", split, 0, config.win_rate_scale),
        factor("h2h", "Balance de victorias H2H a favor de A", h2h_diff, 0, config.win_rate_scale),
        factor("last_game", "Margen del último partido: A menos B", last, 0, config.margin_scale),
        factor("trend", "Cambio de margen reciente: A menos B", _difference(a["trend"], b["trend"]), 0, config.margin_scale),
        factor("efficiency", "Yardas netas por jugada: A menos B", _difference(a["net_yards_per_play"], b["net_yards_per_play"]), 0, config.yards_scale),
    ]


def points_factors(evidence: dict, market: str, reference: float | None, config: PickConfig,
                   *, team: str | None = None) -> list[dict]:
    """Independent scoring/allowance observations vs an explicitly named reference."""
    a, b = evidence["team_a"], evidence["team_b"]
    fa, fb = a["form"], b["form"]
    h2h = evidence["h2h"]
    venue = historical = last = None
    if market == "spread":
        offense = _difference(fa["points_per_game"], fb["points_per_game"])
        defense = _difference(fb["points_allowed_per_game"], fa["points_allowed_per_game"])
        if a["split"] and b["split"]:
            venue = (a["split"]["points_per_game"] + b["split"]["points_allowed_per_game"] -
                     b["split"]["points_per_game"] - a["split"]["points_allowed_per_game"]) / 2
        if h2h.height >= config.min_h2h_games:
            historical = h2h["point_diff"].mean()
        if a["last"] and b["last"]:
            last = (a["last"]["point_diff"] - b["last"]["point_diff"]) / 2
        scale = config.margin_scale
    elif market == "game_total":
        offense = None if fa["points_per_game"] is None or fb["points_per_game"] is None else fa["points_per_game"] + fb["points_per_game"]
        defense = None if fa["points_allowed_per_game"] is None or fb["points_allowed_per_game"] is None else fa["points_allowed_per_game"] + fb["points_allowed_per_game"]
        if a["split"] and b["split"]:
            venue = sum(p["split"][k] for p in (a, b) for k in ("points_per_game", "points_allowed_per_game")) / 2
        if h2h.height >= config.min_h2h_games:
            historical = (h2h["home_score"] + h2h["away_score"]).mean()
        if a["last"] and b["last"]:
            last = sum(p["last"][k] for p in (a, b) for k in ("points_for", "points_against")) / 2
        scale = 2 * config.points_scale
    elif market == "team_total":
        own, opponent = (a, b) if team == a["team"] else (b, a)
        if team not in (a["team"], b["team"]):
            raise ValueError("Team total requires a matchup team")
        offense, defense = own["form"]["points_per_game"], opponent["form"]["points_allowed_per_game"]
        if own["split"] and opponent["split"]:
            venue = _mean(own["split"]["points_per_game"], opponent["split"]["points_allowed_per_game"])
        if h2h.height >= config.min_h2h_games:
            historical = h2h["points_for" if team == a["team"] else "points_against"].mean()
        if own["last"] and opponent["last"]:
            last = _mean(own["last"]["points_for"], opponent["last"]["points_against"])
        scale = config.points_scale
    else:
        raise ValueError("Unsupported points market")
    return [factor(key, label, value, reference, scale) for key, label, value in (
        ("offense", "Referencia basada en puntos anotados", offense),
        ("defense", "Referencia basada en puntos permitidos", defense),
        ("venue", "Referencia ofensiva/defensiva local–visitante", venue),
        ("h2h", "Referencia de enfrentamientos recientes", historical),
        ("last_game", "Referencia del último partido de cada equipo", last),
    )]


def score_factors(factors: list[dict], weights: tuple[tuple[str, float], ...], sample: int, config: PickConfig) -> dict:
    """Missing weights remain in the denominator: missing evidence cannot inflate scores."""
    weights = dict(weights)
    total_weight = sum(weights.values())
    reliability = min(1.0, sample / config.full_sample)
    details = [{**f, "weight": weights[f["key"]], "contribution":
                None if f["strength"] is None else 100 * f["strength"] * weights[f["key"]] / total_weight * reliability}
               for f in factors]
    known = [f for f in details if f["contribution"] is not None]
    signed = sum(f["contribution"] for f in known)
    direction = 1 if signed > 0 else -1 if signed < 0 else 0
    return {"score": round(abs(signed), 1), "signed_score": signed, "direction": direction,
            "coverage": sum(f["weight"] for f in known) / total_weight,
            "sample_multiplier": reliability, "factors": details,
            "supporting": sorted((f for f in known if f["contribution"] * direction > 0), key=lambda f: -abs(f["contribution"])),
            "opposing": sorted((f for f in known if f["contribution"] * direction < 0), key=lambda f: -abs(f["contribution"])),
            "eligible": sample >= config.min_games and len(known) >= config.min_factors and abs(signed) >= config.min_score}
