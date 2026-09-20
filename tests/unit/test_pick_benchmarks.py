import pytest

from nfl_analytics.analysis.pick_benchmarks import benchmark_directions, benchmark_report, settle_benchmarks, wilson_interval


def test_rules_only_use_pregame_form_and_tie_policy():
    matchup = {"team_a": {"form": {"win_pct": .6, "avg_margin": 2}},
               "team_b": {"form": {"win_pct": .6, "avg_margin": 4}}}
    assert benchmark_directions(matchup, "moneyline") == {
        "always_home": 1, "better_recent_record": 1, "better_recent_margin": -1}
    matchup["team_a"]["form"]["win_pct"] = None
    assert benchmark_directions(matchup, "spread")["better_recent_record"] is None


def test_pairing_excludes_abstentions_pushes_and_missing_from_both_rates():
    rows = [{"market": "moneyline", "score": 30, "outcome": outcome,
             "benchmark_outcomes": {"always_home": benchmark}}
            for outcome, benchmark in [("favorable", "unfavorable"), ("unfavorable", "favorable"),
                                       ("favorable", "favorable"), (None, "favorable"),
                                       ("push", "push"), ("favorable", None)]]
    summary = next(r for r in benchmark_report(rows) if r["score_bucket"] == "all")
    assert summary["opportunities"] == 6
    assert summary["issued"] == 5 and summary["abstentions"] == 1
    assert summary["paired_games"] == 3 and summary["excluded_push_or_missing"] == 2
    assert summary["score_rate"] == summary["benchmark_rate"] == pytest.approx(2/3)
    assert summary["only_score_wins"] == summary["only_benchmark_wins"] == 1
    assert summary["difference_percentage_points"] == 0


def test_score_boundaries_count_once_and_include_100():
    rows = [{"market": "moneyline", "score": value, "outcome": "favorable",
             "benchmark_outcomes": {"always_home": "unfavorable"}} for value in (0,20,40,60,80,100)]
    report = benchmark_report(rows)
    assert sum(r["paired_games"] for r in report if r["score_bucket"] != "all") == 6
    assert next(r for r in report if r["score_bucket"] == "80–100")["paired_games"] == 2


def test_wilson_empty_and_small_sample():
    assert wilson_interval(0, 0) == (None, None)
    lo, hi = wilson_interval(5, 10)
    assert lo == pytest.approx(.23659309)
    assert hi == pytest.approx(.76340691)


def test_totals_use_same_reference_and_explicit_team():
    game = {"home_team": "BUF", "away_team": "MIA", "home_score": 24, "away_score": 17}
    candidate = {"market": "team_total", "team": "MIA", "baseline": 20}
    result = settle_benchmarks({"always_over": 1, "always_under": -1}, game, candidate)
    assert result == {"always_over": "unfavorable", "always_under": "favorable"}
    candidate.update(market="game_total", baseline=41)
    assert set(settle_benchmarks({"always_over": 1, "always_under": -1}, game, candidate).values()) == {"push"}
