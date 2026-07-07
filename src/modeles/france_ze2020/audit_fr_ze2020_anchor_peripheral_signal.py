"""
HERALD -- France ZE2020 anchor/peripheral relation-signal audit.

Tests simple interpretable pair scores on the local dual-endpoint relation gate.
No training, no causal claim, no recommendation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    DEFAULT_EDGES_PATH,
    apply_relation_scenario,
    build_pairwise_relation_samples,
    load_edges,
    load_nodes,
)

DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_SCENARIOS = ["dual_endpoint_matched_negatives", "dual_endpoint_temporal_sector_shuffle"]
CLAIM_STATUS = "anchor_peripheral_signal_audit_exploratory_not_recommendation"


def add_anchor_peripheral_scores(samples: pd.DataFrame) -> pd.DataFrame:
    out = samples.copy()
    out["dominance_asymmetry_score"] = (
        out["source_dominant_sector_flag_t"].astype(float)
        - out["target_dominant_sector_flag_t"].astype(float)
    ).abs()
    out["sector_share_product_score"] = (
        out["source_sector_share_t"].astype(float) * out["target_sector_share_t"].astype(float)
    )
    out["anchor_peripheral_score"] = (
        out["dominance_asymmetry_score"] * out["sector_share_product_score"]
    )
    return out


def _score_metrics(frame: pd.DataFrame, score_col: str) -> dict[str, float]:
    labels = frame["relation_label"].astype(int)
    scores = frame[score_col].astype(float)
    return {
        "average_precision": float(average_precision_score(labels, scores)),
        "roc_auc": float(roc_auc_score(labels, scores)),
    }


def run_anchor_peripheral_audit(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    scenarios: list[str] = DEFAULT_SCENARIOS,
    positive_edge_states: list[str] | None = None,
    node_feature_lag: int = 1,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    score_cols = [
        "dominance_asymmetry_score",
        "sector_share_product_score",
        "anchor_peripheral_score",
    ]
    metric_rows = []
    scored_frames = []
    for scenario in scenarios:
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
        scored["falsification_scenario"] = scenario
        scored["negative_strategy"] = negative_strategy
        scored["claim_status"] = CLAIM_STATUS
        scored_frames.append(scored)

        for score_col in score_cols:
            if scored["relation_label"].nunique() < 2:
                continue
            metrics = _score_metrics(scored, score_col)
            metric_rows.append(
                {
                    "falsification_scenario": scenario,
                    "negative_strategy": negative_strategy,
                    "score_name": score_col,
                    "eval_scope": "all_years",
                    "eval_year": "all",
                    "n_rows": int(len(scored)),
                    "n_positive": int(scored["relation_label"].sum()),
                    "average_precision": metrics["average_precision"],
                    "roc_auc": metrics["roc_auc"],
                    "claim_status": CLAIM_STATUS,
                }
            )
            for year, year_frame in scored.groupby("decision_year"):
                if year_frame["relation_label"].nunique() < 2:
                    continue
                year_metrics = _score_metrics(year_frame, score_col)
                metric_rows.append(
                    {
                        "falsification_scenario": scenario,
                        "negative_strategy": negative_strategy,
                        "score_name": score_col,
                        "eval_scope": "by_year",
                        "eval_year": str(int(year)),
                        "n_rows": int(len(year_frame)),
                        "n_positive": int(year_frame["relation_label"].sum()),
                        "average_precision": year_metrics["average_precision"],
                        "roc_auc": year_metrics["roc_auc"],
                        "claim_status": CLAIM_STATUS,
                    }
                )

    metrics = pd.DataFrame(metric_rows)
    all_years = metrics[metrics["eval_scope"] == "all_years"]
    full = all_years[all_years["falsification_scenario"] == "dual_endpoint_matched_negatives"]
    shuffle = all_years[all_years["falsification_scenario"] == "dual_endpoint_temporal_sector_shuffle"]
    if not full.empty and not shuffle.empty:
        shuffle_ap = dict(zip(shuffle["score_name"], shuffle["average_precision"]))
        metrics["ap_drop_vs_temporal_sector_shuffle"] = metrics.apply(
            lambda row: row["average_precision"] - shuffle_ap.get(row["score_name"], float("nan"))
            if row["falsification_scenario"] == "dual_endpoint_matched_negatives"
            and row["eval_scope"] == "all_years"
            else float("nan"),
            axis=1,
        )
    else:
        metrics["ap_drop_vs_temporal_sector_shuffle"] = float("nan")

    return pd.concat(scored_frames, ignore_index=True), metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit interpretable anchor/peripheral relation scores."
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--scenarios", nargs="+", default=DEFAULT_SCENARIOS)
    parser.add_argument("--positive-edge-states", nargs="*", default=["new_relation"])
    parser.add_argument("--node-feature-lag", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    scored, metrics = run_anchor_peripheral_audit(
        nodes=nodes,
        edges=edges,
        scenarios=args.scenarios,
        positive_edge_states=args.positive_edge_states,
        node_feature_lag=args.node_feature_lag,
        seed=args.seed,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_anchor_peripheral_signal"
    scored_path = args.output_dir / f"{stem}_scored_pairs_v1.csv"
    metrics_path = args.output_dir / f"{stem}_metrics_v1.csv"
    run_path = args.output_dir / f"{stem}_run_v1.json"
    scored.to_csv(scored_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "nodes": str(args.nodes),
                "edges": str(args.edges),
                "scored_pairs": str(scored_path),
                "metrics": str(metrics_path),
                "scenarios": args.scenarios,
                "positive_edge_states": " ".join(args.positive_edge_states or []),
                "node_feature_lag": args.node_feature_lag,
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(metrics[metrics["eval_scope"] == "all_years"].to_string(index=False))
    print(f"Wrote {scored_path}")
    print(f"Wrote {metrics_path}")


if __name__ == "__main__":
    main()
