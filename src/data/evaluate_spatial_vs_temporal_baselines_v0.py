import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "spatial_vs_temporal_baselines_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "SPATIAL_VS_TEMPORAL_BASELINES_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
ALPHA_GRID = np.linspace(0.0, 1.0, 21)


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
    adjacency_geo_raw = package["adjacency_geo"].astype(float)
    adjacency_mobility_raw = package["adjacency_mobility"].astype(float)

    return {
        "years": package["years"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
        "adjacency_geo_raw": adjacency_geo_raw,
        "adjacency_geo": normalize_rows(adjacency_geo_raw),
        "adjacency_mobility_raw": adjacency_mobility_raw,
        "adjacency_mobility": normalize_rows(adjacency_mobility_raw),
    }


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def fit_temporal_ridge(data, feature_set):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in feature_set]
    rows = []
    predictions = {}

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
        model = fit_ridge(X_train, y_train_valid)
        y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        predictions[int(target_year)] = {
            "y_true": y_test_valid,
            "y_pred": y_pred,
            "used_features": used_features,
        }
        rows.append(
            {
                "target_year": int(target_year),
                "forecast_origin_year": int(target_year - 1),
                "features": used_features,
                "wmape": wmape(y_test_valid, y_pred),
            }
        )

    return rows, predictions


def build_year_payload(data):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    lag_idx = feature_names.index("side_creations_lag_1")

    _, ridge_lag_preds = fit_temporal_ridge(data, ["side_creations_lag_1"])
    _, ridge_nbcom_preds = fit_temporal_ridge(data, ["side_creations_lag_1", "nb_com"])

    payload = {}
    for target_year in EVALUATION_TARGET_YEARS:
        test_pos = np.where(years == target_year)[0]
        if len(test_pos) != 1:
            continue
        test_pos = int(test_pos[0])

        y_true = data["y_raw"][test_pos]
        lag = data["x_raw"][test_pos, :, lag_idx]
        valid = np.isfinite(y_true) & np.isfinite(lag)

        y_true_valid = y_true[valid]
        lag_valid = lag[valid]
        payload[int(target_year)] = {
            "y_true": y_true_valid,
            "persistence": lag_valid,
            "ridge_lag_only": ridge_lag_preds[int(target_year)]["y_pred"],
            "ridge_lag_nbcom": ridge_nbcom_preds[int(target_year)]["y_pred"],
            "geo_neighbor": (data["adjacency_geo"] @ lag)[valid],
            "mobility_neighbor": (data["adjacency_mobility"] @ lag)[valid],
        }
    return payload


def select_causal_alpha(year_payload, graph_name, base_name):
    alpha_trace = []
    for target_year in EVALUATION_TARGET_YEARS:
        prior_years = [year for year in EVALUATION_TARGET_YEARS if year < target_year]
        if not prior_years:
            alpha_trace.append(
                {
                    "graph": graph_name,
                    "base": base_name,
                    "target_year": int(target_year),
                    "selected_alpha": 1.0,
                    "reason": "default_base_no_prior_years",
                }
            )
            continue

        best_alpha = None
        best_score = None
        for alpha in ALPHA_GRID:
            scores = []
            for year in prior_years:
                base = year_payload[year][base_name]
                neigh = year_payload[year][f"{graph_name}_neighbor"]
                blend = alpha * base + (1.0 - alpha) * neigh
                scores.append(wmape(year_payload[year]["y_true"], blend))
            score = float(np.mean(scores))
            if best_score is None or score < best_score:
                best_score = score
                best_alpha = float(alpha)

        alpha_trace.append(
            {
                "graph": graph_name,
                "base": base_name,
                "target_year": int(target_year),
                "selected_alpha": float(best_alpha),
                "reason": "best_prior_year_mean_wmape",
                "prior_years": prior_years,
                "prior_mean_wmape": float(best_score),
            }
        )
    return alpha_trace


