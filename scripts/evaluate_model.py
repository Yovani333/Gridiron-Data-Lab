"""Chronological evaluation from the project's own data layer.

Example: uv run python scripts/evaluate_model.py --seasons 2024 2025
"""

import argparse
import json
from pathlib import Path

from nfl_analytics.analysis.model_config import ModelConfig
from nfl_analytics.analysis.probability import fit_model
from nfl_analytics.analysis.validation import ablation, examples_from_season, walk_forward
from nfl_analytics.data.datasets import model_season_data
from nfl_analytics.presentation.service import initialize


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate model_v0_1 without future-game features")
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--diagnostics-output", type=Path, help="Compact UI diagnostics JSON")
    parser.add_argument("--model-output", type=Path, help="Optional trained artifact path")
    parser.add_argument("--model-only", action="store_true", help="Fit an artifact without recomputing validation")
    parser.add_argument("--ablation", action="store_true", help="Refit without each model feature")
    args = parser.parse_args()
    initialize()
    config = ModelConfig()
    examples = []
    for season in sorted(set(args.seasons)):
        data = model_season_data(season)
        if data.stats.frame is None:
            raise RuntimeError(f"{season}: team stats unavailable: {data.stats.message}")
        eligible = examples_from_season(data, config)
        if not eligible:
            raise RuntimeError(f"{season}: no eligible games; verify schedule and box-score coverage")
        print(f"{season}: {len(eligible)} juegos elegibles antes del kickoff (corte por fecha)")
        examples.extend(eligible)
    if not args.model_only:
        report = walk_forward(examples, config)
        if args.ablation:
            report["ablation"] = ablation(examples, config)
        print(json.dumps({k: v for k, v in report.items() if k != "predictions"}, indent=2, ensure_ascii=False))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.diagnostics_output:
            args.diagnostics_output.parent.mkdir(parents=True, exist_ok=True)
            args.diagnostics_output.write_text(json.dumps({k: v for k, v in report.items() if k != "predictions"}, indent=2), encoding="utf-8")
    if args.model_output:
        if len(examples) < config.min_training_games:
            raise ValueError("Not enough eligible games for a model artifact")
        model = fit_model(examples, config)
        args.model_output.parent.mkdir(parents=True, exist_ok=True)
        args.model_output.write_text(json.dumps(model.as_dict(), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
