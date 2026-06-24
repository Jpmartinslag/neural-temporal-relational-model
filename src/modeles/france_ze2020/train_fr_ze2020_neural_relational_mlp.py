"""
NEURAL RELATIONAL SMOKE PROTOTYPE -- France ZE2020 MVP3-A.

See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md,
"MVP3 neural prototypes" section. This is a smoke/prototype comparison, not
a headline result: no causal claim, no performance claim, no automatic
recommendation.

PyTorch is NOT installed in this environment (`import torch` fails) and the
task's own rule forbids adding a heavy new dependency -- so this prototype
uses `sklearn.neural_network.MLPRegressor` (already an existing project
dependency, see scikit-learn usage in train_fr_ze2020_baselines.py) instead
of a hand-written PyTorch model. It is still a real (small) neural network:
a 2-hidden-layer MLP, trained causally, with permutation-importance feature
signals exported afterwards.

Reads ONLY:
  data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv
    (time + ZE-to-ZE + ZE-to-sector features, already causal)
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
    (read-only, used ONLY to attach the dominant sector's own national-level
    share/growth signal onto each ZE-year row via a self-join on
    dominant_sector_lag_1 -- these two columns do not otherwise exist at the
    ZE x year grain)

Never dynamic_stgnn_feature_panel_v1.csv, never graph_adjacency_core_v0.csv /
graph_adjacency_mobility_v0.csv.

Four models evaluated on the SAME held-out test rows per eval year (the
discipline already established for MVP2, see HERALD_17 section 10):
  - persistence       (y_hat = lag_1)
  - ridge_temporal     (reused from train_fr_ze2020_baselines.py, unmodified)
  - ridge_relational   (reused from train_fr_ze2020_relational_baselines.py,
                        unmodified)
  - mlp_relational     (this script's own MLPRegressor over temporal +
                        ZE-to-ZE + sector features)

Outputs:
  data/processed/france_ze2020/fr_ze2020_neural_relational_predictions_v1.csv
  data/processed/france_ze2020/fr_ze2020_neural_relational_metrics_v1.csv
  data/processed/france_ze2020/fr_ze2020_neural_relational_feature_signals_v1.csv
    (permutation importance per feature per eval_year -- exploratory only,
    NOT a causal attribution)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.inspection import permutation_importance
from sklearn.neural_network import MLPRegressor
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
from src.modeles.france_ze2020.train_fr_ze2020_relational_baselines import (  # noqa: E402
    COMBINED_FEATURE_COLS as RIDGE_RELATIONAL_FEATURE_COLS,
)
from src.modeles.france_ze2020.train_fr_ze2020_relational_baselines import (  # noqa: E402
    TEMPORAL_FEATURE_COLS as RIDGE_TEMPORAL_FEATURE_COLS,
)
from src.modeles.france_ze2020.train_fr_ze2020_relational_baselines import (  # noqa: E402
    fit_predict_ridge,
)

PROTOTYPE_PANEL_PATH = (
    REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv"
)
SECTOR_FEATURES_PATH = REPO_ROOT / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/processed/france_ze2020"

TARGET_COL = "observed_value"

NEURAL_FEATURE_COLS = [
    "lag_1",
    "lag_2",
    "lag_3",
    "growth_1y_safe",
    "growth_2y_safe",
    "similar_ze_lag_1_mean",
    "similar_ze_lag_1_weighted_mean",
    "similar_ze_growth_1y_safe_mean",
    "similar_ze_count",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "top_sector_signal_lag_1",
    "national_sector_growth_lag_1",
    "national_sector_share_lag_1",
]

COMPLETENESS_MASK_COLS = [
    "mask_lag_1_available",
    "mask_lag_2_available",
    "mask_lag_3_available",
    "relational_feature_available",
    "mask_ze_sector_distribution_lag_1_available",
]

SEED = 42
DEFAULT_MAX_EPOCHS = 300
HIDDEN_LAYER_SIZES = (16, 8)
CLAIM_STATUS = "neural_relational_smoke"

LAG_1_FEATURE_IDX = NEURAL_FEATURE_COLS.index("lag_1")


def load_prototype_panel(path: Path = PROTOTYPE_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def attach_dominant_sector_national_signal(
    panel: pd.DataFrame, sector_features_path: Path = SECTOR_FEATURES_PATH
) -> pd.DataFrame:
    """national_sector_share_lag_1 / national_sector_growth_lag_1 exist only
    at the (sector_code, year) grain in fr_ze2020_sector_relational_features.csv
    -- resolved here for each ZE-year row's OWN dominant_sector_lag_1, via a
    read-only self-join (neither input file is modified)."""
    sector_features = pd.read_csv(sector_features_path, dtype={"ze2020": str})
    sector_features["year"] = sector_features["year"].astype(int)

    national = sector_features[
        ["ze2020", "year", "sector_code", "national_sector_share_lag_1", "national_sector_growth_lag_1"]
    ].rename(columns={"sector_code": "dominant_sector_lag_1"})

    merged = panel.merge(national, on=["ze2020", "year", "dominant_sector_lag_1"], how="left")
    return merged


def _completeness_mask(df: pd.DataFrame) -> pd.Series:
    masks_ok = (df[COMPLETENESS_MASK_COLS] == 1).all(axis=1)
    features_present = df[NEURAL_FEATURE_COLS].notna().all(axis=1)
    return masks_ok & features_present


def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.abs(y_true - y_pred).mean())


def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


class RatioToLevelMLP(BaseEstimator, RegressorMixin):
    """Wraps an MLP trained on the RATIO target (observed_value / lag_1,
    centered near 1.0) and reconstructs a level-scale prediction by
    multiplying back by lag_1. observed_value's raw scale spans ~230 to
    ~180,000 across zones (Paris-area ZE2020 dwarfs rural ones); a plain
    MLPRegressor trained directly on that raw scale collapses to predicting
    near-zero (WMAPE ~1.0, verified empirically before this fix) -- the
    ratio reformulation is the standard fix for heterogeneous-scale panel
    targets and keeps the learning target in a numerically stable range
    ([~0.87, ~1.33] in this panel) without fabricating a different target
    concept (lag_1 is already this script's own most-causal feature)."""

    def __init__(self, ratio_pipeline: Pipeline, lag1_col_idx: int = LAG_1_FEATURE_IDX):
        self.ratio_pipeline = ratio_pipeline
        self.lag1_col_idx = lag1_col_idx

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "RatioToLevelMLP":
        """No-op: the wrapped ratio_pipeline is already fitted before
        construction. Only present so sklearn.inspection.permutation_importance's
        estimator-interface check (which requires .fit, but does not call it
        when evaluating an already-fitted model) accepts this wrapper."""
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        ratio_pred = self.ratio_pipeline.predict(X)
        return ratio_pred * X[:, self.lag1_col_idx]


def fit_predict_mlp(
    train: pd.DataFrame,
    test: pd.DataFrame,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    seed: int = SEED,
) -> tuple[np.ndarray, RatioToLevelMLP]:
    ratio_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPRegressor(
                    hidden_layer_sizes=HIDDEN_LAYER_SIZES,
                    activation="relu",
                    solver="adam",
                    max_iter=max_epochs,
                    random_state=seed,
                    early_stopping=True,
                    n_iter_no_change=10,
                ),
            ),
        ]
    )
    X_train = train[NEURAL_FEATURE_COLS].to_numpy(dtype=float)
    ratio_train = (train[TARGET_COL] / train["lag_1"]).to_numpy(dtype=float)
    ratio_pipeline.fit(X_train, ratio_train)

    model = RatioToLevelMLP(ratio_pipeline)
    y_pred = model.predict(test[NEURAL_FEATURE_COLS].to_numpy(dtype=float))
    return y_pred, model


