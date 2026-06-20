#!/usr/bin/env python3
"""Phase 4P: causal Italy-only linear spatial-lag diagnostic.

This is a diagnostic, not a promotion to multi-country graph training.
Every forecast for year t uses rows and targets from years < t only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from hpc.phase4.run_phase4o_c_residual_spatial_diagnostic import (
    conjugation_permutation,
    load_geometry,
    moran_global,
    queen_adjacency_raw,
    row_normalise,
)

COUNTRY = "IT"
TARGET = "target_births"
BASE_FEATURES = (
    "lag1_births",
    "lag2_births",
    "lag3_births",
    "growth_1y",
    "growth_2y",
    "stock_lag1",
)
GRAPH_FEATURE = "neighbour_lag1"
EVAL_YEARS = tuple(range(2012, 2021))
VALIDATION_START_YEAR = 2011
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
RNG_SEED = 42
EPSILON = 1.0
MIN_PROMOTION_GAIN = 0.01
MAX_WORST_YEAR_REGRESSION = 0.10


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = float(np.abs(y_true).sum())
    if denominator <= 0:
        raise ValueError("Non-positive WMAPE denominator")
    return float(np.abs(y_true - y_pred).sum() / denominator)


def add_neighbour_lag1(
    panel: pd.DataFrame,
    W: np.ndarray,
    region_order: list[str],
) -> pd.DataFrame:
    """Add W @ births[t-1], aligned to a fixed region order."""
    if W.shape != (len(region_order), len(region_order)):
        raise ValueError("Adjacency shape does not match region order")
    work = panel.copy()
    work[GRAPH_FEATURE] = np.nan
    for year, year_frame in work.groupby("year"):
        indexed = year_frame.set_index("region_id")
        missing = set(region_order) - set(indexed.index)
        extra = set(indexed.index) - set(region_order)
        if missing or extra or indexed.index.duplicated().any():
            raise ValueError(
                f"year={year}: panel/graph alignment mismatch; "
                f"missing={sorted(missing)[:3]}, extra={sorted(extra)[:3]}"
            )
        lag1 = indexed.loc[region_order, "lag1_births"].to_numpy(dtype=float)
        values = W @ lag1 if np.isfinite(lag1).all() else np.full(len(lag1), np.nan)
        mapping = dict(zip(region_order, values))
        work.loc[year_frame.index, GRAPH_FEATURE] = year_frame["region_id"].map(mapping)
    return work


def residual_ridge_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    alpha: float,
    use_graph: bool,
) -> np.ndarray:
    features = list(BASE_FEATURES) + ([GRAPH_FEATURE] if use_graph else [])
    train = train[train[TARGET].notna() & train["lag1_births"].notna()].copy()
    test = test[test[TARGET].notna() & test["lag1_births"].notna()].copy()
    if train.empty or test.empty:
        raise ValueError("Residual Ridge requires non-empty train and test rows")

    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    scaler = StandardScaler()
    x_train = imputer.fit_transform(train[features].to_numpy(dtype=float))
    x_test = imputer.transform(test[features].to_numpy(dtype=float))
    x_train = scaler.fit_transform(x_train)
    x_test = scaler.transform(x_test)
    y_train = np.log1p(train[TARGET].to_numpy(dtype=float)) - np.log1p(
        train["lag1_births"].to_numpy(dtype=float)
    )
    model = Ridge(alpha=alpha)
    model.fit(x_train, y_train)
    correction = model.predict(x_test)
    prediction = np.expm1(
        np.log1p(test["lag1_births"].to_numpy(dtype=float)) + correction
    )
    return np.maximum(prediction, 0.0)


def rolling_validation_score(
    panel: pd.DataFrame,
    outer_year: int,
    alpha: float,
    use_graph: bool,
) -> tuple[float, int]:
    scores = []
    rows = 0
    for validation_year in range(VALIDATION_START_YEAR, outer_year):
        train = panel[panel["year"] < validation_year]
        test = panel[panel["year"] == validation_year]
        if train.empty or test.empty:
            continue
        prediction = residual_ridge_predict(train, test, alpha, use_graph)
        scores.append(
            wmape(test[TARGET].to_numpy(dtype=float), prediction)
        )
        rows += len(test)
    if not scores:
        raise ValueError(f"No causal validation folds before {outer_year}")
    return float(np.mean(scores)), rows


def select_alpha(
    panel: pd.DataFrame,
    outer_year: int,
    use_graph: bool,
) -> tuple[float, list[dict]]:
    candidates = []
    for alpha in ALPHAS:
        score, rows = rolling_validation_score(panel, outer_year, alpha, use_graph)
        candidates.append(
            {"alpha": alpha, "mean_yearly_wmape": score, "validation_rows": rows}
        )
    candidates.sort(key=lambda item: (item["mean_yearly_wmape"], -item["alpha"]))
    return float(candidates[0]["alpha"]), candidates


def forecast_panel(
    panel: pd.DataFrame,
    config: str,
    graph_id: str,
    use_graph: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_rows = []
    selection_rows = []
    for year in EVAL_YEARS:
        train = panel[panel["year"] < year]
        test = panel[panel["year"] == year]
        if test.empty:
            raise ValueError(f"Missing Italy test rows for {year}")
        alpha, candidates = select_alpha(panel, year, use_graph)
        prediction = residual_ridge_predict(train, test, alpha, use_graph)
        selection_rows.append(
            {
                "config": config,
                "graph_id": graph_id,
                "year": year,
                "train_max_year": int(train["year"].max()),
                "selected_alpha": alpha,
                "candidates_json": json.dumps(candidates),
                "target_year_used_for_fit_or_selection": False,
            }
        )
        for row, value in zip(test.itertuples(index=False), prediction):
            prediction_rows.append(
                {
                    "country": COUNTRY,
                    "region_id": row.region_id,
                    "year": year,
                    "config": config,
                    "graph_id": graph_id,
                    "y_true": float(row.target_births),
                    "y_pred": float(value),
                }
            )
    return pd.DataFrame(prediction_rows), pd.DataFrame(selection_rows)


def metric_summary(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    yearly_rows = []
    for (config, graph_id, year), frame in predictions.groupby(
        ["config", "graph_id", "year"]
    ):
        yearly_rows.append(
            {
                "config": config,
                "graph_id": graph_id,
                "year": int(year),
                "wmape": wmape(
                    frame["y_true"].to_numpy(dtype=float),
                    frame["y_pred"].to_numpy(dtype=float),
                ),
            }
        )
    yearly = pd.DataFrame(yearly_rows)
    summary_rows = []
    for (config, graph_id), frame in predictions.groupby(["config", "graph_id"]):
        year_frame = yearly[
            yearly["config"].eq(config) & yearly["graph_id"].eq(graph_id)
        ]
        worst = year_frame.loc[year_frame["wmape"].idxmax()]
        summary_rows.append(
            {
                "config": config,
                "graph_id": graph_id,
                "overall_wmape": wmape(
                    frame["y_true"].to_numpy(dtype=float),
                    frame["y_pred"].to_numpy(dtype=float),
                ),
                "mean_yearly_wmape": float(year_frame["wmape"].mean()),
                "worst_year": int(worst["year"]),
                "worst_year_wmape": float(worst["wmape"]),
            }
        )
    return yearly, pd.DataFrame(summary_rows)


def residual_moran(
    predictions: pd.DataFrame,
    W: np.ndarray,
    region_order: list[str],
) -> pd.DataFrame:
    rows = []
    selected = predictions[
        predictions["config"].isin(("p1_ridge_residual", "p2_real_graph"))
    ]
    for (config, year), frame in selected.groupby(["config", "year"]):
        indexed = frame.set_index("region_id").loc[region_order]
        raw = (
            indexed["y_true"].to_numpy(dtype=float)
            - indexed["y_pred"].to_numpy(dtype=float)
        )
        relative = raw / np.maximum(
            np.abs(indexed["y_true"].to_numpy(dtype=float)), EPSILON
        )
        rows.append(
            {
                "config": config,
                "year": int(year),
                "moran_abs": moran_global(raw, W),
                "moran_relative": moran_global(relative, W),
            }
        )
    return pd.DataFrame(rows)


def decision_payload(summary: pd.DataFrame, yearly: pd.DataFrame) -> dict:
    base = summary[summary["config"].eq("p0_persistence")].iloc[0]
    residual = summary[summary["config"].eq("p1_ridge_residual")].iloc[0]
    real = summary[summary["config"].eq("p2_real_graph")].iloc[0]
    controls = summary[summary["config"].eq("p3_permuted_graph")]
    control_yearly = yearly[yearly["config"].eq("p3_permuted_graph")]
    real_yearly = yearly[yearly["config"].eq("p2_real_graph")].set_index("year")
    control_median = float(controls["mean_yearly_wmape"].median())
    gain_vs_persistence = float(
        1.0 - float(real["mean_yearly_wmape"]) / float(base["mean_yearly_wmape"])
    )
    gain_vs_residual = float(
        1.0
        - float(real["mean_yearly_wmape"]) / float(residual["mean_yearly_wmape"])
    )
    worst_year_regression = float(
        float(real["worst_year_wmape"]) / float(base["worst_year_wmape"]) - 1.0
    )
    better_controls = int(
        (controls["mean_yearly_wmape"] <= float(real["mean_yearly_wmape"])).sum()
    )
    empirical_control_p = float((1 + better_controls) / (1 + len(controls)))
    real_year_wins = 0
    for year, real_row in real_yearly.iterrows():
        median_control = float(
            control_yearly[control_yearly["year"].eq(year)]["wmape"].median()
        )
        real_year_wins += int(float(real_row["wmape"]) < median_control)
    supports_spatial_feature = bool(
        gain_vs_persistence >= MIN_PROMOTION_GAIN
        and gain_vs_residual >= MIN_PROMOTION_GAIN
        and empirical_control_p <= 0.05
        and real_year_wins >= 5
        and worst_year_regression <= MAX_WORST_YEAR_REGRESSION
    )
    return {
        "phase": "4P",
        "scope": "Italy-only linear diagnostic",
        "multi_country_graph_training_authorised": False,
        "evaluation_years": list(EVAL_YEARS),
        "target_year_used_for_fit_or_selection": False,
        "neighbour_lag_uses": "queen-neighbour mean target_births at t-1",
        "persistence_mean_yearly_wmape": float(base["mean_yearly_wmape"]),
        "residual_ridge_mean_yearly_wmape": float(residual["mean_yearly_wmape"]),
        "real_graph_mean_yearly_wmape": float(real["mean_yearly_wmape"]),
        "permuted_graph_median_mean_yearly_wmape": control_median,
        "minimum_promotion_gain": MIN_PROMOTION_GAIN,
        "maximum_worst_year_regression": MAX_WORST_YEAR_REGRESSION,
        "real_graph_gain_vs_persistence": gain_vs_persistence,
        "real_graph_gain_vs_residual_ridge": gain_vs_residual,
        "real_graph_gain_vs_permuted_median": float(
            1.0 - float(real["mean_yearly_wmape"]) / control_median
        ),
        "real_graph_worst_year_regression_vs_persistence": worst_year_regression,
        "permuted_controls_beating_or_tying_real": better_controls,
        "n_permuted_controls": int(len(controls)),
        "empirical_permuted_control_p": empirical_control_p,
        "real_graph_year_wins_vs_permuted_median": real_year_wins,
        "diagnostic_supports_spatial_feature": supports_spatial_feature,
        "next_step": (
            "retain Italy spatial lag as country-specific evidence; gather another robust country"
            if supports_spatial_feature
            else "reject Italy spatial lag predictive value; retain non-graph baseline"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--panel",
        type=Path,
        default=Path(
            "data/processed/european_panel/"
            "enterprise_birth_pt_it_at_mainland_panel.csv"
        ),
    )
    parser.add_argument(
        "--geojson",
        type=Path,
        default=Path("data/external/nuts3_2021_eurostat.geojson"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("hpc_results/herald_phase4p_it_spatial_lag_r1"),
    )
    parser.add_argument("--n-graph-controls", type=int, default=99)
    args = parser.parse_args()

    panel_path = args.panel if args.panel.is_absolute() else BASE / args.panel
    geo_path = args.geojson if args.geojson.is_absolute() else BASE / args.geojson
    output_dir = (
        args.output_dir if args.output_dir.is_absolute() else BASE / args.output_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(panel_path)
    panel = panel[panel["country"].eq(COUNTRY)].sort_values(["region_id", "year"])
    region_order = sorted(panel["region_id"].unique())
    gdf = load_geometry(geo_path, COUNTRY, region_order)
    region_order = list(gdf.index)
    W_raw = queen_adjacency_raw(gdf)
    W_real = row_normalise(W_raw)
    rng = np.random.default_rng(RNG_SEED)

    prediction_frames = []
    selection_frames = []
    persistence = panel[panel["year"].isin(EVAL_YEARS)].copy()
    persistence["config"] = "p0_persistence"
    persistence["graph_id"] = "none"
    persistence["y_true"] = persistence[TARGET]
    persistence["y_pred"] = persistence["lag1_births"]
    prediction_frames.append(
        persistence[
            ["country", "region_id", "year", "config", "graph_id", "y_true", "y_pred"]
        ]
    )

    baseline_pred, baseline_sel = forecast_panel(
        panel, "p1_ridge_residual", "none", use_graph=False
    )
    prediction_frames.append(baseline_pred)
    selection_frames.append(baseline_sel)

    real_panel = add_neighbour_lag1(panel, W_real, region_order)
    real_pred, real_sel = forecast_panel(
        real_panel, "p2_real_graph", "real", use_graph=True
    )
    prediction_frames.append(real_pred)
    selection_frames.append(real_sel)

    for control_idx in range(args.n_graph_controls):
        graph_id = f"perm_{control_idx:03d}"
        # conjugation_permutation returns a row-normalised relabelled graph,
        # matching the neighbour-mean feature used by the real graph.
        W_control = conjugation_permutation(W_raw, rng)
        control_panel = add_neighbour_lag1(panel, W_control, region_order)
        control_pred, control_sel = forecast_panel(
            control_panel, "p3_permuted_graph", graph_id, use_graph=True
        )
        prediction_frames.append(control_pred)
        selection_frames.append(control_sel)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    selections = pd.concat(selection_frames, ignore_index=True)
    yearly, summary = metric_summary(predictions)
    moran = residual_moran(predictions, W_real, region_order)
    decision = decision_payload(summary, yearly)

    predictions.to_csv(output_dir / "phase4p_predictions.csv", index=False)
    selections.to_csv(output_dir / "phase4p_selection.csv", index=False)
    yearly.to_csv(output_dir / "phase4p_yearly.csv", index=False)
    summary.to_csv(output_dir / "phase4p_summary.csv", index=False)
    moran.to_csv(output_dir / "phase4p_residual_moran.csv", index=False)
    np.save(output_dir / "italy_queen_adjacency_raw.npy", W_raw)
    np.save(output_dir / "italy_queen_adjacency_norm.npy", W_real)
    (output_dir / "phase4p_decision.json").write_text(
        json.dumps(decision, indent=2), encoding="utf-8"
    )

    print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
