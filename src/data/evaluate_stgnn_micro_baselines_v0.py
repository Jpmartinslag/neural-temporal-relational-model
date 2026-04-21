import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "stgnn_micro_baselines_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "STGNN_MICRO_BASELINES_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]


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
        "node_idx": package["node_idx"].astype(int),
        "x_raw": package["x_raw"].astype(float),
        "x_mask": package["x_mask"].astype(float),
        "y_raw": package["y_raw"].astype(float),
        "adjacency_geo": package["adjacency_geo"].astype(float),
        "adjacency_mobility": package["adjacency_mobility"].astype(float),
    }


def validate_package(data):
    years = data["years"]
    x_raw = data["x_raw"]
    x_mask = data["x_mask"]
    y_raw = data["y_raw"]
    adjacency_geo = data["adjacency_geo"]
    adjacency_mobility = data["adjacency_mobility"]
    feature_name = data["feature_name"]
    node_idx = data["node_idx"]

    checks = {
        "x_raw_shape": list(x_raw.shape),
        "x_mask_shape": list(x_mask.shape),
        "y_raw_shape": list(y_raw.shape),
        "adjacency_geo_shape": list(adjacency_geo.shape),
        "adjacency_mobility_shape": list(adjacency_mobility.shape),
        "years": years.tolist(),
        "target_years": years.tolist(),
        "nodes": int(len(node_idx)),
        "features": feature_name.tolist(),
        "x_y_time_aligned": bool(x_raw.shape[0] == y_raw.shape[0] == len(years)),
        "x_mask_aligned": bool(x_raw.shape == x_mask.shape),
        "geo_node_aligned": bool(adjacency_geo.shape == (len(node_idx), len(node_idx))),
        "mobility_node_aligned": bool(adjacency_mobility.shape == (len(node_idx), len(node_idx))),
        "finite_y_by_target_year": {
            str(int(year)): int(np.isfinite(y_raw[i]).sum()) for i, year in enumerate(years)
        },
        "observed_x_share": float(np.isfinite(x_raw).mean()),
        "mask_observed_share": float(x_mask.mean()),
    }
    required = ["side_creations_lag_1"]
    checks["required_features_present"] = {
        name: bool(name in set(feature_name)) for name in required
    }
    checks["valid"] = all(
        [
            checks["x_y_time_aligned"],
            checks["x_mask_aligned"],
            checks["geo_node_aligned"],
            checks["mobility_node_aligned"],
            all(checks["required_features_present"].values()),
        ]
    )
    return checks


def fit_ridge_lag_only(train_lag, train_y, test_lag):
    X_train, X_test, valid = scale_and_impute_from_train(
        train_lag.reshape(-1, 1),
        test_lag.reshape(-1, 1),
    )
    if not valid.any():
        return test_lag.copy()

    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, train_y)
    return np.clip(model.predict(X_test), a_min=0, a_max=None)


def evaluate_micro_baselines(data):
    years = data["years"]
    target_years = years
    features = data["feature_name"].tolist()
    side_lag_idx = features.index("side_creations_lag_1")
    spatial_lag_idx = features.index("side_creations_spatial_lag_1")
    mobility_lag_idx = features.index("side_creations_mobility_lag_1")

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

        lag_train = data["x_raw"][train_pos, :, side_lag_idx].reshape(-1)
        lag_test = data["x_raw"][test_pos, :, side_lag_idx]
        spatial_test = data["x_raw"][test_pos, :, spatial_lag_idx]
        mobility_test = data["x_raw"][test_pos, :, mobility_lag_idx]

        train_valid = np.isfinite(y_train) & np.isfinite(lag_train)
        test_valid = np.isfinite(y_test) & np.isfinite(lag_test)
        y_train_valid = y_train[train_valid]
        lag_train_valid = lag_train[train_valid]
        y_test_valid = y_test[test_valid]
        lag_test_valid = lag_test[test_valid]

        model_predictions = {
            "persistence": lag_test_valid,
            "ridge_lag_only": fit_ridge_lag_only(
                lag_train_valid,
                y_train_valid,
                lag_test_valid,
            ),
        }

        spatial_valid = test_valid & np.isfinite(spatial_test)
        if spatial_valid.any():
            model_predictions["spatial_lag_diagnostic"] = spatial_test[test_valid]

        mobility_valid = test_valid & np.isfinite(mobility_test)
        if mobility_valid.any():
            model_predictions["mobility_lag_diagnostic"] = mobility_test[test_valid]

        for model_name, y_pred in model_predictions.items():
            rows.append(
                {
                    "forecast_origin_year": int(target_year - 1),
                    "target_year": int(target_year),
                    "train_forecast_origin_years": (years[train_pos] - 1).astype(int).tolist(),
                    "train_target_years": target_years[train_pos].astype(int).tolist(),
                    "model": model_name,
                    "wmape": wmape(y_test_valid, y_pred),
                    "actual_sum": float(np.sum(y_test_valid)),
                    "prediction_sum": float(np.sum(y_pred)),
                    "rows": int(len(y_test_valid)),
                }
            )

    return rows


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
                "years": [row["target_year"] for row in model_rows],
            }
        )
    return sorted(summary, key=lambda row: row["mean_wmape"])


