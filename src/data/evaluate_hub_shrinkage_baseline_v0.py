import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "hub_shrinkage_baseline_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "HUB_SHRINKAGE_BASELINE_V0.md"

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


def build_ridge_predictions(data):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in FEATURES]
    lag_idx = feature_names.index("side_creations_lag_1")
    rows = []
    year_payload = {}

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
        X_test_raw_valid = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]
        lag_test_valid = lag_test[test_valid]

        X_train, X_test, _ = scale_and_impute_from_train(X_train_raw, X_test_raw_valid)
        model = fit_ridge(X_train, y_train_valid)
        ridge_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        hub_threshold = float(np.quantile(y_train_valid, HUB_QUANTILE))
        hub_mask = lag_test_valid >= hub_threshold

        year_payload[int(target_year)] = {
            "y_true": y_test_valid,
            "ridge_pred": ridge_pred,
            "lag": lag_test_valid,
            "hub_mask": hub_mask,
            "hub_threshold": hub_threshold,
        }
        rows.append({"target_year": int(target_year), "model": "ridge_lag_nbcom", "wmape": wmape(y_test_valid, ridge_pred)})

    return rows, year_payload


def select_gamma_causally(year_payload):
    trace = []
    for target_year in EVALUATION_TARGET_YEARS:
        prior_years = [year for year in EVALUATION_TARGET_YEARS if year < target_year]
        if not prior_years:
            trace.append({"target_year": int(target_year), "selected_gamma": 1.0, "reason": "default_no_prior_years"})
            continue

        best_gamma = None
        best_score = None
        for gamma in GAMMA_GRID:
            scores = []
            for year in prior_years:
                payload = year_payload[year]
                adjusted = payload["ridge_pred"].copy()
                mask = payload["hub_mask"]
                adjusted[mask] = payload["lag"][mask] + gamma * (payload["ridge_pred"][mask] - payload["lag"][mask])
                scores.append(wmape(payload["y_true"], adjusted))
            score = float(np.mean(scores))
            if best_score is None or score < best_score:
                best_score = score
                best_gamma = gamma
        trace.append(
            {
                "target_year": int(target_year),
                "selected_gamma": float(best_gamma),
                "reason": "best_prior_year_mean_wmape",
                "prior_years": prior_years,
                "prior_mean_wmape": float(best_score),
            }
        )
    return trace


def evaluate_shrinkage(year_payload, gamma_trace):
    rows = []
    for item in gamma_trace:
        year = item["target_year"]
        gamma = item["selected_gamma"]
        payload = year_payload[year]
        adjusted = payload["ridge_pred"].copy()
        mask = payload["hub_mask"]
        adjusted[mask] = payload["lag"][mask] + gamma * (payload["ridge_pred"][mask] - payload["lag"][mask])
        rows.append(
            {
                "target_year": int(year),
                "model": "hub_shrinkage_baseline",
                "wmape": wmape(payload["y_true"], adjusted),
                "selected_gamma": float(gamma),
                "hub_threshold": float(payload["hub_threshold"]),
                "hub_share": float(np.mean(mask)),
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
    shrink = payload["summary"]["hub_shrinkage_baseline"]
    cmp = payload["comparison_vs_ridge_lag_nbcom"]
    lines = [
        "# Hub Shrinkage Baseline v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester un ajustement causal minimal pour les grands hubs, afin de corriger la sur-prédiction observée en 2022–2023.",
        "",
        f"Règle hub : zones avec `side_creations_lag_1` au-dessus du quantile `{HUB_QUANTILE}` du train.",
        "Ajustement : pour les hubs, rapprocher la prédiction ridge du lag observé avec un coefficient `gamma` choisi causalement sur les années précédentes.",
        "",
        "## Mean WMAPE",
        "",
        f"- `ridge_lag_nbcom` : `{ridge['mean_wmape']:.3f}`",
        f"- `hub_shrinkage_baseline` : `{shrink['mean_wmape']:.3f}`",
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
    ridge_rows, year_payload = build_ridge_predictions(data)
    gamma_trace = select_gamma_causally(year_payload)
    shrink_rows = evaluate_shrinkage(year_payload, gamma_trace)
    all_rows = ridge_rows + shrink_rows
    summary = summarize(all_rows)
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "hub_quantile": HUB_QUANTILE,
        "gamma_grid": GAMMA_GRID,
        "gamma_trace": gamma_trace,
        "rows": all_rows,
        "summary": summary,
        "comparison_vs_ridge_lag_nbcom": compare(summary["hub_shrinkage_baseline"], summary["ridge_lag_nbcom"]),
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
