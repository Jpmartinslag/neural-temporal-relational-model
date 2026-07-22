"""Evaluate context-conditioned lagged sector relations across held-out ZEs.

DEC-077 compares a pooled linear source-lag relation with a small nonlinear
model that may condition the same lag on prior ZE composition. All features end
at t-1; the target is the target sector's observed growth ending at t.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
SECTOR_PANEL_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
)
FEATURE_PANEL_PATH = (
    ROOT
    / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
)
DEFAULT_EVAL_YEARS = list(range(2019, 2026))
DEFAULT_SEEDS = [42, 43, 44, 45, 46]
DEFAULT_FOLDS = list(range(5))
SPLIT_SEED = 20260722
CLAIM_STATUS = (
    "context_conditioned_sector_relation_gate_exploratory_precedence_not_causal"
)
VIEW_NAMES = [
    "no_source_mlp",
    "pooled_linear_relation",
    "context_conditioned_mlp",
    "source_shuffled_mlp",
    "context_shuffled_mlp",
    "target_shuffled_mlp",
]

CONTEXT_COLUMNS = [
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
]
TARGET_COLUMNS = [
    "target_growth_lag_1",
    "target_growth_lag_2",
    "target_share_lag_1",
    "target_national_growth_lag_1",
]
SOURCE_COLUMNS = [
    "source_growth_lag_1",
    "source_growth_lag_2",
    "source_share_lag_1",
    "source_national_growth_lag_1",
]
COMMON_FEATURES = [
    "target_sector",
    "dominant_sector_lag_1",
    *TARGET_COLUMNS,
    *CONTEXT_COLUMNS,
]
RELATION_FEATURES = ["source_sector", *SOURCE_COLUMNS]


def assign_ze_folds(zones: pd.Series, n_folds: int = 5) -> dict[str, int]:
    unique = np.array(sorted(zones.astype(str).str.zfill(4).unique()))
    shuffled = np.random.default_rng(SPLIT_SEED).permutation(unique)
    return {zone: int(index % n_folds) for index, zone in enumerate(shuffled)}


def build_pair_samples(
    sector_panel: pd.DataFrame, feature_panel: pd.DataFrame
) -> pd.DataFrame:
    observed = sector_panel.copy()
    observed["ze2020"] = observed["ze2020"].astype(str).str.zfill(4)
    observed = observed.sort_values(["ze2020", "sector_code", "year"])
    previous = observed.groupby(["ze2020", "sector_code"])[
        "sector_establishment_creations"
    ].shift(1)
    observed["target_growth"] = np.where(
        previous > 0,
        (observed["sector_establishment_creations"] - previous) / previous,
        np.nan,
    )
    labels = observed[["ze2020", "year", "sector_code", "target_growth"]]

    features = feature_panel.copy()
    features["ze2020"] = features["ze2020"].astype(str).str.zfill(4)
    target = features.rename(
        columns={
            "sector_code": "target_sector",
            "sector_growth_lag_1": "target_growth_lag_1",
            "sector_growth_lag_2": "target_growth_lag_2",
            "sector_share_lag_1": "target_share_lag_1",
            "national_sector_growth_lag_1": "target_national_growth_lag_1",
        }
    )
    target = target.merge(
        labels.rename(columns={"sector_code": "target_sector"}),
        on=["ze2020", "year", "target_sector"],
        how="inner",
        validate="one_to_one",
    )
    source = features[
        [
            "ze2020",
            "year",
            "sector_code",
            "sector_growth_lag_1",
            "sector_growth_lag_2",
            "sector_share_lag_1",
            "national_sector_growth_lag_1",
        ]
    ].rename(
        columns={
            "sector_code": "source_sector",
            "sector_growth_lag_1": "source_growth_lag_1",
            "sector_growth_lag_2": "source_growth_lag_2",
            "sector_share_lag_1": "source_share_lag_1",
            "national_sector_growth_lag_1": "source_national_growth_lag_1",
        }
    )
    pairs = target.merge(source, on=["ze2020", "year"], how="inner")
    pairs = pairs[pairs["source_sector"] != pairs["target_sector"]].copy()
    required = [
        "target_growth",
        "dominant_sector_lag_1",
        *TARGET_COLUMNS,
        *SOURCE_COLUMNS,
        *CONTEXT_COLUMNS,
    ]
    pairs = pairs.replace([np.inf, -np.inf], np.nan).dropna(subset=required)
    fold_map = assign_ze_folds(pairs["ze2020"])
    pairs["ze_fold"] = pairs["ze2020"].map(fold_map).astype(int)
    key = ["ze2020", "year", "source_sector", "target_sector"]
    if pairs.duplicated(key).any():
        raise ValueError("Duplicate ZE-year-source-target samples")
    return pairs.sort_values(key).reset_index(drop=True)


def _shuffle_entity_block(
    frame: pd.DataFrame,
    *,
    key_columns: list[str],
    group_columns: list[str],
    value_columns: list[str],
    seed: int,
) -> pd.DataFrame:
    selected = frame[key_columns + value_columns]
    conflicts = selected.groupby(key_columns, dropna=False)[value_columns].nunique(
        dropna=False
    )
    if conflicts.gt(1).any().any():
        raise ValueError("Shuffle key identifies conflicting feature blocks")
    base = selected.drop_duplicates(key_columns)
    rng = np.random.default_rng(seed)
    shuffled = base.copy()
    for _, index in base.groupby(group_columns, sort=True).groups.items():
        positions = np.asarray(list(index))
        shuffled.loc[positions, value_columns] = base.loc[
            rng.permutation(positions), value_columns
        ].to_numpy()
    return frame.drop(columns=value_columns).merge(
        shuffled, on=key_columns, how="left", validate="many_to_one"
    )


def shuffle_source(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    return _shuffle_entity_block(
        frame,
        key_columns=["ze2020", "year", "source_sector"],
        group_columns=["year", "source_sector"],
        value_columns=SOURCE_COLUMNS,
        seed=seed,
    )


def shuffle_context(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    return _shuffle_entity_block(
        frame,
        key_columns=["ze2020", "year"],
        group_columns=["year"],
        value_columns=["dominant_sector_lag_1", *CONTEXT_COLUMNS],
        seed=seed,
    )


def shuffle_training_target(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    return _shuffle_entity_block(
        frame,
        key_columns=["ze2020", "year", "target_sector"],
        group_columns=["year", "target_sector"],
        value_columns=["target_growth"],
        seed=seed,
    )


def _matrix(
    train: pd.DataFrame, test: pd.DataFrame, feature_columns: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    categorical = [
        column
        for column in ["source_sector", "target_sector", "dominant_sector_lag_1"]
        if column in feature_columns
    ]
    train_x = pd.get_dummies(
        train[feature_columns], columns=categorical, dtype=float
    )
    test_x = pd.get_dummies(test[feature_columns], columns=categorical, dtype=float)
    test_x = test_x.reindex(columns=train_x.columns, fill_value=0.0)
    return train_x, test_x


def fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    feature_columns: list[str],
    model_kind: str,
    seed: int,
    max_epochs: int,
) -> tuple[np.ndarray, int, bool]:
    train_x, test_x = _matrix(train, test, feature_columns)
    if model_kind == "ridge":
        model = Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=1.0))])
        model.fit(train_x, train["target_growth"])
        return model.predict(test_x), 0, True
    if model_kind != "mlp":
        raise ValueError(f"Unknown model kind: {model_kind}")
    target_mean = float(train["target_growth"].mean())
    target_std = float(train["target_growth"].std(ddof=0))
    if target_std <= 0:
        raise ValueError("Training target has zero variance")
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
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
    model.fit(train_x, (train["target_growth"] - target_mean) / target_std)
    fitted = model.named_steps["model"]
    return (
        model.predict(test_x) * target_std + target_mean,
        int(fitted.n_iter_),
        bool(fitted.n_iter_ < max_epochs),
    )


def evaluate_gate(
    samples: pd.DataFrame,
    *,
    eval_years: list[int],
    seeds: list[int],
    folds: list[int],
    max_epochs: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    all_features = [*COMMON_FEATURES, *RELATION_FEATURES]
    for seed in seeds:
        for eval_year in eval_years:
            for fold in folds:
                train = samples[
                    (samples["year"] < eval_year) & (samples["ze_fold"] != fold)
                ].copy()
                test = samples[
                    (samples["year"] == eval_year) & (samples["ze_fold"] == fold)
                ].copy()
                if train["year"].nunique() < 4 or train.empty or test.empty:
                    continue
                views = [
                    ("no_source_mlp", train, test, COMMON_FEATURES, "mlp", False),
                    (
                        "pooled_linear_relation",
                        train,
                        test,
                        all_features,
                        "ridge",
                        False,
                    ),
                    (
                        "context_conditioned_mlp",
                        train,
                        test,
                        all_features,
                        "mlp",
                        False,
                    ),
                    (
                        "source_shuffled_mlp",
                        shuffle_source(train, seed + eval_year + fold),
                        shuffle_source(test, seed + 1000 + eval_year + fold),
                        all_features,
                        "mlp",
                        False,
                    ),
                    (
                        "context_shuffled_mlp",
                        shuffle_context(train, seed + 2000 + eval_year + fold),
                        shuffle_context(test, seed + 3000 + eval_year + fold),
                        all_features,
                        "mlp",
                        False,
                    ),
                    (
                        "target_shuffled_mlp",
                        shuffle_training_target(
                            train, seed + 4000 + eval_year + fold
                        ),
                        test,
                        all_features,
                        "mlp",
                        True,
                    ),
                ]
                for view, view_train, view_test, columns, kind, target_shuffled in views:
                    prediction, n_iter, model_converged = fit_predict(
                        view_train,
                        view_test,
                        feature_columns=columns,
                        model_kind=kind,
                        seed=seed,
                        max_epochs=max_epochs,
                    )
                    truth = view_test["target_growth"].to_numpy(dtype=float)
                    rows.append(
                        {
                            "view": view,
                            "seed": seed,
                            "eval_year": eval_year,
                            "ze_fold": fold,
                            "n_train": len(view_train),
                            "n_test": len(view_test),
                            "n_train_years": view_train["year"].nunique(),
                            "train_test_ze_overlap": len(
                                set(view_train["ze2020"]) & set(view_test["ze2020"])
                            ),
                            "mae": mean_absolute_error(truth, prediction),
                            "r2": r2_score(truth, prediction),
                            "model_n_iter": n_iter,
                            "model_converged": int(model_converged),
                            "target_shuffled": int(target_shuffled),
                            "claim_status": CLAIM_STATUS,
                        }
                    )
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        raise ValueError("No context-conditioned relation metrics produced")
    numeric = [
        "mae",
        "r2",
        "n_train",
        "n_test",
        "n_train_years",
        "model_n_iter",
        "model_converged",
    ]
    if not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite context-conditioned relation metrics")
    key = ["view", "seed", "eval_year", "ze_fold"]
    if metrics.duplicated(key).any():
        raise ValueError("Duplicate relation metric keys")
    return metrics.sort_values(key).reset_index(drop=True)


def audit_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    real = metrics[metrics["view"] == "context_conditioned_mlp"][keys + ["mae"]]
    real = real.rename(columns={"mae": "real_mae"})
    comparisons: dict[str, dict[str, float | int]] = {}
    for control in [
        "no_source_mlp",
        "pooled_linear_relation",
        "source_shuffled_mlp",
        "context_shuffled_mlp",
        "target_shuffled_mlp",
    ]:
        other = metrics[metrics["view"] == control][keys + ["mae"]].rename(
            columns={"mae": "control_mae"}
        )
        paired = real.merge(other, on=keys, how="inner", validate="one_to_one")
        lift = paired["control_mae"] - paired["real_mae"]
        comparisons[control] = {
            "mean_mae_lift": float(lift.mean()),
            "paired_win_rate": float((lift > 0).mean()),
            "mean_relative_degradation": float(
                (paired["control_mae"] / paired["real_mae"] - 1).mean()
            ),
            "n_pairs": int(len(paired)),
        }
    primary_models = metrics[metrics["view"] != "target_shuffled_mlp"]
    target_shuffle = metrics[metrics["view"] == "target_shuffled_mlp"]
    integrity = {
        "all_metrics_finite": bool(
            np.isfinite(metrics[["mae", "r2"]].to_numpy(dtype=float)).all()
        ),
        "zero_ze_overlap": bool(metrics["train_test_ze_overlap"].eq(0).all()),
        "identical_test_populations": bool(
            metrics.groupby(keys)["n_test"].nunique().eq(1).all()
        ),
        "all_views_present": set(metrics["view"]) == set(VIEW_NAMES),
        "all_primary_models_converged": bool(
            primary_models["model_converged"].eq(1).all()
        ),
        "target_shuffle_convergence_recorded": bool(
            not target_shuffle.empty
            and target_shuffle["model_converged"].isin([0, 1]).all()
        ),
    }
    gate_pass = (
        all(integrity.values())
        and comparisons["no_source_mlp"]["mean_mae_lift"] > 0
        and comparisons["pooled_linear_relation"]["mean_mae_lift"] > 0
        and comparisons["source_shuffled_mlp"]["mean_mae_lift"] > 0
        and comparisons["source_shuffled_mlp"]["paired_win_rate"] >= 0.60
        and comparisons["context_shuffled_mlp"]["mean_mae_lift"] > 0
        and comparisons["context_shuffled_mlp"]["paired_win_rate"] >= 0.60
        and comparisons["target_shuffled_mlp"]["mean_relative_degradation"] >= 0.05
        and comparisons["target_shuffled_mlp"]["paired_win_rate"] >= 0.80
    )
    return {
        "gate_pass": bool(gate_pass),
        "integrity": integrity,
        "comparisons": comparisons,
        "claim_status": CLAIM_STATUS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector-panel", type=Path, default=SECTOR_PANEL_PATH)
    parser.add_argument("--feature-panel", type=Path, default=FEATURE_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--folds", nargs="+", type=int, default=DEFAULT_FOLDS)
    parser.add_argument("--max-epochs", type=int, default=500)
    args = parser.parse_args()

    sector_panel = pd.read_csv(args.sector_panel, dtype={"ze2020": str})
    feature_panel = pd.read_csv(args.feature_panel, dtype={"ze2020": str})
    samples = build_pair_samples(sector_panel, feature_panel)
    metrics = evaluate_gate(
        samples,
        eval_years=args.eval_years,
        seeds=args.seeds,
        folds=args.folds,
        max_epochs=args.max_epochs,
    )
    summary = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_mae=("mae", "mean"),
            mean_r2=("r2", "mean"),
            convergence_rate=("model_converged", "mean"),
            mean_model_n_iter=("model_n_iter", "mean"),
            rows=("mae", "size"),
        )
        .sort_values("view")
    )
    summary["claim_status"] = CLAIM_STATUS
    gate = audit_gate(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_context_conditioned_sector_relation_gate"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
