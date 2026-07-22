"""Probe whether past graph changes transfer to held-out ZE2020 units.

This is a linear representation diagnostic pre-registered in DEC-069/HERALD_40.
It reuses audited graph inputs and emits exploratory metrics only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    EXPANDING_EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.audit_fr_ze2020_top3_entry_target import (  # noqa: E402
    add_top3_entry_labels,
)
from src.modeles.france_ze2020.run_fr_ze2020_relation_embedding_linear_probes import (  # noqa: E402
    BASE_FEATURE_COLUMNS,
    _graph_columns,
    build_probe_views,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_encoder import (  # noqa: E402
    build_dense_graph_signal_embeddings,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    load_edges,
    load_nodes,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (  # noqa: E402
    ranking_metrics,
)

CLAIM_STATUS = "relational_transition_transfer_probe_exploratory_not_recommendation"
TARGET_HORIZON = 3
TARGET_COLUMN = "future_top3_entry_3y_label"
DEFAULT_EVAL_YEARS = [2020, 2021, 2022]
DEFAULT_SEEDS = [42, 43, 44, 45, 46]
N_FOLDS = 5
VIEW_NAMES = [
    "node_only",
    "node_plus_degree_change",
    "real_relation_change",
    "random_endpoint_relation_change",
    "past_snapshot_relation_change",
    "sector_shuffled_relation_change",
    "target_shuffled_relation_change",
]
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def assign_ze_folds(frame: pd.DataFrame, n_folds: int = N_FOLDS) -> pd.Series:
    """Assign stable, exhaustive ZE-disjoint folds."""
    zones = sorted(frame["ze2020"].astype(str).str.zfill(4).unique())
    mapping = {zone: position % n_folds for position, zone in enumerate(zones)}
    return frame["ze2020"].astype(str).str.zfill(4).map(mapping).astype(int)


def add_graph_changes(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Append within-node first differences for existing graph aggregates."""
    out = frame.sort_values(["node_id", "decision_year"]).copy()
    graph_columns = _graph_columns(out)
    delta_columns = []
    for column in graph_columns:
        delta = f"delta__{column}"
        out[delta] = out.groupby("node_id", sort=False)[column].diff()
        delta_columns.append(delta)
    degree_columns = [column for column in graph_columns if column.endswith("_count")]
    degree_features = [*degree_columns, *(f"delta__{column}" for column in degree_columns)]
    relation_change_features = [
        delta for delta in delta_columns if not delta.removeprefix("delta__").endswith("_count")
    ]
    return out, degree_features, relation_change_features


