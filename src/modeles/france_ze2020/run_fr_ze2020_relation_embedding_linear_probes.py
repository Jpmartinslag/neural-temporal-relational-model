"""Linear probes for audited ZE2020 dynamic relation representations.

The probes test whether existing graph aggregates encode temporal succession and
next-year node state beyond node-only and falsified-graph controls. They do not
train a new graph encoder and do not produce recommendations or causal claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, mean_absolute_error, r2_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (  # noqa: E402
    EXPANDING_EDGES_OUT_PATH,
    NODES_OUT_PATH,
)
from src.modeles.france_ze2020.run_fr_ze2020_dynamic_graph_falsifications import (  # noqa: E402
    apply_dynamic_graph_falsification,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_encoder import (  # noqa: E402
    build_dense_graph_signal_embeddings,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_learner import (  # noqa: E402
    load_edges,
    load_nodes,
)

CLAIM_STATUS = "relation_embedding_linear_probe_exploratory_not_recommendation"
DEFAULT_EVAL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
DEFAULT_SEEDS = [42, 43, 44, 45, 46]
VIEW_NAMES = ["node_only", "real_graph", "random_target_graph", "past_snapshot_graph"]
BASE_FEATURE_COLUMNS = [
    "sector_count_t",
    "sector_share_t",
    "sector_rank_in_ze_year_t",
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
    "dominant_sector_flag_t",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "national_sector_share_lag_1",
    "national_sector_growth_lag_1",
]
FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)


def _graph_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(
        col
        for col in frame.columns
        if col.startswith("relation_graph_") and col != "relation_graph_embedding_available"
    )


def _merge_graph_embeddings(nodes: pd.DataFrame, embeddings: pd.DataFrame) -> pd.DataFrame:
    graph_cols = _graph_columns(embeddings)
    merged = nodes.merge(
        embeddings[["node_id", "decision_year", *graph_cols]],
        on=["node_id", "decision_year"],
        how="left",
        validate="one_to_one",
    )
    merged[graph_cols] = merged[graph_cols].fillna(0.0)
    return merged


def past_only_snapshot_placebo(embeddings: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Replace each graph snapshot with one sampled strictly from its own past."""
    out = embeddings.copy()
    graph_cols = _graph_columns(out)
    rng = np.random.default_rng(seed)
    for _, idx in out.groupby("node_id", sort=False).groups.items():
        ordered = list(out.loc[idx].sort_values("decision_year").index)
        original = out.loc[ordered, graph_cols].to_numpy(copy=True)
        replacement = np.zeros_like(original)
        for position in range(1, len(ordered)):
            replacement[position] = original[int(rng.integers(0, position))]
        out.loc[ordered, graph_cols] = replacement
    return out


def build_probe_views(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    seed: int,
    real_embeddings: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    if real_embeddings is None:
        real_embeddings = build_dense_graph_signal_embeddings(nodes, edges)
    _, random_edges = apply_dynamic_graph_falsification(
        nodes,
        edges,
        scenario="random_edge_targets",
        seed=seed,
    )
    random_embeddings = build_dense_graph_signal_embeddings(nodes, random_edges)
    past_embeddings = past_only_snapshot_placebo(real_embeddings, seed=seed + 1000)
    return {
        "node_only": nodes.copy(),
        "real_graph": _merge_graph_embeddings(nodes, real_embeddings),
        "random_target_graph": _merge_graph_embeddings(nodes, random_embeddings),
        "past_snapshot_graph": _merge_graph_embeddings(nodes, past_embeddings),
    }


def _feature_columns(view_name: str, frame: pd.DataFrame) -> list[str]:
    columns = list(BASE_FEATURE_COLUMNS)
    if view_name != "node_only":
        columns.extend(_graph_columns(frame))
    return columns


def _consecutive_rows(frame: pd.DataFrame) -> pd.DataFrame:
    current = frame.copy()
    future = frame.copy()
    future["decision_year"] = future["decision_year"] - 1
    future = future.rename(columns={col: f"next__{col}" for col in frame.columns if col not in {"node_id", "decision_year"}})
    paired = current.merge(future, on=["node_id", "decision_year"], how="inner", validate="one_to_one")
    paired["target_year"] = paired["decision_year"] + 1
    return paired


def build_successor_pairs(frame: pd.DataFrame, feature_columns: list[str], seed: int) -> pd.DataFrame:
    paired = _consecutive_rows(frame[["node_id", "sector_code", "decision_year", *feature_columns]])
    paired = paired.rename(columns={f"next__{col}": f"candidate__{col}" for col in feature_columns})
    positive = paired.copy()
    positive["label"] = 1

    negative_parts = []
    rng = np.random.default_rng(seed)
    candidate_cols = [f"candidate__{col}" for col in feature_columns]
    for _, group in paired.groupby(["target_year", "sector_code"], sort=False):
        if len(group) < 2:
            continue
        shifted = group.copy()
        offset = int(rng.integers(1, len(group)))
        shifted[candidate_cols] = np.roll(group[candidate_cols].to_numpy(), offset, axis=0)
        shifted["label"] = 0
        negative_parts.append(shifted)
    negative = pd.concat(negative_parts, ignore_index=True)
    pairs = pd.concat([positive, negative], ignore_index=True)
    for col in feature_columns:
        pairs[f"delta__{col}"] = pairs[f"candidate__{col}"] - pairs[col]
        pairs[f"abs_delta__{col}"] = pairs[f"delta__{col}"].abs()
    return pairs


def _finite(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    values = frame[columns].to_numpy(dtype=float)
    return frame[np.isfinite(values).all(axis=1)].copy()


def run_successor_probe(
    frame: pd.DataFrame,
    feature_columns: list[str],
    eval_years: list[int],
    seed: int,
) -> list[dict]:
    pairs = build_successor_pairs(frame, feature_columns, seed=seed + 2000)
    probe_columns = [name for col in feature_columns for name in (f"delta__{col}", f"abs_delta__{col}")]
    pairs = _finite(pairs, probe_columns)
    rows = []
    for eval_year in eval_years:
        train = pairs[pairs["target_year"] < eval_year]
        test = pairs[pairs["target_year"] == eval_year]
        if train["target_year"].nunique() < 3 or test["label"].nunique() < 2:
            continue
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("logit", LogisticRegression(max_iter=500, random_state=seed)),
            ]
        )
        model.fit(train[probe_columns], train["label"])
        score = model.predict_proba(test[probe_columns])[:, 1]
        rows.append(
            {
                "probe": "temporal_successor",
                "eval_year": int(eval_year),
                "seed": int(seed),
                "roc_auc": float(roc_auc_score(test["label"], score)),
                "average_precision": float(average_precision_score(test["label"], score)),
                "mae": np.nan,
                "r2": np.nan,
                "n_train": int(len(train)),
                "n_test": int(len(test)),
            }
        )
    return rows


