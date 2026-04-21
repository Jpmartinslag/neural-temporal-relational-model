import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "hub_segments_diagnostic_v0.json"
REPORT_OUT = ROOT / "reports" / "HUB_SEGMENTS_DIAGNOSTIC_V0.md"

TARGET_YEARS = [2022, 2023]
FEATURES = ["side_creations_lag_1", "nb_com"]
HUB_QUANTILE = 0.67
NEG_GROWTH_EPS = -0.01
POS_GROWTH_EPS = 0.01


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


def load_tensor():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    return {
        "years": package["years"].astype(int),
        "node_idx": package["node_idx"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
    }


def classify_growth(value):
    if not np.isfinite(value):
        return "unknown"
    if value <= NEG_GROWTH_EPS:
        return "declining"
    if value >= POS_GROWTH_EPS:
        return "growing"
    return "flat"


def build_predictions(data):
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in FEATURES]
    lag_idx = feature_names.index("side_creations_lag_1")
    rows = []

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
        lag_test = data["x_raw"][test_pos][:, lag_idx]

        train_valid = np.isfinite(y_train)
        test_valid = np.isfinite(y_test) & np.isfinite(lag_test)
        X_train_raw = X_train_raw[train_valid]
        y_train_valid = y_train[train_valid]
        X_test_raw = X_test_raw[test_valid]
        y_test_valid = y_test[test_valid]
        lag_test_valid = lag_test[test_valid]
        node_idx_valid = data["node_idx"][test_valid]

        X_train, X_test, _ = scale_and_impute_from_train(X_train_raw, X_test_raw)
        model = fit_ridge(X_train, y_train_valid)
        y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        hub_threshold = float(np.quantile(y_train_valid, HUB_QUANTILE))
        growth_vs_lag = np.where(np.abs(lag_test_valid) > 0, (y_test_valid - lag_test_valid) / lag_test_valid, np.nan)

        rows.append(
            pd.DataFrame(
                {
                    "target_year": target_year,
                    "node_idx": node_idx_valid,
                    "y_true": y_test_valid,
                    "lag_value": lag_test_valid,
                    "y_pred": y_pred,
                    "abs_error": np.abs(y_test_valid - y_pred),
                    "signed_error": y_pred - y_test_valid,
                    "hub_threshold": hub_threshold,
                    "is_hub": lag_test_valid >= hub_threshold,
                    "growth_vs_lag": growth_vs_lag,
                    "growth_class": [classify_growth(v) for v in growth_vs_lag],
                    "overpredicted": y_pred > y_test_valid,
                }
            )
        )

    return pd.concat(rows, ignore_index=True)


def build_payload(preds):
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020", "libze2020", "nb_com"])
    regs = (
        pd.read_csv(PANEL_PATH, usecols=["ze2020", "reg"])
        .dropna()
        .drop_duplicates(subset=["ze2020"])
    )
    preds = preds.merge(node_index, on="node_idx", how="left").merge(regs, on="ze2020", how="left")
    hubs = preds[preds["is_hub"]].copy()

    segment_summary = (
        hubs.groupby(["target_year", "growth_class"], as_index=False)
        .agg(
            zones=("ze2020", "count"),
            mean_abs_error=("abs_error", "mean"),
            median_abs_error=("abs_error", "median"),
            mean_signed_error=("signed_error", "mean"),
            overpred_rate=("overpredicted", "mean"),
            mean_nb_com=("nb_com", "mean"),
        )
        .sort_values(["target_year", "growth_class"])
    )

    persistent = (
        hubs.groupby(["node_idx", "ze2020", "libze2020", "reg", "nb_com"], as_index=False)
        .agg(
            years_flagged=("target_year", "count"),
            mean_abs_error=("abs_error", "mean"),
            mean_signed_error=("signed_error", "mean"),
            mean_growth_vs_lag=("growth_vs_lag", "mean"),
            growth_class_2022=("growth_class", lambda s: next((x for x in s if x), "unknown")),
            overpred_rate=("overpredicted", "mean"),
        )
        .sort_values(["years_flagged", "mean_abs_error"], ascending=[False, False])
    )
    persistent["segment"] = persistent["mean_growth_vs_lag"].map(classify_growth)

    payload = {
        "hub_quantile": HUB_QUANTILE,
        "target_years": TARGET_YEARS,
        "segment_summary": segment_summary.to_dict(orient="records"),
        "persistent_problematic_hubs": persistent.head(30).to_dict(orient="records"),
        "persistent_segment_summary": (
            persistent.groupby("segment", as_index=False)
            .agg(
                hubs=("ze2020", "count"),
                mean_abs_error=("mean_abs_error", "mean"),
                mean_signed_error=("mean_signed_error", "mean"),
                overpred_rate=("overpred_rate", "mean"),
            )
            .sort_values("mean_abs_error", ascending=False)
            .to_dict(orient="records")
        ),
    }
    return payload


def write_report(payload):
    lines = [
        "# Hub Segments Diagnostic v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Segment summary by year",
        "",
        "| year | segment | zones | mean_abs_error | mean_signed_error | overpred_rate | mean_nb_com |",
        "| ---: | :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["segment_summary"]:
        lines.append(
            f"| {row['target_year']} | {row['growth_class']} | {row['zones']} | {row['mean_abs_error']:.1f} | {row['mean_signed_error']:.1f} | {row['overpred_rate']:.2f} | {row['mean_nb_com']:.1f} |"
        )

    lines.extend(
        [
            "",
            "## Persistent problematic hubs",
            "",
            "| ze2020 | libze2020 | reg | segment | years_flagged | mean_abs_error | mean_signed_error | mean_growth_vs_lag | overpred_rate |",
            "| ---: | :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["persistent_problematic_hubs"]:
        lines.append(
            f"| {row['ze2020']} | {row['libze2020']} | {row['reg']} | {row['segment']} | {row['years_flagged']} | {row['mean_abs_error']:.1f} | {row['mean_signed_error']:.1f} | {row['mean_growth_vs_lag']:.3f} | {row['overpred_rate']:.2f} |"
        )

    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    preds = build_predictions(load_tensor())
    payload = build_payload(preds)
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
