#!/usr/bin/env python3
"""Phase 4Q: causal Italy-only fixed Spatial-Durbin diagnostic."""

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
from hpc.phase4.run_phase4p_italy_spatial_lag import (
    ALPHAS,
    BASE_FEATURES,
    COUNTRY,
    EPSILON,
    EVAL_YEARS,
    MAX_WORST_YEAR_REGRESSION,
    MIN_PROMOTION_GAIN,
    RNG_SEED,
    TARGET,
    VALIDATION_START_YEAR,
    metric_summary,
    wmape,
)

SPATIAL_SOURCES = (
    "lag1_births",
    "growth_1y",
    "growth_2y",
    "stock_lag1",
)
SPATIAL_FEATURES = tuple(f"neighbour_{name}" for name in SPATIAL_SOURCES)


def add_spatial_durbin_features(
    panel: pd.DataFrame,
    W: np.ndarray,
    region_order: list[str],
) -> pd.DataFrame:
    """Add neighbour means for the fixed forecast-safe feature block."""
    if W.shape != (len(region_order), len(region_order)):
        raise ValueError("Adjacency shape does not match region order")
    work = panel.copy()
    for feature in SPATIAL_FEATURES:
        work[feature] = np.nan
    for year, year_frame in work.groupby("year"):
        indexed = year_frame.set_index("region_id")
        missing = set(region_order) - set(indexed.index)
        extra = set(indexed.index) - set(region_order)
        if missing or extra or indexed.index.duplicated().any():
            raise ValueError(
                f"year={year}: panel/graph alignment mismatch; "
                f"missing={sorted(missing)[:3]}, extra={sorted(extra)[:3]}"
            )
        for source, output in zip(SPATIAL_SOURCES, SPATIAL_FEATURES):
            values = indexed.loc[region_order, source].to_numpy(dtype=float)
            neighbours = (
                W @ values
                if np.isfinite(values).all()
                else np.full(len(values), np.nan)
            )
            mapping = dict(zip(region_order, neighbours))
            work.loc[year_frame.index, output] = year_frame["region_id"].map(mapping)
    return work


def residual_ridge_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    alpha: float,
    use_spatial_block: bool,
) -> np.ndarray:
    features = list(BASE_FEATURES)
    if use_spatial_block:
        features.extend(SPATIAL_FEATURES)
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
    use_spatial_block: bool,
) -> tuple[float, int]:
    scores = []
    rows = 0
    for validation_year in range(VALIDATION_START_YEAR, outer_year):
        train = panel[panel["year"] < validation_year]
        test = panel[panel["year"] == validation_year]
        if train.empty or test.empty:
            continue
        prediction = residual_ridge_predict(
            train, test, alpha, use_spatial_block
        )
        scores.append(wmape(test[TARGET].to_numpy(dtype=float), prediction))
        rows += len(test)
    if not scores:
        raise ValueError(f"No causal validation folds before {outer_year}")
    return float(np.mean(scores)), rows


def select_alpha(
    panel: pd.DataFrame,
    outer_year: int,
    use_spatial_block: bool,
) -> tuple[float, list[dict]]:
    candidates = []
    for alpha in ALPHAS:
        score, rows = rolling_validation_score(
            panel, outer_year, alpha, use_spatial_block
        )
        candidates.append(
            {"alpha": alpha, "mean_yearly_wmape": score, "validation_rows": rows}
        )
    candidates.sort(key=lambda item: (item["mean_yearly_wmape"], -item["alpha"]))
    return float(candidates[0]["alpha"]), candidates