def write_report(payload):
    checks = payload["package_checks"]
    summary = payload["summary"]
    rows = payload["rows"]

    lines = [
        "# STGNN Micro Baselines v0",
        "",
        "Date : 2026-04-20",
        "",
        "## Objectif",
        "",
        "Valider le paquet tensoriel forecast-safe et reconstruire les premières références dans le même cadre temporel que les futurs modèles STGNN.",
        "",
        "Ce rapport ne constitue pas encore une expérience STGNN. Il sert de marche zéro : chargement, alignement, masques et micro-baselines.",
        "",
        "## Paquet tensoriel",
        "",
        f"- Source : `{TENSOR_PATH.relative_to(ROOT)}`",
        f"- Années du panel : `{checks['years']}`",
        f"- Années de cible : `{checks['target_years']}`",
        f"- Shape `x_raw` : `{checks['x_raw_shape']}`",
        f"- Shape `y_raw` : `{checks['y_raw_shape']}`",
        f"- Shape `A_geo` : `{checks['adjacency_geo_shape']}`",
        f"- Shape `A_mobility` : `{checks['adjacency_mobility_shape']}`",
        f"- Part observée selon `x_mask` : `{checks['mask_observed_share']:.3f}`",
        f"- Validation structurelle : `{checks['valid']}`",
        "",
        "## Règle temporelle",
        "",
        "Chaque ligne respecte l'alignement causal déjà matérialisé dans le panel :",
        "",
        "```text",
        "variables retardées disponibles avant ou au début de l'année cible -> target(année cible)",
        "```",
        "",
        "`years` dans le paquet correspond à l'année cible du panel, pas à la date brute de chaque source. Les variables causales portent explicitement leur décalage dans le nom, par exemple `side_creations_lag_1`.",
        "",
        "Pour éviter une fuite de normalisation, `ridge_lag_only` est recalculé par fold à partir de `x_raw`, avec scaling et imputation ajustés seulement sur les années de train du fold.",
        "",
        "`spatial_lag_diagnostic` et `mobility_lag_diagnostic` sont des contrôles d'échelle sur les variables déjà présentes dans le tensor. Ils ne remplacent pas un vrai baseline graphe normalisé.",
        "",
        "## Résumé",
        "",
        "| modèle | mean_wmape | max_wmape | années cible |",
        "| :--- | ---: | ---: | :--- |",
    ]
    for row in summary:
        lines.append(
            f"| {row['model']} | {row['mean_wmape']:.3f} | {row['max_wmape']:.3f} | {row['years']} |"
        )

    lines.extend(
        [
            "",
            "## Détail par année",
            "",
            "| target_year | forecast_origin_year | model | wmape | actual_sum | prediction_sum |",
            "| :--- | :--- | :--- | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            "| {target_year} | {forecast_origin_year} | {model} | {wmape:.3f} | {actual_sum:.0f} | {prediction_sum:.0f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Décision",
            "",
            "Ce script valide le format d'entrée et fixe les références minimales avant tout modèle neural.",
            "",
            "La prochaine étape technique peut être un modèle temporel sans graphe. Aucun résultat STGNN ne doit être interprété avant cette comparaison.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    checks = validate_package(data)
    rows = evaluate_micro_baselines(data)
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "evaluation_target_years": EVALUATION_TARGET_YEARS,
        "package_checks": checks,
        "summary": summarize(rows),
        "rows": rows,
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
