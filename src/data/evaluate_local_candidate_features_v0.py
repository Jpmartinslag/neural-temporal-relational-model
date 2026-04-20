import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "extended_panel_core_v0.csv"
TARGET_HISTORY_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
ENERGY_PATH = ROOT / "data" / "interim" / "tables" / "energy_consumption_ze2020_v0.csv"
SITADEL_ANNUAL_PATH = ROOT / "data" / "interim" / "tables" / "sitadel_surface_ze2020_v0.csv"
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


def safe_log_diff(frame, value_col, periods=1):
    grouped = frame.sort_values(["ze2020", "year"]).groupby("ze2020")[value_col]
    current = np.log1p(frame[value_col].clip(lower=0))
    previous = np.log1p(grouped.shift(periods).clip(lower=0))
    return current - previous


def safe_rolling_mean_log(frame, value_col, window, min_periods=None):
    if min_periods is None:
        min_periods = window
    rolled = (
        frame.sort_values(["ze2020", "year"])
        .groupby("ze2020")[value_col]
        .rolling(window=window, min_periods=min_periods)
        .mean()
        .reset_index(level=0, drop=True)
    )
    return np.log1p(rolled.clip(lower=0))


def safe_rolling_volatility_log(frame, value_col, window, min_periods=None):
    if min_periods is None:
        min_periods = window
    logged = np.log1p(frame[value_col].clip(lower=0))
    work = frame[["ze2020", "year"]].copy()
    work["_logged"] = logged
    return (
        work.sort_values(["ze2020", "year"])
        .groupby("ze2020")["_logged"]
        .rolling(window=window, min_periods=min_periods)
        .std()
        .reset_index(level=0, drop=True)
    )


def merge_engineered_lagged_source(panel, source, prefix, feature_cols):
    source = source[["ze2020", "year"] + feature_cols].copy()
    source["year"] = source["year"] + 1
    rename = {col: f"{prefix}_{col}_lag_1" for col in feature_cols}
    source = source.rename(columns=rename)
    merged = panel.merge(source, on=["ze2020", "year"], how="left")
    return merged, list(rename.values())


def merge_target_history_features(panel):
    if not TARGET_HISTORY_PATH.exists():
        return panel, []

    source = pd.read_csv(TARGET_HISTORY_PATH, dtype={"ze2020": str})
    source = source.rename(columns={"target_year": "year"})
    source = source[["ze2020", "year", "side_establishment_creations_official"]].copy()
    source = source.sort_values(["ze2020", "year"])
    y = "side_establishment_creations_official"
    source["target_side_log_diff_1y"] = safe_log_diff(source, y, periods=1)
    source["target_side_log_diff_2y"] = safe_log_diff(source, y, periods=2)
    source["target_side_roll_mean_3y_log"] = safe_rolling_mean_log(source, y, window=3)
    source["target_side_acceleration"] = (
        source["target_side_log_diff_1y"]
        - source.groupby("ze2020")["target_side_log_diff_1y"].shift(1)
    )
    features = [
        "target_side_log_diff_1y",
        "target_side_log_diff_2y",
        "target_side_roll_mean_3y_log",
        "target_side_acceleration",
    ]
    return merge_engineered_lagged_source(panel, source, "engineered", features)


def merge_energy_engineered_features(panel):
    if not ENERGY_PATH.exists():
        return panel, []

    source = pd.read_csv(ENERGY_PATH, dtype={"ZE2020": str})
    source = source.rename(columns={"ZE2020": "ze2020"})
    source = source.sort_values(["ze2020", "year"]).copy()
    conso_cols = [
        "energy_electricity_conso_nonres",
        "energy_gas_conso_nonres",
        "energy_heat_cold_conso_nonres",
    ]
    pdl_cols = [
        "energy_electricity_pdl_nonres",
        "energy_gas_pdl_nonres",
        "energy_heat_cold_pdl_nonres",
    ]
    for col in conso_cols + pdl_cols:
        if col not in source.columns:
            source[col] = np.nan

    source["energy_nonres_total_conso"] = source[conso_cols].sum(axis=1, min_count=1)
    source["energy_nonres_total_pdl"] = source[pdl_cols].sum(axis=1, min_count=1)
    elec = source["energy_electricity_conso_nonres"]
    gas = source["energy_gas_conso_nonres"]
    elec_gas_total = elec + gas
    source["energy_elec_share"] = np.where(elec_gas_total > 0, elec / elec_gas_total, np.nan)
    source["energy_gas_share"] = np.where(elec_gas_total > 0, gas / elec_gas_total, np.nan)
    source["energy_nonres_log_diff_1y"] = safe_log_diff(source, "energy_nonres_total_conso", periods=1)
    source["energy_nonres_log_diff_2y"] = safe_log_diff(source, "energy_nonres_total_conso", periods=2)
    source["energy_nonres_volatility_3y"] = safe_rolling_volatility_log(
        source,
        "energy_nonres_total_conso",
        window=3,
    )
    source["energy_pdl_log_diff_1y"] = safe_log_diff(source, "energy_nonres_total_pdl", periods=1)
    features = [
        "energy_nonres_log_diff_1y",
        "energy_nonres_log_diff_2y",
        "energy_nonres_volatility_3y",
        "energy_elec_share",
        "energy_gas_share",
        "energy_pdl_log_diff_1y",
    ]
    return merge_engineered_lagged_source(panel, source, "engineered", features)


