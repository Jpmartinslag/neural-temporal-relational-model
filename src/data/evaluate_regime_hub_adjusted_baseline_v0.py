import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "regime_hub_adjusted_baseline_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "REGIME_HUB_ADJUSTED_BASELINE_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
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


def build_ridge_payload(data):
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

        lag_sum = float(np.sum(lag_test_valid))
        if test_pos > 0:
            prev_lag = data["x_raw"][test_pos - 1, :, lag_idx]
            prev_lag = prev_lag[np.isfinite(prev_lag)]
            prev_lag_sum = float(np.sum(prev_lag))
            observed_lag_growth = (lag_sum - prev_lag_sum) / prev_lag_sum if prev_lag_sum != 0 else np.nan
        else:
            observed_lag_growth = np.nan

        payload[int(target_year)] = {
            "y_true": y_test_valid,
            "ridge_pred": ridge_pred,
            "lag": lag_test_valid,
            "hub_mask": hub_mask,
            "hub_threshold": hub_threshold,
            "observed_lag_growth": float(observed_lag_growth),
        }
    return payload


def apply_gamma(payload, gamma):
    pred = payload["ridge_pred"].copy()
    mask = payload["hub_mask"]
    pred[mask] = payload["lag"][mask] + gamma * (payload["ridge_pred"][mask] - payload["lag"][mask])
    return pred


def select_rule_causally(payload):
    trace = []
    for target_year in EVALUATION_TARGET_YEARS:
        prior_years = [year for year in EVALUATION_TARGET_YEARS if year < target_year]
        if not prior_years:
            trace.append(
                {
                    "target_year": int(target_year),
                    "selected_gamma_if_negative_growth": 1.0,
                    "reason": "default_no_prior_years",
                    "observed_lag_growth": payload[target_year]["observed_lag_growth"],
                }
            )
            continue

        candidate_years = [year for year in prior_years if payload[year]["observed_lag_growth"] < 0]
        if not candidate_years:
            trace.append(
                {
                    "target_year": int(target_year),
                    "selected_gamma_if_negative_growth": 1.0,
                    "reason": "no_negative_growth_in_prior_years",
                    "observed_lag_growth": payload[target_year]["observed_lag_growth"],
                }
            )
            continue

        best_gamma = None
        best_score = None
        for gamma in GAMMA_GRID:
            scores = []
            for year in candidate_years:
                pred = apply_gamma(payload[year], gamma)
                scores.append(wmape(payload[year]["y_true"], pred))
            score = float(np.mean(scores))
            if best_score is None or score < best_score:
                best_score = score
                best_gamma = gamma

        trace.append(
            {
                "target_year": int(target_year),
                "selected_gamma_if_negative_growth": float(best_gamma),
                "reason": "best_prior_negative_growth_years",
                "prior_negative_growth_years": candidate_years,
                "prior_mean_wmape": float(best_score),
                "observed_lag_growth": payload[target_year]["observed_lag_growth"],
            }
        )
    return trace


def evaluate_rule(payload, trace):
    rows = []
    for item in trace:
        year = item["target_year"]
        growth = payload[year]["observed_lag_growth"]
        gamma = 1.0 if not np.isfinite(growth) or growth >= 0 else item["selected_gamma_if_negative_growth"]
        pred = apply_gamma(payload[year], gamma)
        rows.append(
            {
                "target_year": int(year),
                "model": "regime_hub_adjusted_baseline",
                "wmape": wmape(payload[year]["y_true"], pred),
                "applied_gamma": float(gamma),
                "observed_lag_growth": float(growth),
                "hub_threshold": float(payload[year]["hub_threshold"]),
                "hub_share": float(np.mean(payload[year]["hub_mask"])),
            }
        )
    return rows


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
    ridge = payload["summary"]["ridge_lag_nbcom"]
    regime = payload["summary"]["regime_hub_adjusted_baseline"]
    cmp = payload["comparison_vs_ridge_lag_nbcom"]
    lines = [
        "# Regime Hub Adjusted Baseline v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester une règle causale simple : ne contracter les hubs que lorsque la croissance agrégée observée du lag devient négative.",
        "",
        "## Mean WMAPE",
        "",
        f"- `ridge_lag_nbcom` : `{ridge['mean_wmape']:.3f}`",
        f"- `regime_hub_adjusted_baseline` : `{regime['mean_wmape']:.3f}`",
        "",
        "## Comparaison contre ridge_lag_nbcom",
        "",
        f"- mean_delta : `{cmp['mean_delta']:.3f}`",
        f"- worsened_years : `{cmp['worsened_years']}`",
        f"- strictly_better : `{cmp['strictly_better']}`",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    payload = build_ridge_payload(data)
    ridge_rows = [{"target_year": year, "model": "ridge_lag_nbcom", "wmape": wmape(p["y_true"], p["ridge_pred"])} for year, p in payload.items()]
    trace = select_rule_causally(payload)
    regime_rows = evaluate_rule(payload, trace)
    all_rows = ridge_rows + regime_rows
    summary = summarize(all_rows)
    result = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "hub_quantile": HUB_QUANTILE,
        "gamma_grid": GAMMA_GRID,
        "regime_trace": trace,
        "rows": all_rows,
        "summary": summary,
        "comparison_vs_ridge_lag_nbcom": compare(summary["regime_hub_adjusted_baseline"], summary["ridge_lag_nbcom"]),
    }
    METRICS_OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
