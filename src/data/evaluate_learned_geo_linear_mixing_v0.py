import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "learned_geo_linear_mixing_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "LEARNED_GEO_LINEAR_MIXING_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
LAG_ONLY_FEATURES = ["side_creations_lag_1"]
BASE_FEATURES = ["side_creations_lag_1", "nb_com"]


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
        "adjacency_geo_raw": package["adjacency_geo"].astype(float),
        "adjacency_geo": normalize_rows(package["adjacency_geo"].astype(float)),
    }


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def build_baseline_features(data, test_pos, feature_indices):
    return data["x_raw"][test_pos][:, feature_indices]


def build_geo_mixed_features(data, pos, feature_indices):
    local = data["x_raw"][pos][:, feature_indices]
    spatial = data["adjacency_geo"] @ local
    return np.concatenate([local, spatial], axis=1)


def evaluate_ridge_feature_matrix(data, feature_builder, input_features, feature_labels):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in input_features]
    rows = []
    predictions = {}
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
        predictions[int(target_year)] = y_pred
        coefficients[str(target_year)] = {
            "alpha": float(model.alpha_),
            "coefficients": {name: float(value) for name, value in zip(used_features, model.coef_)},
            "intercept": float(model.intercept_),
        }

    return rows, predictions, coefficients


def summarize_rows(rows):
    return {
        "mean_wmape": float(np.mean([row["wmape"] for row in rows])),
        "max_wmape": float(np.max([row["wmape"] for row in rows])),
        "per_year_wmape": {str(row["target_year"]): float(row["wmape"]) for row in rows},
    }


def compare_to_reference(candidate_summary, reference_summary):
    deltas = {}
    worsened_years = []
    for year, ref_wmape in reference_summary["per_year_wmape"].items():
        candidate_wmape = candidate_summary["per_year_wmape"][year]
        delta = candidate_wmape - ref_wmape
        deltas[year] = float(delta)
        if delta > 0:
            worsened_years.append(int(year))
    mean_delta = candidate_summary["mean_wmape"] - reference_summary["mean_wmape"]
    return {
        "mean_delta": float(mean_delta),
        "per_year_delta": deltas,
        "worsened_years": worsened_years,
        "strictly_better": bool(mean_delta < 0 and len(worsened_years) == 0),
    }


