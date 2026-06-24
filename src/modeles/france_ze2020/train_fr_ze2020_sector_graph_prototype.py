"""
SECTOR GRAPH SMOKE PROTOTYPE -- France ZE2020 MVP3-B.

See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md,
"MVP3 neural prototypes" section. Experimental/smoke only: no causal claim,
no performance claim, no automatic recommendation.

PyTorch and torch_geometric are NOT installed in this environment and the
task forbids adding a heavy dependency -- so "message passing" here is
implemented manually (numpy/pandas aggregation), then digested by a small
sklearn MLPRegressor: h_i = MLP([x_i, mean_neighbor_x_i_intra_ze,
mean_neighbor_x_i_cross_ze]). This is the "GraphSAGE simplificado manual"
fallback the task explicitly allows.

Nodes: ZE2020 x sector (node_id = f"{ze2020}_{sector_code}", e.g. "0051_GI").
Built directly from fr_ze2020_sector_relational_features.csv (already at
this exact grain) plus the contemporaneous sector_share from
fr_ze2020_sector_panel.csv (read-only, used only as this script's TARGET).

Edges (2 types implemented; a 3rd is folded into node features -- see below):
  1. Intra-ZE composition: every sector node is connected to its 8 sibling
     sector nodes within the SAME ze2020 x year. Message = mean of the
     siblings' OWN sector_share_lag_1 / sector_growth_lag_1 (already
     causal). No history needed -- these are already lag features.
  2. Cross-ZE, same sector, similar trajectory: for a given (sector_code,
     year), ZE-to-ZE Pearson correlation over each zone's sector_growth_lag_1
     history restricted to years < year (same expanding-window method
     already used for the Category A ZE-to-ZE similarity in
     build_fr_ze2020_relational_model_ready_panel.py, scoped here to one
     sector at a time instead of the zone's overall growth). Top-5
     positive-correlation zones become the node's cross-ZE neighbors;
     message = mean of their OWN sector_share_lag_1 / sector_growth_lag_1
     for the SAME sector.
  3. "Mesmo setor nacional" (documented simplification): rather than a
     third literal edge set connecting every node to every other node of
     the same sector_code nationally (which would duplicate edge type 2's
     top-k mechanism at far higher cost for a smoke prototype), this is
     folded into node features: national_sector_share_lag_1 and
     national_sector_growth_lag_1 are already part of every node's own
     feature vector (from fr_ze2020_sector_relational_features.csv), so
     every node already "sees" the national sector signal without a
     separate edge type.

Never graph_adjacency_core_v0.csv / graph_adjacency_mobility_v0.csv, never
dynamic_stgnn_feature_panel_v1.csv.

Target: sector_share (current year, NOT sector_establishment_creations --
the raw count target proved numerically unstable for a small MLP in MVP3-A,
see train_fr_ze2020_neural_relational_mlp.py's RatioToLevelMLP docstring;
sector_share is bounded in [0, 1] by construction and needs no rescaling
trick). Baseline: y_hat = sector_share_lag_1 (persistence, node-level).

Outputs:
  data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv
  data/processed/france_ze2020/fr_ze2020_sector_graph_metrics_v1.csv
  data/processed/france_ze2020/fr_ze2020_sector_graph_relation_signals_v1.csv
    (top edges per type per eval_year, exploratory only -- never a
    recommendation, never a causal claim)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
SECTOR_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
SECTOR_FEATURES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"

TARGET_COL = "sector_share"

OWN_FEATURE_COLS = [
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
    "national_sector_share_lag_1",
    "national_sector_growth_lag_1",
    "dominant_sector_flag",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
]
MESSAGE_PASS_BASE_COLS = ["sector_share_lag_1", "sector_growth_lag_1"]
GRAPH_FEATURE_COLS = OWN_FEATURE_COLS + [
    "intra_ze_share_mean",
    "intra_ze_growth_mean",
    "cross_ze_share_mean",
    "cross_ze_growth_mean",
    "cross_ze_neighbor_count",
]

TOP_K_NEIGHBORS = 5
MIN_HISTORY_YEARS = 3
MIN_TRAIN_YEARS = 4
TOP_N_RELATIONS_PER_YEAR = 20

SEED = 42
DEFAULT_MAX_EPOCHS = 300
HIDDEN_LAYER_SIZES = (16, 8)
DEFAULT_EVAL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
CLAIM_STATUS = "sector_graph_smoke"


def load_sector_panel(path: Path = SECTOR_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_features(path: Path = SECTOR_FEATURES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def build_node_table(
    sector_features: pd.DataFrame | None = None, sector_panel: pd.DataFrame | None = None
) -> pd.DataFrame:
    if sector_features is None:
        sector_features = load_sector_features()
    if sector_panel is None:
        sector_panel = load_sector_panel()

    nodes = sector_features.merge(
        sector_panel[["ze2020", "year", "sector_code", "sector_share"]],
        on=["ze2020", "year", "sector_code"],
        how="left",
    )
    nodes["dominant_sector_flag"] = (
        nodes["sector_code"] == nodes["dominant_sector_lag_1"]
    ).astype(int)
    nodes["node_id"] = nodes["ze2020"] + "_" + nodes["sector_code"]
    return nodes


def _completeness_mask(nodes: pd.DataFrame) -> pd.Series:
    """notna() alone is not enough: fr_ze2020_sector_relational_features.csv
    has exactly one zone-sector-year with sector_establishment_creations=0,
    which makes that row's OWN sector_growth_lag_1/lag_2 (division by that
    zero) equal to +-inf, not NaN -- np.isfinite catches this too. That
    upstream panel is already committed/tested (MVP2 Categoria C) and is
    not modified here; this is a defensive completeness check scoped to
    this script's own modeling step."""
    cols = OWN_FEATURE_COLS + [TARGET_COL]
    finite = np.isfinite(nodes[cols].to_numpy(dtype=float)).all(axis=1)
    return pd.Series(finite, index=nodes.index)


