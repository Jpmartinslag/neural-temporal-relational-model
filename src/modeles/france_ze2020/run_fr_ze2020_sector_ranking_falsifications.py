"""
HERALD -- France ZE2020 sector ranking falsification block.

Runs controlled ablations/placebos for the temporal-relational ZE x sector
ranking task. Inputs are read-only; every perturbation is applied in memory.
Outputs are exploratory falsification evidence only: no causal claim, no
automatic recommendation, no policy prescription.
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

from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (
    DEFAULT_EVAL_YEARS_BY_HORIZON,
    DEFAULT_EVAL_YEARS,
    DEFAULT_K,
    DEFAULT_MAX_EPOCHS,
    RANKING_PANEL_PATH,
    load_ranking_panel,
    run_sector_ranking,
)

CLAIM_STATUS = "sector_ranking_falsification_exploratory_not_recommendation"

RELATIONAL_COLUMNS = [
    "relation_signal_strength_mean_to_t",
    "relation_signal_strength_max_to_t",
    "relation_stability_mean_to_t",
    "relation_count_to_t",
]

SECTOR_COMPOSITION_COLUMNS = [
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

TEMPORAL_COLUMNS = [
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
]

SCENARIOS = [
    "full_control",
    "no_relational",
    "random_relational",
    "no_sector_composition",
    "sector_shuffle",
    "temporal_shuffle",
]


def _shuffle_columns(df: pd.DataFrame, columns: list[str], seed: int, group_cols: list[str] | None = None) -> pd.DataFrame:
    out = df.copy()
    rng = np.random.default_rng(seed)
    if group_cols is None:
        for col in columns:
            out[col] = rng.permutation(out[col].to_numpy())
        return out

    for _, idx in out.groupby(group_cols, sort=False).groups.items():
        idx_list = list(idx)
        if len(idx_list) <= 1:
            continue
        for col in columns:
            out.loc[idx_list, col] = rng.permutation(out.loc[idx_list, col].to_numpy())
    return out


def apply_falsification(panel: pd.DataFrame, scenario: str, seed: int) -> pd.DataFrame:
    """Return an in-memory perturbed copy for one falsification scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown falsification scenario: {scenario}")

    out = panel.copy()
    if scenario == "full_control":
        return out
    if scenario == "no_relational":
        out[RELATIONAL_COLUMNS] = 0.0
        return out
    if scenario == "random_relational":
        return _shuffle_columns(out, RELATIONAL_COLUMNS, seed=seed, group_cols=["decision_year"])
    if scenario == "no_sector_composition":
        out[SECTOR_COMPOSITION_COLUMNS] = 0.0
        return out
    if scenario == "sector_shuffle":
        return _shuffle_columns(out, SECTOR_COMPOSITION_COLUMNS, seed=seed, group_cols=["ze2020", "decision_year"])
    if scenario == "temporal_shuffle":
        return _shuffle_columns(out, TEMPORAL_COLUMNS, seed=seed, group_cols=["decision_year"])
    raise AssertionError("unreachable")


def run_falsification_suite(
    panel: pd.DataFrame,
    scenarios: list[str] = SCENARIOS,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    k: int = DEFAULT_K,
    min_train_years: int = 3,
    seed: int = 42,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    target_horizon: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames = []
    metric_frames = []
    scenario_rows = []

    for scenario in scenarios:
        perturbed = apply_falsification(panel, scenario=scenario, seed=seed)
        predictions, metrics = run_sector_ranking(
            perturbed,
            eval_years=eval_years,
            k=k,
            min_train_years=min_train_years,
            seed=seed,
            max_epochs=max_epochs,
            target_horizon=target_horizon,
        )
        predictions["falsification_scenario"] = scenario
        predictions["claim_status"] = CLAIM_STATUS
        metrics["falsification_scenario"] = scenario
        metrics["claim_status"] = CLAIM_STATUS
        prediction_frames.append(predictions)
        metric_frames.append(metrics)
        scenario_rows.append(
            {
                "falsification_scenario": scenario,
                "seed": seed,
                "target_horizon_years": target_horizon,
                "eval_years": " ".join(str(y) for y in eval_years),
                "k": k,
                "max_epochs": max_epochs,
                "claim_status": CLAIM_STATUS,
            }
        )

    all_predictions = pd.concat(prediction_frames, ignore_index=True)
    all_metrics = pd.concat(metric_frames, ignore_index=True)
    scenario_manifest = pd.DataFrame(scenario_rows)
    return all_predictions, all_metrics, scenario_manifest


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby(["falsification_scenario", "model"], as_index=False)
        .agg(
            mean_ndcg_at_k=("ndcg_at_k", "mean"),
            std_ndcg_at_k=("ndcg_at_k", "std"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_hit_rate_at_k=("hit_rate_at_k", "mean"),
            n_rows=("ndcg_at_k", "size"),
        )
        .fillna({"std_ndcg_at_k": 0.0})
        .sort_values(["falsification_scenario", "mean_ndcg_at_k"], ascending=[True, False])
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 sector ranking falsifications. Exploratory only; "
            "no causal or automatic recommendation claim."
        )
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="+", default=SCENARIOS, choices=SCENARIOS)
    parser.add_argument("--target-horizon", type=int, choices=[1, 3], default=3)
    parser.add_argument("--eval-years", type=int, nargs="+", default=None)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--min-train-years", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS)
    args = parser.parse_args()

    panel = load_ranking_panel(args.panel)
    eval_years = args.eval_years or DEFAULT_EVAL_YEARS_BY_HORIZON[args.target_horizon]
    predictions, metrics, scenario_manifest = run_falsification_suite(
        panel,
        scenarios=args.scenarios,
        eval_years=eval_years,
        k=args.k,
        min_train_years=args.min_train_years,
        seed=args.seed,
        max_epochs=args.max_epochs,
        target_horizon=args.target_horizon,
    )
    summary = summarize_metrics(metrics)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / f"fr_ze2020_sector_ranking_falsification_{args.target_horizon}y_predictions_v1.csv"
    metrics_path = args.output_dir / f"fr_ze2020_sector_ranking_falsification_{args.target_horizon}y_metrics_v1.csv"
    summary_path = args.output_dir / f"fr_ze2020_sector_ranking_falsification_{args.target_horizon}y_summary_v1.csv"
    manifest_path = args.output_dir / f"fr_ze2020_sector_ranking_falsification_{args.target_horizon}y_manifest_v1.csv"
    json_path = args.output_dir / f"fr_ze2020_sector_ranking_falsification_{args.target_horizon}y_run_v1.json"

    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    scenario_manifest.to_csv(manifest_path, index=False)
    run_payload = {
        "status": "FALSIFICATION_RUN_COMPLETE",
        "claim_status": CLAIM_STATUS,
        "scenarios": args.scenarios,
        "target_horizon_years": args.target_horizon,
        "eval_years": eval_years,
        "seed": args.seed,
        "max_epochs": args.max_epochs,
    }
    json_text = json.dumps(run_payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(json_text)

    print("SECTOR RANKING FALSIFICATIONS -- exploratory, not causal, not automatic recommendation.")
    print(summary.pivot(index="falsification_scenario", columns="model", values="mean_ndcg_at_k"))
    print(f"Predictions: {predictions_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