def write_report(payload):
    baseline_lag = payload["ridge_lag_only"]["summary"]
    baseline_nbcom = payload["ridge_lag_nbcom"]["summary"]
    model = payload["learned_geo_linear_mixing"]["summary"]
    cmp_lag = payload["comparisons"]["vs_ridge_lag_only"]
    cmp_nbcom = payload["comparisons"]["vs_ridge_lag_nbcom"]

    lines = [
        "# Learned Geo Linear Mixing v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester le premier modèle spatial appris minimal, sans stack neuronale.",
        "",
        "Le modèle ajoute au bloc local `side_creations_lag_1 + nb_com` leurs versions agrégées par voisinage géographique normalisé, puis ajuste un `Ridge` sur l'ensemble.",
        "",
        "## Blocs comparés",
        "",
        f"- `ridge_lag_only` : `{baseline_lag['mean_wmape']:.3f}`",
        f"- `ridge_lag_nbcom` : `{baseline_nbcom['mean_wmape']:.3f}`",
        f"- `learned_geo_linear_mixing` : `{model['mean_wmape']:.3f}`",
        "",
        "## Features du modèle appris",
        "",
        "- `side_creations_lag_1`",
        "- `nb_com`",
        "- `geo_neighbor_side_creations_lag_1`",
        "- `geo_neighbor_nb_com`",
        "",
        "## Comparaison contre ridge_lag_only",
        "",
        f"- mean_delta : `{cmp_lag['mean_delta']:.3f}`",
        f"- worsened_years : `{cmp_lag['worsened_years']}`",
        f"- strictly_better : `{cmp_lag['strictly_better']}`",
        "",
        "## Comparaison contre ridge_lag_nbcom",
        "",
        f"- mean_delta : `{cmp_nbcom['mean_delta']:.3f}`",
        f"- worsened_years : `{cmp_nbcom['worsened_years']}`",
        f"- strictly_better : `{cmp_nbcom['strictly_better']}`",
        "",
        "## WMAPE par année",
        "",
        "| model | 2021 | 2022 | 2023 | 2024 |",
        "| :--- | ---: | ---: | ---: | ---: |",
        f"| ridge_lag_only | {baseline_lag['per_year_wmape']['2021']:.3f} | {baseline_lag['per_year_wmape']['2022']:.3f} | {baseline_lag['per_year_wmape']['2023']:.3f} | {baseline_lag['per_year_wmape']['2024']:.3f} |",
        f"| ridge_lag_nbcom | {baseline_nbcom['per_year_wmape']['2021']:.3f} | {baseline_nbcom['per_year_wmape']['2022']:.3f} | {baseline_nbcom['per_year_wmape']['2023']:.3f} | {baseline_nbcom['per_year_wmape']['2024']:.3f} |",
        f"| learned_geo_linear_mixing | {model['per_year_wmape']['2021']:.3f} | {model['per_year_wmape']['2022']:.3f} | {model['per_year_wmape']['2023']:.3f} | {model['per_year_wmape']['2024']:.3f} |",
        "",
        "## Décision",
        "",
        "Ce test ne prouve pas encore la valeur d'un GNN. Il vérifie seulement si une transformation spatiale apprise minimale à partir du graphe géographique dépasse les meilleures références tabulaires courtes.",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()

    baseline_rows_lag, _, coeffs_lag = evaluate_ridge_feature_matrix(
        data,
        build_baseline_features,
        LAG_ONLY_FEATURES,
        LAG_ONLY_FEATURES,
    )
    geo_feature_labels = ["side_creations_lag_1", "nb_com", "geo_neighbor_side_creations_lag_1", "geo_neighbor_nb_com"]
    baseline_summary_lag = summarize_rows(baseline_rows_lag)

    baseline_rows_nbcom, _, coeffs_nbcom = evaluate_ridge_feature_matrix(
        data,
        build_baseline_features,
        BASE_FEATURES,
        BASE_FEATURES,
    )
    baseline_summary_nbcom = summarize_rows(baseline_rows_nbcom)

    geo_rows, _, geo_coeffs = evaluate_ridge_feature_matrix(
        data,
        build_geo_mixed_features,
        BASE_FEATURES,
        geo_feature_labels,
    )
    geo_summary = summarize_rows(geo_rows)

    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "adjacency_checks": {
            "geo_raw_row_sum_min": float(data["adjacency_geo_raw"].sum(axis=1).min()),
            "geo_raw_row_sum_max": float(data["adjacency_geo_raw"].sum(axis=1).max()),
            "geo_norm_row_sum_min": float(data["adjacency_geo"].sum(axis=1).min()),
            "geo_norm_row_sum_max": float(data["adjacency_geo"].sum(axis=1).max()),
        },
        "ridge_lag_only": {
            "feature_set": LAG_ONLY_FEATURES,
            "rows": baseline_rows_lag,
            "summary": baseline_summary_lag,
            "coefficients": coeffs_lag,
        },
        "ridge_lag_nbcom": {
            "feature_set": BASE_FEATURES,
            "rows": baseline_rows_nbcom,
            "summary": baseline_summary_nbcom,
            "coefficients": coeffs_nbcom,
        },
        "learned_geo_linear_mixing": {
            "feature_set": geo_feature_labels,
            "rows": geo_rows,
            "summary": geo_summary,
            "coefficients": geo_coeffs,
        },
        "comparisons": {
            "vs_ridge_lag_only": compare_to_reference(geo_summary, baseline_summary_lag),
            "vs_ridge_lag_nbcom": compare_to_reference(geo_summary, baseline_summary_nbcom),
        },
    }

    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