def add_intra_ze_messages(nodes: pd.DataFrame) -> pd.DataFrame:
    """Edge type 1: mean of the OTHER 8 sector nodes' own lag features,
    within the same (ze2020, year). Vectorized group sum-minus-self -- no
    history needed, since sector_share_lag_1/sector_growth_lag_1 of the
    siblings are themselves already causal (computed in
    build_fr_ze2020_sector_relational_features.py)."""
    df = nodes.copy()
    group = df.groupby(["ze2020", "year"])
    for col, out_col in zip(MESSAGE_PASS_BASE_COLS, ["intra_ze_share_mean", "intra_ze_growth_mean"]):
        group_sum = group[col].transform("sum")
        group_count = group[col].transform("count")
        df[out_col] = (group_sum - df[col]) / (group_count - 1)
    return df


def _cross_ze_similarity_matrix(
    sector_history: pd.DataFrame, min_history_years: int = MIN_HISTORY_YEARS
) -> pd.DataFrame | None:
    if sector_history.empty:
        return None
    pivot = sector_history.pivot(index="ze2020", columns="year", values="sector_growth_lag_1")
    return pivot.T.corr(min_periods=min_history_years)


def add_cross_ze_messages(
    nodes: pd.DataFrame, top_k: int = TOP_K_NEIGHBORS, target_years: list[int] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Edge type 2: for each (sector_code, year), ZE-to-ZE similarity using
    strictly prior years (years < year) of that sector's own
    sector_growth_lag_1 series -- never the evaluated year itself. Returns
    the node table with cross_ze_* columns added, plus a long edge table
    (source_node, target_node, year, weight) for the relation_signals
    export.

    Builds result rows into plain lists first and merges ONCE at the end
    (rather than writing into the full node table inside the loop) --
    repeated boolean-mask assignment into a 30k+ row frame inside a
    9-sectors x 13-years x 280-zones loop is O(n^2) and was measured to
    take >25s for a 5-year subset before this fix; the list-then-merge
    pattern (same one used in build_fr_ze2020_relational_model_ready_panel.py)
    is O(n log n).

    target_years restricts which YEARS get a similarity matrix computed
    (still using only their own strictly-prior history) -- years not in
    this list get NaN/0 cross-ze columns, same as years with insufficient
    history. Defaults to every year present in `nodes`; pass the actual
    eval_years list to skip wasted work on years that will never be
    evaluated (smoke-mode speed, not a correctness change: a year either
    in or out of this list still only ever uses its own < year history)."""
    message_rows = []
    edge_rows = []
    years_to_process = sorted(target_years) if target_years is not None else None

    for sector_code, sector_df in nodes.groupby("sector_code"):
        sector_df = sector_df.sort_values("year")
        candidate_years = years_to_process or sorted(sector_df["year"].unique())
        for year in candidate_years:
            history = sector_df[sector_df["year"] < year]
            corr = _cross_ze_similarity_matrix(history)
            current = sector_df[sector_df["year"] == year].set_index("ze2020")

            for zone in current.index:
                neighbors: list[str] = []
                weights: list[float] = []
                if corr is not None and zone in corr.index:
                    candidates = corr.loc[zone].drop(labels=[zone], errors="ignore").dropna()
                    candidates = candidates[candidates > 0].sort_values(ascending=False).head(top_k)
                    neighbors = candidates.index.tolist()
                    weights = candidates.to_numpy(dtype=float).tolist()

                neighbor_rows = current.reindex(neighbors).dropna(subset=MESSAGE_PASS_BASE_COLS)
                count = len(neighbor_rows)

                message_rows.append(
                    {
                        "ze2020": zone,
                        "year": year,
                        "sector_code": sector_code,
                        "cross_ze_share_mean": neighbor_rows["sector_share_lag_1"].mean() if count else np.nan,
                        "cross_ze_growth_mean": neighbor_rows["sector_growth_lag_1"].mean() if count else np.nan,
                        "cross_ze_neighbor_count": count,
                    }
                )

                for neighbor_zone, weight in zip(neighbors, weights):
                    if neighbor_zone in neighbor_rows.index:
                        edge_rows.append(
                            {
                                "source_node": f"{zone}_{sector_code}",
                                "target_node": f"{neighbor_zone}_{sector_code}",
                                "year": year,
                                "relation_type": "cross_ze_same_sector",
                                "learned_or_aggregated_weight": weight,
                                "signal_strength": weight,
                                "claim_status": CLAIM_STATUS,
                            }
                        )

    messages = pd.DataFrame(message_rows)
    df = nodes.merge(messages, on=["ze2020", "year", "sector_code"], how="left")
    edges = pd.DataFrame(edge_rows)
    return df, edges


def intra_ze_relation_signals(nodes: pd.DataFrame, eval_years: list[int]) -> pd.DataFrame:
    """Exploratory signal for edge type 1: for each (ze2020, year), the
    Pearson correlation between the dominant sector's and the runner-up
    sector's sector_growth_lag_1 history (years < year, same causal
    discipline) -- 'do this zone's two biggest sectors move together'.
    Bounded to TOP_N_RELATIONS_PER_YEAR strongest pairs per year."""
    rows = []
    for year in eval_years:
        history = nodes[nodes["year"] < year]
        if history.empty:
            continue
        current = nodes[nodes["year"] == year]
        ranked = current.sort_values(["ze2020", "sector_share"], ascending=[True, False])
        top2 = ranked.groupby("ze2020").head(2)

        for ze2020, pair in top2.groupby("ze2020"):
            if len(pair) < 2:
                continue
            sector_a, sector_b = pair["sector_code"].tolist()[:2]
            series_a = history[(history["ze2020"] == ze2020) & (history["sector_code"] == sector_a)].set_index(
                "year"
            )["sector_growth_lag_1"]
            series_b = history[(history["ze2020"] == ze2020) & (history["sector_code"] == sector_b)].set_index(
                "year"
            )["sector_growth_lag_1"]
            # pandas .corr() excludes NaN pairwise (sector_growth_lag_1 is
            # NaN for years 2012-2013 by construction); np.corrcoef does
            # NOT and silently returns NaN for the whole pair if any input
            # year is unavailable -- this was found empirically (every
            # candidate pair returned NaN) before switching to .corr().
            if series_a.notna().sum() < MIN_HISTORY_YEARS or series_b.notna().sum() < MIN_HISTORY_YEARS:
                continue
            corr = series_a.corr(series_b, min_periods=MIN_HISTORY_YEARS)
            if pd.isna(corr):
                continue
            rows.append(
                {
                    "source_node": f"{ze2020}_{sector_a}",
                    "target_node": f"{ze2020}_{sector_b}",
                    "year": year,
                    "relation_type": "intra_ze_composition",
                    "learned_or_aggregated_weight": 1.0 / 8.0,
                    "signal_strength": float(corr),
                    "claim_status": CLAIM_STATUS,
                }
            )

    signals = pd.DataFrame(rows)
    if signals.empty:
        return signals
    signals["_abs_signal"] = signals["signal_strength"].abs()
    return (
        signals.sort_values("_abs_signal", ascending=False)
        .groupby("year")
        .head(TOP_N_RELATIONS_PER_YEAR)
        .drop(columns="_abs_signal")
        .reset_index(drop=True)
    )


def compute_wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.abs(y_true).sum()
    if denom == 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denom)


def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.abs(y_true - y_pred).mean())


def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def predict_persistence(test: pd.DataFrame) -> np.ndarray:
    return test["sector_share_lag_1"].to_numpy(dtype=float)


def fit_predict_graph_mlp(
    train: pd.DataFrame, test: pd.DataFrame, max_epochs: int = DEFAULT_MAX_EPOCHS, seed: int = SEED
) -> np.ndarray:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPRegressor(
                    hidden_layer_sizes=HIDDEN_LAYER_SIZES,
                    activation="relu",
                    solver="adam",
                    max_iter=max_epochs,
                    random_state=seed,
                    early_stopping=True,
                    n_iter_no_change=10,
                ),
            ),
        ]
    )
    model.fit(train[GRAPH_FEATURE_COLS].to_numpy(dtype=float), train[TARGET_COL].to_numpy(dtype=float))
    return model.predict(test[GRAPH_FEATURE_COLS].to_numpy(dtype=float))


def build_graph_node_features(nodes: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if nodes is None:
        nodes = build_node_table()
    nodes = add_intra_ze_messages(nodes)
    nodes, cross_ze_edges = add_cross_ze_messages(nodes)
    return nodes, cross_ze_edges


def run_sector_graph_smoke(
    nodes: pd.DataFrame,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    min_train_years: int = MIN_TRAIN_YEARS,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    graph_cols_finite = pd.Series(
        np.isfinite(nodes[GRAPH_FEATURE_COLS].to_numpy(dtype=float)).all(axis=1), index=nodes.index
    )
    complete = nodes[_completeness_mask(nodes) & graph_cols_finite]

    pred_rows = []
    metric_rows = []

    for eval_year in eval_years:
        test = complete[complete["year"] == eval_year]
        if test.empty:
            continue
        train = complete[complete["year"] < eval_year]
        if train["year"].nunique() < min_train_years:
            continue

        y_true = test[TARGET_COL].to_numpy(dtype=float)
        predictions = {
            "persistence_sector": predict_persistence(test),
            "graph_mlp": fit_predict_graph_mlp(train, test, max_epochs=max_epochs, seed=seed),
        }

        for model_name, y_pred in predictions.items():
            for node_id, ze2020, sector_code, year, yt, yp in zip(
                test["node_id"], test["ze2020"], test["sector_code"], test["year"], y_true, y_pred
            ):
                pred_rows.append(
                    {
                        "node_id": node_id,
                        "ze2020": ze2020,
                        "sector_code": sector_code,
                        "year": int(year),
                        "model": model_name,
                        "y_true": float(yt),
                        "y_pred": float(yp),
                        "claim_status": CLAIM_STATUS,
                    }
                )
            metric_rows.append(
                {
                    "eval_year": eval_year,
                    "model": model_name,
                    "n_test": len(test),
                    "n_train_years": train["year"].nunique(),
                    "wmape": compute_wmape(y_true, y_pred),
                    "mae": compute_mae(y_true, y_pred),
                    "rmse": compute_rmse(y_true, y_pred),
                    "claim_status": CLAIM_STATUS,
                }
            )

    return pd.DataFrame(pred_rows), pd.DataFrame(metric_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 sector graph smoke prototype (MVP3-B) -- "
            "persistence_sector vs. graph_mlp (manual message passing + small MLP), "
            "not a headline claim, not causal, not a recommendation"
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--min-train-years", type=int, default=MIN_TRAIN_YEARS)
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    nodes = build_node_table()
    nodes, cross_ze_edges = build_graph_node_features(nodes)

    predictions, metrics = run_sector_graph_smoke(
        nodes,
        eval_years=args.eval_years,
        min_train_years=args.min_train_years,
        max_epochs=args.max_epochs,
        seed=args.seed,
    )
    intra_signals = intra_ze_relation_signals(nodes, args.eval_years)
    cross_signals = (
        cross_ze_edges[cross_ze_edges["year"].isin(args.eval_years)]
        .sort_values("signal_strength", ascending=False)
        .groupby("year")
        .head(TOP_N_RELATIONS_PER_YEAR)
        .reset_index(drop=True)
        if not cross_ze_edges.empty
        else cross_ze_edges
    )
    relation_signals = pd.concat([intra_signals, cross_signals], ignore_index=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = args.output_dir / "fr_ze2020_sector_graph_predictions_v1.csv"
    metrics_path = args.output_dir / "fr_ze2020_sector_graph_metrics_v1.csv"
    signals_path = args.output_dir / "fr_ze2020_sector_graph_relation_signals_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    relation_signals.to_csv(signals_path, index=False)

    print("SECTOR GRAPH SMOKE -- not a validated headline claim, not causal, not a recommendation.")
    print(metrics.pivot(index="eval_year", columns="model", values="wmape"))
    print(f"Mean WMAPE: {metrics.groupby('model')['wmape'].mean().to_dict()}")
    print(f"Predictions: {pred_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Relation signals (exploratory only): {signals_path}")


if __name__ == "__main__":
    main()