def merge_rei_engineered_features(panel):
    if not REI_PATH.exists():
        return panel, []

    source = pd.read_csv(REI_PATH, dtype={"ZE2020": str})
    source = source.rename(columns={"ZE2020": "ze2020"})
    source = source.sort_values(["ze2020", "year"]).copy()
    base_cols = ["rei_cfe_commune_base", "rei_cfe_epci_base"]
    product_cols = ["rei_cfe_commune_product", "rei_cfe_epci_product"]
    article_cols = ["rei_cfe_commune_articles", "rei_cfe_epci_articles"]
    for col in base_cols + product_cols + article_cols:
        if col not in source.columns:
            source[col] = np.nan

    source["rei_cfe_total_base"] = source[base_cols].sum(axis=1, min_count=1)
    source["rei_cfe_total_product"] = source[product_cols].sum(axis=1, min_count=1)
    source["rei_cfe_total_articles"] = source[article_cols].sum(axis=1, min_count=1)
    source["rei_cfe_base_log_diff_1y"] = safe_log_diff(source, "rei_cfe_total_base", periods=1)
    source["rei_cfe_product_log_diff_1y"] = safe_log_diff(source, "rei_cfe_total_product", periods=1)
    source["rei_cfe_articles_log_diff_1y"] = safe_log_diff(source, "rei_cfe_total_articles", periods=1)
    source["rei_cfe_base_volatility_3y"] = safe_rolling_volatility_log(
        source,
        "rei_cfe_total_base",
        window=3,
    )
    features = [
        "rei_cfe_base_log_diff_1y",
        "rei_cfe_product_log_diff_1y",
        "rei_cfe_articles_log_diff_1y",
        "rei_cfe_base_volatility_3y",
    ]
    return merge_engineered_lagged_source(panel, source, "engineered", features)


def merge_sitadel_engineered_features(panel):
    if not SITADEL_ANNUAL_PATH.exists():
        return panel, []

    source = pd.read_csv(SITADEL_ANNUAL_PATH, dtype={"ZE2020": str})
    source = source.rename(columns={"ZE2020": "ze2020"})
    source = source.sort_values(["ze2020", "year"]).copy()
    surface_cols = ["sitadel_surface_autorisee", "sitadel_surface_commencee"]
    for col in surface_cols:
        if col not in source.columns:
            source[col] = np.nan

    source["sitadel_autorisee_roll_mean_2y_log"] = safe_rolling_mean_log(
        source,
        "sitadel_surface_autorisee",
        window=2,
    )
    source["sitadel_commencee_roll_mean_2y_log"] = safe_rolling_mean_log(
        source,
        "sitadel_surface_commencee",
        window=2,
    )
    source["sitadel_autorisee_volatility_3y"] = safe_rolling_volatility_log(
        source,
        "sitadel_surface_autorisee",
        window=3,
    )
    source["sitadel_commencee_volatility_3y"] = safe_rolling_volatility_log(
        source,
        "sitadel_surface_commencee",
        window=3,
    )
    features = [
        "sitadel_autorisee_roll_mean_2y_log",
        "sitadel_commencee_roll_mean_2y_log",
        "sitadel_autorisee_volatility_3y",
        "sitadel_commencee_volatility_3y",
    ]
    return merge_engineered_lagged_source(panel, source, "engineered", features)


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


