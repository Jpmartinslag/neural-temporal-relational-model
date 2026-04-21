import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.neural_network import MLPRegressor


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "minimal_nonlinear_geo_mixing_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "MINIMAL_NONLINEAR_GEO_MIXING_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
LAG_ONLY_FEATURES = ["side_creations_lag_1"]
BASE_FEATURES = ["side_creations_lag_1", "nb_com"]
NONLINEAR_GEO_FEATURES = [
    "side_creations_lag_1",
    "nb_com",
    "geo_neighbor_side_creations_lag_1",
    "geo_neighbor_nb_com",
]


def wmape(y_true, y_pred):
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def normalize_rows(matrix):
    row_sums = matrix.sum(axis=1, keepdims=True)
    safe_denominator = np.where(row_sums > 0, row_sums, 1.0)
    normalized = matrix / safe_denominator
    normalized[row_sums.squeeze() == 0] = 0.0
    return normalized


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


def load_tensor_package():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    return {
        "years": package["years"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
        "adjacency_geo": normalize_rows(package["adjacency_geo"].astype(float)),
    }


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def fit_small_mlp(X_train, y_train):
    y_mean = float(np.mean(y_train))
    y_std = float(np.std(y_train))
    if y_std == 0:
        y_std = 1.0
    y_train_scaled = (y_train - y_mean) / y_std

    model = MLPRegressor(
        hidden_layer_sizes=(8,),
        activation="tanh",
        solver="lbfgs",
        alpha=1e-2,
        max_iter=2000,
        random_state=0,
    )
    model.fit(X_train, y_train_scaled)
    return model, y_mean, y_std


def build_baseline_features(data, pos, feature_indices):
    return data["x_raw"][pos][:, feature_indices]


def build_geo_features(data, pos, feature_indices):
    local = data["x_raw"][pos][:, feature_indices]
    spatial = data["adjacency_geo"] @ local
    return np.concatenate([local, spatial], axis=1)


def evaluate_ridge(data, input_features):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in input_features]
    rows = []

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

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test)
        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]

        X_train, X_test, _ = scale_and_impute_from_train(X_train_raw, X_test_raw)
        model = fit_ridge(X_train, y_train_valid)
        y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)
        rows.append({"target_year": int(target_year), "wmape": wmape(y_test_valid, y_pred)})
    return rows


def evaluate_small_mlp_geo(data):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in BASE_FEATURES]
    rows = []
    coefficients = {}

    for target_year in EVALUATION_TARGET_YEARS:
        test_pos = np.where(years == target_year)[0]
        if len(test_pos) != 1:
            continue
        test_pos = int(test_pos[0])
        train_pos = np.where(years < target_year)[0]

        y_train = data["y_raw"][train_pos].reshape(-1)
        y_test = data["y_raw"][test_pos]
        X_train_raw = np.concatenate([build_geo_features(data, int(pos), feature_indices) for pos in train_pos], axis=0)
        X_test_raw = build_geo_features(data, test_pos, feature_indices)

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test)
        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
        used_features = [name for name, ok in zip(NONLINEAR_GEO_FEATURES, valid) if ok]
        model, y_mean, y_std = fit_small_mlp(X_train, y_train_valid)
        y_pred = model.predict(X_test) * y_std + y_mean
        y_pred = np.clip(y_pred, a_min=0, a_max=None)

        rows.append(
            {
                "target_year": int(target_year),
                "forecast_origin_year": int(target_year - 1),
                "features": used_features,
                "wmape": wmape(y_test_valid, y_pred),
                "actual_sum": float(np.sum(y_test_valid)),
                "prediction_sum": float(np.sum(y_pred)),
                "rows": int(len(y_test_valid)),
            }
        )
        coefficients[str(target_year)] = {
            "hidden_layer_sizes": [8],
            "activation": "tanh",
            "solver": "lbfgs",
            "alpha": 1e-2,
        }
    return rows, coefficients


def summarize_rows(rows):
    return {
        "mean_wmape": float(np.mean([row["wmape"] for row in rows])),
        "max_wmape": float(np.max([row["wmape"] for row in rows])),
        "per_year_wmape": {str(row["target_year"]): float(row["wmape"]) for row in rows},
    }


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
    lines = [
        "# Minimal Nonlinear Geo Mixing v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester un seul modèle spatial non linéaire minimal et léger après l'épuisement de la ligne spatiale linéaire.",
        "",
        "Architecture : MLP très petit sur quatre features :",
        "- `side_creations_lag_1`",
        "- `nb_com`",
        "- `geo_neighbor_side_creations_lag_1`",
        "- `geo_neighbor_nb_com`",
        "",
        "## Mean WMAPE",
        "",
        f"- `ridge_lag_only` : `{payload['ridge_lag_only']['summary']['mean_wmape']:.3f}`",
        f"- `ridge_lag_nbcom` : `{payload['ridge_lag_nbcom']['summary']['mean_wmape']:.3f}`",
        f"- `minimal_nonlinear_geo_mixing` : `{payload['minimal_nonlinear_geo_mixing']['summary']['mean_wmape']:.3f}`",
        "",
        "## Comparaison contre ridge_lag_nbcom",
        "",
        f"- mean_delta : `{payload['comparisons']['vs_ridge_lag_nbcom']['mean_delta']:.3f}`",
        f"- worsened_years : `{payload['comparisons']['vs_ridge_lag_nbcom']['worsened_years']}`",
        f"- strictly_better : `{payload['comparisons']['vs_ridge_lag_nbcom']['strictly_better']}`",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    lag_rows = evaluate_ridge(data, LAG_ONLY_FEATURES)
    nbcom_rows = evaluate_ridge(data, BASE_FEATURES)
    nonlinear_rows, nonlinear_meta = evaluate_small_mlp_geo(data)

    lag_summary = summarize_rows(lag_rows)
    nbcom_summary = summarize_rows(nbcom_rows)
    nonlinear_summary = summarize_rows(nonlinear_rows)

    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "ridge_lag_only": {"rows": lag_rows, "summary": lag_summary},
        "ridge_lag_nbcom": {"rows": nbcom_rows, "summary": nbcom_summary},
        "minimal_nonlinear_geo_mixing": {"rows": nonlinear_rows, "summary": nonlinear_summary, "model_meta": nonlinear_meta},
        "comparisons": {
            "vs_ridge_lag_only": compare(nonlinear_summary, lag_summary),
            "vs_ridge_lag_nbcom": compare(nonlinear_summary, nbcom_summary),
        },
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
