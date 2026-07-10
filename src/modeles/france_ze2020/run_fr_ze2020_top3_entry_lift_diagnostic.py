"""
HERALD -- France ZE2020 target-aligned relation-lift diagnostic.

Builds rolling relation-lift features for the future top-3 entry target using
only prior decision years. This is a diagnostic for improving the relation
layer, not a final model and not an automatic recommendation system.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.audit_fr_ze2020_top3_entry_target import (  # noqa: E402
    add_top3_entry_labels,
)
from src.modeles.france_ze2020.run_fr_ze2020_top3_entry_ranking_smoke import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    DEFAULT_SEEDS,
    _complete_frame,
    _fit_predict_logit,
    _fit_predict_mlp,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (  # noqa: E402
    DEFAULT_K,
    MODEL_FEATURE_COLUMNS,
    RANKING_PANEL_PATH,
    load_ranking_panel,
    ranking_metrics,
)

CLAIM_STATUS = "top3_entry_lift_diagnostic_not_recommendation"
RELATION_BIN_COLUMNS = [
    "relation_has_signal_bin",
    "relation_count_bin",
    "relation_strength_bin",
    "relation_stability_bin",
]
LIFT_SUFFIXES = ["entry_lift_prior", "entry_rate_prior", "entry_rows_prior"]
FEATURE_CONFIGS = [
    "no_relation_features",
    "base_formula_features",
    "target_aligned_lift_features",
    "base_plus_target_aligned_lifts",
    "shuffled_target_aligned_lifts",
]


def relation_lift_columns() -> list[str]:
    return [f"{col}_{suffix}" for col in RELATION_BIN_COLUMNS for suffix in LIFT_SUFFIXES]


def add_relation_bins(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    out["relation_has_signal_bin"] = (out["relation_count_to_t"].astype(float) > 0).astype(int)
    out["relation_count_bin"] = pd.cut(
        out["relation_count_to_t"].astype(float),
        bins=[-1, 0, 1, 4, np.inf],
        labels=[0, 1, 2, 3],
    ).astype(int)
    out["relation_strength_bin"] = pd.cut(
        out["relation_signal_strength_max_to_t"].astype(float),
        bins=[-np.inf, 0, 0.25, 0.5, 0.75, np.inf],
        labels=[0, 1, 2, 3, 4],
    ).astype(int)
    out["relation_stability_bin"] = pd.cut(
        out["relation_stability_mean_to_t"].astype(float),
        bins=[-np.inf, 0, 0.25, 0.5, 0.75, np.inf],
        labels=[0, 1, 2, 3, 4],
    ).astype(int)
    return out


def add_target_aligned_relation_lifts(panel: pd.DataFrame, target_horizon: int = 3) -> pd.DataFrame:
    """Add rolling prior-year relation lift features without mutating input."""
    out = add_relation_bins(add_top3_entry_labels(panel, horizons=[target_horizon]))
    target_col = f"future_growth_{target_horizon}y"
    label_col = f"future_top3_entry_{target_horizon}y_label"
    mask_col = f"mask_future_growth_{target_horizon}y_available"

    for col in relation_lift_columns():
        out[col] = 1.0 if col.endswith("_lift_prior") else 0.0

    eligible = (
        (out["ranking_feature_complete"] == 1)
        & (out[mask_col] == 1)
        & np.isfinite(out[target_col].to_numpy(dtype=float))
    )
    for decision_year in sorted(int(y) for y in out["decision_year"].unique()):
        hist = out[eligible & (out["decision_year"] < decision_year)].copy()
        apply_idx = out.index[out["decision_year"] == decision_year]
        if hist.empty:
            continue
        base_rate = float(hist[label_col].mean())
        if not np.isfinite(base_rate) or base_rate <= 0:
            continue
        for bin_col in RELATION_BIN_COLUMNS:
            stats = hist.groupby(bin_col)[label_col].agg(["mean", "count"])
            rate = out.loc[apply_idx, bin_col].map(stats["mean"]).fillna(base_rate).astype(float)
            rows = out.loc[apply_idx, bin_col].map(stats["count"]).fillna(0).astype(int)
            out.loc[apply_idx, f"{bin_col}_entry_rate_prior"] = rate
            out.loc[apply_idx, f"{bin_col}_entry_rows_prior"] = rows
            out.loc[apply_idx, f"{bin_col}_entry_lift_prior"] = (rate / base_rate).clip(0.25, 2.0)
    return out


def _shuffle_lift_columns(panel: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = panel.copy()
    rng = np.random.default_rng(seed)
    for col in relation_lift_columns():
        out[col] = out.groupby("decision_year")[col].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


def _feature_columns(config_name: str) -> list[str]:
    base = list(MODEL_FEATURE_COLUMNS)
    no_relation = [col for col in base if not col.startswith("relation_")]
    lift_cols = relation_lift_columns()
    if config_name == "no_relation_features":
        return no_relation
    if config_name == "base_formula_features":
        return base
    if config_name == "target_aligned_lift_features":
        return no_relation + lift_cols
    if config_name in {"base_plus_target_aligned_lifts", "shuffled_target_aligned_lifts"}:
        return base + lift_cols
    raise ValueError(f"Unknown feature config: {config_name}")


def run_top3_entry_lift_diagnostic(
    panel: pd.DataFrame,
    *,
    target_horizon: int = 3,
    eval_years: list[int] | None = None,
    seeds: list[int] | None = None,
    feature_configs: list[str] | None = None,
    max_epochs: int = 60,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_years = eval_years or DEFAULT_EVAL_YEARS
    seeds = seeds or DEFAULT_SEEDS
    feature_configs = feature_configs or FEATURE_CONFIGS
    unknown = set(feature_configs).difference(FEATURE_CONFIGS)
    if unknown:
        raise ValueError(f"Unknown feature configs: {sorted(unknown)}")

    labelled = add_target_aligned_relation_lifts(panel, target_horizon=target_horizon)
    target_col = f"future_growth_{target_horizon}y"
    label_col = f"future_top3_entry_{target_horizon}y_label"
    pred_rows = []
    metric_rows = []

    for seed in seeds:
        shuffled = _shuffle_lift_columns(labelled, seed=seed + 2000)
        frames = {
            "no_relation_features": labelled,
            "base_formula_features": labelled,
            "target_aligned_lift_features": labelled,
            "base_plus_target_aligned_lifts": labelled,
            "shuffled_target_aligned_lifts": shuffled,
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
        description="France ZE2020 target-aligned relation-lift diagnostic; exploratory only."
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-horizon", type=int, choices=[3], default=3)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--feature-configs", nargs="+", choices=FEATURE_CONFIGS, default=FEATURE_CONFIGS)
    parser.add_argument("--max-epochs", type=int, default=60)
    args = parser.parse_args()

    panel = load_ranking_panel(args.panel)
    predictions, metrics, summary = run_top3_entry_lift_diagnostic(
        panel,
        target_horizon=args.target_horizon,
        eval_years=args.eval_years,
        seeds=args.seeds,
        feature_configs=args.feature_configs,
        max_epochs=args.max_epochs,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "fr_ze2020_top3_entry_lift_predictions_v1.csv", index=False)
    metrics.to_csv(args.output_dir / "fr_ze2020_top3_entry_lift_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / "fr_ze2020_top3_entry_lift_summary_v1.csv", index=False)
    (args.output_dir / "fr_ze2020_top3_entry_lift_run_v1.json").write_text(
        json.dumps(
            {
                "status": "TOP3_ENTRY_LIFT_DIAGNOSTIC_COMPLETE",
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

    print("TOP-3 ENTRY RELATION-LIFT DIAGNOSTIC -- not causal, not recommendation.")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
