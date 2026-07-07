"""
HERALD -- France ZE2020 relation lift-over-formulas audit.

Compares the local compatibility learner against simple interpretable pair
formulas on the same dual-endpoint relation gate.

No causal claim. No automatic recommendation. No validated dynamic-GNN claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.audit_fr_ze2020_anchor_peripheral_signal import (  # noqa: E402
    add_anchor_peripheral_scores,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    DEFAULT_EDGES_PATH,
    apply_relation_scenario,
    build_pairwise_relation_samples,
    load_edges,
    load_nodes,
    run_dynamic_relation_learner,
)

DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_SCENARIOS = ["dual_endpoint_matched_negatives", "dual_endpoint_temporal_sector_shuffle"]
DEFAULT_EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
FORMULA_SCORE_COLUMNS = [
    "dominance_asymmetry_score",
    "sector_share_product_score",
    "anchor_peripheral_score",
]
CLAIM_STATUS = "relation_lift_over_formulas_audit_exploratory_not_recommendation"


def _safe_metrics(labels: pd.Series, scores: pd.Series) -> tuple[float, float]:
    if labels.nunique() < 2:
        return float("nan"), float("nan")
    labels_array = labels.astype(int).to_numpy()
    scores_array = scores.astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    return (
        float(average_precision_score(labels_array, scores_array)),
        float(roc_auc_score(labels_array, scores_array)),
    )


def _formula_metrics_for_scenario(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenario: str,
    eval_years: list[int],
    positive_edge_states: list[str] | None,
    node_feature_lag: int,
    seed: int,
) -> pd.DataFrame:
    scenario_nodes, scenario_edges, negative_strategy = apply_relation_scenario(
        nodes,
        edges,
        scenario=scenario,
        seed=seed,
    )
    samples = build_pairwise_relation_samples(
        scenario_nodes,
        scenario_edges,
        negative_strategy=negative_strategy,
        negative_ratio=1,
        node_feature_lag=node_feature_lag,
        positive_edge_states=positive_edge_states,
        seed=seed,
    )
    scored = add_anchor_peripheral_scores(samples)

    rows: list[dict[str, object]] = []
    for eval_year in eval_years:
        test = scored[scored["decision_year"] == eval_year].copy()
        if test.empty or test["relation_label"].nunique() < 2:
            continue
        for score_name in FORMULA_SCORE_COLUMNS:
            ap, auc = _safe_metrics(test["relation_label"], test[score_name])
            rows.append(
                {
                    "eval_year": int(eval_year),
                    "falsification_scenario": scenario,
                    "negative_strategy": negative_strategy,
                    "model_or_score": score_name,
                    "score_family": "formula",
                    "average_precision": ap,
                    "roc_auc": auc,
                    "n_rows": int(len(test)),
                    "n_positive": int(test["relation_label"].sum()),
                    "claim_status": CLAIM_STATUS,
                }
            )
    return pd.DataFrame(rows)


def _compatibility_metrics_for_scenarios(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenarios: list[str],
    eval_years: list[int],
    positive_edge_states: list[str] | None,
    node_feature_lag: int,
    seed: int,
    max_iter: int,
) -> pd.DataFrame:
    _, metrics, _ = run_dynamic_relation_learner(
        nodes=nodes,
        edges=edges,
        scenarios=scenarios,
        eval_years=eval_years,
        negative_ratio=1,
        min_train_years=2,
        seed=seed,
        max_iter=max_iter,
        test_pair_mode="unseen_pair",
        node_feature_lag=node_feature_lag,
        positive_edge_states=positive_edge_states,
        feature_family="sector_position_no_rank",
        pair_feature_mode="compatibility_only",
    )
    out = metrics[metrics["model"] == "relation_logit"].copy()
    out = out.rename(columns={"model": "model_or_score", "n_test_rows": "n_rows"})
    out["score_family"] = "local_learner"
    out["n_positive"] = np.nan
    out["claim_status"] = CLAIM_STATUS
    return out[
        [
            "eval_year",
            "falsification_scenario",
            "negative_strategy",
            "model_or_score",
            "score_family",
            "average_precision",
            "roc_auc",
            "n_rows",
            "n_positive",
            "claim_status",
        ]
    ].copy()


def run_relation_lift_over_formulas_audit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenarios: list[str] = DEFAULT_SCENARIOS,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    positive_edge_states: list[str] | None = None,
    node_feature_lag: int = 1,
    seed: int = 42,
    max_iter: int = 300,
) -> pd.DataFrame:
    formula_frames = [
        _formula_metrics_for_scenario(
            nodes=nodes,
            edges=edges,
            scenario=scenario,
            eval_years=eval_years,
            positive_edge_states=positive_edge_states,
            node_feature_lag=node_feature_lag,
            seed=seed,
        )
        for scenario in scenarios
    ]
    formula_metrics = pd.concat(formula_frames, ignore_index=True)
    compatibility_metrics = _compatibility_metrics_for_scenarios(
        nodes=nodes,
        edges=edges,
        scenarios=scenarios,
        eval_years=eval_years,
        positive_edge_states=positive_edge_states,
        node_feature_lag=node_feature_lag,
        seed=seed,
        max_iter=max_iter,
    )
    metrics = pd.concat([formula_metrics, compatibility_metrics], ignore_index=True)

    best_formula = (
        formula_metrics.groupby(["eval_year", "falsification_scenario"], as_index=False)
        .agg(best_formula_ap=("average_precision", "max"), best_formula_auc=("roc_auc", "max"))
    )
    metrics = metrics.merge(best_formula, on=["eval_year", "falsification_scenario"], how="left")
    metrics["ap_lift_over_best_formula"] = (
        metrics["average_precision"].astype(float) - metrics["best_formula_ap"].astype(float)
    )
    metrics["auc_lift_over_best_formula"] = (
        metrics["roc_auc"].astype(float) - metrics["best_formula_auc"].astype(float)
    )

    all_year_rows = []
    for (scenario, score_name), group in metrics.groupby(["falsification_scenario", "model_or_score"]):
        weighted_ap = np.average(group["average_precision"], weights=group["n_rows"].astype(float))
        weighted_auc = np.average(group["roc_auc"], weights=group["n_rows"].astype(float))
        best_formula_ap = np.average(group["best_formula_ap"], weights=group["n_rows"].astype(float))
        best_formula_auc = np.average(group["best_formula_auc"], weights=group["n_rows"].astype(float))
        all_year_rows.append(
            {
                "eval_year": "mean",
                "falsification_scenario": scenario,
                "negative_strategy": group["negative_strategy"].iloc[0],
                "model_or_score": score_name,
                "score_family": group["score_family"].iloc[0],
                "average_precision": float(weighted_ap),
                "roc_auc": float(weighted_auc),
                "n_rows": int(group["n_rows"].sum()),
                "n_positive": (
                    float(group["n_positive"].sum())
                    if group["n_positive"].notna().any()
                    else float("nan")
                ),
                "claim_status": CLAIM_STATUS,
                "best_formula_ap": float(best_formula_ap),
                "best_formula_auc": float(best_formula_auc),
                "ap_lift_over_best_formula": float(weighted_ap - best_formula_ap),
                "auc_lift_over_best_formula": float(weighted_auc - best_formula_auc),
            }
        )

    return pd.concat([metrics, pd.DataFrame(all_year_rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare local compatibility learner against formula relation scores."
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--scenarios", nargs="+", default=DEFAULT_SCENARIOS)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--positive-edge-states", nargs="*", default=["new_relation"])
    parser.add_argument("--node-feature-lag", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iter", type=int, default=300)
    args = parser.parse_args()

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    metrics = run_relation_lift_over_formulas_audit(
        nodes=nodes,
        edges=edges,
        scenarios=args.scenarios,
        eval_years=args.eval_years,
        positive_edge_states=args.positive_edge_states,
        node_feature_lag=args.node_feature_lag,
        seed=args.seed,
        max_iter=args.max_iter,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_relation_lift_over_formulas"
    metrics_path = args.output_dir / f"{stem}_metrics_v1.csv"
    run_path = args.output_dir / f"{stem}_run_v1.json"
    metrics.to_csv(metrics_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "nodes": str(args.nodes),
                "edges": str(args.edges),
                "metrics": str(metrics_path),
                "scenarios": args.scenarios,
                "eval_years": args.eval_years,
                "positive_edge_states": " ".join(args.positive_edge_states or []),
                "node_feature_lag": args.node_feature_lag,
                "feature_family": "sector_position_no_rank",
                "pair_feature_mode": "compatibility_only",
                "test_pair_mode": "unseen_pair",
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(metrics[metrics["eval_year"].astype(str) == "mean"].to_string(index=False))
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
