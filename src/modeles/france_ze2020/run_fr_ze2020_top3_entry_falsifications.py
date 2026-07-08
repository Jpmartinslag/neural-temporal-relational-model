"""
HERALD -- France ZE2020 top-3 entry ranking falsifications.

Runs in-memory perturbations around the HERALD_32 target-aligned smoke. This
script reuses the smoke runner; it does not define a new model and does not
write to canonical processed data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_ranking_smoke import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    DEFAULT_SEEDS,
    FEATURE_CONFIGS,
    run_top3_entry_ranking_smoke,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (  # noqa: E402
    RANKING_PANEL_PATH,
    load_ranking_panel,
)

CLAIM_STATUS = "top3_entry_falsification_not_recommendation"
SCENARIOS = [
    "full_control",
    "temporal_shuffle",
    "sector_shuffle",
    "target_shuffle",
]
TEMPORAL_COLUMNS = [
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
]
SECTOR_COLUMNS = [
    "sector_count_t",
    "sector_share_t",
    "sector_rank_in_ze_year_t",
    "dominant_sector_flag_t",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "national_sector_share_lag_1",
    "national_sector_growth_lag_1",
]


def _shuffle_columns(
    df: pd.DataFrame,
    columns: list[str],
    *,
    seed: int,
    group_cols: list[str],
) -> pd.DataFrame:
    out = df.copy()
    rng = np.random.default_rng(seed)
    for _, idx in out.groupby(group_cols, sort=False).groups.items():
        idx_list = list(idx)
        if len(idx_list) <= 1:
            continue
        for col in columns:
            out.loc[idx_list, col] = rng.permutation(out.loc[idx_list, col].to_numpy())
    return out


def apply_top3_entry_falsification(panel: pd.DataFrame, scenario: str, seed: int) -> pd.DataFrame:
    """Return an in-memory perturbed copy for one falsification scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown falsification scenario: {scenario}")
    if scenario == "full_control":
        return panel.copy()
    if scenario == "temporal_shuffle":
        return _shuffle_columns(panel, TEMPORAL_COLUMNS, seed=seed, group_cols=["decision_year"])
    if scenario == "sector_shuffle":
        return _shuffle_columns(panel, SECTOR_COLUMNS, seed=seed, group_cols=["ze2020", "decision_year"])
    if scenario == "target_shuffle":
        return _shuffle_columns(
            panel,
            ["future_growth_3y", "sector_count_t_plus_3", "sector_share_t_plus_3"],
            seed=seed,
            group_cols=["ze2020", "decision_year"],
        )
    raise AssertionError("unreachable")


def run_top3_entry_falsification_suite(
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
        perturbed = apply_top3_entry_falsification(panel, scenario=scenario, seed=min(seeds) + 9000)
        predictions, metrics, summary = run_top3_entry_ranking_smoke(
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
        description="France ZE2020 top-3 entry falsifications; exploratory only."
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
    predictions, metrics, summary = run_top3_entry_falsification_suite(
        panel,
        scenarios=args.scenarios,
        target_horizon=args.target_horizon,
        eval_years=args.eval_years,
        seeds=args.seeds,
        feature_configs=args.feature_configs,
        max_epochs=args.max_epochs,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "fr_ze2020_top3_entry_falsification_predictions_v1.csv", index=False)
    metrics.to_csv(args.output_dir / "fr_ze2020_top3_entry_falsification_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / "fr_ze2020_top3_entry_falsification_summary_v1.csv", index=False)
    (args.output_dir / "fr_ze2020_top3_entry_falsification_run_v1.json").write_text(
        json.dumps(
            {
                "status": "TOP3_ENTRY_FALSIFICATION_COMPLETE",
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

    print("TOP-3 ENTRY FALSIFICATIONS -- not causal, not recommendation.")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