def run_next_state_probe(
    frame: pd.DataFrame,
    feature_columns: list[str],
    eval_years: list[int],
    seed: int,
) -> list[dict]:
    paired = _consecutive_rows(frame[["node_id", "decision_year", "sector_share_t", *[c for c in feature_columns if c != "sector_share_t"]]])
    target = "next__sector_share_t"
    paired = _finite(paired, [*feature_columns, target])
    rows = []
    for eval_year in eval_years:
        train = paired[paired["target_year"] < eval_year]
        test = paired[paired["target_year"] == eval_year]
        if train["target_year"].nunique() < 3 or test.empty:
            continue
        model = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
        model.fit(train[feature_columns], train[target])
        prediction = model.predict(test[feature_columns])
        rows.append(
            {
                "probe": "next_sector_share",
                "eval_year": int(eval_year),
                "seed": int(seed),
                "roc_auc": np.nan,
                "average_precision": np.nan,
                "mae": float(mean_absolute_error(test[target], prediction)),
                "r2": float(r2_score(test[target], prediction)),
                "n_train": int(len(train)),
                "n_test": int(len(test)),
            }
        )
    return rows


def run_linear_probes(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    rows = []
    real_embeddings = build_dense_graph_signal_embeddings(nodes, edges)
    for seed in seeds:
        views = build_probe_views(nodes, edges, seed=seed, real_embeddings=real_embeddings)
        for view_name, frame in views.items():
            feature_columns = _feature_columns(view_name, frame)
            for row in run_successor_probe(frame, feature_columns, eval_years, seed):
                rows.append({**row, "view": view_name, "claim_status": CLAIM_STATUS})
            for row in run_next_state_probe(frame, feature_columns, eval_years, seed):
                rows.append({**row, "view": view_name, "claim_status": CLAIM_STATUS})
    metrics = pd.DataFrame(rows).sort_values(["probe", "view", "seed", "eval_year"]).reset_index(drop=True)
    if metrics.empty:
        raise ValueError("No linear-probe metrics were produced")
    summary = (
        metrics.groupby(["probe", "view"], as_index=False)
        .agg(
            mean_roc_auc=("roc_auc", "mean"),
            mean_average_precision=("average_precision", "mean"),
            mean_mae=("mae", "mean"),
            mean_r2=("r2", "mean"),
            n_seed_years=("eval_year", "size"),
            n_seeds=("seed", "nunique"),
        )
    )
    summary["claim_status"] = CLAIM_STATUS
    return metrics, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Linear probes for existing ZE2020 relation embeddings.")
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=EXPANDING_EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()

    joined_paths = f"{args.nodes}\n{args.edges}"
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined_paths:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    metrics, summary = run_linear_probes(nodes, edges, args.eval_years, args.seeds)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_relation_embedding_linear_probe"
    metrics_path = args.output_dir / f"{stem}_metrics_v1.csv"
    summary_path = args.output_dir / f"{stem}_summary_v1.csv"
    run_path = args.output_dir / f"{stem}_run_v1.json"
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "nodes": str(args.nodes),
                "edges": str(args.edges),
                "eval_years": args.eval_years,
                "seeds": args.seeds,
                "views": VIEW_NAMES,
                "metrics": str(metrics_path),
                "summary": str(summary_path),
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
