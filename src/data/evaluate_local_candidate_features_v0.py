import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "extended_panel_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
ENERGY_PATH = ROOT / "data" / "interim" / "tables" / "energy_consumption_ze2020_v0.csv"
SITADEL_MONTHLY_DERIVED_PATH = ROOT / "data" / "interim" / "tables" / "sitadel_monthly_derived_annual_ze2020_v0.csv"
METRICS_PATH = ROOT / "reports" / "local_candidate_feature_metrics_v0.json"


def wmape(y_true, y_pred):
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100


def scale_and_impute_from_train(X_train_raw, X_test_raw):
    X_train_scaled = np.zeros_like(X_train_raw, dtype=float)
    X_test_scaled = np.zeros_like(X_test_raw, dtype=float)
    valid = []

    for i in range(X_train_raw.shape[1]):
        train_feat = X_train_raw[:, i]
        test_feat = X_test_raw[:, i]
        observed_train = train_feat[np.isfinite(train_feat)]
        if len(observed_train) == 0:
            valid.append(False)
            continue

        mean = observed_train.mean()
        std = observed_train.std()
        if std == 0:
            std = 1.0

        X_train_scaled[:, i] = np.where(np.isfinite(train_feat), (train_feat - mean) / std, 0.0)
        X_test_scaled[:, i] = np.where(np.isfinite(test_feat), (test_feat - mean) / std, 0.0)
        valid.append(True)

    valid = np.array(valid, dtype=bool)
    return X_train_scaled[:, valid], X_test_scaled[:, valid], valid


def merge_lagged_source(panel, path, prefix):
    if not path.exists():
        return panel, []

    source = pd.read_csv(path, dtype={"ZE2020": str})
    source = source.rename(columns={"ZE2020": "ze2020"})
    feature_cols = [c for c in source.columns if c not in {"ze2020", "year"}]
    source["year"] = source["year"] + 1
    source = source.rename(columns={c: f"{prefix}_{c}_lag_1" for c in feature_cols})

    merged = panel.merge(source, on=["ze2020", "year"], how="left")
    return merged, [f"{prefix}_{c}_lag_1" for c in feature_cols]


def merge_current_source(panel, path, prefix, keep_contains):
    if not path.exists():
        return panel, []

    source = pd.read_csv(path, dtype={"ZE2020": str})
    source = source.rename(columns={"ZE2020": "ze2020"})
    feature_cols = [
        c
        for c in source.columns
        if c not in {"ze2020", "year"} and any(pattern in c for pattern in keep_contains)
    ]
    source = source[["ze2020", "year"] + feature_cols].rename(
        columns={c: f"{prefix}_{c}_current" for c in feature_cols}
    )

    merged = panel.merge(source, on=["ze2020", "year"], how="left")
    return merged, [f"{prefix}_{c}_current" for c in feature_cols]


def add_log_transforms(panel, features):
    transformed = []
    for feature in features:
        if feature not in panel.columns:
            continue
        out = f"log1p_{feature}"
        panel[out] = np.log1p(panel[feature].clip(lower=0))
        transformed.append(out)
    return panel, transformed


def add_target_growth(panel):
    panel = panel.sort_values(["ze2020", "year"]).copy()
    lag = panel.groupby("ze2020")["side_establishment_creations_official"].shift(1)
    panel["target_growth"] = (
        panel["side_establishment_creations_official"] - lag
    ) / lag.replace(0, np.nan)
    return panel


