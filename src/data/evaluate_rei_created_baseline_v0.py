import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
PRED_OUT = ROOT / "data" / "processed" / "rei_created_baseline_predictions_v0.csv"
METRICS_OUT = ROOT / "reports" / "rei_created_baseline_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "REI_CREATED_BASELINE_V0.md"

TARGET_YEARS = [2021, 2022, 2023, 2024]
BASE_FEATURES = ["side_creations_lag_1", "nb_com"]
REI_FEATURE = "rei_cfe_microentrepreneurs_created_n_1_lag_1"


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


def load_frame():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    feature_names = [str(x) for x in package["feature_name"]]
    idx_side = feature_names.index("side_creations_lag_1")
    idx_nb = feature_names.index("nb_com")

    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020", "libze2020"])
    rei = pd.read_csv(REI_PATH).rename(columns={"ZE2020": "ze2020"}).sort_values(["ze2020", "year"])
    rei[REI_FEATURE] = rei.groupby("ze2020")["rei_cfe_microentrepreneurs_created_n_1"].shift(1)
    rei = rei[["ze2020", "year", REI_FEATURE]]

    years = package["years"].astype(int)
    frames = []
    for pos, year in enumerate(years):
        frames.append(
            pd.DataFrame(
                {
                    "node_idx": package["node_idx"].astype(int),
                    "target_year": int(year),
                    "y_true": package["y_raw"][pos].astype(float),
                    "side_creations_lag_1": package["x_raw"][pos][:, idx_side].astype(float),
                    "nb_com": package["x_raw"][pos][:, idx_nb].astype(float),
                }
            )
        )
    df = pd.concat(frames, ignore_index=True)
    df = df.merge(node_index, on="node_idx", how="left")
    df = df.merge(rei, left_on=["ze2020", "target_year"], right_on=["ze2020", "year"], how="left").drop(columns=["year"])
    return df


def evaluate(df, feature_set):
    rows = []
    metrics = []
    for target_year in TARGET_YEARS:
        train_df = df[df["target_year"] < target_year].copy()
        test_df = df[df["target_year"] == target_year].copy()
        train_df = train_df[np.isfinite(train_df["y_true"])]
        test_df = test_df[np.isfinite(test_df["y_true"]) & np.isfinite(test_df["side_creations_lag_1"])]

        X_train_raw = train_df[feature_set].to_numpy(dtype=float)
        y_train = train_df["y_true"].to_numpy(dtype=float)
        X_test_raw = test_df[feature_set].to_numpy(dtype=float)
        y_test = test_df["y_true"].to_numpy(dtype=float)

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
        kept_features = [f for f, ok in zip(feature_set, valid) if ok]
        model = fit_ridge(X_train, y_train)
        pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        out = test_df[["target_year", "node_idx", "ze2020", "libze2020", "y_true", "side_creations_lag_1", "nb_com"]].copy()
        out["features_used"] = ",".join(kept_features)
        out["prediction"] = pred
        rows.append(out)
        metrics.append({"target_year": int(target_year), "features": kept_features, "wmape": wmape(y_test, pred)})
    return pd.concat(rows, ignore_index=True), metrics


def summarize(rows):
    return {
        "mean_wmape": float(np.mean([r["wmape"] for r in rows])),
        "max_wmape": float(np.max([r["wmape"] for r in rows])),
        "per_year_wmape": {str(r["target_year"]): float(r["wmape"]) for r in rows},
    }


def compare(candidate, baseline):
    deltas = {}
    worsened = []
    for year, base_val in baseline["per_year_wmape"].items():
        cand_val = candidate["per_year_wmape"][year]
        delta = cand_val - base_val
        deltas[year] = float(delta)
        if delta > 1e-6:
            worsened.append(int(year))
    return {
        "mean_delta": float(candidate["mean_wmape"] - baseline["mean_wmape"]),
        "per_year_delta": deltas,
        "worsened_years": worsened,
        "strictly_better_with_tolerance": bool(candidate["mean_wmape"] < baseline["mean_wmape"] and len(worsened) == 0),
    }


def write_report(payload):
    base = payload["ridge_lag_nbcom"]["summary"]
    rei = payload["rei_created_baseline"]["summary"]
    cmp = payload["comparison_vs_ridge_lag_nbcom"]
    lines = [
        "# REI Created Baseline v0",
        "",
        "Operational short baseline promoted from the REI validation step.",
        "",
        f"- baseline old (`ridge_lag_nbcom`): `{base['mean_wmape']:.3f}`",
        f"- baseline new (`rei_created_baseline`): `{rei['mean_wmape']:.3f}`",
        f"- mean_delta: `{cmp['mean_delta']:.3f}`",
        f"- worsened_years: `{cmp['worsened_years']}`",
        f"- strictly_better_with_tolerance: `{cmp['strictly_better_with_tolerance']}`",
        "",
        "| year | ridge_lag_nbcom | rei_created_baseline | delta |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for year in ["2021", "2022", "2023", "2024"]:
        delta = cmp["per_year_delta"][year]
        lines.append(f"| {year} | {base['per_year_wmape'][year]:.3f} | {rei['per_year_wmape'][year]:.3f} | {delta:.6f} |")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    df = load_frame()
    base_pred, base_rows = evaluate(df, BASE_FEATURES)
    rei_pred, rei_rows = evaluate(df, BASE_FEATURES + [REI_FEATURE])

    pred = base_pred.rename(columns={"prediction": "pred_ridge_lag_nbcom"}).merge(
        rei_pred[["target_year", "node_idx", "prediction"]].rename(columns={"prediction": "pred_rei_created_baseline"}),
        on=["target_year", "node_idx"],
        how="left",
    )
    pred.to_csv(PRED_OUT, index=False)

    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "rei_source": str(REI_PATH.relative_to(ROOT)),
        "rei_created_baseline": {
            "feature_set": BASE_FEATURES + [REI_FEATURE],
            "summary": summarize(rei_rows),
            "rows": rei_rows,
        },
        "ridge_lag_nbcom": {
            "feature_set": BASE_FEATURES,
            "summary": summarize(base_rows),
            "rows": base_rows,
        },
        "comparison_vs_ridge_lag_nbcom": compare(summarize(rei_rows), summarize(base_rows)),
        "prediction_output": str(PRED_OUT.relative_to(ROOT)),
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved predictions to {PRED_OUT}")
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
