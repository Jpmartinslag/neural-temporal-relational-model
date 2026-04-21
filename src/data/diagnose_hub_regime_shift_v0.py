import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "hub_regime_shift_diagnostic_v0.json"
REPORT_OUT = ROOT / "reports" / "HUB_REGIME_SHIFT_DIAGNOSTIC_V0.md"

YEARS = [2022, 2023, 2024]
FEATURES = ["side_creations_lag_1", "nb_com"]
HUB_QUANTILE = 0.67
GAMMA_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]


def wmape(y_true, y_pred):
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def scale_and_impute_from_train(X_train_raw, X_test_raw):
    X_train_scaled = np.zeros_like(X_train_raw, dtype=float)
    X_test_scaled = np.zeros_like(X_test_raw, dtype=float)
    valid = []
    for i in range(X_train_raw.shape[1]):
        train_col = X_train_raw[:, i]
        test_col = X_test_raw[:, i]
        observed_train = train_col[np.isfinite(train_col)]
        if len(observed_train) == 0:
            valid.append(False)
            continue
        mean = observed_train.mean()
        std = observed_train.std()
        if std == 0:
            std = 1.0
        X_train_scaled[:, i] = np.where(np.isfinite(train_col), (train_col - mean) / std, 0.0)
        X_test_scaled[:, i] = np.where(np.isfinite(test_col), (test_col - mean) / std, 0.0)
        valid.append(True)
    valid = np.array(valid, dtype=bool)
    return X_train_scaled[:, valid], X_test_scaled[:, valid], valid


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def load_tensor_package():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    return {
        "years": package["years"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
    }


def ridge_payload(data):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in FEATURES]
    lag_idx = feature_names.index("side_creations_lag_1")
    payload = {}

    for target_year in YEARS:
        test_pos = np.where(years == target_year)[0]
        if len(test_pos) != 1:
            continue
        test_pos = int(test_pos[0])
        train_pos = np.where(years < target_year)[0]

        y_train = data["y_raw"][train_pos].reshape(-1)
        y_test = data["y_raw"][test_pos]
        X_train_raw = data["x_raw"][train_pos][:, :, feature_indices].reshape(-1, len(feature_indices))
        X_test_raw = data["x_raw"][test_pos][:, feature_indices]
        lag_test = data["x_raw"][test_pos][:, lag_idx]

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test) & np.isfinite(lag_test)
        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]
        lag_test_valid = lag_test[test_valid]

        X_train, X_test, _ = scale_and_impute_from_train(X_train_raw, X_test_raw)
        model = fit_ridge(X_train, y_train_valid)
        ridge_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        hub_threshold = float(np.quantile(y_train_valid, HUB_QUANTILE))
        hub_mask = lag_test_valid >= hub_threshold

        payload[target_year] = {
            "y_true": y_test_valid,
            "ridge_pred": ridge_pred,
            "lag": lag_test_valid,
            "hub_mask": hub_mask,
            "hub_threshold": hub_threshold,
        }
    return payload


def select_gamma_causally(payload):
    trace = {}
    for target_year in YEARS:
        prior_years = [year for year in YEARS if year < target_year]
        if not prior_years:
            trace[target_year] = 1.0
            continue
        best_gamma = None
        best_score = None
        for gamma in GAMMA_GRID:
            scores = []
            for year in prior_years:
                p = payload[year]
                pred = p["ridge_pred"].copy()
                mask = p["hub_mask"]
                pred[mask] = p["lag"][mask] + gamma * (p["ridge_pred"][mask] - p["lag"][mask])
                scores.append(wmape(p["y_true"], pred))
            score = float(np.mean(scores))
            if best_score is None or score < best_score:
                best_score = score
                best_gamma = gamma
        trace[target_year] = best_gamma
    return trace


def summarize_subset(y_true, lag, ridge_pred):
    return {
        "rows": int(len(y_true)),
        "target_sum": float(np.sum(y_true)),
        "lag_sum": float(np.sum(lag)),
        "ridge_sum": float(np.sum(ridge_pred)),
        "mean_growth_vs_lag": float(np.mean(np.where(np.abs(lag) > 0, (y_true - lag) / lag, np.nan))),
        "ridge_wmape": float(wmape(y_true, ridge_pred)),
    }


def build_payload(payload, gamma_trace):
    out = {"hub_quantile": HUB_QUANTILE, "gamma_trace": gamma_trace, "years": {}}
    for year, p in payload.items():
        hub = p["hub_mask"]
        shrink_pred = p["ridge_pred"].copy()
        gamma = gamma_trace[year]
        shrink_pred[hub] = p["lag"][hub] + gamma * (p["ridge_pred"][hub] - p["lag"][hub])
        out["years"][str(year)] = {
            "hub_threshold": float(p["hub_threshold"]),
            "hub_share": float(np.mean(hub)),
            "all_zones": summarize_subset(p["y_true"], p["lag"], p["ridge_pred"]),
            "hub_zones": summarize_subset(p["y_true"][hub], p["lag"][hub], p["ridge_pred"][hub]),
            "non_hub_zones": summarize_subset(p["y_true"][~hub], p["lag"][~hub], p["ridge_pred"][~hub]),
            "hub_shrinkage_wmape": float(wmape(p["y_true"], shrink_pred)),
            "hub_shrinkage_delta_vs_ridge": float(wmape(p["y_true"], shrink_pred) - wmape(p["y_true"], p["ridge_pred"])),
        }
    return out


def write_report(payload):
    lines = [
        "# Hub Regime Shift Diagnostic v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Expliquer pourquoi le shrinkage des hubs aide fortement en 2023 mais casse 2024.",
        "",
        "| year | hub_share | all_growth_vs_lag | hub_growth_vs_lag | non_hub_growth_vs_lag | ridge_wmape | shrinkage_delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for year in ["2022", "2023", "2024"]:
        item = payload["years"][year]
        lines.append(
            f"| {year} | {item['hub_share']:.3f} | {item['all_zones']['mean_growth_vs_lag']:.3f} | {item['hub_zones']['mean_growth_vs_lag']:.3f} | {item['non_hub_zones']['mean_growth_vs_lag']:.3f} | {item['all_zones']['ridge_wmape']:.3f} | {item['hub_shrinkage_delta_vs_ridge']:.3f} |"
        )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    payload = ridge_payload(data)
    gamma_trace = select_gamma_causally(payload)
    result = build_payload(payload, gamma_trace)
    METRICS_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
