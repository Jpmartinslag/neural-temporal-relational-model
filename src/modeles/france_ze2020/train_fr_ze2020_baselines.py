"""
EXPLORATORY SMOKE BASELINE -- France ZE2020 minimal current training path.

Reads ONLY data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv
(never data/processed/dynamic_stgnn_feature_panel_v1.csv or any other
dynamic_stgnn_* file -- that panel is LEGACY_DO_NOT_USE_FOR_CURRENT_METHOD,
see reports/canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md section 5
and reports/herald_artifact_registry.json::FR_DYNAMIC_STGNN_LEGACY_FEATURE_PANEL).

Two causal rolling-origin baselines, evaluated on the SAME eval-year window
so their errors are directly comparable (HERALD Intelligence Layer lesson:
never compare baselines computed over different year ranges):

  - persistence: y_hat[t] = lag_1[t]  (last observed year, no fitting)
  - ridge:       Ridge(alpha=RIDGE_ALPHA) on [lag_1, lag_2, lag_3,
                 growth_1y_safe, growth_2y_safe], refit per eval year on
                 all strictly prior years with complete features
                 (RIDGE_MIN_TRAIN years minimum), same alpha/min-train
                 convention as build_pt_municipal_prediction_layer.py /
                 build_observatory_export.py.

This is a smoke/organizational baseline, not a headline result: no claim of
"best model", no comparison to the legacy/Q7 track, no HPC. Metrics are
written with an explicit `claim_status=exploratory_smoke` column so no
downstream reader mistakes this for a validated number.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[3]
PANEL_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/processed/france_ze2020"

TARGET_COL = "observed_value"
FEATURE_COLS = ["lag_1", "lag_2", "lag_3", "growth_1y_safe", "growth_2y_safe"]
FEATURE_MASK_COLS = ["mask_lag_1_available", "mask_lag_2_available", "mask_lag_3_available"]

RIDGE_ALPHA = 1.0
RIDGE_MIN_TRAIN_YEARS = 4

DEFAULT_EVAL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

CLAIM_STATUS = "exploratory_smoke"


def load_panel(panel_path: Path = PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(panel_path, dtype={"ze2020": str})
    return df.sort_values(["year", "ze2020"]).reset_index(drop=True)


def _feature_complete_mask(df: pd.DataFrame) -> pd.Series:
    return (df[FEATURE_MASK_COLS] == 1).all(axis=1)


def causal_train_test_split(
    panel: pd.DataFrame, eval_year: int, min_train_years: int = RIDGE_MIN_TRAIN_YEARS
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Strictly t-1-and-earlier training rows for `eval_year`, or None if
    fewer than `min_train_years` complete prior years exist."""
    complete = panel[_feature_complete_mask(panel)]
    train = complete[complete["year"] < eval_year]
    n_train_years = train["year"].nunique()
    if n_train_years < min_train_years:
        return None
    test = panel[(panel["year"] == eval_year) & _feature_complete_mask(panel)]
    return train, test


def predict_persistence(test: pd.DataFrame) -> np.ndarray:
    """y_hat = lag_1 (last observed year). No fitting, no parameters."""
    return test["lag_1"].to_numpy(dtype=float)


def fit_predict_ridge(
    train: pd.DataFrame, test: pd.DataFrame, alpha: float = RIDGE_ALPHA
) -> np.ndarray:
    model = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
    model.fit(
        train[FEATURE_COLS].to_numpy(dtype=float),
        train[TARGET_COL].to_numpy(dtype=float),
    )
    return model.predict(test[FEATURE_COLS].to_numpy(dtype=float))


def compute_wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.abs(y_true).sum()
    if denom == 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denom)


def run_baselines(
    panel: pd.DataFrame,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    min_train_years: int = RIDGE_MIN_TRAIN_YEARS,
    alpha: float = RIDGE_ALPHA,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pred_rows = []
    metric_rows = []
    for eval_year in eval_years:
        split = causal_train_test_split(panel, eval_year, min_train_years)
        if split is None:
            continue
        train, test = split
        if test.empty:
            continue

        y_true = test[TARGET_COL].to_numpy(dtype=float)
        y_persistence = predict_persistence(test)
        y_ridge = fit_predict_ridge(train, test, alpha=alpha)

        for model_name, y_pred in (("persistence", y_persistence), ("ridge", y_ridge)):
            for ze2020, year, yt, yp in zip(test["ze2020"], test["year"], y_true, y_pred):
                pred_rows.append(
                    {
                        "ze2020": ze2020,
                        "year": int(year),
                        "model": model_name,
                        "y_true": float(yt),
                        "y_pred": float(yp),
                        "claim_status": CLAIM_STATUS,
                    }
                )
            metric_rows.append(
                {
                    "eval_year": eval_year,
                    "model": model_name,
                    "n_test": len(test),
                    "n_train_years": train["year"].nunique(),
                    "wmape": compute_wmape(y_true, y_pred),
                    "claim_status": CLAIM_STATUS,
                }
            )

    predictions = pd.DataFrame(pred_rows)
    metrics = pd.DataFrame(metric_rows)
    return predictions, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="France ZE2020 minimal current baselines (exploratory smoke, not a headline claim)"
    )
    parser.add_argument("--panel-path", type=Path, default=PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--min-train-years", type=int, default=RIDGE_MIN_TRAIN_YEARS)
    parser.add_argument("--alpha", type=float, default=RIDGE_ALPHA)
    args = parser.parse_args()

    panel = load_panel(args.panel_path)
    predictions, metrics = run_baselines(
        panel, args.eval_years, args.min_train_years, args.alpha
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = args.output_dir / "fr_ze2020_baseline_predictions_v1.csv"
    metrics_path = args.output_dir / "fr_ze2020_baseline_metrics_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    print("EXPLORATORY SMOKE BASELINE -- not a validated headline claim.")
    print(metrics.pivot(index="eval_year", columns="model", values="wmape"))
    print(f"Mean yearly WMAPE: {metrics.groupby('model')['wmape'].mean().to_dict()}")
    print(f"Predictions: {pred_path}")
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
