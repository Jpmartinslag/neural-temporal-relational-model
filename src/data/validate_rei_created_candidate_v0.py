import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
METRICS_OUT = ROOT / "reports" / "rei_created_candidate_validation_v0.json"
REPORT_OUT = ROOT / "reports" / "REI_CREATED_CANDIDATE_VALIDATION_V0.md"

BASE_FEATURES = ["side_creations_lag_1", "nb_com"]
REI_FEATURE = "rei_cfe_microentrepreneurs_created_n_1_lag_1"
TARGET_YEARS = [2021, 2022, 2023, 2024]
HUB_QUANTILE = 0.67
TOL = 1e-6


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

    frames = []
    years = package["years"].astype(int)
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


def fit_predict(df, feature_set):
    rows = []
    for target_year in TARGET_YEARS:
        train_df = df[df["target_year"] < target_year].copy()
        test_df = df[df["target_year"] == target_year].copy()
        train_df = train_df[np.isfinite(train_df["y_true"])]
        test_df = test_df[np.isfinite(test_df["y_true"]) & np.isfinite(test_df["side_creations_lag_1"])]

        X_train_raw = train_df[feature_set].to_numpy(dtype=float)
        y_train = train_df["y_true"].to_numpy(dtype=float)
        X_test_raw = test_df[feature_set].to_numpy(dtype=float)
        X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)

        model = fit_ridge(X_train, y_train)
        pred = np.clip(model.predict(X_test), a_min=0, a_max=None)
        out = test_df[["target_year", "node_idx", "ze2020", "libze2020", "y_true", "side_creations_lag_1"]].copy()
        out["prediction"] = pred
        out["abs_error"] = np.abs(out["y_true"] - out["prediction"])
        out["hub_threshold"] = float(np.quantile(y_train, HUB_QUANTILE))
        out["is_hub"] = out["side_creations_lag_1"] >= out["hub_threshold"]
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def year_summary(frame):
    out = []
    for year, sub in frame.groupby("target_year"):
        out.append(
            {
                "target_year": int(year),
                "wmape": wmape(sub["y_true"].to_numpy(float), sub["prediction"].to_numpy(float)),
                "rows": int(len(sub)),
            }
        )
    return out


def compare_years(base_rows, cand_rows):
    out = []
    for b, c in zip(base_rows, cand_rows):
        delta = c["wmape"] - b["wmape"]
        out.append(
            {
                "target_year": b["target_year"],
                "baseline_wmape": b["wmape"],
                "candidate_wmape": c["wmape"],
                "delta": float(delta),
                "worse_beyond_tol": bool(delta > TOL),
            }
        )
    return out


def subset_summary(base_pred, cand_pred, subset_name, mask):
    b = base_pred[mask].copy()
    c = cand_pred[mask].copy()
    return {
        "subset": subset_name,
        "rows": int(len(b)),
        "baseline_wmape": wmape(b["y_true"].to_numpy(float), b["prediction"].to_numpy(float)),
        "candidate_wmape": wmape(c["y_true"].to_numpy(float), c["prediction"].to_numpy(float)),
        "mean_abs_error_delta": float((c["abs_error"] - b["abs_error"]).mean()),
    }


def main():
    df = load_frame()
    base_pred = fit_predict(df, BASE_FEATURES)
    cand_pred = fit_predict(df, BASE_FEATURES + [REI_FEATURE])

    base_years = year_summary(base_pred)
    cand_years = year_summary(cand_pred)
    cmp_years = compare_years(base_years, cand_years)

    payload = {
        "candidate_feature": REI_FEATURE,
        "baseline_mean_wmape": float(np.mean([r["wmape"] for r in base_years])),
        "candidate_mean_wmape": float(np.mean([r["wmape"] for r in cand_years])),
        "year_comparison": cmp_years,
        "strictly_better_with_tolerance": bool(
            np.mean([r["wmape"] for r in cand_years]) < np.mean([r["wmape"] for r in base_years])
            and all(not r["worse_beyond_tol"] for r in cmp_years)
        ),
        "subsets": [
            subset_summary(base_pred, cand_pred, "all", base_pred["target_year"] >= 0),
            subset_summary(base_pred, cand_pred, "hubs", base_pred["is_hub"]),
            subset_summary(base_pred, cand_pred, "non_hubs", ~base_pred["is_hub"]),
            subset_summary(base_pred, cand_pred, "2023_hubs", (base_pred["target_year"] == 2023) & base_pred["is_hub"]),
            subset_summary(base_pred, cand_pred, "2024_hubs", (base_pred["target_year"] == 2024) & base_pred["is_hub"]),
        ],
        "top_improved_2023": (
            pd.DataFrame(
                {
                    "ze2020": base_pred.loc[base_pred["target_year"] == 2023, "ze2020"].to_numpy(),
                    "libze2020": base_pred.loc[base_pred["target_year"] == 2023, "libze2020"].to_numpy(),
                    "baseline_abs_error": base_pred.loc[base_pred["target_year"] == 2023, "abs_error"].to_numpy(),
                    "candidate_abs_error": cand_pred.loc[cand_pred["target_year"] == 2023, "abs_error"].to_numpy(),
                }
            )
            .assign(delta=lambda x: x["candidate_abs_error"] - x["baseline_abs_error"])
            .sort_values("delta")
            .head(15)
            .to_dict(orient="records")
        ),
    }

    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# REI Created Candidate Validation v0",
        "",
        f"- candidate: `{REI_FEATURE}`",
        f"- baseline mean WMAPE: `{payload['baseline_mean_wmape']:.3f}`",
        f"- candidate mean WMAPE: `{payload['candidate_mean_wmape']:.3f}`",
        f"- strictly_better_with_tolerance: `{payload['strictly_better_with_tolerance']}`",
        "",
        "| year | baseline | candidate | delta | worse_beyond_tol |",
        "| ---: | ---: | ---: | ---: | :--- |",
    ]
    for row in payload["year_comparison"]:
        lines.append(
            f"| {row['target_year']} | {row['baseline_wmape']:.3f} | {row['candidate_wmape']:.3f} | {row['delta']:.6f} | {row['worse_beyond_tol']} |"
        )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
