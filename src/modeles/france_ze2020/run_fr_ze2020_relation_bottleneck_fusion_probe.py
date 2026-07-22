"""Pre-prediction ZE-similarity bottleneck fusion gate from DEC-072."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
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
from src.modeles.france_ze2020.run_fr_ze2020_similarity_nonlinear_transfer_probe import (  # noqa: E402
    make_mlp_scorer,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    load_edges,
    load_nodes,
)

CLAIM_STATUS = "relation_bottleneck_fusion_probe_exploratory_not_recommendation"
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def build_bottleneck_model(
    node_columns: list[str],
    relation_columns: list[str],
    *,
    seed: int,
    max_epochs: int,
) -> Pipeline:
    """Build the fixed training-only node/relation preprocessing and MLP head."""
    relation_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("pca", PCA(n_components=0.90, svd_solver="full")),
        ]
    )
    preprocess = ColumnTransformer(
        [
            ("node", StandardScaler(), node_columns),
            ("relation", relation_pipeline, relation_columns),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
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


def make_bottleneck_scorer(
    node_columns: list[str], relation_columns: list[str], max_epochs: int
):
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
        model = build_bottleneck_model(
            node_columns,
            relation_columns,
            seed=seed,
            max_epochs=max_epochs,
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


def evaluate_bottleneck_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    real = metrics[metrics["view"] == "mlp_bottleneck_ze_similarity"][
        keys + ["ndcg_at_3"]
    ].rename(columns={"ndcg_at_3": "real"})
    comparisons = {}
    for control_name in [
        "mlp_node_only",
        "mlp_raw_ze_similarity",
        "mlp_bottleneck_endpoint_randomized",
        "mlp_bottleneck_target_shuffled",
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
    endpoint = comparisons["mlp_bottleneck_endpoint_randomized"]
    pass_gate = (
        comparisons["mlp_node_only"]["mean_ndcg_lift"] > 0
        and comparisons["mlp_raw_ze_similarity"]["mean_ndcg_lift"] > 0
        and endpoint["mean_ndcg_lift"] > 0
        and endpoint["paired_win_rate"] >= 0.60
        and comparisons["mlp_bottleneck_target_shuffled"]["mean_ndcg_lift"] > 0
    )
    return {
        "gate_pass": bool(pass_gate),
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def run_bottleneck_probe(
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
    node_columns = list(BASE_FEATURE_COLUMNS)
    raw_mlp_scorer = make_mlp_scorer(max_epochs)
    rows: list[dict[str, object]] = []

    for seed in seeds:
        real, features = build_balanced_family_frame(
            nodes, edges, ["ze_similarity"], seed=seed
        )
        randomized, randomized_features = build_balanced_family_frame(
            nodes,
            edges,
            ["ze_similarity"],
            seed=seed + 5000,
            randomize_endpoints=True,
        )
        if features != randomized_features:
            raise AssertionError("ZE-similarity feature mismatch")
        relation_columns = [column for column in features if column not in node_columns]
        bottleneck_scorer = make_bottleneck_scorer(
            node_columns, relation_columns, max_epochs
        )
        configurations = [
            ("mlp_node_only", nodes, node_columns, raw_mlp_scorer, False),
            ("mlp_raw_ze_similarity", real, features, raw_mlp_scorer, False),
            (
                "mlp_bottleneck_ze_similarity",
                real,
                features,
                bottleneck_scorer,
                False,
            ),
            (
                "mlp_bottleneck_endpoint_randomized",
                randomized,
                randomized_features,
                bottleneck_scorer,
                False,
            ),
            (
                "mlp_bottleneck_target_shuffled",
                real,
                features,
                bottleneck_scorer,
                True,
            ),
        ]
        for view_name, frame, feature_columns, scorer, shuffle_target in configurations:
            rows.extend(
                evaluate_transfer_view(
                    frame,
                    view_name=view_name,
                    feature_columns=feature_columns,
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
        raise ValueError("Missing or non-finite bottleneck metrics")
    return metrics, _summary(metrics), evaluate_bottleneck_gate(metrics)


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

    metrics, summary, gate = run_bottleneck_probe(
        load_nodes(args.nodes),
        load_edges(args.edges),
        eval_years=args.eval_years,
        seeds=args.seeds,
        max_epochs=args.max_epochs,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_relation_bottleneck_fusion_probe"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