def evaluate_models(data):
    year_payload = build_year_payload(data)
    rows = []

    for target_year in EVALUATION_TARGET_YEARS:
        payload = year_payload[target_year]
        rows.extend(
            [
                {"target_year": int(target_year), "model": "persistence", "wmape": wmape(payload["y_true"], payload["persistence"])},
                {"target_year": int(target_year), "model": "ridge_lag_only", "wmape": wmape(payload["y_true"], payload["ridge_lag_only"])},
                {"target_year": int(target_year), "model": "ridge_lag_nbcom", "wmape": wmape(payload["y_true"], payload["ridge_lag_nbcom"])},
                {"target_year": int(target_year), "model": "geo_neighbor_average", "wmape": wmape(payload["y_true"], payload["geo_neighbor"])},
                {"target_year": int(target_year), "model": "mobility_neighbor_average", "wmape": wmape(payload["y_true"], payload["mobility_neighbor"])},
            ]
        )

    all_alpha_traces = []
    for graph_name in ["geo", "mobility"]:
        for base_name in ["persistence", "ridge_lag_only", "ridge_lag_nbcom"]:
            trace = select_causal_alpha(year_payload, graph_name, base_name)
            all_alpha_traces.extend(trace)
            for item in trace:
                target_year = item["target_year"]
                alpha = item["selected_alpha"]
                base = year_payload[target_year][base_name]
                neigh = year_payload[target_year][f"{graph_name}_neighbor"]
                blend = alpha * base + (1.0 - alpha) * neigh
                rows.append(
                    {
                        "target_year": int(target_year),
                        "model": f"{graph_name}_blend_from_{base_name}",
                        "wmape": wmape(year_payload[target_year]["y_true"], blend),
                        "selected_alpha": float(alpha),
                    }
                )

    return rows, all_alpha_traces


def summarize(rows):
    summary = []
    models = sorted({row["model"] for row in rows})
    for model in models:
        model_rows = [row for row in rows if row["model"] == model]
        summary.append(
            {
                "model": model,
                "mean_wmape": float(np.mean([row["wmape"] for row in model_rows])),
                "max_wmape": float(np.max([row["wmape"] for row in model_rows])),
                "per_year_wmape": {str(row["target_year"]): float(row["wmape"]) for row in model_rows},
            }
        )
    return sorted(summary, key=lambda item: item["mean_wmape"])


def compare_to_reference(summary_rows, reference_model):
    reference = next(row for row in summary_rows if row["model"] == reference_model)
    comparisons = {}
    for row in summary_rows:
        if row["model"] == reference_model:
            continue
        worsened_years = []
        per_year_delta = {}
        for year, ref_wmape in reference["per_year_wmape"].items():
            delta = row["per_year_wmape"][year] - ref_wmape
            per_year_delta[year] = float(delta)
            if delta > 0:
                worsened_years.append(int(year))
        comparisons[row["model"]] = {
            "mean_delta": float(row["mean_wmape"] - reference["mean_wmape"]),
            "worsened_years": worsened_years,
            "strictly_better": bool((row["mean_wmape"] < reference["mean_wmape"]) and not worsened_years),
            "per_year_delta": per_year_delta,
        }
    return comparisons


