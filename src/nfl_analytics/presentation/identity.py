"""Safe visual identities from provider metadata, with text fallbacks."""

from html import escape
import re
from urllib.parse import urlsplit

import streamlit as st


def image_url(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme == "https" and parsed.hostname and not parsed.username else None


def team_identity(team: str) -> dict:
    item = st.session_state.get("team_identities", {}).get(team, {})
    color = item.get("team_color")
    return {"name": item.get("team_name") or team,
            "color": color if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#1685ff",
            "logo": image_url(item.get("team_logo_espn"))}


def avatar(url, label: str, *, player: bool = False) -> str:
    url = image_url(url)
    initials = "".join(part[0] for part in label.split()[:2]) if player else label
    image = f'<img src="{escape(url, quote=True)}" alt="{escape(label, quote=True)}" loading="lazy" referrerpolicy="no-referrer">' if url else ""
    return f'<span class="identity-avatar {"portrait" if player else "crest"}"><span>{escape(initials)}</span>{image}</span>'


def team_badge(team: str) -> str:
    identity = team_identity(team)
    return f'<div class="team-identity" style="--team-accent:{identity["color"]}">{avatar(identity["logo"], team)}<span><strong>{escape(team)}</strong><small>{escape(identity["name"])}</small></span></div>'