def forecast_panel(
    panel: pd.DataFrame,
    config: str,
    graph_id: str,
    use_spatial_block: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_rows = []
    selection_rows = []
    for year in EVAL_YEARS:
        train = panel[panel["year"] < year]
        test = panel[panel["year"] == year]
        if test.empty:
            raise ValueError(f"Missing Italy test rows for {year}")
        alpha, candidates = select_alpha(panel, year, use_spatial_block)
        prediction = residual_ridge_predict(
            train, test, alpha, use_spatial_block
        )
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


def residual_moran(
    predictions: pd.DataFrame,
    W: np.ndarray,
    region_order: list[str],
) -> pd.DataFrame:
    rows = []
    selected = predictions[
        predictions["config"].isin(("q1_ridge_residual", "q2_real_durbin"))
    ]
    for (config, year), frame in selected.groupby(["config", "year"]):
        indexed = frame.set_index("region_id").loc[region_order]
        residual = (
            indexed["y_true"].to_numpy(dtype=float)
            - indexed["y_pred"].to_numpy(dtype=float)
        )
        relative = residual / np.maximum(
            np.abs(indexed["y_true"].to_numpy(dtype=float)), EPSILON
        )
        rows.append(
            {
                "config": config,
                "year": int(year),
                "moran_abs": moran_global(residual, W),
                "moran_relative": moran_global(relative, W),
            }
        )
    return pd.DataFrame(rows)


def decision_payload(
    summary: pd.DataFrame,
    yearly: pd.DataFrame,
    moran: pd.DataFrame,
) -> dict:
    persistence = summary[summary["config"].eq("q0_persistence")].iloc[0]
    residual = summary[summary["config"].eq("q1_ridge_residual")].iloc[0]
    real = summary[summary["config"].eq("q2_real_durbin")].iloc[0]
    controls = summary[summary["config"].eq("q3_permuted_durbin")]
    controls_yearly = yearly[yearly["config"].eq("q3_permuted_durbin")]
    real_yearly = yearly[yearly["config"].eq("q2_real_durbin")].set_index("year")

    control_median = float(controls["mean_yearly_wmape"].median())
    better_controls = int(
        (controls["mean_yearly_wmape"] <= float(real["mean_yearly_wmape"])).sum()
    )
    empirical_p = float((1 + better_controls) / (1 + len(controls)))
    yearly_wins = sum(
        float(row["wmape"])
        < float(
            controls_yearly[controls_yearly["year"].eq(year)]["wmape"].median()
        )
        for year, row in real_yearly.iterrows()
    )
    gain_persistence = float(
        1.0
        - float(real["mean_yearly_wmape"])
        / float(persistence["mean_yearly_wmape"])
    )
    gain_residual = float(
        1.0
        - float(real["mean_yearly_wmape"]) / float(residual["mean_yearly_wmape"])
    )
    worst_regression = float(
        float(real["worst_year_wmape"])
        / float(persistence["worst_year_wmape"])
        - 1.0
    )
    moran_means = moran.groupby("config")["moran_relative"].mean()
    moran_before = float(moran_means["q1_ridge_residual"])
    moran_after = float(moran_means["q2_real_durbin"])
    moran_reduced = bool(moran_after < moran_before)
    passed = bool(
        gain_persistence >= MIN_PROMOTION_GAIN
        and gain_residual >= MIN_PROMOTION_GAIN
        and empirical_p <= 0.05
        and yearly_wins >= 5
        and worst_regression <= MAX_WORST_YEAR_REGRESSION
        and moran_reduced
    )
    return {
        "phase": "4Q",
        "scope": "Italy-only fixed Spatial-Durbin diagnostic",
        "evaluation_years": list(EVAL_YEARS),
        "spatial_sources": list(SPATIAL_SOURCES),
        "target_year_used_for_fit_or_selection": False,
        "minimum_promotion_gain": MIN_PROMOTION_GAIN,
        "maximum_worst_year_regression": MAX_WORST_YEAR_REGRESSION,
        "persistence_mean_yearly_wmape": float(
            persistence["mean_yearly_wmape"]
        ),
        "residual_ridge_mean_yearly_wmape": float(
            residual["mean_yearly_wmape"]
        ),
        "real_durbin_mean_yearly_wmape": float(real["mean_yearly_wmape"]),
        "permuted_durbin_median_mean_yearly_wmape": control_median,
        "real_durbin_gain_vs_persistence": gain_persistence,
        "real_durbin_gain_vs_residual_ridge": gain_residual,
        "real_durbin_gain_vs_permuted_median": float(
            1.0 - float(real["mean_yearly_wmape"]) / control_median
        ),
        "real_durbin_worst_year_regression_vs_persistence": worst_regression,
        "permuted_controls_beating_or_tying_real": better_controls,
        "n_permuted_controls": int(len(controls)),
        "empirical_permuted_control_p": empirical_p,
        "real_durbin_year_wins_vs_permuted_median": int(yearly_wins),
        "mean_relative_moran_before": moran_before,
        "mean_relative_moran_after": moran_after,
        "relative_moran_reduced": moran_reduced,
        "diagnostic_supports_spatial_durbin": passed,
        "multi_country_graph_training_authorised": False,
        "next_step": (
            "retain Italy Spatial-Durbin as local linear evidence only"
            if passed
            else "close geographic graph branch under current data"
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
        default=Path("hpc_results/herald_phase4q_it_spatial_durbin_r1"),
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
    persistence["config"] = "q0_persistence"
    persistence["graph_id"] = "none"
    persistence["y_true"] = persistence[TARGET]
    persistence["y_pred"] = persistence["lag1_births"]
    prediction_frames.append(
        persistence[
            ["country", "region_id", "year", "config", "graph_id", "y_true", "y_pred"]
        ]
    )

    residual_pred, residual_sel = forecast_panel(
        panel, "q1_ridge_residual", "none", use_spatial_block=False
    )
    prediction_frames.append(residual_pred)
    selection_frames.append(residual_sel)

    real_panel = add_spatial_durbin_features(panel, W_real, region_order)
    real_pred, real_sel = forecast_panel(
        real_panel, "q2_real_durbin", "real", use_spatial_block=True
    )
    prediction_frames.append(real_pred)
    selection_frames.append(real_sel)

    for control_idx in range(args.n_graph_controls):
        graph_id = f"perm_{control_idx:03d}"
        W_control = conjugation_permutation(W_raw, rng)
        control_panel = add_spatial_durbin_features(
            panel, W_control, region_order
        )
        control_pred, control_sel = forecast_panel(
            control_panel,
            "q3_permuted_durbin",
            graph_id,
            use_spatial_block=True,
        )
        prediction_frames.append(control_pred)
        selection_frames.append(control_sel)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    selections = pd.concat(selection_frames, ignore_index=True)
    yearly, summary = metric_summary(predictions)
    moran = residual_moran(predictions, W_real, region_order)
    decision = decision_payload(summary, yearly, moran)

    predictions.to_csv(output_dir / "phase4q_predictions.csv", index=False)
    selections.to_csv(output_dir / "phase4q_selection.csv", index=False)
    yearly.to_csv(output_dir / "phase4q_yearly.csv", index=False)
    summary.to_csv(output_dir / "phase4q_summary.csv", index=False)
    moran.to_csv(output_dir / "phase4q_residual_moran.csv", index=False)
    np.save(output_dir / "italy_queen_adjacency_raw.npy", W_raw)
    np.save(output_dir / "italy_queen_adjacency_norm.npy", W_real)
    (output_dir / "phase4q_decision.json").write_text(
        json.dumps(decision, indent=2), encoding="utf-8"
    )

    print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()

