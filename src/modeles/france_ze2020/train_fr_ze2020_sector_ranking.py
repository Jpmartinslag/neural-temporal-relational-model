"""
HERALD -- France ZE2020 temporal-relational sector ranking.

First ranking-oriented training script after HERALD_23. This is a neural
temporal-relational ranking block, not a static graph run. It trains/evaluates
simple baselines, Ridge, and a small MLP over audited temporal, sector, and
relation indicators.

Output is exploratory ranking evidence only: no causal claim, no automatic
recommendation, no policy prescription.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_sector_ranking_panel import (
    FEATURE_COLUMNS,
    OUT_PATH as RANKING_PANEL_PATH,
)

DEFAULT_OUTPUT_DIR = ROOT / "data/processed/france_ze2020"
DEFAULT_EVAL_YEARS = [2019, 2020, 2021, 2022]
DEFAULT_EVAL_YEARS_BY_HORIZON = {
    1: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    3: DEFAULT_EVAL_YEARS,
}
DEFAULT_K = 3
DEFAULT_MAX_EPOCHS = 400
SEED = 42
CLAIM_STATUS = "sector_ranking_exploratory_not_recommendation"

MODEL_FEATURE_COLUMNS = FEATURE_COLUMNS


def load_ranking_panel(path: Path = RANKING_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def target_columns(target_horizon: int) -> tuple[str, str]:
    if target_horizon not in {1, 3}:
        raise ValueError(f"Unsupported target_horizon={target_horizon}; expected 1 or 3")
    return f"future_growth_{target_horizon}y", f"future_top3_growth_{target_horizon}y_label"


def mature_training_rows(
    frame: pd.DataFrame,
    *,
    eval_year: int,
    target_horizon: int,
) -> pd.DataFrame:
    """Return rows whose future outcome is observable by ``eval_year``."""
    outcome_year = frame["decision_year"].astype(int) + int(target_horizon)
    return frame[outcome_year <= int(eval_year)].copy()


def _with_target_label(df: pd.DataFrame, target_horizon: int) -> pd.DataFrame:
    target_col, label_col = target_columns(target_horizon)
    if target_col not in df.columns:
        raise ValueError(f"Missing target column: {target_col}")
    out = df.copy()
    if label_col not in out.columns:
        rank_col = f"future_rank_growth_{target_horizon}y_in_ze_year"
        out[rank_col] = (
            out.groupby(["ze2020", "decision_year"])[target_col]
            .rank(ascending=False, method="min")
        )
        out[label_col] = (
            (out[rank_col] <= DEFAULT_K) & np.isfinite(out[target_col].to_numpy(dtype=float))
        ).astype(int)
    return out


def _complete(df: pd.DataFrame, target_horizon: int = 3) -> pd.DataFrame:
    target_col, _ = target_columns(target_horizon)
    finite_features = np.isfinite(df[MODEL_FEATURE_COLUMNS].to_numpy(dtype=float)).all(axis=1)
    finite_target = np.isfinite(df[target_col].to_numpy(dtype=float))
    return df[(df["ranking_feature_complete"] == 1) & finite_features & finite_target].copy()


def _ndcg_at_k(group: pd.DataFrame, score_col: str, k: int, label_col: str) -> float:
    ranked = group.sort_values(score_col, ascending=False).head(k)
    gains = ranked[label_col].to_numpy(dtype=float)
    discounts = 1.0 / np.log2(np.arange(2, len(gains) + 2))
    dcg = float((gains * discounts).sum())
    ideal = group.sort_values(label_col, ascending=False).head(k)
    ideal_gains = ideal[label_col].to_numpy(dtype=float)
    idcg = float((ideal_gains * discounts[: len(ideal_gains)]).sum())
    return dcg / idcg if idcg > 0 else float("nan")


def ranking_metrics(
    predictions: pd.DataFrame,
    model_name: str,
    k: int,
    target_col: str = "future_growth_3y",
    label_col: str = "future_top3_growth_3y_label",
) -> dict[str, float]:
    rows = []
    for (_, _), group in predictions.groupby(["ze2020", "decision_year"]):
        if len(group) < k:
            continue
        top_pred = group.sort_values("score", ascending=False).head(k)
        relevant = set(group.loc[group[label_col] == 1, "sector_code"])
        selected = set(top_pred["sector_code"])
        hit_count = len(selected & relevant)
        rows.append(
            {
                "precision_at_k": hit_count / k,
                "hit_rate_at_k": 1.0 if hit_count else 0.0,
                "ndcg_at_k": _ndcg_at_k(group, "score", k, label_col),
                "mean_future_growth_top_k": float(top_pred[target_col].mean()),
                "mean_future_growth_actual_top_k": float(
                    group.sort_values(target_col, ascending=False).head(k)[target_col].mean()
                ),
            }
        )
    if not rows:
        return {
            "model": model_name,
            "precision_at_k": float("nan"),
            "hit_rate_at_k": float("nan"),
            "ndcg_at_k": float("nan"),
            "mean_future_growth_top_k": float("nan"),
            "mean_future_growth_actual_top_k": float("nan"),
        }
    metrics = pd.DataFrame(rows).mean(numeric_only=True).to_dict()
    metrics["model"] = model_name
    return metrics


def _baseline_scores(test: pd.DataFrame, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {
        "random": rng.random(len(test)),
        "past_volume": test["sector_count_t"].to_numpy(dtype=float),
        "past_growth": test["sector_growth_lag_1"].to_numpy(dtype=float),
        "specialization": test["sector_share_t"].to_numpy(dtype=float),
        "national_growth": test["national_sector_growth_lag_1"].to_numpy(dtype=float),
        "relation_signal": test["relation_signal_strength_mean_to_t"].to_numpy(dtype=float),
    }


def _fit_predict_ridge(train: pd.DataFrame, test: pd.DataFrame, target_col: str) -> np.ndarray:
    model = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    model.fit(train[MODEL_FEATURE_COLUMNS], train[target_col])
    return model.predict(test[MODEL_FEATURE_COLUMNS])


def _fit_predict_mlp(
    train: pd.DataFrame,
    test: pd.DataFrame,
    seed: int,
    max_epochs: int,
    target_col: str,
) -> np.ndarray:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPRegressor(
                    hidden_layer_sizes=(32, 16),
                    activation="relu",
                    solver="adam",
                    max_iter=max_epochs,
                    random_state=seed,
                    early_stopping=True,
                    n_iter_no_change=15,
                ),
            ),
        ]
    )
    model.fit(train[MODEL_FEATURE_COLUMNS], train[target_col])
    return model.predict(test[MODEL_FEATURE_COLUMNS])


def run_sector_ranking(
    panel: pd.DataFrame,
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    k: int = DEFAULT_K,
    min_train_years: int = 3,
    seed: int = SEED,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    target_horizon: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = _with_target_label(panel, target_horizon=target_horizon)
    target_col, label_col = target_columns(target_horizon)
    complete = _complete(panel, target_horizon=target_horizon)
    pred_rows = []
    metric_rows = []

    for eval_year in eval_years:
        test = complete[complete["decision_year"] == eval_year].copy()
        train = mature_training_rows(
            complete,
            eval_year=eval_year,
            target_horizon=target_horizon,
        )
        if test.empty or train["decision_year"].nunique() < min_train_years:
            continue

        scores = _baseline_scores(test, seed=seed + eval_year)
        scores["ridge_ranking"] = _fit_predict_ridge(train, test, target_col=target_col)
        scores["mlp_temporal_relational"] = _fit_predict_mlp(
            train,
            test,
            seed=seed,
            max_epochs=max_epochs,
            target_col=target_col,
        )

        for model_name, score_values in scores.items():
            pred = test[
                [
                    "ze2020",
                    "ze2020_label",
                    "sector_code",
                    "sector_label",
                    "decision_year",
                    target_col,
                    label_col,
                ]
            ].copy()
            pred = pred.rename(columns={target_col: "target_growth", label_col: "target_top3_label"})
            pred["target_horizon_years"] = target_horizon
            pred["model"] = model_name
            pred["score"] = score_values
            pred["rank_predicted"] = pred.groupby(["ze2020", "decision_year"])["score"].rank(
                ascending=False, method="first"
            )
            pred["claim_status"] = CLAIM_STATUS
            pred_rows.append(pred)

            m = ranking_metrics(
                pred,
                model_name,
                k,
                target_col="target_growth",
                label_col="target_top3_label",
            )
            m.update(
                {
                    "eval_year": eval_year,
                    "target_horizon_years": target_horizon,
                    "k": k,
                    "n_test_rows": len(test),
                    "n_test_groups": test.groupby(["ze2020", "decision_year"]).ngroups,
                    "n_train_years": train["decision_year"].nunique(),
                    "claim_status": CLAIM_STATUS,
                }
            )
            metric_rows.append(m)

    predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    metrics = pd.DataFrame(metric_rows)
    return predictions, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 sector ranking: baselines + neural temporal-relational MLP. "
            "Exploratory only, not a causal or automatic recommendation claim."
        )
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-horizon", type=int, choices=[1, 3], default=3)
    parser.add_argument("--eval-years", type=int, nargs="+", default=None)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--min-train-years", type=int, default=3)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--max-epochs", type=int, default=DEFAULT_MAX_EPOCHS)
    args = parser.parse_args()

    panel = load_ranking_panel(args.panel)
    eval_years = args.eval_years or DEFAULT_EVAL_YEARS_BY_HORIZON[args.target_horizon]
    predictions, metrics = run_sector_ranking(
        panel,
        eval_years=eval_years,
        k=args.k,
        min_train_years=args.min_train_years,
        seed=args.seed,
        max_epochs=args.max_epochs,
        target_horizon=args.target_horizon,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = args.output_dir / f"fr_ze2020_sector_ranking_{args.target_horizon}y_predictions_v1.csv"
    metrics_path = args.output_dir / f"fr_ze2020_sector_ranking_{args.target_horizon}y_metrics_v1.csv"
    predictions.to_csv(pred_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    print("SECTOR RANKING -- exploratory, not causal, not automatic recommendation.")
    print(metrics.pivot(index="eval_year", columns="model", values="ndcg_at_k"))
    print(f"Predictions: {pred_path}")
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
