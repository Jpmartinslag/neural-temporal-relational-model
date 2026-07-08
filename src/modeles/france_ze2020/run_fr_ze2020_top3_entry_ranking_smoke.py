"""
HERALD -- France ZE2020 top-3 entry ranking smoke.

Tests whether formula relation features help rank sectors that enter the future
top-3 growth set. This is a small target-aligned diagnostic, not a final model,
not a dynamic-GNN claim, and not an automatic recommendation system.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.audit_fr_ze2020_top3_entry_target import (  # noqa: E402
    add_top3_entry_labels,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (  # noqa: E402
    DEFAULT_K,
    MODEL_FEATURE_COLUMNS,
    RANKING_PANEL_PATH,
    load_ranking_panel,
    ranking_metrics,
)

DEFAULT_SEEDS = [42, 43, 44]
DEFAULT_EVAL_YEARS = [2017, 2018, 2019, 2020, 2021, 2022]
FEATURE_CONFIGS = [
    "no_relation_features",
    "base_formula_features",
    "shuffled_relation_features",
]
CLAIM_STATUS = "top3_entry_ranking_smoke_not_recommendation"


def _feature_columns(config_name: str) -> list[str]:
    base = list(MODEL_FEATURE_COLUMNS)
    relation_cols = [col for col in base if col.startswith("relation_")]
    if config_name == "base_formula_features":
        return base
    if config_name == "no_relation_features":
        return [col for col in base if col not in relation_cols]
    if config_name == "shuffled_relation_features":
        return base
    raise ValueError(f"Unknown feature config: {config_name}")


def _shuffle_relation_columns(panel: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = panel.copy()
    rng = np.random.default_rng(seed)
    relation_cols = [col for col in MODEL_FEATURE_COLUMNS if col.startswith("relation_")]
    for col in relation_cols:
        out[col] = out.groupby("decision_year")[col].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


def _complete_frame(panel: pd.DataFrame, feature_columns: list[str], target_horizon: int) -> pd.DataFrame:
    target_col = f"future_growth_{target_horizon}y"
    label_col = f"future_top3_entry_{target_horizon}y_label"
    mask_col = f"mask_future_growth_{target_horizon}y_available"
    finite_features = np.isfinite(panel[feature_columns].to_numpy(dtype=float)).all(axis=1)
    finite_target = np.isfinite(panel[target_col].to_numpy(dtype=float))
    return panel[
        (panel["ranking_feature_complete"] == 1)
        & (panel[mask_col] == 1)
        & finite_features
        & finite_target
        & panel[label_col].isin([0, 1])
    ].copy()


def _fit_predict_logit(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
    label_col: str,
    seed: int,
) -> np.ndarray:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logit",
                LogisticRegression(class_weight="balanced", max_iter=500, random_state=seed),
            ),
        ]
    )
    model.fit(train[feature_columns], train[label_col])
    return model.predict_proba(test[feature_columns])[:, 1]


def _fit_predict_mlp(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
    label_col: str,
    seed: int,
    max_epochs: int,
) -> np.ndarray:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
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
    model.fit(train[feature_columns], train[label_col])
    return model.predict_proba(test[feature_columns])[:, 1]


def run_top3_entry_ranking_smoke(
    panel: pd.DataFrame,
    *,
    target_horizon: int = 3,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
    feature_configs: list[str] | None = None,
    max_epochs: int = 80,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    feature_configs = feature_configs or FEATURE_CONFIGS
    unknown = set(feature_configs).difference(FEATURE_CONFIGS)
    if unknown:
        raise ValueError(f"Unknown feature configs: {sorted(unknown)}")

    labelled = add_top3_entry_labels(panel, horizons=[target_horizon])
    target_col = f"future_growth_{target_horizon}y"
    label_col = f"future_top3_entry_{target_horizon}y_label"
    pred_rows = []
    metric_rows = []

    for seed in seeds:
        shuffled = _shuffle_relation_columns(labelled, seed=seed + 1000)
        frames = {
            "no_relation_features": labelled,
            "base_formula_features": labelled,
            "shuffled_relation_features": shuffled,
        }
        for config_name in feature_configs:
            frame = frames[config_name]
            feature_columns = _feature_columns(config_name)
            complete = _complete_frame(frame, feature_columns, target_horizon)
            for eval_year in eval_years:
                test = complete[complete["decision_year"] == eval_year].copy()
                train = complete[complete["decision_year"] < eval_year].copy()
                if test.empty or train["decision_year"].nunique() < 3:
                    continue
                if train[label_col].nunique() < 2 or test[label_col].nunique() < 2:
                    continue

                scores = {
                    "logit_entry_classifier": _fit_predict_logit(
                        train,
                        test,
                        feature_columns,
                        label_col,
                        seed,
                    ),
                    "mlp_entry_classifier": _fit_predict_mlp(
                        train,
                        test,
                        feature_columns,
                        label_col,
                        seed,
                        max_epochs,
                    ),
                }
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
                        ascending=False,
                        method="first",
                    )
                    pred["feature_config"] = config_name
                    pred["seed"] = seed
                    pred["claim_status"] = CLAIM_STATUS
                    pred_rows.append(pred)

                    metrics = ranking_metrics(
                        pred,
                        model_name,
                        DEFAULT_K,
                        target_col="target_growth",
                        label_col="target_top3_label",
                    )
                    metrics.update(
                        {
                            "eval_year": eval_year,
                            "target_horizon_years": target_horizon,
                            "k": DEFAULT_K,
                            "n_test_rows": len(test),
                            "n_test_groups": test.groupby(["ze2020", "decision_year"]).ngroups,
                            "n_train_years": train["decision_year"].nunique(),
                            "feature_config": config_name,
                            "seed": seed,
                            "claim_status": CLAIM_STATUS,
                        }
                    )
                    metric_rows.append(metrics)

    predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    metrics = pd.DataFrame(metric_rows)
    summary = (
        metrics.groupby(["target_horizon_years", "feature_config", "model"], as_index=False)
        .agg(
            mean_ndcg_at_k=("ndcg_at_k", "mean"),
            std_ndcg_at_k=("ndcg_at_k", "std"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_hit_rate_at_k=("hit_rate_at_k", "mean"),
            n_rows=("ndcg_at_k", "size"),
            n_seeds=("seed", "nunique"),
        )
        .fillna({"std_ndcg_at_k": 0.0})
        .sort_values(["model", "mean_ndcg_at_k"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return predictions, metrics, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="France ZE2020 top-3 entry ranking smoke; exploratory only."
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-horizon", type=int, choices=[1, 3], default=3)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--feature-configs", nargs="+", choices=FEATURE_CONFIGS, default=FEATURE_CONFIGS)
    parser.add_argument("--max-epochs", type=int, default=80)
    args = parser.parse_args()

    panel = load_ranking_panel(args.panel)
    predictions, metrics, summary = run_top3_entry_ranking_smoke(
        panel,
        target_horizon=args.target_horizon,
        eval_years=args.eval_years,
        seeds=args.seeds,
        feature_configs=args.feature_configs,
        max_epochs=args.max_epochs,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "fr_ze2020_top3_entry_ranking_predictions_v1.csv", index=False)
    metrics.to_csv(args.output_dir / "fr_ze2020_top3_entry_ranking_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / "fr_ze2020_top3_entry_ranking_summary_v1.csv", index=False)
    (args.output_dir / "fr_ze2020_top3_entry_ranking_run_v1.json").write_text(
        json.dumps(
            {
                "status": "TOP3_ENTRY_RANKING_SMOKE_COMPLETE",
                "panel": str(args.panel),
                "target_horizon": args.target_horizon,
                "eval_years": args.eval_years,
                "seeds": args.seeds,
                "feature_configs": args.feature_configs,
                "max_epochs": args.max_epochs,
                "claim_status": CLAIM_STATUS,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print("TOP-3 ENTRY RANKING SMOKE -- not causal, not recommendation.")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
