import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.neural_network import MLPRegressor


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
METRICS_OUT = ROOT / "reports" / "temporal_non_graph_baseline_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "TEMPORAL_NON_GRAPH_BASELINE_V0.md"

EVALUATION_TARGET_YEARS = [2021, 2022, 2023, 2024]
GRAPH_DERIVED_FEATURES = {
    "side_creations_spatial_lag_1",
    "side_creations_mobility_lag_1",
}


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


def build_feature_groups(feature_names):
    feature_names = list(feature_names)
    lag_only = ["side_creations_lag_1"]
    no_graph_core = [name for name in feature_names if name not in GRAPH_DERIVED_FEATURES]
    return {
        "lag_only": lag_only,
        "no_graph_core": no_graph_core,
    }


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def fit_predict_mlp(X_train, y_train, X_test):
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
    y_pred_scaled = model.predict(X_test)
    return np.clip(y_pred_scaled * y_std + y_mean, a_min=0, a_max=None)


def evaluate_models(data):
    years = data["years"]
    target_years = years
    feature_names = data["feature_name"].tolist()
    feature_groups = build_feature_groups(feature_names)
    lag_idx = feature_names.index("side_creations_lag_1")
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
        lag_test = data["x_raw"][test_pos, :, lag_idx]
        persistence_valid = np.isfinite(y_test) & np.isfinite(lag_test)
        rows.append(
            {
                "forecast_origin_year": int(target_year - 1),
                "target_year": int(target_year),
                "model": "persistence",
                "feature_group": "lag_only",
                "features_used": ["side_creations_lag_1"],
                "wmape": wmape(y_test[persistence_valid], lag_test[persistence_valid]),
                "actual_sum": float(np.sum(y_test[persistence_valid])),
                "prediction_sum": float(np.sum(lag_test[persistence_valid])),
                "rows": int(persistence_valid.sum()),
            }
        )

        for group_name, group_features in feature_groups.items():
            group_indices = [feature_names.index(name) for name in group_features]
            X_train_raw = data["x_raw"][train_pos][:, :, group_indices].reshape(-1, len(group_indices))
            X_test_raw = data["x_raw"][test_pos][:, group_indices]

            train_valid = np.isfinite(y_train)
            test_valid = np.isfinite(y_test)
            X_train_raw = X_train_raw[train_valid]
            y_train_valid = y_train[train_valid]
            X_test_raw = X_test_raw[test_valid]
            y_test_valid = y_test[test_valid]

            X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
            used_features = [name for name, ok in zip(group_features, valid) if ok]
            if not used_features:
                continue

            for model_name in ["ridge", "mlp"]:
                if model_name == "ridge":
                    model = fit_ridge(X_train, y_train_valid)
                    y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)
                else:
                    y_pred = fit_predict_mlp(X_train, y_train_valid, X_test)
                rows.append(
                    {
                        "forecast_origin_year": int(target_year - 1),
                        "target_year": int(target_year),
                        "model": f"{model_name}_{group_name}",
                        "feature_group": group_name,
                        "features_used": used_features,
                        "wmape": wmape(y_test_valid, y_pred),
                        "actual_sum": float(np.sum(y_test_valid)),
                        "prediction_sum": float(np.sum(y_pred)),
                        "rows": int(len(y_test_valid)),
                    }
                )

    return rows, feature_groups


def summarize(rows):
    summary = []
    models = sorted({row["model"] for row in rows})
    for model in models:
        model_rows = [row for row in rows if row["model"] == model]
        summary.append(
            {
                "model": model,
                "feature_group": model_rows[0]["feature_group"],
                "mean_wmape": float(np.mean([row["wmape"] for row in model_rows])),
                "max_wmape": float(np.max([row["wmape"] for row in model_rows])),
                "years": [row["target_year"] for row in model_rows],
            }
        )
    return sorted(summary, key=lambda row: row["mean_wmape"])


def write_report(payload):
    feature_groups = payload["feature_groups"]
    summary = payload["summary"]
    rows = payload["rows"]

    lines = [
        "# Temporal Non-Graph Baseline v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Tester le premier modèle temporel sans graphe avant toute architecture STGNN.",
        "",
        "Le protocole exclut explicitement les entrées de graphe et retire aussi les deux variables déjà dérivées du graphe : `side_creations_spatial_lag_1` et `side_creations_mobility_lag_1` du groupe `no_graph_core`.",
        "",
        "## Groupes de variables",
        "",
        f"- `lag_only` : `{feature_groups['lag_only']}`",
        f"- `no_graph_core` : `{feature_groups['no_graph_core']}`",
        "",
        "## Modèles évalués",
        "",
        "- `persistence`",
        "- `ridge_lag_only`",
        "- `mlp_lag_only`",
        "- `ridge_no_graph_core`",
        "- `mlp_no_graph_core`",
        "",
        "## Résumé",
        "",
        "| modèle | groupe | mean_wmape | max_wmape | années cible |",
        "| :--- | :--- | ---: | ---: | :--- |",
    ]
    for row in summary:
        lines.append(
            f"| {row['model']} | {row['feature_group']} | {row['mean_wmape']:.3f} | {row['max_wmape']:.3f} | {row['years']} |"
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
            "La question de cette étape n'est pas encore de savoir si le graphe aide.",
            "",
            "La question est : une non-linéarité temporelle simple, sans graphe, bat-elle déjà `ridge_lag_only` ?",
            "",
            "Si la réponse est non, il faudra rester prudent avant d'attribuer un futur gain au seul composant graphe.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    rows, feature_groups = evaluate_models(data)
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "evaluation_target_years": EVALUATION_TARGET_YEARS,
        "feature_groups": feature_groups,
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