def causal_model_selection_check(backtest_rows):
    """Select the best model using only prior test years.

    This is a stricter check than mean WMAPE: it asks whether the apparent
    average winner could have been chosen without looking at the current year.
    """
    forecast_safe_models = {
        "persistence",
        "ridge_lag_only",
        "ridge_sitadel_only",
        "ridge_sitadel_log",
        "ridge_sitadel_monthly_lag",
        "ridge_sitadel_monthly_lag_log",
        "ridge_rei_only",
        "ridge_rei_log",
        "ridge_energy_only",
        "ridge_energy_log",
        "ridge_local_all",
        "ridge_local_all_log",
        "ridge_engineered_target",
        "ridge_engineered_energy",
        "ridge_engineered_rei",
        "ridge_engineered_sitadel",
        "ridge_engineered_local",
        "ridge_engineered_all",
    }
    rows = [row for row in backtest_rows if row["model"] in forecast_safe_models]
    years = sorted({row["test_year"] for row in rows})
    wmape_by_year_model = {
        (row["test_year"], row["model"]): row["wmape"]
        for row in rows
    }

    selected = []
    for year in years:
        prior_years = [prior for prior in years if prior < year]
        if not prior_years:
            selected_model = "ridge_lag_only"
            prior_mean_wmape = None
        else:
            candidates = []
            for model in forecast_safe_models:
                prior_values = [
                    wmape_by_year_model.get((prior_year, model))
                    for prior_year in prior_years
                ]
                prior_values = [value for value in prior_values if value is not None]
                if len(prior_values) == len(prior_years):
                    candidates.append((float(np.mean(prior_values)), model))
            prior_mean_wmape, selected_model = min(candidates)

        selected.append(
            {
                "test_year": int(year),
                "selected_model": selected_model,
                "prior_mean_wmape": prior_mean_wmape,
                "test_wmape": float(wmape_by_year_model[(year, selected_model)]),
            }
        )

    return {
        "mean_wmape": float(np.mean([row["test_wmape"] for row in selected])),
        "selected_runs": selected,
        "methodology": (
            "For each test year, choose the forecast-safe model with the best "
            "mean WMAPE on earlier test years only; first year defaults to ridge_lag_only."
        ),
    }


def evaluate_candidates():
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    panel = add_target_growth(panel)

    panel, target_engineered_features = merge_target_history_features(panel)
    panel, energy_engineered_features = merge_energy_engineered_features(panel)
    panel, rei_engineered_features = merge_rei_engineered_features(panel)
    panel, sitadel_engineered_features = merge_sitadel_engineered_features(panel)

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
    panel, sitadel_log_features = add_log_transforms(panel, sitadel_features)

    candidate_groups = {
        "ridge_sitadel_only": ["side_creations_lag_1"] + sitadel_features,
        "ridge_sitadel_log": ["side_creations_lag_1"] + sitadel_log_features,
    }
    if target_engineered_features:
        candidate_groups["ridge_engineered_target"] = (
            ["side_creations_lag_1"] + target_engineered_features
        )
    if energy_engineered_features:
        candidate_groups["ridge_engineered_energy"] = (
            ["side_creations_lag_1"] + energy_engineered_features
        )
    if rei_engineered_features:
        candidate_groups["ridge_engineered_rei"] = (
            ["side_creations_lag_1"] + rei_engineered_features
        )
    if sitadel_engineered_features:
        candidate_groups["ridge_engineered_sitadel"] = (
            ["side_creations_lag_1"] + sitadel_engineered_features
        )
    if energy_engineered_features or rei_engineered_features or sitadel_engineered_features:
        candidate_groups["ridge_engineered_local"] = (
            ["side_creations_lag_1"]
            + energy_engineered_features
            + rei_engineered_features
            + sitadel_engineered_features
        )
    if target_engineered_features or energy_engineered_features or rei_engineered_features or sitadel_engineered_features:
        candidate_groups["ridge_engineered_all"] = (
            ["side_creations_lag_1"]
            + target_engineered_features
            + energy_engineered_features
            + rei_engineered_features
            + sitadel_engineered_features
        )
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
        panel, rei_log_features = add_log_transforms(panel, rei_features)
        candidate_groups["ridge_rei_only"] = ["side_creations_lag_1"] + rei_features
        candidate_groups["ridge_rei_log"] = ["side_creations_lag_1"] + rei_log_features
    else:
        rei_log_features = []
    if energy_features:
        panel, energy_log_features = add_log_transforms(panel, energy_features)
        candidate_groups["ridge_energy_only"] = ["side_creations_lag_1"] + energy_features
        candidate_groups["ridge_energy_log"] = ["side_creations_lag_1"] + energy_log_features
    else:
        energy_log_features = []
    if rei_features or energy_features:
        candidate_groups["ridge_local_all"] = ["side_creations_lag_1"] + sitadel_features + rei_features + energy_features
        candidate_groups["ridge_local_all_log"] = (
            ["side_creations_lag_1"] + sitadel_log_features + rei_log_features + energy_log_features
        )

    all_candidate_features = (
        target_engineered_features
        + energy_engineered_features
        + rei_engineered_features
        + sitadel_engineered_features
        + sitadel_features
        + sitadel_log_features
        + rei_features
        + rei_log_features
        + energy_features
        + energy_log_features
        + sitadel_monthly_lag_features
        + sitadel_monthly_lag_log_features
        + sitadel_monthly_q1_nowcast_features
        + sitadel_monthly_q1_nowcast_log_features
        + sitadel_monthly_h1_nowcast_features
        + sitadel_monthly_h1_nowcast_log_features
    )
    corr_rows = within_year_correlations(panel, all_candidate_features)
    backtest_rows = rolling_candidate_backtest(panel, candidate_groups)
    causal_selection = causal_model_selection_check(backtest_rows)
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
        "causal_model_selection_check": causal_selection,
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
