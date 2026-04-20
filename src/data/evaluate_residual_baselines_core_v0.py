import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNetCV, HuberRegressor, RidgeCV
from sklearn.utils._testing import ignore_warnings

from evaluate_local_candidate_features_v0 import (
    ENERGY_PATH,
    PANEL_PATH,
    REI_PATH,
    SITADEL_MONTHLY_DERIVED_PATH,
    add_log_transforms,
    merge_current_source,
    merge_energy_engineered_features,
    merge_lagged_source,
    merge_rei_engineered_features,
    merge_sitadel_engineered_features,
    merge_target_history_features,
    scale_and_impute_from_train,
    wmape,
)


ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "reports" / "residual_baseline_metrics_core_v0.json"
PREDICTIONS_PATH = ROOT / "data" / "processed" / "residual_baseline_predictions_core_v0.csv"


def build_panel_and_feature_groups():
    panel = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})

    panel, target_engineered_features = merge_target_history_features(panel)
    panel, energy_engineered_features = merge_energy_engineered_features(panel)
    panel, rei_engineered_features = merge_rei_engineered_features(panel)
    panel, sitadel_engineered_features = merge_sitadel_engineered_features(panel)

    # REI is intentionally excluded from residual baselines until its
    # publication lag/vintage safety is audited. The source remains buildable
    # as a diagnostic table, but it must not drive candidate model selection.
    rei_features = []
    rei_log_features = []
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

    sitadel_features = [
        "sitadel_surface_autorisee_lag_1",
        "sitadel_surface_commencee_lag_1",
    ]
    panel, sitadel_log_features = add_log_transforms(panel, sitadel_features)

    if energy_features:
        panel, energy_log_features = add_log_transforms(panel, energy_features)
    else:
        energy_log_features = []
    if sitadel_monthly_lag_features:
        panel, sitadel_monthly_lag_log_features = add_log_transforms(panel, sitadel_monthly_lag_features)
    else:
        sitadel_monthly_lag_log_features = []
    if sitadel_monthly_q1_nowcast_features:
        panel, sitadel_monthly_q1_nowcast_log_features = add_log_transforms(
            panel,
            sitadel_monthly_q1_nowcast_features,
        )
    else:
        sitadel_monthly_q1_nowcast_log_features = []

    feature_groups = {
        "lag_only": ["side_creations_lag_1"],
        "sitadel_only": ["side_creations_lag_1"] + sitadel_features,
        "energy_only": ["side_creations_lag_1"] + energy_features,
        "sitadel_energy": ["side_creations_lag_1"] + sitadel_features + energy_features,
        "local_all": ["side_creations_lag_1"] + sitadel_features + energy_features,
        "local_all_log": ["side_creations_lag_1"] + sitadel_log_features + energy_log_features,
        "engineered_target": ["side_creations_lag_1"] + target_engineered_features,
        "engineered_energy": ["side_creations_lag_1"] + energy_engineered_features,
        "engineered_sitadel": ["side_creations_lag_1"] + sitadel_engineered_features,
        "engineered_local": (
            ["side_creations_lag_1"]
            + energy_engineered_features
            + sitadel_engineered_features
        ),
        "engineered_all": (
            ["side_creations_lag_1"]
            + target_engineered_features
            + energy_engineered_features
            + sitadel_engineered_features
        ),
        "sitadel_monthly_lag_log": ["side_creations_lag_1"] + sitadel_monthly_lag_log_features,
        "sitadel_q1_nowcast_log": ["side_creations_lag_1"] + sitadel_monthly_q1_nowcast_log_features,
    }
    return panel, {name: cols for name, cols in feature_groups.items() if cols}


