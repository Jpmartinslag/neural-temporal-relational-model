import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "ridge_nbcom_weak_years_diagnostic_v0.json"
REPORT_OUT = ROOT / "reports" / "RIDGE_NBCOM_WEAK_YEARS_DIAGNOSTIC_V0.md"

TARGET_YEARS = [2022, 2023]
FEATURES = ["side_creations_lag_1", "nb_com"]


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
        "node_idx": package["node_idx"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
    }


def build_zone_level_predictions(data):
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in FEATURES]
    frames = []

    for target_year in TARGET_YEARS:
        test_pos = np.where(data["years"] == target_year)[0]
        if len(test_pos) != 1:
            continue
        test_pos = int(test_pos[0])
        train_pos = np.where(data["years"] < target_year)[0]

        y_train = data["y_raw"][train_pos].reshape(-1)
        y_test = data["y_raw"][test_pos]
        X_train_raw = data["x_raw"][train_pos][:, :, feature_indices].reshape(-1, len(feature_indices))
        X_test_raw = data["x_raw"][test_pos][:, feature_indices]

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test)

        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw_valid = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]
        node_idx_valid = data["node_idx"][test_valid]

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw_valid)
        used_features = [name for name, ok in zip(FEATURES, valid) if ok]
        model = fit_ridge(X_train, y_train_valid)
        y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        frame = pd.DataFrame(
            {
                "target_year": target_year,
                "node_idx": node_idx_valid,
                "y_true": y_test_valid,
                "y_pred": y_pred,
                "abs_error": np.abs(y_test_valid - y_pred),
            }
        )
        if "side_creations_lag_1" in used_features:
            lag_col = X_test_raw_valid[:, used_features.index("side_creations_lag_1")]
            frame["lag_value"] = lag_col
            frame["growth_vs_lag"] = np.where(
                np.abs(lag_col) > 0,
                (frame["y_true"] - lag_col) / lag_col,
                np.nan,
            )
        if "nb_com" in used_features:
            frame["nb_com"] = X_test_raw_valid[:, used_features.index("nb_com")]
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def add_context(predictions):
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020", "libze2020"])
    panel = pd.read_csv(PANEL_PATH, usecols=["ze2020", "reg", "year", "population_total", "jobs_lt_total", "unemployment_rate_est"])
    panel = panel.rename(columns={"year": "target_year"})
    out = predictions.merge(node_index, on="node_idx", how="left").merge(panel, on=["ze2020", "target_year"], how="left")

    y_bins = out.groupby("target_year")["y_true"].transform(
        lambda s: pd.qcut(s.rank(method="first"), q=3, labels=["small", "medium", "large"])
    )
    out["target_band"] = y_bins.astype(str)
    return out


def summarize(df, cols):
    return (
        df.groupby(cols, dropna=False)
        .agg(
            zones=("ze2020", "count"),
            mean_abs_error=("abs_error", "mean"),
            median_abs_error=("abs_error", "median"),
            mean_target=("y_true", "mean"),
            mean_prediction=("y_pred", "mean"),
            mean_growth_vs_lag=("growth_vs_lag", "mean"),
            mean_nb_com=("nb_com", "mean"),
        )
        .reset_index()
    )


def build_payload(df):
    payload = {
        "source_tensor": str(TENSOR_PATH.relative_to(ROOT)),
        "target_years": TARGET_YEARS,
        "overall_by_year": summarize(df, ["target_year"]).to_dict(orient="records"),
        "by_year_and_target_band": summarize(df, ["target_year", "target_band"]).to_dict(orient="records"),
        "by_year_and_region": summarize(df, ["target_year", "reg"]).to_dict(orient="records"),
        "worst_zones": df.sort_values(["target_year", "abs_error"], ascending=[True, False])
        .groupby("target_year")
        .head(10)[
            ["target_year", "ze2020", "libze2020", "reg", "y_true", "y_pred", "abs_error", "growth_vs_lag", "nb_com"]
        ]
        .to_dict(orient="records"),
    }
    return payload


def write_report(payload):
    lines = [
        "# Ridge NbCom Weak Years Diagnostic v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Comprendre pourquoi `ridge_lag_nbcom` reste plus faible en 2022 et 2023 qu'en 2021 et 2024.",
        "",
        "## Par année",
        "",
        "| target_year | zones | mean_abs_error | median_abs_error | mean_target | mean_growth_vs_lag | mean_nb_com |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["overall_by_year"]:
        lines.append(
            f"| {int(row['target_year'])} | {int(row['zones'])} | {row['mean_abs_error']:.3f} | {row['median_abs_error']:.3f} | {row['mean_target']:.1f} | {row['mean_growth_vs_lag']:.3f} | {row['mean_nb_com']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Par bande de taille du target",
            "",
            "| target_year | target_band | zones | mean_abs_error | mean_target | mean_growth_vs_lag |",
            "| ---: | :--- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["by_year_and_target_band"]:
        lines.append(
            f"| {int(row['target_year'])} | {row['target_band']} | {int(row['zones'])} | {row['mean_abs_error']:.3f} | {row['mean_target']:.1f} | {row['mean_growth_vs_lag']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Pires zones par année",
            "",
            "| target_year | ze2020 | libze2020 | reg | y_true | y_pred | abs_error | growth_vs_lag | nb_com |",
            "| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["worst_zones"]:
        lines.append(
            f"| {int(row['target_year'])} | {int(row['ze2020'])} | {row['libze2020']} | {int(row['reg']) if pd.notna(row['reg']) else ''} | {row['y_true']:.1f} | {row['y_pred']:.1f} | {row['abs_error']:.1f} | {row['growth_vs_lag']:.3f} | {row['nb_com']:.1f} |"
        )

    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = load_tensor_package()
    predictions = build_zone_level_predictions(data)
    predictions = add_context(predictions)
    payload = build_payload(predictions)
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
