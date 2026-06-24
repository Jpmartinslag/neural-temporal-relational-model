"""
RELATIONAL SMOKE BASELINE -- France ZE2020 MVP2 comparison.

Reads ONLY data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv
(never dynamic_stgnn_feature_panel_v1.csv or any legacy adjacency matrix --
see reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md).

Three causal rolling-origin models, evaluated on the SAME held-out rows so
their errors are directly comparable:

  - persistence:       y_hat[t] = lag_1[t]                       (control)
  - ridge_temporal:    Ridge on lag_1/2/3, growth_1y/2y_safe      (= the
                        existing train_fr_ze2020_baselines.py Ridge model,
                        NOT modified or replaced -- this script only adds a
                        third model next to it for comparison)
  - ridge_relational:  ridge_temporal's features + similar_ze_lag_1_mean,
                        similar_ze_lag_1_weighted_mean,
                        similar_ze_growth_1y_safe_mean

This is a smoke/organizational comparison, not a headline result: no claim
of "best model", no causality, no recommendation. Every output row carries
claim_status=relational_smoke_result.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.modeles.france_ze2020.train_fr_ze2020_baselines import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    RIDGE_ALPHA,
    RIDGE_MIN_TRAIN_YEARS,
    compute_wmape,
    predict_persistence,
)

RELATIONAL_PANEL_PATH = (
    REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/processed/france_ze2020"

TARGET_COL = "observed_value"
TEMPORAL_FEATURE_COLS = ["lag_1", "lag_2", "lag_3", "growth_1y_safe", "growth_2y_safe"]
RELATIONAL_FEATURE_COLS = [
    "similar_ze_lag_1_mean",
    "similar_ze_lag_1_weighted_mean",
    "similar_ze_growth_1y_safe_mean",
]
COMBINED_FEATURE_COLS = TEMPORAL_FEATURE_COLS + RELATIONAL_FEATURE_COLS
TEMPORAL_MASK_COLS = ["mask_lag_1_available", "mask_lag_2_available", "mask_lag_3_available"]

CLAIM_STATUS = "relational_smoke_result"


def load_relational_panel(panel_path: Path = RELATIONAL_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(panel_path, dtype={"ze2020": str})
    return df.sort_values(["year", "ze2020"]).reset_index(drop=True)


def _temporal_complete_mask(df: pd.DataFrame) -> pd.Series:
    return (df[TEMPORAL_MASK_COLS] == 1).all(axis=1)


def _relational_complete_mask(df: pd.DataFrame) -> pd.Series:
    return _temporal_complete_mask(df) & (df["relational_feature_available"] == 1)


def fit_predict_ridge(
    train: pd.DataFrame, test: pd.DataFrame, feature_cols: list[str], alpha: float = RIDGE_ALPHA
) -> np.ndarray:
    model = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
    model.fit(
        train[feature_cols].to_numpy(dtype=float),
        train[TARGET_COL].to_numpy(dtype=float),
    )
    return model.predict(test[feature_cols].to_numpy(dtype=float))


def run_relational_baselines(
    panel: pd.DataFrame,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    min_train_years: int = RIDGE_MIN_TRAIN_YEARS,
    alpha: float = RIDGE_ALPHA,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pred_rows = []
    metric_rows = []

    for eval_year in eval_years:
        test = panel[_relational_complete_mask(panel) & (panel["year"] == eval_year)]
        if test.empty:
            continue
        y_true = test[TARGET_COL].to_numpy(dtype=float)

        predictions: dict[str, np.ndarray] = {"persistence": predict_persistence(test)}

        train_temporal = panel[_temporal_complete_mask(panel) & (panel["year"] < eval_year)]
        if train_temporal["year"].nunique() >= min_train_years:
            predictions["ridge_temporal"] = fit_predict_ridge(
                train_temporal, test, TEMPORAL_FEATURE_COLS, alpha
            )

        train_relational = panel[_relational_complete_mask(panel) & (panel["year"] < eval_year)]
        if train_relational["year"].nunique() >= min_train_years:
            predictions["ridge_relational"] = fit_predict_ridge(
                train_relational, test, COMBINED_FEATURE_COLS, alpha
            )

        for model_name, y_pred in predictions.items():
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
                    "n_train_years": (
                        train_relational["year"].nunique()
                        if model_name == "ridge_relational"
                        else train_temporal["year"].nunique()
                        if model_name == "ridge_temporal"
                        else None
                    ),
                    "wmape": compute_wmape(y_true, y_pred),
                    "claim_status": CLAIM_STATUS,
                }
            )

    predictions_df = pd.DataFrame(pred_rows)
    metrics_df = pd.DataFrame(metric_rows)
    return predictions_df, metrics_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 relational smoke comparison "
            "(persistence vs. ridge_temporal vs. ridge_relational) -- not a headline claim"
        )
    )
    parser.add_argument("--panel-path", type=Path, default=RELATIONAL_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--min-train-years", type=int, default=RIDGE_MIN_TRAIN_YEARS)
    parser.add_argument("--alpha", type=float, default=RIDGE_ALPHA)
    args = parser.parse_args()

    panel = load_relational_panel(args.panel_path)
    predictions, metrics = run_relational_baselines(
        panel, args.eval_years, args.min_train_years, args.alpha
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = args.output_dir / "fr_ze2020_relational_baseline_predictions_v1.csv"
    metrics_path = args.output_dir / "fr_ze2020_relational_baseline_metrics_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    print("RELATIONAL SMOKE RESULT -- not a validated headline claim.")
    print(metrics.pivot(index="eval_year", columns="model", values="wmape"))
    print(f"Mean WMAPE (each model's own available years): {metrics.groupby('model')['wmape'].mean().to_dict()}")

    # HERALD Intelligence Layer lesson: never average models over mismatched
    # year sets -- ridge_relational has fewer available eval years (needs
    # min_train_years of *relational* history) than persistence/ridge_temporal.
    years_per_model = metrics.groupby("model")["eval_year"].apply(set)
    comparable_years = sorted(set.intersection(*years_per_model))
    if comparable_years:
        comparable = metrics[metrics["eval_year"].isin(comparable_years)]
        print(
            f"Comparable-window mean WMAPE (years where all models ran, {comparable_years}): "
            f"{comparable.groupby('model')['wmape'].mean().to_dict()}"
        )
    else:
        print("Comparable-window mean WMAPE: no eval year has all models available.")
    print(f"Predictions: {pred_path}")
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
