import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
METRICS_OUT = ROOT / "reports" / "rei_hub_interaction_baseline_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "REI_HUB_INTERACTION_BASELINE_V0.md"
PRED_OUT = ROOT / "data" / "processed" / "rei_hub_interaction_baseline_predictions_v0.csv"

TARGET_YEARS = [2021, 2022, 2023, 2024]
BASE_FEATURES = ["side_creations_lag_1", "nb_com", "rei_cfe_microentrepreneurs_created_n_1_lag_1"]
HUB_QUANTILE = 0.67


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
    rei["rei_cfe_microentrepreneurs_created_n_1_lag_1"] = rei.groupby("ze2020")["rei_cfe_microentrepreneurs_created_n_1"].shift(1)
    rei = rei[["ze2020", "year", "rei_cfe_microentrepreneurs_created_n_1_lag_1"]]

    frames = []
    for pos, year in enumerate(package["years"].astype(int)):
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


def add_interactions(train_df, test_df):
    hub_threshold = float(np.quantile(train_df["side_creations_lag_1"].dropna(), HUB_QUANTILE))
    train_df = train_df.copy()
    test_df = test_df.copy()
    train_df["hub_flag"] = (train_df["side_creations_lag_1"] >= hub_threshold).astype(float)
    test_df["hub_flag"] = (test_df["side_creations_lag_1"] >= hub_threshold).astype(float)
    train_df["rei_x_hub"] = train_df["rei_cfe_microentrepreneurs_created_n_1_lag_1"] * train_df["hub_flag"]
    test_df["rei_x_hub"] = test_df["rei_cfe_microentrepreneurs_created_n_1_lag_1"] * test_df["hub_flag"]
    return train_df, test_df


def evaluate(df):
    rows = []
    preds = []
    for target_year in TARGET_YEARS:
        train_df = df[df["target_year"] < target_year].copy()
        test_df = df[df["target_year"] == target_year].copy()
        train_df = train_df[np.isfinite(train_df["y_true"])]
        test_df = test_df[np.isfinite(test_df["y_true"]) & np.isfinite(test_df["side_creations_lag_1"])]

        base_train, base_test = add_interactions(train_df, test_df)
        feature_set = BASE_FEATURES + ["hub_flag", "rei_x_hub"]

        X_train_raw = base_train[feature_set].to_numpy(dtype=float)
        y_train = base_train["y_true"].to_numpy(dtype=float)
        X_test_raw = base_test[feature_set].to_numpy(dtype=float)
        y_test = base_test["y_true"].to_numpy(dtype=float)

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
        kept = [f for f, ok in zip(feature_set, valid) if ok]
        model = fit_ridge(X_train, y_train)
        pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

        preds.append(
            base_test[["target_year", "node_idx", "ze2020", "libze2020", "y_true"]]
            .assign(features_used=",".join(kept), prediction=pred)
        )
        rows.append({"target_year": int(target_year), "features": kept, "wmape": wmape(y_test, pred)})
    return pd.concat(preds, ignore_index=True), rows


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


def main():
    df = load_frame()
    pred, rows = evaluate(df)
    pred.to_csv(PRED_OUT, index=False)

    baseline_metrics = json.load(open(ROOT / "reports" / "rei_created_baseline_metrics_v0.json"))
    baseline_summary = baseline_metrics["rei_created_baseline"]["summary"]
    candidate_summary = summarize(rows)
    payload = {
        "feature_set": BASE_FEATURES + ["hub_flag", "rei_x_hub"],
        "summary": candidate_summary,
        "rows": rows,
        "comparison_vs_rei_created_baseline": compare(candidate_summary, baseline_summary),
        "prediction_output": str(PRED_OUT.relative_to(ROOT)),
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    cmp = payload["comparison_vs_rei_created_baseline"]
    lines = [
        "# REI Hub Interaction Baseline v0",
        "",
        f"- mean_wmape: `{candidate_summary['mean_wmape']:.3f}`",
        f"- mean_delta vs rei_created_baseline: `{cmp['mean_delta']:.3f}`",
        f"- worsened_years: `{cmp['worsened_years']}`",
        f"- strictly_better_with_tolerance: `{cmp['strictly_better_with_tolerance']}`",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved predictions to {PRED_OUT}")
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
