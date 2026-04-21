import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "causal_segmented_hub_baseline_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "CAUSAL_SEGMENTED_HUB_BASELINE_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
FEATURES = ["side_creations_lag_1", "nb_com"]
HUB_QUANTILE = 0.67
GAMMA_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
MOMENTUM_THRESHOLDS = [-0.10, -0.05, -0.02, 0.0]


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


def build_payload(data):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in FEATURES]
    lag_idx = feature_names.index("side_creations_lag_1")
    payload = {}

    for target_year in EVALUATION_TARGET_YEARS:
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

        if test_pos > 0:
            prev_lag = data["x_raw"][test_pos - 1, :, lag_idx]
            prev_lag_valid = prev_lag[test_valid]
            recent_momentum = np.where(np.abs(prev_lag_valid) > 0, (lag_test_valid - prev_lag_valid) / prev_lag_valid, np.nan)
        else:
            recent_momentum = np.full_like(lag_test_valid, np.nan, dtype=float)

        payload[int(target_year)] = {
            "y_true": y_test_valid,
            "ridge_pred": ridge_pred,
            "lag": lag_test_valid,
            "hub_mask": hub_mask,
            "hub_threshold": hub_threshold,
            "recent_momentum": recent_momentum,
        }
    return payload


def apply_rule(item, gamma, momentum_threshold):
    pred = item["ridge_pred"].copy()
    target_mask = item["hub_mask"] & np.isfinite(item["recent_momentum"]) & (item["recent_momentum"] <= momentum_threshold)
    pred[target_mask] = item["lag"][target_mask] + gamma * (item["ridge_pred"][target_mask] - item["lag"][target_mask])
    return pred, target_mask


def select_rule_causally(payload):
    trace = []
    years = sorted(payload.keys())
    for target_year in years:
        prior_years = [year for year in years if year < target_year]
        if not prior_years:
            trace.append(
                {
                    "target_year": int(target_year),
                    "selected_gamma": 1.0,
                    "selected_momentum_threshold": 0.0,
                    "reason": "default_no_prior_years",
                }
            )
            continue

        best = None
        for momentum_threshold in MOMENTUM_THRESHOLDS:
            for gamma in GAMMA_GRID:
                scores = []
                for year in prior_years:
                    pred, _ = apply_rule(payload[year], gamma, momentum_threshold)
                    scores.append(wmape(payload[year]["y_true"], pred))
                score = float(np.mean(scores))
                candidate = (score, -momentum_threshold, -gamma, momentum_threshold, gamma)
                if best is None or candidate < best:
                    best = candidate

        score, _, _, momentum_threshold, gamma = best
        trace.append(
            {
                "target_year": int(target_year),
                "selected_gamma": float(gamma),
                "selected_momentum_threshold": float(momentum_threshold),
                "reason": "best_prior_year_mean_wmape",
                "prior_years": prior_years,
                "prior_mean_wmape": float(score),
            }
        )
    return trace


def summarize(rows):
    out = {}
    for model in sorted({row["model"] for row in rows}):
        model_rows = [row for row in rows if row["model"] == model]
        out[model] = {
            "mean_wmape": float(np.mean([row["wmape"] for row in model_rows])),
            "max_wmape": float(np.max([row["wmape"] for row in model_rows])),
            "per_year_wmape": {str(row["target_year"]): float(row["wmape"]) for row in model_rows},
        }
    return out


def compare(candidate_summary, baseline_summary):
    deltas = {}
    worsened_years = []
    for year, baseline_wmape in baseline_summary["per_year_wmape"].items():
        candidate_wmape = candidate_summary["per_year_wmape"][year]
        delta = candidate_wmape - baseline_wmape
        deltas[year] = float(delta)
        if delta > 0:
            worsened_years.append(int(year))
    mean_delta = candidate_summary["mean_wmape"] - baseline_summary["mean_wmape"]
    return {
        "mean_delta": float(mean_delta),
        "per_year_delta": deltas,
        "worsened_years": worsened_years,
        "strictly_better": bool(mean_delta < 0 and len(worsened_years) == 0),
    }


def write_report(payload):
    baseline = payload["summary"]["ridge_lag_nbcom"]
    candidate = payload["summary"]["causal_segmented_hub_baseline"]
    cmp = payload["comparison_vs_ridge_lag_nbcom"]
    lines = [
        "# Causal Segmented Hub Baseline v0",
        "",
        "Date : 2026-04-21",
        "",
        "Shrinkage applique uniquement aux hubs dont le momentum recent observe avant l'annee cible est sous un seuil causalement choisi.",
        "",
        f"- ridge_lag_nbcom: `{baseline['mean_wmape']:.3f}`",
        f"- causal_segmented_hub_baseline: `{candidate['mean_wmape']:.3f}`",
        f"- mean_delta: `{cmp['mean_delta']:.3f}`",
        f"- worsened_years: `{cmp['worsened_years']}`",
        f"- strictly_better: `{cmp['strictly_better']}`",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    payload = build_payload(load_tensor_package())
    trace = select_rule_causally(payload)

    rows = []
    for year, item in payload.items():
        rows.append({"target_year": int(year), "model": "ridge_lag_nbcom", "wmape": wmape(item["y_true"], item["ridge_pred"])})
    for rule in trace:
        year = rule["target_year"]
        pred, active_mask = apply_rule(payload[year], rule["selected_gamma"], rule["selected_momentum_threshold"])
        rows.append(
            {
                "target_year": int(year),
                "model": "causal_segmented_hub_baseline",
                "wmape": wmape(payload[year]["y_true"], pred),
                "selected_gamma": float(rule["selected_gamma"]),
                "selected_momentum_threshold": float(rule["selected_momentum_threshold"]),
                "active_share": float(np.mean(active_mask)),
                "hub_share": float(np.mean(payload[year]["hub_mask"])),
            }
        )

    summary = summarize(rows)
    result = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "hub_quantile": HUB_QUANTILE,
        "gamma_grid": GAMMA_GRID,
        "momentum_thresholds": MOMENTUM_THRESHOLDS,
        "rule_trace": trace,
        "rows": rows,
        "summary": summary,
        "comparison_vs_ridge_lag_nbcom": compare(summary["causal_segmented_hub_baseline"], summary["ridge_lag_nbcom"]),
    }
    METRICS_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
