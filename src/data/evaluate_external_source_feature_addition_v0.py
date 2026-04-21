import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
ENERGY_PATH = ROOT / "data" / "interim" / "tables" / "energy_consumption_ze2020_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
METRICS_OUT = ROOT / "reports" / "external_source_feature_addition_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "EXTERNAL_SOURCE_FEATURE_ADDITION_V0.md"

BASE_FEATURES = ["side_creations_lag_1", "nb_com"]
CANDIDATES = [
    ("energy_electricity_pdl_nonres", ENERGY_PATH),
    ("rei_cfe_microentrepreneurs_created_n_1", REI_PATH),
]
TARGET_YEARS = [2021, 2022, 2023, 2024]


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


def load_tensor():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    return {
        "years": package["years"].astype(int),
        "node_idx": package["node_idx"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
    }


def load_external_lags():
    pieces = []
    for col, path in CANDIDATES:
        df = pd.read_csv(path)
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"ze2020": "ze2020"})
        keep = df[["ze2020", "year", col]].copy().sort_values(["ze2020", "year"])
        keep[f"{col}_lag_1"] = keep.groupby("ze2020")[col].shift(1)
        pieces.append(keep[["ze2020", "year", f"{col}_lag_1"]])

    out = pieces[0]
    for piece in pieces[1:]:
        out = out.merge(piece, on=["ze2020", "year"], how="outer")
    return out


def build_frame():
    tensor = load_tensor()
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020"])
    external = load_external_lags()

    feature_names = tensor["feature_name"].tolist()
    base_idx = [feature_names.index(name) for name in BASE_FEATURES]

    frames = []
    for pos, year in enumerate(tensor["years"]):
        frames.append(
            pd.DataFrame(
                {
                    "node_idx": tensor["node_idx"],
                    "target_year": int(year),
                    "y_true": tensor["y_raw"][pos],
                    "side_creations_lag_1": tensor["x_raw"][pos][:, base_idx[0]],
                    "nb_com": tensor["x_raw"][pos][:, base_idx[1]],
                }
            )
        )
    df = pd.concat(frames, ignore_index=True)
    df = df.merge(node_index, on="node_idx", how="left")
    df = df.merge(external, left_on=["ze2020", "target_year"], right_on=["ze2020", "year"], how="left").drop(columns=["year"])
    return df


def evaluate(df, feature_set):
    rows = []
    for target_year in TARGET_YEARS:
        train_df = df[df["target_year"] < target_year].copy()
        test_df = df[df["target_year"] == target_year].copy()
        train_df = train_df[np.isfinite(train_df["y_true"])]
        test_df = test_df[np.isfinite(test_df["y_true"])]

        X_train_raw = train_df[feature_set].to_numpy(dtype=float)
        y_train = train_df["y_true"].to_numpy(dtype=float)
        X_test_raw = test_df[feature_set].to_numpy(dtype=float)
        y_test = test_df["y_true"].to_numpy(dtype=float)

        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
        kept = [f for f, ok in zip(feature_set, valid) if ok]
        model = fit_ridge(X_train, y_train)
        y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)
        rows.append({"target_year": int(target_year), "features": kept, "wmape": wmape(y_test, y_pred)})
    return rows


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
        if delta > 0:
            worsened.append(int(year))
    mean_delta = candidate["mean_wmape"] - baseline["mean_wmape"]
    return {
        "mean_delta": float(mean_delta),
        "per_year_delta": deltas,
        "worsened_years": worsened,
        "strictly_better": bool(mean_delta < 0 and len(worsened) == 0),
    }


def main():
    df = build_frame()
    baseline_rows = evaluate(df, BASE_FEATURES)
    baseline_summary = summarize(baseline_rows)

    results = []
    for col, _ in CANDIDATES:
        lag_col = f"{col}_lag_1"
        rows = evaluate(df, BASE_FEATURES + [lag_col])
        summary = summarize(rows)
        results.append(
            {
                "feature": lag_col,
                "rows": rows,
                "summary": summary,
                "comparison_vs_ridge_lag_nbcom": compare(summary, baseline_summary),
            }
        )

    payload = {
        "baseline": {"summary": baseline_summary},
        "candidate_results": results,
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# External Source Feature Addition v0",
        "",
        f"- baseline ridge_lag_nbcom: `{baseline_summary['mean_wmape']:.3f}`",
        "",
        "| feature | mean_wmape | mean_delta | worsened_years | strictly_better |",
        "| :--- | ---: | ---: | :--- | :--- |",
    ]
    for item in results:
        cmp = item["comparison_vs_ridge_lag_nbcom"]
        lines.append(
            f"| {item['feature']} | {item['summary']['mean_wmape']:.3f} | {cmp['mean_delta']:.3f} | {cmp['worsened_years']} | {cmp['strictly_better']} |"
        )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
