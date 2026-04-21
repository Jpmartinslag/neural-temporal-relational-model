import itertools
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "temporal_feature_addition_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "TEMPORAL_FEATURE_ADDITION_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
BASE_FEATURE = "side_creations_lag_1"
CANDIDATE_FEATURES = [
    "stock_lag_1",
    "total_establishments",
    "nb_com",
    "pop_lag_1",
    "pop_lag_2",
    "regime_signal_lag_1",
    "sitadel_surface_autorisee_lag_1",
    "sitadel_surface_commencee_lag_1",
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
    target_years = years
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in feature_set]
    rows = []

    for target_year in EVALUATION_TARGET_YEARS:
        test_pos = np.where(target_years == target_year)[0]
        if len(test_pos) != 1:
            continue
        test_pos = int(test_pos[0])
        train_pos = np.where(target_years < target_year)[0]
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


def build_baseline_reference(data):
    rows = evaluate_feature_set(data, [BASE_FEATURE])
    summary = summarize_rows(rows)
    return {
        "name": "ridge_lag_only",
        "feature_set": [BASE_FEATURE],
        "rows": rows,
        "summary": summary,
    }


def compare_to_baseline(candidate_summary, baseline_summary):
    deltas = {}
    worsened_years = []
    improved_years = []
    for year, baseline_wmape in baseline_summary["per_year_wmape"].items():
        candidate_wmape = candidate_summary["per_year_wmape"][year]
        delta = candidate_wmape - baseline_wmape
        deltas[str(year)] = float(delta)
        if delta > 0:
            worsened_years.append(int(year))
        elif delta < 0:
            improved_years.append(int(year))

    mean_delta = candidate_summary["mean_wmape"] - baseline_summary["mean_wmape"]
    max_yearly_degradation = max(deltas.values()) if deltas else 0.0
    return {
        "mean_delta_vs_ridge_lag_only": float(mean_delta),
        "per_year_delta_vs_ridge_lag_only": deltas,
        "improved_years": improved_years,
        "worsened_years": worsened_years,
        "max_yearly_degradation": float(max_yearly_degradation),
        "accepted_strict": bool(mean_delta < 0 and len(worsened_years) == 0),
        "accepted_soft": bool(mean_delta < 0 and max_yearly_degradation <= 0.25),
    }


def evaluate_candidates(data):
    baseline = build_baseline_reference(data)
    candidate_results = []

    for feature in CANDIDATE_FEATURES:
        feature_set = [BASE_FEATURE, feature]
        rows = evaluate_feature_set(data, feature_set)
        summary = summarize_rows(rows)
        comparison = compare_to_baseline(summary, baseline["summary"])
        candidate_results.append(
            {
                "name": f"{BASE_FEATURE}+{feature}",
                "feature_set": feature_set,
                "rows": rows,
                "summary": summary,
                "comparison": comparison,
            }
        )

    candidate_results = sorted(
        candidate_results,
        key=lambda item: item["summary"]["mean_wmape"],
    )

    top_candidates = [item["feature_set"][1] for item in candidate_results[:3]]
    combination_results = []
    for size in [2, 3]:
        for combo in itertools.combinations(top_candidates, size):
            feature_set = [BASE_FEATURE] + list(combo)
            rows = evaluate_feature_set(data, feature_set)
            summary = summarize_rows(rows)
            comparison = compare_to_baseline(summary, baseline["summary"])
            combination_results.append(
                {
                    "name": "+".join(feature_set),
                    "feature_set": feature_set,
                    "rows": rows,
                    "summary": summary,
                    "comparison": comparison,
                }
            )

    combination_results = sorted(
        combination_results,
        key=lambda item: item["summary"]["mean_wmape"],
    )
    return baseline, candidate_results, combination_results


def write_report(baseline, candidate_results, combination_results):
    lines = [
        "# Temporal Feature Addition v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester une expansion séquentielle et conservatrice de `ridge_lag_only`.",
        "",
        "Le principe est simple : garder `side_creations_lag_1` comme base, ajouter une variable à la fois, puis ne tester que de petites combinaisons des meilleurs candidats.",
        "",
        "## Baseline de référence",
        "",
        f"- Modèle : `ridge_lag_only`",
        f"- Variables : `{baseline['feature_set']}`",
        f"- Mean WMAPE : `{baseline['summary']['mean_wmape']:.3f}`",
        "",
        "## Ajouts unitaires",
        "",
        "| candidate | mean_wmape | mean_delta_vs_baseline | worsened_years | accepted_strict | accepted_soft |",
        "| :--- | ---: | ---: | :--- | :---: | :---: |",
    ]
    for item in candidate_results:
        cmp = item["comparison"]
        lines.append(
            f"| {item['feature_set'][1]} | {item['summary']['mean_wmape']:.3f} | {cmp['mean_delta_vs_ridge_lag_only']:.3f} | {cmp['worsened_years']} | {cmp['accepted_strict']} | {cmp['accepted_soft']} |"
        )

    lines.extend(
        [
            "",
            "## Petites combinaisons",
            "",
            "| feature_set | mean_wmape | mean_delta_vs_baseline | worsened_years | accepted_strict | accepted_soft |",
            "| :--- | ---: | ---: | :--- | :---: | :---: |",
        ]
    )
    for item in combination_results:
        cmp = item["comparison"]
        lines.append(
            f"| {item['feature_set']} | {item['summary']['mean_wmape']:.3f} | {cmp['mean_delta_vs_ridge_lag_only']:.3f} | {cmp['worsened_years']} | {cmp['accepted_strict']} | {cmp['accepted_soft']} |"
        )

    lines.extend(
        [
            "",
            "## Détail du baseline",
            "",
            "| target_year | wmape |",
            "| :--- | ---: |",
        ]
    )
    for row in baseline["rows"]:
        lines.append(f"| {row['target_year']} | {row['wmape']:.3f} |")

    lines.extend(
        [
            "",
            "## Décision",
            "",
            "Une variable n'est pas retenue juste parce qu'elle améliore la moyenne. Elle doit aussi éviter une dégradation annuelle nette contre `ridge_lag_only`.",
            "",
            "Ce rapport doit servir à choisir le prochain sous-ensemble temporel minimal avant tout retour vers des modèles plus complexes.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    baseline, candidate_results, combination_results = evaluate_candidates(data)
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "baseline": baseline,
        "single_feature_additions": candidate_results,
        "combination_results": combination_results,
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(baseline, candidate_results, combination_results)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
