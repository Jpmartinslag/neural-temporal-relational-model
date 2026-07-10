"""
HERALD -- France ZE2020 top-3 entry relation-lift falsifications.

Runs in-memory perturbations around the HERALD_36 relation-lift diagnostic.
This is a relation-layer construction test, not a final model, not a causal
claim, and not an automatic recommendation system.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_falsifications import (  # noqa: E402
    SCENARIOS,
    apply_top3_entry_falsification,
)
from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_lift_diagnostic import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    DEFAULT_SEEDS,
    FEATURE_CONFIGS,
    run_top3_entry_lift_diagnostic,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (  # noqa: E402
    RANKING_PANEL_PATH,
    load_ranking_panel,
)

CLAIM_STATUS = "top3_entry_lift_falsification_not_recommendation"


def run_top3_entry_lift_falsification_suite(
    panel: pd.DataFrame,
    *,
    scenarios: list[str] | None = None,
    target_horizon: int = 3,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
    feature_configs: list[str] | None = None,
    max_epochs: int = 80,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scenarios = scenarios or SCENARIOS
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    feature_configs = feature_configs or FEATURE_CONFIGS
    unknown = set(scenarios).difference(SCENARIOS)
    if unknown:
        raise ValueError(f"Unknown scenarios: {sorted(unknown)}")

    prediction_frames = []
    metric_frames = []
    summary_frames = []
    for scenario in scenarios:
        perturbed = apply_top3_entry_falsification(panel, scenario=scenario, seed=min(seeds) + 9100)
        predictions, metrics, summary = run_top3_entry_lift_diagnostic(
            perturbed,
            target_horizon=target_horizon,
            eval_years=eval_years,
            seeds=seeds,
            feature_configs=feature_configs,
            max_epochs=max_epochs,
        )
        for frame in (predictions, metrics, summary):
            frame["falsification_scenario"] = scenario
            frame["claim_status"] = CLAIM_STATUS
        prediction_frames.append(predictions)
        metric_frames.append(metrics)
        summary_frames.append(summary)

    all_predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    all_metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    all_summary = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    all_summary = all_summary.sort_values(
        ["falsification_scenario", "model", "mean_ndcg_at_k"],
        ascending=[True, True, False],
    ).reset_index(drop=True)
    return all_predictions, all_metrics, all_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="France ZE2020 top-3 entry relation-lift falsifications; exploratory only."
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-horizon", type=int, choices=[3], default=3)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--feature-configs", nargs="+", choices=FEATURE_CONFIGS, default=FEATURE_CONFIGS)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=SCENARIOS)
    parser.add_argument("--max-epochs", type=int, default=80)
    args = parser.parse_args()

    panel = load_ranking_panel(args.panel)
    predictions, metrics, summary = run_top3_entry_lift_falsification_suite(
        panel,
        scenarios=args.scenarios,
        target_horizon=args.target_horizon,
        eval_years=args.eval_years,
        seeds=args.seeds,
        feature_configs=args.feature_configs,
        max_epochs=args.max_epochs,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "fr_ze2020_top3_entry_lift_falsification_predictions_v1.csv", index=False)
    metrics.to_csv(args.output_dir / "fr_ze2020_top3_entry_lift_falsification_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / "fr_ze2020_top3_entry_lift_falsification_summary_v1.csv", index=False)
    (args.output_dir / "fr_ze2020_top3_entry_lift_falsification_run_v1.json").write_text(
        json.dumps(
            {
                "status": "TOP3_ENTRY_LIFT_FALSIFICATION_COMPLETE",
                "panel": str(args.panel),
                "target_horizon": args.target_horizon,
                "eval_years": args.eval_years,
                "seeds": args.seeds,
                "feature_configs": args.feature_configs,
                "scenarios": args.scenarios,
                "max_epochs": args.max_epochs,
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print("TOP-3 ENTRY LIFT FALSIFICATIONS -- not causal, not recommendation.")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
