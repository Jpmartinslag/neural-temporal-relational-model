"""Minimal nonlinear transfer gate for the isolated ZE-similarity block."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    EXPANDING_EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_edge_family_isolation_probe import (  # noqa: E402
    build_balanced_family_frame,
)
from src.modeles.france_ze2020.run_fr_ze2020_relation_embedding_linear_probes import (  # noqa: E402
    BASE_FEATURE_COLUMNS,
)
from src.modeles.france_ze2020.run_fr_ze2020_relational_transition_transfer_probe import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    DEFAULT_SEEDS,
    TARGET_COLUMN,
    _shuffle_training_target,
    assign_ze_folds,
    evaluate_transfer_view,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    load_edges,
    load_nodes,
)

CLAIM_STATUS = "similarity_nonlinear_transfer_probe_exploratory_not_recommendation"
VIEW_NAMES = [
    "logit_node_only",
    "logit_ze_similarity",
    "mlp_node_only",
    "mlp_ze_similarity",
    "mlp_ze_similarity_endpoint_randomized",
    "mlp_ze_similarity_target_shuffled",
]
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def make_mlp_scorer(max_epochs: int):
    """Return the fixed DEC-071 MLP behind the shared transfer evaluator."""

    def fit_score(
        train: pd.DataFrame,
        test: pd.DataFrame,
        feature_columns: list[str],
        seed: int,
        shuffle_target: bool,
    ) -> np.ndarray:
        labels = (
            _shuffle_training_target(train, seed=seed)
            if shuffle_target
            else train[TARGET_COLUMN]
        )
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=(32, 16),
                        activation="relu",
                        solver="adam",
                        max_iter=max_epochs,
                        random_state=seed,
                        early_stopping=True,
                        n_iter_no_change=15,
                    ),
                ),
            ]
        )
        model.fit(train[feature_columns], labels)
        return model.predict_proba(test[feature_columns])[:, 1]

    return fit_score


def _summary(metrics: pd.DataFrame) -> pd.DataFrame:
    summary = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_ndcg_at_3=("ndcg_at_3", "mean"),
            mean_precision_at_3=("precision_at_3", "mean"),
            mean_hit_rate_at_3=("hit_rate_at_3", "mean"),
            mean_average_precision=("average_precision", "mean"),
            n_paired_evaluations=("ndcg_at_3", "size"),
            n_seeds=("seed", "nunique"),
        )
        .sort_values("view")
        .reset_index(drop=True)
    )
    summary["claim_status"] = CLAIM_STATUS
    return summary


def evaluate_nonlinear_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    real = metrics[metrics["view"] == "mlp_ze_similarity"][keys + ["ndcg_at_3"]]
    real = real.rename(columns={"ndcg_at_3": "real"})
    comparisons = {}
    for control_name in [
        "mlp_node_only",
        "logit_ze_similarity",
        "mlp_ze_similarity_endpoint_randomized",
        "mlp_ze_similarity_target_shuffled",
    ]:
        control = metrics[metrics["view"] == control_name][keys + ["ndcg_at_3"]]
        control = control.rename(columns={"ndcg_at_3": "control"})
        paired = real.merge(control, on=keys, how="inner", validate="one_to_one")
        delta = paired["real"] - paired["control"]
        comparisons[control_name] = {
            "mean_ndcg_lift": float(delta.mean()),
            "paired_win_rate": float((delta > 0).mean()),
            "n_pairs": int(len(paired)),
        }
    endpoint = comparisons["mlp_ze_similarity_endpoint_randomized"]
    pass_gate = (
        comparisons["mlp_node_only"]["mean_ndcg_lift"] > 0
        and comparisons["logit_ze_similarity"]["mean_ndcg_lift"] > 0
        and endpoint["mean_ndcg_lift"] > 0
        and endpoint["paired_win_rate"] >= 0.60
        and comparisons["mlp_ze_similarity_target_shuffled"]["mean_ndcg_lift"] > 0
    )
    return {
        "gate_pass": bool(pass_gate),
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def run_nonlinear_probe(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
    max_epochs: int = 200,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    nodes = nodes.copy()
    nodes["ze2020"] = nodes["ze2020"].astype(str).str.zfill(4)
    nodes["ze_fold"] = assign_ze_folds(nodes)
    rows: list[dict[str, object]] = []
    mlp_scorer = make_mlp_scorer(max_epochs)

    for seed in seeds:
        real, relation_features = build_balanced_family_frame(
            nodes, edges, ["ze_similarity"], seed=seed
        )
        randomized, randomized_features = build_balanced_family_frame(
            nodes,
            edges,
            ["ze_similarity"],
            seed=seed + 5000,
            randomize_endpoints=True,
        )
        if relation_features != randomized_features:
            raise AssertionError("ZE-similarity feature mismatch")
        configurations = [
            ("logit_node_only", nodes, list(BASE_FEATURE_COLUMNS), None, False),
            ("logit_ze_similarity", real, relation_features, None, False),
            ("mlp_node_only", nodes, list(BASE_FEATURE_COLUMNS), mlp_scorer, False),
            ("mlp_ze_similarity", real, relation_features, mlp_scorer, False),
            (
                "mlp_ze_similarity_endpoint_randomized",
                randomized,
                randomized_features,
                mlp_scorer,
                False,
            ),
            (
                "mlp_ze_similarity_target_shuffled",
                real,
                relation_features,
                mlp_scorer,
                True,
            ),
        ]
        for view_name, frame, features, scorer, shuffle_target in configurations:
            rows.extend(
                evaluate_transfer_view(
                    frame,
                    view_name=view_name,
                    feature_columns=features,
                    seed=seed,
                    eval_years=eval_years,
                    shuffle_target=shuffle_target,
                    claim_status=CLAIM_STATUS,
                    fit_score_fn=scorer,
                )
            )

    metrics = pd.DataFrame(rows).sort_values(
        ["view", "seed", "eval_year", "ze_fold"]
    ).reset_index(drop=True)
    numeric = ["ndcg_at_3", "precision_at_3", "hit_rate_at_3", "average_precision"]
    if metrics.empty or not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Missing or non-finite nonlinear-probe metrics")
    return metrics, _summary(metrics), evaluate_nonlinear_gate(metrics)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=EXPANDING_EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-epochs", type=int, default=200)
    args = parser.parse_args()

    joined = f"{args.nodes}\n{args.edges}"
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")

    metrics, summary, gate = run_nonlinear_probe(
        load_nodes(args.nodes),
        load_edges(args.edges),
        eval_years=args.eval_years,
        seeds=args.seeds,
        max_epochs=args.max_epochs,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_similarity_nonlinear_transfer_probe"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
