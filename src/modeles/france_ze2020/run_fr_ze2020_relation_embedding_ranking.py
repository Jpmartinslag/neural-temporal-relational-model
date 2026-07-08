"""
HERALD -- France ZE2020 relation-embedding ranking diagnostic.

Compares retrospective ZE2020 x sector ranking with and without the HERALD_29
dynamic relation encoder embeddings. This is an evaluation harness, not a final
model, not a causal analysis, and not an automatic recommendation system.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.modeles.france_ze2020.train_fr_ze2020_sector_ranking as ranking  # noqa: E402

RANKING_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv"
ENCODER_EMBEDDINGS_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_node_embeddings_v1.csv"
)
DEFAULT_SEEDS = [42, 43, 44, 45, 46]
DEFAULT_EVAL_YEARS_BY_HORIZON = {
    1: [2022, 2023, 2024],
    3: [2020, 2021, 2022],
}
FEATURE_CONFIGS = [
    "base_formula_features",
    "no_relation_features",
    "learned_sparse_embeddings",
    "dense_graph_embeddings",
    "all_embeddings",
    "shuffled_dense_graph_embeddings",
]
CLAIM_STATUS = "relation_embedding_ranking_diagnostic_not_recommendation"
FORBIDDEN_EMBEDDING_COLUMNS = {"relation_label", "sample_role", "edge_state"}


def load_encoder_embeddings(path: Path = ENCODER_EMBEDDINGS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    missing_forbidden = FORBIDDEN_EMBEDDING_COLUMNS.intersection(df.columns)
    if missing_forbidden:
        raise ValueError(f"Forbidden label-like embedding columns present: {sorted(missing_forbidden)}")
    df["ze2020"] = df["ze2020"].astype(str).str.zfill(4)
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def embedding_column_groups(embeddings: pd.DataFrame) -> tuple[list[str], list[str]]:
    learned_cols = [
        col
        for col in embeddings.columns
        if col.startswith("relation_")
        and not col.startswith("relation_graph_")
        and col not in {"relation_embedding_available", "claim_status"}
        and pd.api.types.is_numeric_dtype(embeddings[col])
    ]
    if "relation_embedding_available" in embeddings.columns:
        learned_cols.append("relation_embedding_available")
    dense_graph_cols = [
        col
        for col in embeddings.columns
        if col.startswith("relation_graph_") and pd.api.types.is_numeric_dtype(embeddings[col])
    ]
    return learned_cols, dense_graph_cols


def merge_panel_embeddings(panel: pd.DataFrame, embeddings: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    learned_cols, dense_graph_cols = embedding_column_groups(embeddings)
    keep_cols = ["ze2020", "sector_code", "decision_year", *learned_cols, *dense_graph_cols]
    merged = panel.merge(
        embeddings[keep_cols],
        on=["ze2020", "sector_code", "decision_year"],
        how="left",
    )
    embedding_cols = [*learned_cols, *dense_graph_cols]
    merged[embedding_cols] = merged[embedding_cols].fillna(0.0)
    return merged, learned_cols, dense_graph_cols


def shuffle_columns_by_year(df: pd.DataFrame, columns: list[str], seed: int) -> pd.DataFrame:
    out = df.copy()
    rng = np.random.default_rng(seed)
    for col in columns:
        out[col] = out.groupby("decision_year")[col].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


@contextmanager
def temporary_model_features(feature_columns: list[str]):
    old = ranking.MODEL_FEATURE_COLUMNS
    ranking.MODEL_FEATURE_COLUMNS = feature_columns
    try:
        yield
    finally:
        ranking.MODEL_FEATURE_COLUMNS = old


def run_one_config(
    panel: pd.DataFrame,
    feature_columns: list[str],
    config_name: str,
    target_horizon: int,
    eval_years: list[int],
    seed: int,
    max_epochs: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    with temporary_model_features(feature_columns):
        predictions, metrics = ranking.run_sector_ranking(
            panel,
            eval_years=eval_years,
            k=ranking.DEFAULT_K,
            min_train_years=3,
            seed=seed,
            max_epochs=max_epochs,
            target_horizon=target_horizon,
        )
    predictions["feature_config"] = config_name
    predictions["seed"] = seed
    predictions["claim_status"] = CLAIM_STATUS
    metrics["feature_config"] = config_name
    metrics["seed"] = seed
    metrics["claim_status"] = CLAIM_STATUS
    return predictions, metrics


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby(["target_horizon_years", "feature_config", "model"], as_index=False)
        .agg(
            mean_ndcg_at_k=("ndcg_at_k", "mean"),
            std_ndcg_at_k=("ndcg_at_k", "std"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_hit_rate_at_k=("hit_rate_at_k", "mean"),
            n_rows=("ndcg_at_k", "size"),
            n_seeds=("seed", "nunique"),
        )
        .fillna({"std_ndcg_at_k": 0.0})
        .sort_values(["target_horizon_years", "feature_config", "mean_ndcg_at_k"], ascending=[True, True, False])
        .reset_index(drop=True)
    )


def coverage_summary(merged: pd.DataFrame) -> pd.DataFrame:
    learned_col = "relation_embedding_available"
    graph_col = "relation_graph_embedding_available"
    rows = []
    for year, frame in merged.groupby("decision_year"):
        rows.append(
            {
                "decision_year": int(year),
                "rows": int(len(frame)),
                "learned_sparse_available": int(frame[learned_col].sum()) if learned_col in frame else 0,
                "dense_graph_available": int(frame[graph_col].sum()) if graph_col in frame else 0,
                "claim_status": CLAIM_STATUS,
            }
        )
    return pd.DataFrame(rows)


def run_relation_embedding_ranking_diagnostic(
    panel: pd.DataFrame,
    embeddings: pd.DataFrame,
    target_horizons: list[int],
    seeds: list[int],
    max_epochs: int,
    feature_configs: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    merged, learned_cols, dense_graph_cols = merge_panel_embeddings(panel, embeddings)
    selected_configs = feature_configs or FEATURE_CONFIGS
    unknown = set(selected_configs).difference(FEATURE_CONFIGS)
    if unknown:
        raise ValueError(f"Unknown feature_configs: {sorted(unknown)}")
    base_features = list(ranking.MODEL_FEATURE_COLUMNS)
    no_relation_features = [col for col in base_features if not col.startswith("relation_")]
    configs = {
        "base_formula_features": (merged, base_features),
        "no_relation_features": (merged, no_relation_features),
        "learned_sparse_embeddings": (merged, base_features + learned_cols),
        "dense_graph_embeddings": (merged, base_features + dense_graph_cols),
        "all_embeddings": (merged, base_features + learned_cols + dense_graph_cols),
    }

    prediction_frames = []
    metric_frames = []
    for target_horizon in target_horizons:
        eval_years = DEFAULT_EVAL_YEARS_BY_HORIZON[target_horizon]
        for seed in seeds:
            shuffled = shuffle_columns_by_year(merged, dense_graph_cols, seed=seed + 1000)
            run_configs = {
                **configs,
                "shuffled_dense_graph_embeddings": (shuffled, base_features + dense_graph_cols),
            }
            for config_name in selected_configs:
                frame, feature_columns = run_configs[config_name]
                predictions, metrics = run_one_config(
                    frame,
                    feature_columns,
                    config_name=config_name,
                    target_horizon=target_horizon,
                    eval_years=eval_years,
                    seed=seed,
                    max_epochs=max_epochs,
                )
                prediction_frames.append(predictions)
                metric_frames.append(metrics)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics = pd.concat(metric_frames, ignore_index=True)
    summary = summarize_metrics(metrics)
    coverage = coverage_summary(merged)
    return predictions, metrics, summary, coverage


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 relation-embedding ranking diagnostic. "
            "Exploratory only; no causal or automatic recommendation claim."
        )
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--embeddings", type=Path, default=ENCODER_EMBEDDINGS_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-horizons", nargs="+", type=int, choices=[1, 3], default=[1, 3])
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--feature-configs", nargs="+", choices=FEATURE_CONFIGS, default=FEATURE_CONFIGS)
    parser.add_argument("--max-epochs", type=int, default=120)
    args = parser.parse_args()

    panel = ranking.load_ranking_panel(args.panel)
    embeddings = load_encoder_embeddings(args.embeddings)
    predictions, metrics, summary, coverage = run_relation_embedding_ranking_diagnostic(
        panel=panel,
        embeddings=embeddings,
        target_horizons=args.target_horizons,
        seeds=args.seeds,
        max_epochs=args.max_epochs,
        feature_configs=args.feature_configs,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "fr_ze2020_relation_embedding_ranking_predictions_v1.csv"
    metrics_path = args.output_dir / "fr_ze2020_relation_embedding_ranking_metrics_v1.csv"
    summary_path = args.output_dir / "fr_ze2020_relation_embedding_ranking_summary_v1.csv"
    coverage_path = args.output_dir / "fr_ze2020_relation_embedding_ranking_coverage_v1.csv"
    run_path = args.output_dir / "fr_ze2020_relation_embedding_ranking_run_v1.json"

    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    run_path.write_text(
        json.dumps(
            {
                "status": "RELATION_EMBEDDING_RANKING_DIAGNOSTIC_COMPLETE",
                "panel": str(args.panel),
                "embeddings": str(args.embeddings),
                "target_horizons": args.target_horizons,
                "seeds": args.seeds,
                "feature_configs": args.feature_configs,
                "max_epochs": args.max_epochs,
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print("RELATION EMBEDDING RANKING DIAGNOSTIC -- not causal, not automatic recommendation.")
    print(summary.to_string(index=False))
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