def within_year_correlations(panel, features):
    rows = []
    for feature in features:
        if feature not in panel.columns:
            continue
        for year, frame in panel.groupby("year"):
            valid = frame[[feature, "target_growth"]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(valid) < 20 or valid[feature].std() == 0 or valid["target_growth"].std() == 0:
                continue
            rows.append(
                {
                    "feature": feature,
                    "year": int(year),
                    "corr_with_target_growth": float(valid[feature].corr(valid["target_growth"])),
                    "n": int(len(valid)),
                }
            )
    return rows


def rolling_candidate_backtest(panel, candidate_groups):
    years = sorted(panel["year"].unique())
    test_years = [2021, 2022, 2023, 2024]
    alphas = np.logspace(-3, 5, 20)
    base_features = ["side_creations_lag_1"]

    results = []
    for test_year in test_years:
        train = panel[panel["year"] < test_year].copy()
        test = panel[panel["year"] == test_year].copy()
        y_train = train["side_establishment_creations_official"].to_numpy(dtype=float)
        y_test = test["side_establishment_creations_official"].to_numpy(dtype=float)
        y_prev = test["side_creations_lag_1"].to_numpy(dtype=float)

        results.append(
            {
                "test_year": int(test_year),
                "model": "persistence",
                "wmape": float(wmape(y_test, y_prev)),
                "features": [],
            }
        )

        for name, features in {"ridge_lag_only": base_features, **candidate_groups}.items():
            cols = [c for c in features if c in panel.columns]
            X_train_raw = train[cols].to_numpy(dtype=float)
            X_test_raw = test[cols].to_numpy(dtype=float)
            X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
            used = [col for col, is_valid in zip(cols, valid) if is_valid]
            if not used:
                continue

            model = RidgeCV(alphas=alphas)
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            results.append(
                {
                    "test_year": int(test_year),
                    "model": name,
                    "wmape": float(wmape(y_test, pred)),
                    "features": used,
                }
            )

    return results


def evaluate_candidates():
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    panel = add_target_growth(panel)

    panel, rei_features = merge_lagged_source(panel, REI_PATH, "rei")
    panel, energy_features = merge_lagged_source(panel, ENERGY_PATH, "energy")
    panel, sitadel_monthly_lag_features = merge_lagged_source(
        panel,
        SITADEL_MONTHLY_DERIVED_PATH,
        "sitadel_monthly",
    )
    panel, sitadel_monthly_q1_nowcast_features = merge_current_source(
        panel,
        SITADEL_MONTHLY_DERIVED_PATH,
        "sitadel_monthly",
        keep_contains=["_q1_"],
    )
    panel, sitadel_monthly_h1_nowcast_features = merge_current_source(
        panel,
        SITADEL_MONTHLY_DERIVED_PATH,
        "sitadel_monthly",
        keep_contains=["_h1_"],
    )

    sitadel_features = [
        "sitadel_surface_autorisee_lag_1",
        "sitadel_surface_commencee_lag_1",
    ]

    candidate_groups = {
        "ridge_sitadel_only": ["side_creations_lag_1"] + sitadel_features,
    }
    if sitadel_monthly_lag_features:
        panel, sitadel_monthly_lag_log_features = add_log_transforms(panel, sitadel_monthly_lag_features)
        candidate_groups["ridge_sitadel_monthly_lag"] = ["side_creations_lag_1"] + sitadel_monthly_lag_features
        candidate_groups["ridge_sitadel_monthly_lag_log"] = ["side_creations_lag_1"] + sitadel_monthly_lag_log_features
    else:
        sitadel_monthly_lag_log_features = []

    if sitadel_monthly_q1_nowcast_features:
        panel, sitadel_monthly_q1_nowcast_log_features = add_log_transforms(panel, sitadel_monthly_q1_nowcast_features)
        candidate_groups["ridge_sitadel_monthly_q1_nowcast"] = (
            ["side_creations_lag_1"] + sitadel_monthly_q1_nowcast_features
        )
        candidate_groups["ridge_sitadel_monthly_q1_nowcast_log"] = (
            ["side_creations_lag_1"] + sitadel_monthly_q1_nowcast_log_features
        )
    else:
        sitadel_monthly_q1_nowcast_log_features = []

    if sitadel_monthly_h1_nowcast_features:
        panel, sitadel_monthly_h1_nowcast_log_features = add_log_transforms(panel, sitadel_monthly_h1_nowcast_features)
        candidate_groups["ridge_sitadel_monthly_h1_nowcast"] = (
            ["side_creations_lag_1"] + sitadel_monthly_h1_nowcast_features
        )
        candidate_groups["ridge_sitadel_monthly_h1_nowcast_log"] = (
            ["side_creations_lag_1"] + sitadel_monthly_h1_nowcast_log_features
        )
    else:
        sitadel_monthly_h1_nowcast_log_features = []

    if rei_features:
        candidate_groups["ridge_rei_only"] = ["side_creations_lag_1"] + rei_features
    if energy_features:
        candidate_groups["ridge_energy_only"] = ["side_creations_lag_1"] + energy_features
    if rei_features or energy_features:
        candidate_groups["ridge_local_all"] = ["side_creations_lag_1"] + sitadel_features + rei_features + energy_features

    all_candidate_features = (
        sitadel_features
        + rei_features
        + energy_features
        + sitadel_monthly_lag_features
        + sitadel_monthly_lag_log_features
        + sitadel_monthly_q1_nowcast_features
        + sitadel_monthly_q1_nowcast_log_features
        + sitadel_monthly_h1_nowcast_features
        + sitadel_monthly_h1_nowcast_log_features
    )
    corr_rows = within_year_correlations(panel, all_candidate_features)
    backtest_rows = rolling_candidate_backtest(panel, candidate_groups)
    summary = (
        pd.DataFrame(backtest_rows)
        .groupby("model")["wmape"]
        .mean()
        .sort_values()
        .to_dict()
    )

    output = {
        "summary_mean_wmape": summary,
        "within_year_correlations": corr_rows,
        "all_runs": backtest_rows,
        "available_candidate_features": all_candidate_features,
        "methodology": (
            "Candidate sources are evaluated incrementally against ridge_lag_only. "
            "Lagged sources are forecast-safe T-1. SITADEL monthly Q1/H1 current-year features are nowcast variants, not pure forecast features."
        ),
    }

    os.makedirs(METRICS_PATH.parent, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(json.dumps({"summary_mean_wmape": summary}, indent=2))
    print(f"Saved local candidate metrics to {METRICS_PATH}")


if __name__ == "__main__":
    evaluate_candidates()