@ignore_warnings(category=ConvergenceWarning)
def fit_model(model_name, X_train, y_train):
    if model_name == "ridge":
        model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    elif model_name == "huber":
        model = HuberRegressor(alpha=1e-4, epsilon=1.35, max_iter=1000)
    elif model_name == "elasticnet":
        cv = min(3, max(2, len(y_train) // 280 - 1))
        model = ElasticNetCV(
            alphas=np.logspace(-3, 2, 12),
            l1_ratio=[0.1, 0.5, 0.9],
            cv=cv,
            max_iter=10000,
            random_state=0,
        )
    else:
        raise ValueError(f"Unknown model: {model_name}")

    model.fit(X_train, y_train)
    return model


def residual_predictions(panel, feature_groups):
    test_years = [2021, 2022, 2023, 2024]
    model_names = ["ridge", "huber", "elasticnet"]
    lambdas = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    rows = []
    prediction_rows = []

    for test_year in test_years:
        train = panel[panel["year"] < test_year].copy()
        test = panel[panel["year"] == test_year].copy()
        y_train = train["side_establishment_creations_official"].to_numpy(dtype=float)
        y_test = test["side_establishment_creations_official"].to_numpy(dtype=float)
        prev_train = train["side_creations_lag_1"].to_numpy(dtype=float)
        prev_test = test["side_creations_lag_1"].to_numpy(dtype=float)

        rows.append(
            {
                "test_year": int(test_year),
                "feature_group": "none",
                "model": "persistence",
                "residual_target": "none",
                "lambda": 0.0,
                "wmape": float(wmape(y_test, prev_test)),
                "features": [],
            }
        )
        for ze2020, actual, previous in zip(test["ze2020"], y_test, prev_test):
            prediction_rows.append(
                {
                    "test_year": int(test_year),
                    "ze2020": ze2020,
                    "model_id": "persistence",
                    "lambda": 0.0,
                    "actual": float(actual),
                    "persistence": float(previous),
                    "prediction": float(previous),
                }
            )
        X_train_lag, X_test_lag, _ = scale_and_impute_from_train(
            train[["side_creations_lag_1"]].to_numpy(dtype=float),
            test[["side_creations_lag_1"]].to_numpy(dtype=float),
        )
        ridge_level = RidgeCV(alphas=np.logspace(-3, 5, 20))
        ridge_level.fit(X_train_lag, y_train)
        ridge_level_pred = np.clip(ridge_level.predict(X_test_lag), a_min=0, a_max=None)
        rows.append(
            {
                "test_year": int(test_year),
                "feature_group": "lag_only",
                "model": "ridge_level",
                "residual_target": "level",
                "lambda": 1.0,
                "wmape": float(wmape(y_test, ridge_level_pred)),
                "features": ["side_creations_lag_1"],
            }
        )
        for ze2020, actual, previous, predicted in zip(
            test["ze2020"],
            y_test,
            prev_test,
            ridge_level_pred,
        ):
            prediction_rows.append(
                {
                    "test_year": int(test_year),
                    "ze2020": ze2020,
                    "model_id": "ridge_level_lag_only",
                    "lambda": 1.0,
                    "actual": float(actual),
                    "persistence": float(previous),
                    "prediction": float(predicted),
                }
            )

        for group_name, features in feature_groups.items():
            cols = [col for col in features if col in panel.columns]
            if not cols:
                continue
            X_train_raw = train[cols].to_numpy(dtype=float)
            X_test_raw = test[cols].to_numpy(dtype=float)
            X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
            used = [col for col, is_valid in zip(cols, valid) if is_valid]
            if not used:
                continue

            residual_targets = {
                "absolute": y_train - prev_train,
                "log": np.log1p(y_train.clip(min=0)) - np.log1p(prev_train.clip(min=0)),
            }
            for residual_target, residual_train in residual_targets.items():
                for model_name in model_names:
                    model = fit_model(model_name, X_train, residual_train)
                    residual_pred = model.predict(X_test)
                    if residual_target == "absolute":
                        unshrunk = prev_test + residual_pred
                    else:
                        unshrunk = np.expm1(np.log1p(prev_test.clip(min=0)) + residual_pred)
                    correction = unshrunk - prev_test

                    for shrinkage in lambdas:
                        pred = np.clip(prev_test + shrinkage * correction, a_min=0, a_max=None)
                        score = float(wmape(y_test, pred))
                        model_id = f"{model_name}_{residual_target}_{group_name}"
                        rows.append(
                            {
                                "test_year": int(test_year),
                                "feature_group": group_name,
                                "model": model_name,
                                "residual_target": residual_target,
                                "lambda": float(shrinkage),
                                "wmape": score,
                                "features": used,
                            }
                        )
                        for ze2020, actual, previous, predicted in zip(
                            test["ze2020"],
                            y_test,
                            prev_test,
                            pred,
                        ):
                            prediction_rows.append(
                                {
                                    "test_year": int(test_year),
                                    "ze2020": ze2020,
                                    "model_id": model_id,
                                    "lambda": float(shrinkage),
                                    "actual": float(actual),
                                    "persistence": float(previous),
                                    "prediction": float(predicted),
                                }
                            )

    return rows, prediction_rows


def summarize(rows):
    frame = pd.DataFrame(rows)
    summary = (
        frame.groupby(["model", "residual_target", "feature_group", "lambda"])["wmape"]
        .agg(["mean", "std", "max", "min"])
        .reset_index()
        .sort_values(["mean", "std"])
    )
    best_by_mean = summary.head(20).to_dict(orient="records")

    prior_selected = []
    test_years = sorted(frame["test_year"].unique())
    candidate_frame = frame[
        ~(
            (frame["model"] == "persistence")
            & (frame["feature_group"] == "none")
        )
    ].copy()
    candidate_frame = candidate_frame[~candidate_frame["feature_group"].str.contains("nowcast", na=False)].copy()
    key_cols = ["model", "residual_target", "feature_group", "lambda"]

    for test_year in test_years:
        if test_year == min(test_years):
            selected = {
                "model": "persistence",
                "residual_target": "none",
                "feature_group": "none",
                "lambda": 0.0,
            }
        else:
            prior = candidate_frame[candidate_frame["test_year"] < test_year]
            prior_summary = (
                prior.groupby(key_cols)["wmape"]
                .mean()
                .reset_index()
                .sort_values("wmape")
            )
            selected = prior_summary.iloc[0][key_cols].to_dict()

        mask = np.ones(len(frame), dtype=bool)
        mask &= frame["test_year"].eq(test_year).to_numpy()
        for col, value in selected.items():
            mask &= frame[col].eq(value).to_numpy()
        chosen_rows = frame[mask]
        if chosen_rows.empty:
            raise RuntimeError(f"No selected row for {test_year}: {selected}")
        chosen = chosen_rows.iloc[0]
        prior_selected.append(
            {
                "test_year": int(test_year),
                "selected_model": str(chosen["model"]),
                "selected_residual_target": str(chosen["residual_target"]),
                "selected_feature_group": str(chosen["feature_group"]),
                "selected_lambda": float(chosen["lambda"]),
                "test_wmape": float(chosen["wmape"]),
            }
        )

    return {
        "best_by_mean": best_by_mean,
        "causal_prior_selection": {
            "mean_wmape": float(np.mean([row["test_wmape"] for row in prior_selected])),
            "selected_runs": prior_selected,
            "methodology": (
                "For each test year after the first, select the model/residual/lambda "
                "with best mean WMAPE on earlier test years only. First year defaults to persistence."
            ),
        },
        "conservative_prior_selection": conservative_prior_selection(frame, candidate_frame, key_cols),
    }


def conservative_prior_selection(frame, candidate_frame, key_cols):
    test_years = sorted(frame["test_year"].unique())
    selected_rows = []
    min_prior_years = 2

    for test_year in test_years:
        prior_years = [year for year in test_years if year < test_year]
        if len(prior_years) < min_prior_years:
            selected = {
                "model": "ridge_level",
                "residual_target": "level",
                "feature_group": "lag_only",
                "lambda": 1.0,
            }
            reason = "default_until_two_prior_test_years_exist"
        else:
            prior = candidate_frame[candidate_frame["test_year"].isin(prior_years)]
            prior_summary = (
                prior.groupby(key_cols)["wmape"]
                .agg(["mean", "max"])
                .reset_index()
                .sort_values(["mean", "max"])
            )
            selected = prior_summary.iloc[0][key_cols].to_dict()
            reason = "best_prior_mean_with_prior_max_tiebreak"

        mask = np.ones(len(frame), dtype=bool)
        mask &= frame["test_year"].eq(test_year).to_numpy()
        for col, value in selected.items():
            mask &= frame[col].eq(value).to_numpy()
        chosen_rows = frame[mask]
        if chosen_rows.empty:
            raise RuntimeError(f"No conservative selected row for {test_year}: {selected}")
        chosen = chosen_rows.iloc[0]
        selected_rows.append(
            {
                "test_year": int(test_year),
                "selected_model": str(chosen["model"]),
                "selected_residual_target": str(chosen["residual_target"]),
                "selected_feature_group": str(chosen["feature_group"]),
                "selected_lambda": float(chosen["lambda"]),
                "test_wmape": float(chosen["wmape"]),
                "reason": reason,
            }
        )

    return {
        "mean_wmape": float(np.mean([row["test_wmape"] for row in selected_rows])),
        "selected_runs": selected_rows,
        "methodology": (
            "Use ridge_level lag-only until at least two prior test years exist. "
            "After that, select the forecast-safe model/residual/lambda with best prior mean WMAPE, "
            "using prior max WMAPE as tie-breaker. Nowcast groups are excluded."
        ),
    }


def evaluate_residual_baselines():
    panel, feature_groups = build_panel_and_feature_groups()
    rows, prediction_rows = residual_predictions(panel, feature_groups)
    summary = summarize(rows)
    output = {
        **summary,
        "all_runs": rows,
        "feature_groups": feature_groups,
        "methodology": (
            "Residual baselines predict corrections over persistence. Absolute residual uses "
            "y(t)-y(t-1); log residual uses log1p(y(t))-log1p(y(t-1)). Predictions are "
            "persistence + lambda * correction with lambda in [0, 0.1, 0.25, 0.5, 0.75, 1]."
        ),
    }

    os.makedirs(METRICS_PATH.parent, exist_ok=True)
    os.makedirs(PREDICTIONS_PATH.parent, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    pd.DataFrame(prediction_rows).to_csv(PREDICTIONS_PATH, index=False)

    print(json.dumps({
        "best_by_mean": output["best_by_mean"][:10],
        "causal_prior_selection": output["causal_prior_selection"],
        "conservative_prior_selection": output["conservative_prior_selection"],
    }, indent=2))
    print(f"Saved residual metrics to {METRICS_PATH}")
    print(f"Saved residual predictions to {PREDICTIONS_PATH}")


if __name__ == "__main__":
    evaluate_residual_baselines()
