"""Pure descriptive analysis built on the project's normalized data contracts."""

from .form import head_to_head, recent_form
from .matchup import analyze_matchup, compare_teams
from .play_by_play import advanced_summary
from .team_stats import box_score_summary

__all__ = ["head_to_head", "recent_form", "analyze_matchup", "compare_teams", "advanced_summary", "box_score_summary"]
