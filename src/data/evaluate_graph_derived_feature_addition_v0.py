import itertools
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "graph_derived_feature_addition_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "GRAPH_DERIVED_FEATURE_ADDITION_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
BASE_FEATURE_SET = ["side_creations_lag_1", "nb_com"]
GRAPH_DERIVED_FEATURES = [
    "side_creations_spatial_lag_1",
    "side_creations_mobility_lag_1",
]


def wmape(y_true, y_pred):
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100)


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
    }


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def evaluate_feature_set(data, feature_set):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in feature_set]
    rows = []

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
        X_train_raw = data["x_raw"][train_pos][:, :, feature_indices].reshape(-1, len(feature_indices))
        X_test_raw = data["x_raw"][test_pos][:, feature_indices]

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test)
        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
        used_features = [name for name, ok in zip(feature_set, valid) if ok]
        if not used_features:
            continue

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

    return rows


def summarize_rows(rows):
    per_year = {row["target_year"]: row["wmape"] for row in rows}
    return {
        "mean_wmape": float(np.mean([row["wmape"] for row in rows])),
        "max_wmape": float(np.max([row["wmape"] for row in rows])),
        "per_year_wmape": per_year,
    }


def compare(candidate_summary, baseline_summary):
    deltas = {}
    worsened_years = []

    for year, baseline_wmape in baseline_summary["per_year_wmape"].items():
        candidate_wmape = candidate_summary["per_year_wmape"][year]
        delta = candidate_wmape - baseline_wmape
        deltas[str(year)] = float(delta)
        if delta > 0:
            worsened_years.append(int(year))

    mean_delta = candidate_summary["mean_wmape"] - baseline_summary["mean_wmape"]
    return {
        "mean_delta": float(mean_delta),
        "per_year_delta": deltas,
        "worsened_years": worsened_years,
        "strictly_better": bool(mean_delta < 0 and len(worsened_years) == 0),
    }


def build_reference(data):
    rows = evaluate_feature_set(data, BASE_FEATURE_SET)
    summary = summarize_rows(rows)
    return {
        "name": "ridge_lag_nbcom",
        "feature_set": BASE_FEATURE_SET,
        "rows": rows,
        "summary": summary,
    }


def evaluate_candidates(data):
    baseline = build_reference(data)
    single_feature_results = []

    for feature in GRAPH_DERIVED_FEATURES:
        feature_set = BASE_FEATURE_SET + [feature]
        rows = evaluate_feature_set(data, feature_set)
        summary = summarize_rows(rows)
        single_feature_results.append(
            {
                "name": "+".join(feature_set),
                "feature_set": feature_set,
                "rows": rows,
                "summary": summary,
                "comparison_vs_ridge_lag_nbcom": compare(summary, baseline["summary"]),
            }
        )

    combo_results = []
    for combo in itertools.combinations(GRAPH_DERIVED_FEATURES, 2):
        feature_set = BASE_FEATURE_SET + list(combo)
        rows = evaluate_feature_set(data, feature_set)
        summary = summarize_rows(rows)
        combo_results.append(
            {
                "name": "+".join(feature_set),
                "feature_set": feature_set,
                "rows": rows,
                "summary": summary,
                "comparison_vs_ridge_lag_nbcom": compare(summary, baseline["summary"]),
            }
        )

    single_feature_results = sorted(single_feature_results, key=lambda item: item["summary"]["mean_wmape"])
    combo_results = sorted(combo_results, key=lambda item: item["summary"]["mean_wmape"])
    return baseline, single_feature_results, combo_results


def write_report(baseline, single_feature_results, combo_results):
    lines = [
        "# Graph-Derived Feature Addition v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester si les variables déjà dérivées du graphe dans le tenseur peuvent améliorer `ridge_lag_nbcom` comme covariables tabulaires, avant tout modèle de graphe plus complexe.",
        "",
        "## Baseline de référence",
        "",
        f"- Modèle : `{baseline['name']}`",
        f"- Variables : `{baseline['feature_set']}`",
        f"- Mean WMAPE : `{baseline['summary']['mean_wmape']:.3f}`",
        "",
        "## Ajouts unitaires dérivés du graphe",
        "",
        "| candidate | mean_wmape | mean_delta | worsened_years | strictly_better |",
        "| :--- | ---: | ---: | :--- | :---: |",
    ]

    for item in single_feature_results:
        cmp = item["comparison_vs_ridge_lag_nbcom"]
        lines.append(
            f"| {item['feature_set'][-1]} | {item['summary']['mean_wmape']:.3f} | {cmp['mean_delta']:.3f} | {cmp['worsened_years']} | {cmp['strictly_better']} |"
        )

    lines.extend(
        [
            "",
            "## Combinaison courte",
            "",
            "| feature_set | mean_wmape | mean_delta | worsened_years | strictly_better |",
            "| :--- | ---: | ---: | :--- | :---: |",
        ]
    )

    for item in combo_results:
        cmp = item["comparison_vs_ridge_lag_nbcom"]
        lines.append(
            f"| {item['feature_set']} | {item['summary']['mean_wmape']:.3f} | {cmp['mean_delta']:.3f} | {cmp['worsened_years']} | {cmp['strictly_better']} |"
        )

    lines.extend(
        [
            "",
            "## Décision",
            "",
            "Ce rapport ne teste pas encore une architecture de graphe. Il vérifie seulement si les lags agrégés par voisinage ou mobilité ont une valeur incrémentale comme covariables tabulaires au-dessus du meilleur baseline temporel court.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    baseline, single_feature_results, combo_results = evaluate_candidates(data)
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "baseline": baseline,
        "single_feature_results": single_feature_results,
        "combination_results": combo_results,
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(baseline, single_feature_results, combo_results)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
