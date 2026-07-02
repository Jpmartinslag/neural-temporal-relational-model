"""
HERALD -- France ZE2020 dynamic graph ranker falsification block.

Runs controlled ablations/placebos for the HERALD_25 dynamic graph ranker.
Inputs are read-only; perturbations are applied in memory.

No causal claim. No automatic recommendation. No policy prescription.
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

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_graph_ranker import (
    BASE_FEATURE_COLUMNS,
    DEFAULT_EVAL_YEARS_BY_HORIZON,
    DEFAULT_K,
    DEFAULT_MAX_EPOCHS,
    EDGE_TYPES,
    load_edges,
    load_nodes,
    run_dynamic_graph_ranker,
)

CLAIM_STATUS = "dynamic_graph_falsification_exploratory_not_recommendation"

TEMPORAL_COLUMNS = [
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
]

SECTOR_COLUMNS = [
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

SCENARIOS = [
    "full_control",
    "no_edges",
    "edge_sign_only",
    "random_edge_weights",
    "random_edge_targets",
    "no_cross_ze_same_sector",
    "no_intra_ze_sector",
    "no_ze_similarity",
    "temporal_shuffle",
    "sector_shuffle",
]


def _empty_edges_like(edges: pd.DataFrame) -> pd.DataFrame:
    return edges.iloc[0:0].copy()


def _shuffle_columns(
    df: pd.DataFrame,
    columns: list[str],
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


def apply_dynamic_graph_falsification(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenario: str,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown dynamic graph falsification scenario: {scenario}")

    out_nodes = nodes.copy()
    out_edges = edges.copy()
    rng = np.random.default_rng(seed)

    if scenario == "full_control":
        return out_nodes, out_edges
    if scenario == "no_edges":
        return out_nodes, _empty_edges_like(out_edges)
    if scenario == "edge_sign_only":
        out_edges["edge_weight"] = np.sign(out_edges["edge_weight"].to_numpy(dtype=float))
        out_edges.loc[out_edges["edge_weight"] == 0, "edge_weight"] = 1.0
        return out_nodes, out_edges
    if scenario == "random_edge_weights":
        out_edges["edge_weight"] = rng.permutation(out_edges["edge_weight"].to_numpy())
        return out_nodes, out_edges
    if scenario == "random_edge_targets":
        for _, idx in out_edges.groupby(["decision_year", "edge_type"], sort=False).groups.items():
            idx_list = list(idx)
            if len(idx_list) <= 1:
                continue
            out_edges.loc[idx_list, "target_node_id"] = rng.permutation(
                out_edges.loc[idx_list, "target_node_id"].to_numpy()
            )
        out_edges = out_edges[out_edges["source_node_id"] != out_edges["target_node_id"]].copy()
        return out_nodes, out_edges
    if scenario.startswith("no_"):
        edge_type = scenario.removeprefix("no_")
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"Unknown edge type in scenario: {scenario}")
        return out_nodes, out_edges[out_edges["edge_type"] != edge_type].copy()
    if scenario == "temporal_shuffle":
        return _shuffle_columns(out_nodes, TEMPORAL_COLUMNS, seed=seed, group_cols=["decision_year"]), out_edges
    if scenario == "sector_shuffle":
        return _shuffle_columns(
            out_nodes,
            SECTOR_COLUMNS,
            seed=seed,
            group_cols=["ze2020", "decision_year"],
        ), out_edges
    raise AssertionError("unreachable")


def run_dynamic_graph_falsification_suite(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenarios: list[str] = SCENARIOS,
    eval_years: list[int] | None = None,
    k: int = DEFAULT_K,
    min_train_years: int = 3,
    seed: int = 42,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    target_horizon: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS_BY_HORIZON[target_horizon]
    prediction_frames = []
    metric_frames = []
    manifest_rows = []

    for scenario in scenarios:
        scenario_nodes, scenario_edges = apply_dynamic_graph_falsification(
            nodes, edges, scenario=scenario, seed=seed
        )
        predictions, metrics = run_dynamic_graph_ranker(
            scenario_nodes,
            scenario_edges,
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
        manifest_rows.append(
            {
                "falsification_scenario": scenario,
                "seed": int(seed),
                "target_horizon_years": int(target_horizon),
                "eval_years": " ".join(str(y) for y in eval_years),
                "k": int(k),
                "max_epochs": int(max_epochs),
                "claim_status": CLAIM_STATUS,
            }
        )

    all_predictions = pd.concat(prediction_frames, ignore_index=True)
    all_metrics = pd.concat(metric_frames, ignore_index=True)
    manifest = pd.DataFrame(manifest_rows)
    return all_predictions, all_metrics, manifest


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
            "France ZE2020 dynamic graph ranker falsifications. Exploratory only; "
            "no causal or automatic recommendation claim."
        )
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="+", default=SCENARIOS, choices=SCENARIOS)
    parser.add_argument("--target-horizon", type=int, choices=[1, 3], default=3)
    parser.add_argument("--eval-years", type=int, nargs="+", default=None)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--min-train-years", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS)
    args = parser.parse_args()

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    eval_years = args.eval_years or DEFAULT_EVAL_YEARS_BY_HORIZON[args.target_horizon]
    predictions, metrics, manifest = run_dynamic_graph_falsification_suite(
        nodes,
        edges,
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
    stem = f"fr_ze2020_dynamic_graph_falsification_{args.target_horizon}y"
    predictions_path = args.output_dir / f"{stem}_predictions_v1.csv"
    metrics_path = args.output_dir / f"{stem}_metrics_v1.csv"
    summary_path = args.output_dir / f"{stem}_summary_v1.csv"
    manifest_path = args.output_dir / f"{stem}_manifest_v1.csv"
    json_path = args.output_dir / f"{stem}_run_v1.json"

    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    manifest.to_csv(manifest_path, index=False)
    json_path.write_text(
        json.dumps(
            {
                "status": "DYNAMIC_GRAPH_FALSIFICATION_RUN_COMPLETE",
                "claim_status": CLAIM_STATUS,
                "scenarios": args.scenarios,
                "target_horizon_years": args.target_horizon,
                "eval_years": eval_years,
                "seed": args.seed,
                "max_epochs": args.max_epochs,
                "base_feature_columns": BASE_FEATURE_COLUMNS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print("DYNAMIC GRAPH FALSIFICATIONS -- exploratory, not causal, not automatic recommendation.")
    print(summary.pivot(index="falsification_scenario", columns="model", values="mean_ndcg_at_k"))
    print(f"Predictions: {predictions_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