def run_neural_relational_smoke(
    panel: pd.DataFrame,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    min_train_years: int = RIDGE_MIN_TRAIN_YEARS,
    alpha: float = RIDGE_ALPHA,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    complete = panel[_completeness_mask(panel)]

    pred_rows = []
    metric_rows = []
    signal_rows = []

    for eval_year in eval_years:
        test = complete[complete["year"] == eval_year]
        if test.empty:
            continue
        train = complete[complete["year"] < eval_year]
        if train["year"].nunique() < min_train_years:
            continue

        y_true = test[TARGET_COL].to_numpy(dtype=float)
        predictions: dict[str, np.ndarray] = {
            "persistence": predict_persistence(test),
            "ridge_temporal": fit_predict_ridge(train, test, RIDGE_TEMPORAL_FEATURE_COLS, alpha),
            "ridge_relational": fit_predict_ridge(train, test, RIDGE_RELATIONAL_FEATURE_COLS, alpha),
        }
        mlp_pred, mlp_model = fit_predict_mlp(train, test, max_epochs=max_epochs, seed=seed)
        predictions["mlp_relational"] = mlp_pred

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
                    "n_train_years": train["year"].nunique(),
                    "wmape": compute_wmape(y_true, y_pred),
                    "mae": compute_mae(y_true, y_pred),
                    "rmse": compute_rmse(y_true, y_pred),
                    "claim_status": CLAIM_STATUS,
                }
            )

        importances = permutation_importance(
            mlp_model,
            test[NEURAL_FEATURE_COLS].to_numpy(dtype=float),
            y_true,
            n_repeats=10,
            random_state=seed,
            scoring="neg_mean_absolute_error",
        )
        for feature, importance_score in zip(NEURAL_FEATURE_COLS, importances.importances_mean):
            signal_rows.append(
                {
                    "feature": feature,
                    "importance_score": float(importance_score),
                    "eval_year": eval_year,
                    "claim_status": CLAIM_STATUS,
                }
            )

    predictions_df = pd.DataFrame(pred_rows)
    metrics_df = pd.DataFrame(metric_rows)
    signals_df = pd.DataFrame(signal_rows)
    return predictions_df, metrics_df, signals_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 neural relational smoke prototype (MVP3-A) -- "
            "persistence vs. ridge_temporal vs. ridge_relational vs. mlp_relational, "
            "not a headline claim, not causal, not a recommendation"
        )
    )
    parser.add_argument("--panel-path", type=Path, default=PROTOTYPE_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--min-train-years", type=int, default=RIDGE_MIN_TRAIN_YEARS)
    parser.add_argument("--alpha", type=float, default=RIDGE_ALPHA)
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    panel = load_prototype_panel(args.panel_path)
    panel = attach_dominant_sector_national_signal(panel)

    predictions, metrics, signals = run_neural_relational_smoke(
        panel,
        eval_years=args.eval_years,
        min_train_years=args.min_train_years,
        alpha=args.alpha,
        max_epochs=args.max_epochs,
        seed=args.seed,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = args.output_dir / "fr_ze2020_neural_relational_predictions_v1.csv"
    metrics_path = args.output_dir / "fr_ze2020_neural_relational_metrics_v1.csv"
    signals_path = args.output_dir / "fr_ze2020_neural_relational_feature_signals_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    signals.to_csv(signals_path, index=False)

    print("NEURAL RELATIONAL SMOKE -- not a validated headline claim, not causal, not a recommendation.")
    print(metrics.pivot(index="eval_year", columns="model", values="wmape"))
    print(f"Mean WMAPE (each model's own available years): {metrics.groupby('model')['wmape'].mean().to_dict()}")
    print(f"Predictions: {pred_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Feature signals (permutation importance, exploratory only): {signals_path}")


if __name__ == "__main__":
    main()
