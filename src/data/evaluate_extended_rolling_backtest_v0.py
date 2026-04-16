import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, RidgeCV
import json
import os

def wmape(y_true, y_pred):
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100

def scale_and_impute_from_train(X_train_raw, X_test_raw):
    """Fit mean/std on observed training values only; missing values become train mean."""
    X_train_scaled = np.zeros_like(X_train_raw, dtype=float)
    X_test_scaled = np.zeros_like(X_test_raw, dtype=float)

    for i in range(X_train_raw.shape[1]):
        train_feat = X_train_raw[:, i]
        test_feat = X_test_raw[:, i]
        observed_train = train_feat[np.isfinite(train_feat)]

        if len(observed_train) == 0:
            continue

        mean = observed_train.mean()
        std = observed_train.std()
        if std == 0:
            std = 1.0

        X_train_scaled[:, i] = np.where(np.isfinite(train_feat), (train_feat - mean) / std, 0.0)
        X_test_scaled[:, i] = np.where(np.isfinite(test_feat), (test_feat - mean) / std, 0.0)

    return X_train_scaled, X_test_scaled

def run_rigorous_rolling_backtest():
    tensor_path = 'data/processed/stgnn_tensor_package_extended_nowcast_q1_core_v1.npz'
    output_metrics_path = 'reports/extended_rolling_backtest_metrics_v0.json'

    data = np.load(tensor_path, allow_pickle=True)
    x_raw = data['x_raw']
    y_raw = data['y_raw']
    feature_names = list(data['feature_name'])
    years = list(data['years'])

    # Models to test on VOLUME
    models_volume = {
        "persistence": None,
        "ridge_lag_only": ["side_creations_lag_1"],
        "ridge_stock_lag": ["side_creations_lag_1", "stock_lag_1"],
        "ridge_sitadel_lag": [
            "side_creations_lag_1",
            "sitadel_surface_autorisee_lag_1",
            "sitadel_surface_commencee_lag_1",
        ],
        "ridge_spatial_lag_geo": ["side_creations_lag_1", "side_creations_spatial_lag_1"],
        "ridge_spatial_lag_mobility": ["side_creations_lag_1", "side_creations_mobility_lag_1"],
        "ridge_forecast": [
            "side_creations_lag_1",
            "stock_lag_1",
            "pop_lag_2",
            "regime_signal_lag_1",
            "sitadel_surface_autorisee_lag_1",
            "sitadel_surface_commencee_lag_1",
        ],
        "ridge_nowcast_q1": [
            "side_creations_lag_1",
            "stock_lag_1",
            "pop_lag_2",
            "regime_signal_jan_mar",
            "sitadel_surface_autorisee_lag_1",
            "sitadel_surface_commencee_lag_1",
        ],
    }

    test_years = [2021, 2022, 2023, 2024]
    alphas = np.logspace(-3, 5, 20)

    backtest_results = []

    for test_yr in test_years:
        print(f"Testing Year: {test_yr}")
        train_yr_indices = [i for i, y in enumerate(years) if y < test_yr]
        test_yr_idx = years.index(test_yr)

        Y_test_volume = y_raw[test_yr_idx]

        # 1. Persistence
        Y_prev = y_raw[test_yr_idx - 1]
        backtest_results.append({
            "test_year": int(test_yr),
            "model": "persistence",
            "wmape": float(wmape(Y_test_volume, Y_prev))
        })

        # 2. Volume Models
        for name, features in models_volume.items():
            if name == "persistence": continue
            f_indices = [feature_names.index(f) for f in features]

            X_train_raw = x_raw[train_yr_indices][:, :, f_indices].reshape(-1, len(f_indices))
            Y_train = y_raw[train_yr_indices].flatten()
            X_test_raw = x_raw[test_yr_idx][:, f_indices]
            X_train_scaled, X_test_scaled = scale_and_impute_from_train(X_train_raw, X_test_raw)

            model = RidgeCV(alphas=alphas)
            model.fit(X_train_scaled, Y_train)
            Y_pred = model.predict(X_test_scaled)

            backtest_results.append({
                "test_year": int(test_yr),
                "model": name,
                "wmape": float(wmape(Y_test_volume, Y_pred))
            })

    df_results = pd.DataFrame(backtest_results)
    summary = df_results.groupby("model")["wmape"].mean().to_dict()

    full_output = {
        "summary_mean_wmape": summary,
        "detail_by_year": df_results.pivot(index='test_year', columns='model', values='wmape').to_dict(),
        "all_runs": backtest_results,
        "methodology": "Per-fold scaling and mean-imputation fitted only on years before each test year."
    }

    os.makedirs(os.path.dirname(output_metrics_path), exist_ok=True)
    with open(output_metrics_path, 'w') as f:
        json.dump(full_output, f, indent=4)

    print("\n### Rigorous Rolling Backtest (Spatial Geo vs Mobility) 2021-2024 ###")
    for m, val in sorted(summary.items(), key=lambda x: x[1]):
        print(f"{m:25}: {val:.4f}")

if __name__ == "__main__":
    run_rigorous_rolling_backtest()
