"""
HERALD -- France ZE2020 dynamic graph ranking prototype.

First HERALD_25 smoke encoder over the dynamic graph input bundle. This is a
small, auditable prototype: typed message passing is computed explicitly with
pandas/numpy, then Ridge and MLP ranking heads are evaluated retrospectively.

No causal claim. No automatic recommendation. No policy prescription.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EDGES_OUT_PATH,
    LABEL_COLUMNS,
    NODES_OUT_PATH,
    NODE_FEATURE_COLUMNS,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (
    DEFAULT_K,
    mature_training_rows,
    ranking_metrics,
)

DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_EVAL_YEARS_BY_HORIZON = {
    1: [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    3: [2019, 2020, 2021, 2022],
}
DEFAULT_MAX_EPOCHS = 250
SEED = 42
CLAIM_STATUS = "dynamic_graph_ranker_smoke_not_recommendation"

BASE_FEATURE_COLUMNS = [
    c
    for c in NODE_FEATURE_COLUMNS
    if c not in {"relation_signal_strength_mean_to_t", "relation_signal_strength_max_to_t"}
]
EDGE_TYPES = ["cross_ze_same_sector", "intra_ze_sector", "ze_similarity"]


def load_nodes(path: Path = NODES_OUT_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def load_edges(path: Path = EDGES_OUT_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def target_columns(target_horizon: int) -> tuple[str, str]:
    if target_horizon not in {1, 3}:
        raise ValueError(f"Unsupported target_horizon={target_horizon}; expected 1 or 3")
    target_col = f"future_growth_{target_horizon}y"
    label_col = f"future_top3_growth_{target_horizon}y_label"
    return target_col, label_col


def _with_target_label(nodes: pd.DataFrame, target_horizon: int) -> pd.DataFrame:
    target_col, label_col = target_columns(target_horizon)
    if target_col not in nodes.columns:
        raise ValueError(f"Missing target column: {target_col}")
    out = nodes.copy()
    if label_col not in out.columns:
        rank_col = f"future_rank_growth_{target_horizon}y_in_ze_year"
        out[rank_col] = (
            out.groupby(["ze2020", "decision_year"])[target_col]
            .rank(ascending=False, method="min")
        )
        out[label_col] = (
            (out[rank_col] <= DEFAULT_K) & np.isfinite(out[target_col].to_numpy(dtype=float))
        ).astype(int)
    return out


def _message_column(edge_type: str, feature: str) -> str:
    return f"msg_{edge_type}_{feature}"


def build_typed_messages(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    feature_columns: list[str] = BASE_FEATURE_COLUMNS,
) -> pd.DataFrame:
    """Aggregate signed, typed incoming messages for each target node-year.

    For each edge type and feature:

        message[target] = sum(edge_weight * source_feature) / sum(abs(edge_weight))

    This keeps negative associations visible while avoiding an unstable denominator when
    positive and negative weights cancel.
    """
    base = nodes[["node_id", "decision_year"]].copy()
    for edge_type in EDGE_TYPES:
        typed = edges[edges["edge_type"] == edge_type].copy()
        if typed.empty:
            base[f"msg_{edge_type}_edge_count"] = 0
            for feature in feature_columns:
                base[_message_column(edge_type, feature)] = 0.0
            continue

        source_features = nodes[["node_id", "decision_year", *feature_columns]].rename(
            columns={"node_id": "source_node_id"}
        )
        joined = typed.merge(source_features, on=["source_node_id", "decision_year"], how="inner")
        joined["abs_weight"] = joined["edge_weight"].abs()
        grouped = joined.groupby(["target_node_id", "decision_year"], as_index=False)
        denom = grouped["abs_weight"].sum().rename(columns={"target_node_id": "node_id"})
        denom = denom.rename(columns={"abs_weight": f"msg_{edge_type}_abs_weight_sum"})
        counts = grouped.size().rename(columns={"target_node_id": "node_id", "size": f"msg_{edge_type}_edge_count"})

        msg = denom.merge(counts, on=["node_id", "decision_year"], how="outer")
        for feature in feature_columns:
            weighted_col = f"_weighted_{feature}"
            joined[weighted_col] = joined["edge_weight"] * joined[feature].astype(float)
            sums = (
                joined.groupby(["target_node_id", "decision_year"], as_index=False)[weighted_col]
                .sum()
                .rename(columns={"target_node_id": "node_id"})
            )
            msg = msg.merge(sums, on=["node_id", "decision_year"], how="left")
            out_col = _message_column(edge_type, feature)
            msg[out_col] = msg[weighted_col] / msg[f"msg_{edge_type}_abs_weight_sum"].replace(0, np.nan)
            msg = msg.drop(columns=[weighted_col])

        base = base.merge(msg, on=["node_id", "decision_year"], how="left")

    message_cols = [c for c in base.columns if c.startswith("msg_")]
    base[message_cols] = base[message_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return base


def build_dynamic_graph_feature_frame(
    nodes: pd.DataFrame | None = None,
    edges: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    if nodes is None:
        nodes = load_nodes()
    if edges is None:
        edges = load_edges()
    messages = build_typed_messages(nodes, edges)
    frame = nodes.merge(messages, on=["node_id", "decision_year"], how="left")
    message_columns = [c for c in messages.columns if c.startswith("msg_")]
    model_features = [*BASE_FEATURE_COLUMNS, *message_columns]
    frame[message_columns] = frame[message_columns].fillna(0.0)
    return frame, model_features


def _complete(frame: pd.DataFrame, model_features: list[str], target_horizon: int) -> pd.DataFrame:
    target_col, _ = target_columns(target_horizon)
    finite_features = np.isfinite(frame[model_features].to_numpy(dtype=float)).all(axis=1)
    finite_target = np.isfinite(frame[target_col].to_numpy(dtype=float))
    return frame[(frame["feature_complete"] == 1) & finite_features & finite_target].copy()


def _baseline_scores(test: pd.DataFrame, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {
        "random": rng.random(len(test)),
        "past_volume": test["sector_count_t"].to_numpy(dtype=float),
        "past_growth": test["sector_growth_lag_1"].to_numpy(dtype=float),
        "specialization": test["sector_share_t"].to_numpy(dtype=float),
        "national_growth": test["national_sector_growth_lag_1"].to_numpy(dtype=float),
    }


def _fit_predict_ridge(
    train: pd.DataFrame,
    test: pd.DataFrame,
    model_features: list[str],
    target_col: str,
) -> np.ndarray:
    model = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    model.fit(train[model_features], train[target_col])
    return model.predict(test[model_features])


def _fit_predict_mlp(
    train: pd.DataFrame,
    test: pd.DataFrame,
    model_features: list[str],
    target_col: str,
    seed: int,
    max_epochs: int,
) -> np.ndarray:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPRegressor(
                    hidden_layer_sizes=(48, 24),
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
    model.fit(train[model_features], train[target_col])
    return model.predict(test[model_features])


def run_dynamic_graph_ranker(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    eval_years: list[int],
    k: int = DEFAULT_K,
    min_train_years: int = 3,
    seed: int = SEED,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    target_horizon: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame, model_features = build_dynamic_graph_feature_frame(nodes, edges)
    frame = _with_target_label(frame, target_horizon=target_horizon)
    target_col, label_col = target_columns(target_horizon)
    complete = _complete(frame, model_features, target_horizon=target_horizon)
    pred_rows = []
    metric_rows = []

    for eval_year in eval_years:
        test = complete[complete["decision_year"] == eval_year].copy()
        train = mature_training_rows(
            complete,
            eval_year=eval_year,
            target_horizon=target_horizon,
        )
        if test.empty or train["decision_year"].nunique() < min_train_years:
            continue

        scores = _baseline_scores(test, seed=seed + eval_year)
        scores["ridge_dynamic_graph"] = _fit_predict_ridge(
            train, test, model_features=model_features, target_col=target_col
        )
        scores["mlp_dynamic_graph"] = _fit_predict_mlp(
            train,
            test,
            model_features=model_features,
            target_col=target_col,
            seed=seed,
            max_epochs=max_epochs,
        )

        for model_name, score_values in scores.items():
            pred = test[
                [
                    "node_id",
                    "ze2020",
                    "ze2020_label",
                    "sector_code",
                    "sector_label",
                    "decision_year",
                    target_col,
                    label_col,
                ]
            ].copy()
            pred = pred.rename(columns={target_col: "target_growth", label_col: "target_top3_label"})
            pred["target_horizon_years"] = target_horizon
            pred["model"] = model_name
            pred["score"] = score_values
            pred["rank_predicted"] = pred.groupby(["ze2020", "decision_year"])["score"].rank(
                ascending=False, method="first"
            )
            pred["claim_status"] = CLAIM_STATUS
            pred_rows.append(pred)

            metrics = ranking_metrics(
                pred,
                model_name,
                k,
                target_col="target_growth",
                label_col="target_top3_label",
            )
            metrics.update(
                {
                    "eval_year": int(eval_year),
                    "target_horizon_years": int(target_horizon),
                    "k": int(k),
                    "n_test_rows": int(len(test)),
                    "n_test_groups": int(test.groupby(["ze2020", "decision_year"]).ngroups),
                    "n_train_years": int(train["decision_year"].nunique()),
                    "n_model_features": int(len(model_features)),
                    "claim_status": CLAIM_STATUS,
                }
            )
            metric_rows.append(metrics)

    predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    metrics = pd.DataFrame(metric_rows)
    return predictions, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 dynamic graph ranker smoke. Exploratory only; no causal or "
            "automatic recommendation claim."
        )
    )
    parser.add_argument("--nodes", type=Path, default=NODES_OUT_PATH)
    parser.add_argument("--edges", type=Path, default=EDGES_OUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-horizon", type=int, choices=[1, 3], default=3)
    parser.add_argument("--eval-years", type=int, nargs="+", default=None)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--min-train-years", type=int, default=3)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS)
    args = parser.parse_args()

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    eval_years = args.eval_years or DEFAULT_EVAL_YEARS_BY_HORIZON[args.target_horizon]
    predictions, metrics = run_dynamic_graph_ranker(
        nodes,
        edges,
        eval_years=eval_years,
        k=args.k,
        min_train_years=args.min_train_years,
        seed=args.seed,
        max_epochs=args.max_epochs,
        target_horizon=args.target_horizon,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = args.output_dir / f"fr_ze2020_dynamic_graph_ranker_{args.target_horizon}y_predictions_v1.csv"
    metrics_path = args.output_dir / f"fr_ze2020_dynamic_graph_ranker_{args.target_horizon}y_metrics_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    print("DYNAMIC GRAPH RANKER -- smoke only, not causal, not automatic recommendation.")
    if not metrics.empty:
        print(metrics.pivot(index="eval_year", columns="model", values="ndcg_at_k"))
    print(f"Predictions: {pred_path}")
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