def write_report(data, summary_rows, alpha_trace, comparisons_lag, comparisons_nbcom):
    geo_raw = data["adjacency_geo_raw"]
    geo_norm = data["adjacency_geo"]
    mob_raw = data["adjacency_mobility_raw"]
    mob_norm = data["adjacency_mobility"]

    lines = [
        "# Spatial vs Temporal Baselines v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Comparer des baselines spatiaux simples à toutes les références temporelles actuelles du projet.",
        "",
        "## Vérification des matrices",
        "",
        f"- `adjacency_geo_raw` row-sum min/max : `{float(geo_raw.sum(axis=1).min()):.3f}` / `{float(geo_raw.sum(axis=1).max()):.3f}`",
        f"- `adjacency_geo` row-sum min/max après normalisation : `{float(geo_norm.sum(axis=1).min()):.3f}` / `{float(geo_norm.sum(axis=1).max()):.3f}`",
        f"- `adjacency_mobility_raw` row-sum min/max : `{float(mob_raw.sum(axis=1).min()):.3f}` / `{float(mob_raw.sum(axis=1).max()):.3f}`",
        f"- `adjacency_mobility` row-sum min/max après normalisation : `{float(mob_norm.sum(axis=1).min()):.3f}` / `{float(mob_norm.sum(axis=1).max()):.3f}`",
        "",
        "## Références temporelles",
        "",
        "- `persistence`",
        "- `ridge_lag_only`",
        "- `ridge_lag_nbcom`",
        "",
        "## Baselines spatiaux évalués",
        "",
        "- `geo_neighbor_average`",
        "- `mobility_neighbor_average`",
        "- blends causaux à partir de `persistence`",
        "- blends causaux à partir de `ridge_lag_only`",
        "- blends causaux à partir de `ridge_lag_nbcom`",
        "",
        "## Résumé",
        "",
        "| model | mean_wmape | max_wmape |",
        "| :--- | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['model']} | {row['mean_wmape']:.3f} | {row['max_wmape']:.3f} |")

    lines.extend(
        [
            "",
            "## Trace des alphas causaux",
            "",
            "| graph | base | target_year | selected_alpha | reason |",
            "| :--- | :--- | :--- | ---: | :--- |",
        ]
    )
    for row in alpha_trace:
        lines.append(
            f"| {row['graph']} | {row['base']} | {row['target_year']} | {row['selected_alpha']:.2f} | {row['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Comparaison contre ridge_lag_only",
            "",
            "| model | mean_delta | worsened_years | strictly_better |",
            "| :--- | ---: | :--- | :---: |",
        ]
    )
    for model, row in comparisons_lag.items():
        lines.append(f"| {model} | {row['mean_delta']:.3f} | {row['worsened_years']} | {row['strictly_better']} |")

    lines.extend(
        [
            "",
            "## Comparaison contre ridge_lag_nbcom",
            "",
            "| model | mean_delta | worsened_years | strictly_better |",
            "| :--- | ---: | :--- | :---: |",
        ]
    )
    for model, row in comparisons_nbcom.items():
        lines.append(f"| {model} | {row['mean_delta']:.3f} | {row['worsened_years']} | {row['strictly_better']} |")

    lines.extend(
        [
            "",
            "## Décision",
            "",
            "Un baseline spatial simple n'est retenu que s'il améliore la moyenne ET n'aggrave aucune année contre la référence temporelle considérée.",
            "",
            "Ce rapport ne doit pas surinterpréter un gain spatial si l'alpha causal retombe à `1.0`, car cela signifie que la meilleure décision reste de revenir entièrement à la référence temporelle.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    rows, alpha_trace = evaluate_models(data)
    summary_rows = summarize(rows)
    comparisons_lag = compare_to_reference(summary_rows, "ridge_lag_only")
    comparisons_nbcom = compare_to_reference(summary_rows, "ridge_lag_nbcom")
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "adjacency_checks": {
            "geo_raw_row_sum_min": float(data["adjacency_geo_raw"].sum(axis=1).min()),
            "geo_raw_row_sum_max": float(data["adjacency_geo_raw"].sum(axis=1).max()),
            "geo_norm_row_sum_min": float(data["adjacency_geo"].sum(axis=1).min()),
            "geo_norm_row_sum_max": float(data["adjacency_geo"].sum(axis=1).max()),
            "mobility_raw_row_sum_min": float(data["adjacency_mobility_raw"].sum(axis=1).min()),
            "mobility_raw_row_sum_max": float(data["adjacency_mobility_raw"].sum(axis=1).max()),
            "mobility_norm_row_sum_min": float(data["adjacency_mobility"].sum(axis=1).min()),
            "mobility_norm_row_sum_max": float(data["adjacency_mobility"].sum(axis=1).max()),
        },
        "summary": summary_rows,
        "alpha_trace": alpha_trace,
        "comparisons_vs_ridge_lag_only": comparisons_lag,
        "comparisons_vs_ridge_lag_nbcom": comparisons_nbcom,
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(data, summary_rows, alpha_trace, comparisons_lag, comparisons_nbcom)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
