import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
ARTIFACT_OUT = ROOT / "data" / "processed" / "final_rei_created_baseline_artifact_v0.json"
FIT_OUT = ROOT / "data" / "processed" / "final_rei_created_baseline_fitted_values_v0.csv"
REPORT_OUT = ROOT / "reports" / "FINAL_REI_CREATED_BASELINE_V0.md"

FEATURES = ["side_creations_lag_1", "nb_com", "rei_cfe_microentrepreneurs_created_n_1_lag_1"]


def wmape(y_true, y_pred):
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def scale_and_impute(X_raw):
    X_scaled = np.zeros_like(X_raw, dtype=float)
    means = []
    stds = []
    valid = []
    for i in range(X_raw.shape[1]):
        col = X_raw[:, i]
        observed = col[np.isfinite(col)]
        if len(observed) == 0:
            valid.append(False)
            means.append(None)
            stds.append(None)
            continue
        mean = float(observed.mean())
        std = float(observed.std())
        if std == 0:
            std = 1.0
        X_scaled[:, i] = np.where(np.isfinite(col), (col - mean) / std, 0.0)
        valid.append(True)
        means.append(mean)
        stds.append(std)
    valid = np.array(valid, dtype=bool)
    return X_scaled[:, valid], valid, means, stds


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


def main():
    df = load_frame()
    train_df = df[np.isfinite(df["y_true"]) & np.isfinite(df["side_creations_lag_1"])].copy()

    X_raw = train_df[FEATURES].to_numpy(dtype=float)
    y = train_df["y_true"].to_numpy(dtype=float)
    X, valid, means, stds = scale_and_impute(X_raw)
    kept_features = [f for f, ok in zip(FEATURES, valid) if ok]
    kept_means = [m for m, ok in zip(means, valid) if ok]
    kept_stds = [s for s, ok in zip(stds, valid) if ok]

    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X, y)
    pred = np.clip(model.predict(X), a_min=0, a_max=None)

    fitted = train_df[["target_year", "node_idx", "ze2020", "libze2020", "y_true"]].copy()
    fitted["prediction"] = pred
    fitted.to_csv(FIT_OUT, index=False)

    artifact = {
        "model": "final_rei_created_baseline_v0",
        "feature_set": kept_features,
        "train_years": sorted(train_df["target_year"].unique().tolist()),
        "n_rows": int(len(train_df)),
        "alpha": float(model.alpha_),
        "intercept": float(model.intercept_),
        "feature_means": {f: float(m) for f, m in zip(kept_features, kept_means)},
        "feature_stds": {f: float(s) for f, s in zip(kept_features, kept_stds)},
        "coefficients": {f: float(c) for f, c in zip(kept_features, model.coef_)},
        "in_sample_wmape": wmape(y, pred),
        "prediction_output": str(FIT_OUT.relative_to(ROOT)),
    }
    ARTIFACT_OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Final REI Created Baseline v0",
        "",
        "Final operational artifact fitted on all available observed years.",
        "",
        f"- model: `{artifact['model']}`",
        f"- feature_set: `{artifact['feature_set']}`",
        f"- train_years: `{artifact['train_years']}`",
        f"- rows: `{artifact['n_rows']}`",
        f"- alpha: `{artifact['alpha']}`",
        f"- in_sample_wmape: `{artifact['in_sample_wmape']:.3f}`",
        f"- artifact_output: `{ARTIFACT_OUT.relative_to(ROOT)}`",
        f"- fitted_values_output: `{artifact['prediction_output']}`",
        "",
        "| feature | mean | std | coefficient |",
        "| --- | ---: | ---: | ---: |",
    ]
    for feat in kept_features:
        lines.append(
            f"| {feat} | {artifact['feature_means'][feat]:.6f} | {artifact['feature_stds'][feat]:.6f} | {artifact['coefficients'][feat]:.6f} |"
        )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(f"Saved artifact to {ARTIFACT_OUT}")
    print(f"Saved fitted values to {FIT_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