def eligible_transition_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep observed non-top-3 sectors eligible to enter the future top 3."""
    out = add_top3_entry_labels(frame, horizons=[TARGET_HORIZON])
    finite_target = np.isfinite(out["future_growth_3y"].to_numpy(dtype=float))
    return out[
        (out["feature_complete"] == 1)
        & (out["mask_future_growth_3y_available"] == 1)
        & (out["sector_rank_in_ze_year_t"] > 3)
        & finite_target
    ].copy()


def shuffle_sector_alignment(
    frame: pd.DataFrame,
    relation_change_columns: list[str],
    seed: int,
) -> pd.DataFrame:
    """Break sector alignment inside ZE-year while preserving local distributions."""
    out = frame.copy()
    rng = np.random.default_rng(seed)
    for _, indices in out.groupby(["ze2020", "decision_year"], sort=False).groups.items():
        index = list(indices)
        if len(index) > 1:
            out.loc[index, relation_change_columns] = rng.permutation(
                out.loc[index, relation_change_columns].to_numpy()
            )
    return out


def _feature_sets(
    degree_features: list[str],
    relation_change_features: list[str],
) -> dict[str, list[str]]:
    base = list(BASE_FEATURE_COLUMNS)
    degree = [*base, *degree_features]
    relation = [*degree, *relation_change_features]
    return {
        "node_only": base,
        "node_plus_degree_change": degree,
        "real_relation_change": relation,
        "random_endpoint_relation_change": relation,
        "past_snapshot_relation_change": relation,
        "sector_shuffled_relation_change": relation,
        "target_shuffled_relation_change": relation,
    }


def _view_frames(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    seed: int,
    real_embeddings: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, list[str]]]:
    probe_views = build_probe_views(nodes, edges, seed=seed, real_embeddings=real_embeddings)
    real, degree_features, relation_features = add_graph_changes(probe_views["real_graph"])
    endpoint, _, _ = add_graph_changes(probe_views["random_endpoint_graph"])
    past, _, _ = add_graph_changes(probe_views["past_snapshot_graph"])
    sector_shuffle = shuffle_sector_alignment(real, relation_features, seed=seed + 3000)
    frames = {
        "node_only": real,
        "node_plus_degree_change": real,
        "real_relation_change": real,
        "random_endpoint_relation_change": endpoint,
        "past_snapshot_relation_change": past,
        "sector_shuffled_relation_change": sector_shuffle,
        "target_shuffled_relation_change": real,
    }
    return frames, _feature_sets(degree_features, relation_features)


def _shuffle_training_target(train: pd.DataFrame, seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    shuffled = train[TARGET_COLUMN].copy()
    for _, indices in train.groupby("decision_year", sort=False).groups.items():
        index = list(indices)
        shuffled.loc[index] = rng.permutation(train.loc[index, TARGET_COLUMN].to_numpy())
    return shuffled


def _fit_score(
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
                "logit",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=500,
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(train[feature_columns], labels)
    return model.predict_proba(test[feature_columns])[:, 1]


def evaluate_transfer_view(
    frame: pd.DataFrame,
    *,
    view_name: str,
    feature_columns: list[str],
    seed: int,
    eval_years: list[int],
    shuffle_target: bool = False,
    claim_status: str = CLAIM_STATUS,
    fit_score_fn=None,
) -> list[dict[str, object]]:
    """Evaluate one representation under the shared ZE-disjoint protocol."""
    candidates = eligible_transition_candidates(frame)
    finite = np.isfinite(candidates[feature_columns].to_numpy(dtype=float)).all(axis=1)
    candidates = candidates[finite].copy()
    rows: list[dict[str, object]] = []
    for eval_year in eval_years:
        for fold in range(N_FOLDS):
            train = candidates[
                (candidates["ze_fold"] != fold)
                & (candidates["decision_year"] + TARGET_HORIZON <= eval_year)
            ].copy()
            test = candidates[
                (candidates["ze_fold"] == fold)
                & (candidates["decision_year"] == eval_year)
            ].copy()
            overlap = set(train["ze2020"]) & set(test["ze2020"])
            if overlap:
                raise AssertionError(f"ZE leakage in fold {fold}: {sorted(overlap)[:3]}")
            if train[TARGET_COLUMN].nunique() < 2 or test.empty:
                continue
            scorer = fit_score_fn or _fit_score
            score = scorer(
                train,
                test,
                feature_columns,
                seed=seed + eval_year * 10 + fold,
                shuffle_target=shuffle_target,
            )
            scored = test.assign(score=score)
            ranking = ranking_metrics(
                scored,
                model_name=view_name,
                k=3,
                target_col="future_growth_3y",
                label_col=TARGET_COLUMN,
            )
            rows.append(
                {
                    "view": view_name,
                    "seed": int(seed),
                    "eval_year": int(eval_year),
                    "ze_fold": int(fold),
                    "ndcg_at_3": float(ranking["ndcg_at_k"]),
                    "precision_at_3": float(ranking["precision_at_k"]),
                    "hit_rate_at_3": float(ranking["hit_rate_at_k"]),
                    "average_precision": float(
                        average_precision_score(test[TARGET_COLUMN], score)
                    ),
                    "n_train": int(len(train)),
                    "n_test": int(len(test)),
                    "n_test_positive": int(test[TARGET_COLUMN].sum()),
                    "n_train_ze": int(train["ze2020"].nunique()),
                    "n_test_ze": int(test["ze2020"].nunique()),
                    "ze_overlap_count": 0,
                    "claim_status": claim_status,
                }
            )
    return rows


def run_transfer_probe(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    nodes = nodes.copy()
    nodes["ze2020"] = nodes["ze2020"].astype(str).str.zfill(4)
    nodes["ze_fold"] = assign_ze_folds(nodes)
    real_embeddings = build_dense_graph_signal_embeddings(nodes, edges)
    rows: list[dict[str, object]] = []

    for seed in seeds:
        frames, feature_sets = _view_frames(nodes, edges, seed, real_embeddings)
        for view_name in VIEW_NAMES:
            features = feature_sets[view_name]
            rows.extend(
                evaluate_transfer_view(
                    frames[view_name],
                    view_name=view_name,
                    feature_columns=features,
                    seed=seed,
                    eval_years=eval_years,
                    shuffle_target=view_name == "target_shuffled_relation_change",
                )
            )

    metrics = pd.DataFrame(rows).sort_values(
        ["view", "seed", "eval_year", "ze_fold"]
    ).reset_index(drop=True)
    if metrics.empty:
        raise ValueError("No transfer-probe metrics were produced")
    numeric = ["ndcg_at_3", "precision_at_3", "hit_rate_at_3", "average_precision"]
    if not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite transfer-probe metric")
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
    gate = evaluate_gate(metrics)
    return metrics, summary, gate


def evaluate_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    real = metrics[metrics["view"] == "real_relation_change"][keys + ["ndcg_at_3"]]
    real = real.rename(columns={"ndcg_at_3": "real_ndcg"})
    comparisons: dict[str, dict[str, float]] = {}
    for view in VIEW_NAMES:
        if view == "real_relation_change":
            continue
        other = metrics[metrics["view"] == view][keys + ["ndcg_at_3"]]
        other = other.rename(columns={"ndcg_at_3": "control_ndcg"})
        paired = real.merge(other, on=keys, how="inner", validate="one_to_one")
        delta = paired["real_ndcg"] - paired["control_ndcg"]
        comparisons[view] = {
            "mean_ndcg_lift": float(delta.mean()),
            "paired_win_rate": float((delta > 0).mean()),
            "n_pairs": int(len(paired)),
        }
    node_controls = ["node_only", "node_plus_degree_change"]
    graph_placebos = [
        "random_endpoint_relation_change",
        "past_snapshot_relation_change",
        "sector_shuffled_relation_change",
        "target_shuffled_relation_change",
    ]
    pass_gate = (
        all(comparisons[name]["mean_ndcg_lift"] > 0 for name in node_controls)
        and all(
            comparisons[name]["mean_ndcg_lift"] > 0
            and comparisons[name]["paired_win_rate"] >= 0.60
            for name in graph_placebos
        )
    )
    return {
        "gate_pass": bool(pass_gate),
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=EXPANDING_EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()

    joined = f"{args.nodes}\n{args.edges}"
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")

    metrics, summary, gate = run_transfer_probe(
        load_nodes(args.nodes),
        load_edges(args.edges),
        eval_years=args.eval_years,
        seeds=args.seeds,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_relational_transition_transfer_probe"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
