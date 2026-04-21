import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
EDGES_PATH = ROOT / "data" / "processed" / "graph_edges_ze2020_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "gated_geo_linear_mixing_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "GATED_GEO_LINEAR_MIXING_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
LAG_ONLY_FEATURES = ["side_creations_lag_1"]
BASE_FEATURES = ["side_creations_lag_1", "nb_com"]
DEGREE_GATE_THRESHOLD = 9


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


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def load_tensor_package():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020"])
    edges = pd.read_csv(EDGES_PATH, usecols=["source_ze2020", "target_ze2020"])
    degree = pd.concat([edges["source_ze2020"], edges["target_ze2020"]]).value_counts()
    node_index["degree"] = node_index["ze2020"].map(degree).fillna(0).astype(int)
    degree_by_node_idx = node_index.sort_values("node_idx")["degree"].to_numpy()

    return {
        "years": package["years"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
        "adjacency_geo_raw": package["adjacency_geo"].astype(float),
        "adjacency_geo": normalize_rows(package["adjacency_geo"].astype(float)),
        "node_degree": degree_by_node_idx,
    }


def build_baseline_features(data, pos, feature_indices):
    return data["x_raw"][pos][:, feature_indices]


def build_gated_geo_features(data, pos, feature_indices):
    local = data["x_raw"][pos][:, feature_indices]
    spatial = data["adjacency_geo"] @ local
    gate = (data["node_degree"] < DEGREE_GATE_THRESHOLD).astype(float).reshape(-1, 1)
    spatial_gated = spatial * gate
    return np.concatenate([local, spatial_gated], axis=1)


def evaluate_ridge_feature_matrix(data, feature_builder, input_features, feature_labels):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in input_features]
    rows = []
    coefficients = {}

    for target_year in EVALUATION_TARGET_YEARS:
        test_pos = np.where(years == target_year)[0]
        if len(test_pos) != 1:
            continue
        test_pos = int(test_pos[0])
        train_pos = np.where(years < target_year)[0]
        if len(train_pos) == 0:
            continue

        y_train = data["y_raw"][train_pos].reshape(-1)
        y_test = data["y_raw"][test_pos]
        X_train_raw = np.concatenate(
            [feature_builder(data, int(pos), feature_indices) for pos in train_pos],
            axis=0,
        )
        X_test_raw = feature_builder(data, test_pos, feature_indices)

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test)
        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
        used_features = [name for name, ok in zip(feature_labels, valid) if ok]
        model = fit_ridge(X_train, y_train_valid)
        y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

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
            "alpha": float(model.alpha_),
            "coefficients": {name: float(value) for name, value in zip(used_features, model.coef_)},
            "intercept": float(model.intercept_),
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
        "# Gated Geo Linear Mixing v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester un dernier modèle spatial linéaire avec gate par degré du nœud.",
        "",
        f"Règle de gate : contribution spatiale active seulement si `degree < {DEGREE_GATE_THRESHOLD}`.",
        "",
        "## Mean WMAPE",
        "",
        f"- `ridge_lag_only` : `{payload['ridge_lag_only']['summary']['mean_wmape']:.3f}`",
        f"- `ridge_lag_nbcom` : `{payload['ridge_lag_nbcom']['summary']['mean_wmape']:.3f}`",
        f"- `gated_geo_linear_mixing` : `{payload['gated_geo_linear_mixing']['summary']['mean_wmape']:.3f}`",
        "",
        "## Comparaison contre ridge_lag_nbcom",
        "",
        f"- mean_delta : `{payload['comparisons']['vs_ridge_lag_nbcom']['mean_delta']:.3f}`",
        f"- worsened_years : `{payload['comparisons']['vs_ridge_lag_nbcom']['worsened_years']}`",
        f"- strictly_better : `{payload['comparisons']['vs_ridge_lag_nbcom']['strictly_better']}`",
        "",
        "## WMAPE par année",
        "",
        "| model | 2021 | 2022 | 2023 | 2024 |",
        "| :--- | ---: | ---: | ---: | ---: |",
        f"| ridge_lag_only | {payload['ridge_lag_only']['summary']['per_year_wmape']['2021']:.3f} | {payload['ridge_lag_only']['summary']['per_year_wmape']['2022']:.3f} | {payload['ridge_lag_only']['summary']['per_year_wmape']['2023']:.3f} | {payload['ridge_lag_only']['summary']['per_year_wmape']['2024']:.3f} |",
        f"| ridge_lag_nbcom | {payload['ridge_lag_nbcom']['summary']['per_year_wmape']['2021']:.3f} | {payload['ridge_lag_nbcom']['summary']['per_year_wmape']['2022']:.3f} | {payload['ridge_lag_nbcom']['summary']['per_year_wmape']['2023']:.3f} | {payload['ridge_lag_nbcom']['summary']['per_year_wmape']['2024']:.3f} |",
        f"| gated_geo_linear_mixing | {payload['gated_geo_linear_mixing']['summary']['per_year_wmape']['2021']:.3f} | {payload['gated_geo_linear_mixing']['summary']['per_year_wmape']['2022']:.3f} | {payload['gated_geo_linear_mixing']['summary']['per_year_wmape']['2023']:.3f} | {payload['gated_geo_linear_mixing']['summary']['per_year_wmape']['2024']:.3f} |",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()

    lag_rows, lag_coeffs = evaluate_ridge_feature_matrix(data, build_baseline_features, LAG_ONLY_FEATURES, LAG_ONLY_FEATURES)
    nbcom_rows, nbcom_coeffs = evaluate_ridge_feature_matrix(data, build_baseline_features, BASE_FEATURES, BASE_FEATURES)

    gated_labels = [
        "side_creations_lag_1",
        "nb_com",
        "gated_geo_neighbor_side_creations_lag_1",
        "gated_geo_neighbor_nb_com",
    ]
    gated_rows, gated_coeffs = evaluate_ridge_feature_matrix(data, build_gated_geo_features, BASE_FEATURES, gated_labels)

    lag_summary = summarize_rows(lag_rows)
    nbcom_summary = summarize_rows(nbcom_rows)
    gated_summary = summarize_rows(gated_rows)

    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "degree_gate_threshold": DEGREE_GATE_THRESHOLD,
        "nodes_below_threshold": int((data["node_degree"] < DEGREE_GATE_THRESHOLD).sum()),
        "nodes_at_or_above_threshold": int((data["node_degree"] >= DEGREE_GATE_THRESHOLD).sum()),
        "ridge_lag_only": {"rows": lag_rows, "summary": lag_summary, "coefficients": lag_coeffs},
        "ridge_lag_nbcom": {"rows": nbcom_rows, "summary": nbcom_summary, "coefficients": nbcom_coeffs},
        "gated_geo_linear_mixing": {"rows": gated_rows, "summary": gated_summary, "coefficients": gated_coeffs},
        "comparisons": {
            "vs_ridge_lag_only": compare(gated_summary, lag_summary),
            "vs_ridge_lag_nbcom": compare(gated_summary, nbcom_summary),
        },
    }

    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
