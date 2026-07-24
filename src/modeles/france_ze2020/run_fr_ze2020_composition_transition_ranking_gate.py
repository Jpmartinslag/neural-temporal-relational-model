"""Rank next-year ZE-sector composition transitions under DEC-080."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.run_fr_ze2020_temporal_bipartite_reconstruction_gate import (
    FOLDS,
    PANEL_PATH,
    SECTORS,
    _stable_rng,
    assign_ze_folds,
    load_share_panel,
)

SEEDS = [42, 43, 44, 45, 46]
EVAL_YEARS = list(range(2017, 2025))
CLAIM_STATUS = "composition_transition_ranking_preflight_not_recommendation"
VIEWS = [
    "zero_change",
    "past_delta",
    "ridge_joint",
    "mlp_joint",
    "mlp_target_history_only",
    "mlp_current_only",
    "mlp_sector_shuffle",
    "mlp_temporal_shuffle",
    "mlp_target_shuffle",
    "random_ranking",
]

CURRENT_COLUMNS = [f"current_{sector}" for sector in SECTORS]
LAG_COLUMNS = [f"lag_{sector}" for sector in SECTORS]
DELTA_COLUMNS = [f"delta_{sector}" for sector in SECTORS]
TARGET_COLUMNS = [f"target_{sector}" for sector in SECTORS]
FULL_FEATURES = CURRENT_COLUMNS + LAG_COLUMNS + DELTA_COLUMNS + TARGET_COLUMNS
CURRENT_FEATURES = CURRENT_COLUMNS + TARGET_COLUMNS
TARGET_HISTORY_FEATURES = ["own_current", "own_lag", "own_delta", *TARGET_COLUMNS]


def build_transition_samples(
    shares: pd.DataFrame, zones: list[str], years: list[int]
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    available = set(shares.index)
    for year in years:
        for zone in sorted(zones):
            required = [(zone, year - 1), (zone, year), (zone, year + 1)]
            if not all(key in available for key in required):
                continue
            lag = shares.loc[(zone, year - 1), SECTORS].to_numpy(dtype=float)
            current = shares.loc[(zone, year), SECTORS].to_numpy(dtype=float)
            future = shares.loc[(zone, year + 1), SECTORS].to_numpy(dtype=float)
            delta = current - lag
            target = future - current
            top3 = set(np.argsort(np.abs(target))[-3:])
            group_id = f"{zone}|{year}"
            for target_index, sector in enumerate(SECTORS):
                row: dict[str, object] = {
                    "ze2020": zone,
                    "decision_year": year,
                    "sector_code": sector,
                    "target_index": target_index,
                    "group_id": group_id,
                    "target_change": target[target_index],
                    "target_magnitude": abs(target[target_index]),
                    "target_top3_change": int(target_index in top3),
                    "own_current": current[target_index],
                    "own_lag": lag[target_index],
                    "own_delta": delta[target_index],
                }
                row.update(dict(zip(CURRENT_COLUMNS, current)))
                row.update(dict(zip(LAG_COLUMNS, lag)))
                row.update(dict(zip(DELTA_COLUMNS, delta)))
                row.update(
                    {
                        column: float(index == target_index)
                        for index, column in enumerate(TARGET_COLUMNS)
                    }
                )
                rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No composition-transition samples")
    counts = frame.groupby("group_id").size()
    positives = frame.groupby("group_id")["target_top3_change"].sum()
    if not counts.eq(len(SECTORS)).all() or not positives.eq(3).all():
        raise ValueError("Incomplete or invalid ZE-year transition group")
    return frame.sort_values(
        ["decision_year", "ze2020", "sector_code"]
    ).reset_index(drop=True)


def shuffle_sector_identity(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = frame.copy()
    for group_id, indices in out.groupby("group_id", sort=True).groups.items():
        idx = list(indices)
        permutation = _stable_rng(seed, "transition_sector", group_id).permutation(
            len(SECTORS)
        )
        for columns in [CURRENT_COLUMNS, LAG_COLUMNS, DELTA_COLUMNS]:
            values = out.loc[idx[0], columns].to_numpy(dtype=float)[permutation]
            out.loc[idx, columns] = np.tile(values, (len(idx), 1))
    return out


def shuffle_temporal_profiles(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = frame.copy()
    groups = out[["group_id", "decision_year", *LAG_COLUMNS]].drop_duplicates(
        "group_id"
    )
    replacements: dict[str, np.ndarray] = {}
    for year, year_groups in groups.groupby("decision_year", sort=True):
        ordered = year_groups.sort_values("group_id")
        permutation = _stable_rng(seed, "transition_time", year).permutation(
            len(ordered)
        )
        values = ordered[LAG_COLUMNS].to_numpy(dtype=float)[permutation]
        replacements.update(dict(zip(ordered["group_id"], values)))
    for group_id, indices in out.groupby("group_id", sort=True).groups.items():
        idx = list(indices)
        lag = replacements[group_id]
        current = out.loc[idx[0], CURRENT_COLUMNS].to_numpy(dtype=float)
        out.loc[idx, LAG_COLUMNS] = np.tile(lag, (len(idx), 1))
        out.loc[idx, DELTA_COLUMNS] = np.tile(current - lag, (len(idx), 1))
    return out


def shuffle_training_target(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = frame.copy()
    rng = np.random.default_rng(seed)
    for _, indices in out.groupby(
        ["decision_year", "sector_code"], sort=True
    ).groups.items():
        idx = list(indices)
        out.loc[idx, "target_change"] = rng.permutation(
            out.loc[idx, "target_change"].to_numpy(dtype=float)
        )
    return out


def fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    features: list[str],
    model_kind: str,
    seed: int,
    max_epochs: int,
) -> tuple[np.ndarray, int, bool]:
    target_mean = float(train["target_change"].mean())
    target_std = float(train["target_change"].std(ddof=0))
    if target_std <= 0:
        raise ValueError("Constant transition target")
    scaled_target = (train["target_change"] - target_mean) / target_std
    if model_kind == "ridge":
        model = Pipeline(
            [("scale", StandardScaler()), ("model", Ridge(alpha=1.0))]
        )
        model.fit(train[features], scaled_target)
        return model.predict(test[features]) * target_std + target_mean, 0, True
    if model_kind != "mlp":
        raise ValueError(f"Unknown model kind: {model_kind}")
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                MLPRegressor(
                    hidden_layer_sizes=(64, 32),
                    activation="relu",
                    solver="adam",
                    alpha=0.001,
                    learning_rate_init=0.001,
                    max_iter=max_epochs,
                    early_stopping=True,
                    validation_fraction=0.15,
                    n_iter_no_change=20,
                    random_state=seed,
                ),
            ),
        ]
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(train[features], scaled_target)
    fitted = model.named_steps["model"]
    converged = not any(issubclass(item.category, ConvergenceWarning) for item in caught)
    prediction = model.predict(test[features]) * target_std + target_mean
    return prediction, int(fitted.n_iter_), converged


def transition_metrics(test: pd.DataFrame, prediction: np.ndarray) -> dict[str, float]:
    scored = test[
        [
            "ze2020",
            "decision_year",
            "sector_code",
            "target_change",
            "target_magnitude",
            "target_top3_change",
        ]
    ].copy()
    scored["prediction"] = np.asarray(prediction, dtype=float)
    scored["predicted_magnitude"] = scored["prediction"].abs()
    ndcg_values = []
    precision_values = []
    hit_values = []
    top3_errors = []
    sign_hits = []
    discounts = 1.0 / np.log2(np.arange(2, 5))
    for _, group in scored.groupby(["ze2020", "decision_year"], sort=False):
        selected = group.nlargest(3, "predicted_magnitude")
        ideal = group.nlargest(3, "target_magnitude")
        dcg = float((selected["target_magnitude"].to_numpy() * discounts).sum())
        idcg = float((ideal["target_magnitude"].to_numpy() * discounts).sum())
        ndcg_values.append(dcg / idcg if idcg > 0 else 0.0)
        selected_sectors = set(selected["sector_code"])
        actual_sectors = set(ideal["sector_code"])
        hits = len(selected_sectors & actual_sectors)
        precision_values.append(hits / 3)
        hit_values.append(float(hits > 0))
        top3_errors.extend((ideal["prediction"] - ideal["target_change"]).abs())
        nonzero = ideal[ideal["target_change"] != 0]
        sign_hits.extend(
            np.sign(nonzero["prediction"]) == np.sign(nonzero["target_change"])
        )
    error = scored["prediction"] - scored["target_change"]
    return {
        "ndcg_at_3": float(np.mean(ndcg_values)),
        "precision_at_3": float(np.mean(precision_values)),
        "hit_rate_at_3": float(np.mean(hit_values)),
        "signed_mae": float(error.abs().mean()),
        "top3_signed_mae": float(np.mean(top3_errors)),
        "top3_sign_accuracy": float(np.mean(sign_hits)),
    }


def metric_row(
    test: pd.DataFrame,
    prediction: np.ndarray,
    *,
    view: str,
    seed: int,
    eval_year: int,
    fold: int,
    epochs: int,
    converged: bool,
    checksum: str,
) -> dict[str, object]:
    return {
        "view": view,
        "seed": seed,
        "eval_year": eval_year,
        "ze_fold": fold,
        **transition_metrics(test, prediction),
        "n_test": int(len(test)),
        "n_test_groups": int(test["group_id"].nunique()),
        "n_test_top3": int(test["target_top3_change"].sum()),
        "epochs": epochs,
        "converged": bool(converged),
        "target_key_sha256": checksum,
        "train_test_ze_overlap": 0,
        "max_training_decision_year": eval_year - 1,
        "claim_status": CLAIM_STATUS,
    }


def evaluate_fold(
    shares: pd.DataFrame,
    fold_map: dict[str, int],
    *,
    seed: int,
    eval_year: int,
    fold: int,
    max_epochs: int,
) -> list[dict[str, object]]:
    zones = sorted({index[0] for index in shares.index})
    train_zones = [zone for zone in zones if fold_map[zone] != fold]
    test_zones = [zone for zone in zones if fold_map[zone] == fold]
    if set(train_zones) & set(test_zones):
        raise AssertionError("Train/test ZE overlap")
    train = build_transition_samples(
        shares, train_zones, list(range(2013, eval_year))
    )
    test = build_transition_samples(shares, test_zones, [eval_year])
    payload = test[
        ["ze2020", "decision_year", "sector_code", "target_change"]
    ].astype(str)
    checksum = hashlib.sha256(
        "\n".join(payload.agg("|".join, axis=1).sort_values()).encode()
    ).hexdigest()

    rows = []
    baselines = {
        "zero_change": np.zeros(len(test)),
        "past_delta": test["own_delta"].to_numpy(dtype=float),
        "random_ranking": np.array(
            [
                _stable_rng(seed, "transition_random", eval_year, fold, key).normal()
                for key in payload.agg("|".join, axis=1)
            ]
        ),
    }
    for view, prediction in baselines.items():
        rows.append(
            metric_row(
                test,
                prediction,
                view=view,
                seed=seed,
                eval_year=eval_year,
                fold=fold,
                epochs=0,
                converged=True,
                checksum=checksum,
            )
        )

    model_specs = {
        "ridge_joint": (train, test, FULL_FEATURES, "ridge"),
        "mlp_joint": (train, test, FULL_FEATURES, "mlp"),
        "mlp_target_history_only": (
            train,
            test,
            TARGET_HISTORY_FEATURES,
            "mlp",
        ),
        "mlp_current_only": (train, test, CURRENT_FEATURES, "mlp"),
        "mlp_sector_shuffle": (
            shuffle_sector_identity(train, seed),
            shuffle_sector_identity(test, seed),
            FULL_FEATURES,
            "mlp",
        ),
        "mlp_temporal_shuffle": (
            shuffle_temporal_profiles(train, seed),
            shuffle_temporal_profiles(test, seed),
            FULL_FEATURES,
            "mlp",
        ),
        "mlp_target_shuffle": (
            shuffle_training_target(train, seed),
            test,
            FULL_FEATURES,
            "mlp",
        ),
    }
    for view, (train_view, test_view, features, kind) in model_specs.items():
        prediction, epochs, converged = fit_predict(
            train_view,
            test_view,
            features=features,
            model_kind=kind,
            seed=seed + eval_year * 100 + fold,
            max_epochs=max_epochs,
        )
        rows.append(
            metric_row(
                test,
                prediction,
                view=view,
                seed=seed,
                eval_year=eval_year,
                fold=fold,
                epochs=epochs,
                converged=converged,
                checksum=checksum,
            )
        )
    return rows


def evaluate(
    shares: pd.DataFrame,
    *,
    seeds: list[int],
    eval_years: list[int],
    folds: list[int],
    max_epochs: int,
) -> pd.DataFrame:
    fold_map = assign_ze_folds([index[0] for index in shares.index])
    rows = []
    for seed in seeds:
        for eval_year in eval_years:
            for fold in folds:
                rows.extend(
                    evaluate_fold(
                        shares,
                        fold_map,
                        seed=seed,
                        eval_year=eval_year,
                        fold=fold,
                        max_epochs=max_epochs,
                    )
                )
    metrics = pd.DataFrame(rows)
    key = ["view", "seed", "eval_year", "ze_fold"]
    if metrics.duplicated(key).any():
        raise ValueError("Duplicate transition metric keys")
    numeric = [
        "ndcg_at_3",
        "precision_at_3",
        "hit_rate_at_3",
        "signed_mae",
        "top3_signed_mae",
        "top3_sign_accuracy",
    ]
    if not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite transition metrics")
    return metrics.sort_values(key).reset_index(drop=True)


def audit_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    full = metrics[metrics["view"] == "mlp_joint"][keys + ["ndcg_at_3"]].rename(
        columns={"ndcg_at_3": "full"}
    )
    comparisons = {}
    for control in [view for view in VIEWS if view != "mlp_joint"]:
        other = metrics[metrics["view"] == control][keys + ["ndcg_at_3"]].rename(
            columns={"ndcg_at_3": "control"}
        )
        paired = full.merge(other, on=keys, validate="one_to_one")
        lift = paired["full"] - paired["control"]
        comparisons[control] = {
            "mean_ndcg_lift": float(lift.mean()),
            "paired_win_rate": float((lift > 0).mean()),
            "n_pairs": int(len(paired)),
        }

    yearly = metrics[
        metrics["view"].isin(
            [
                "mlp_joint",
                "past_delta",
                "ridge_joint",
                "mlp_target_history_only",
                "mlp_current_only",
            ]
        )
    ].groupby(["eval_year", "view"])["ndcg_at_3"].mean().unstack()
    required_year_columns = {
        "mlp_joint",
        "past_delta",
        "ridge_joint",
        "mlp_target_history_only",
        "mlp_current_only",
    }
    years_beating_controls = (
        int(
            (
                (yearly["mlp_joint"] > yearly["past_delta"])
                & (yearly["mlp_joint"] > yearly["ridge_joint"])
                & (yearly["mlp_joint"] > yearly["mlp_target_history_only"])
                & (yearly["mlp_joint"] > yearly["mlp_current_only"])
            ).sum()
        )
        if required_year_columns.issubset(yearly.columns)
        else 0
    )
    summary = metrics.groupby("view").mean(numeric_only=True)
    sign_gate = bool(
        summary.loc["mlp_joint", "top3_sign_accuracy"]
        > summary.loc["past_delta", "top3_sign_accuracy"]
        and summary.loc["mlp_joint", "top3_sign_accuracy"]
        > summary.loc["ridge_joint", "top3_sign_accuracy"]
    ) if {"mlp_joint", "past_delta", "ridge_joint"}.issubset(summary.index) else False
    seed_ndcg = metrics[metrics["view"] == "mlp_joint"].groupby("seed")[
        "ndcg_at_3"
    ].mean()
    seed_cv = float(seed_ndcg.std(ddof=0) / seed_ndcg.mean()) if len(seed_ndcg) > 1 else 0.0
    expected_groups = len(SEEDS) * len(EVAL_YEARS) * len(FOLDS)
    integrity = {
        "all_metrics_finite": bool(
            np.isfinite(
                metrics[
                    [
                        "ndcg_at_3",
                        "precision_at_3",
                        "signed_mae",
                        "top3_sign_accuracy",
                    ]
                ].to_numpy(float)
            ).all()
        ),
        "all_views_present": set(metrics["view"]) == set(VIEWS),
        "registered_seeds": set(metrics["seed"]) == set(SEEDS),
        "registered_years": set(metrics["eval_year"]) == set(EVAL_YEARS),
        "registered_folds": set(metrics["ze_fold"]) == set(FOLDS),
        "complete_view_grid": bool(
            metrics.groupby(keys)["view"].nunique().eq(len(VIEWS)).all()
            and metrics.groupby(keys).ngroups == expected_groups
        ),
        "identical_targets": bool(
            metrics.groupby(keys)["target_key_sha256"].nunique().eq(1).all()
        ),
        "complete_sector_groups": bool(
            metrics["n_test"].eq(len(SECTORS) * metrics["n_test_groups"]).all()
            and metrics["n_test_top3"].eq(3 * metrics["n_test_groups"]).all()
        ),
        "zero_ze_overlap": bool(metrics["train_test_ze_overlap"].eq(0).all()),
        "mature_training_labels": bool(
            metrics["max_training_decision_year"].eq(metrics["eval_year"] - 1).all()
        ),
        "full_configuration": len(metrics) == len(VIEWS) * expected_groups,
    }
    pairwise_controls = [
        "past_delta",
        "ridge_joint",
        "mlp_target_history_only",
        "mlp_current_only",
        "mlp_sector_shuffle",
        "mlp_temporal_shuffle",
    ]
    gate_pass = (
        all(integrity.values())
        and all(
            comparisons[view]["mean_ndcg_lift"] > 0
            and comparisons[view]["paired_win_rate"] >= 0.60
            for view in pairwise_controls
        )
        and comparisons["mlp_target_shuffle"]["mean_ndcg_lift"] > 0
        and comparisons["mlp_target_shuffle"]["paired_win_rate"] >= 0.80
        and sign_gate
        and years_beating_controls >= 6
        and seed_cv <= 0.20
    )
    return {
        "gate_pass": bool(gate_pass),
        "integrity": integrity,
        "comparisons": comparisons,
        "top3_sign_accuracy_gate": sign_gate,
        "years_beating_all_controls": years_beating_controls,
        "mlp_joint_seed_ndcg_cv": seed_cv,
        "claim_status": CLAIM_STATUS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--eval-years", type=int, nargs="+", default=EVAL_YEARS)
    parser.add_argument("--folds", type=int, nargs="+", default=FOLDS)
    parser.add_argument("--max-epochs", type=int, default=300)
    args = parser.parse_args()
    metrics = evaluate(
        load_share_panel(args.panel),
        seeds=args.seeds,
        eval_years=args.eval_years,
        folds=args.folds,
        max_epochs=args.max_epochs,
    )
    summary = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_ndcg_at_3=("ndcg_at_3", "mean"),
            mean_precision_at_3=("precision_at_3", "mean"),
            mean_signed_mae=("signed_mae", "mean"),
            mean_top3_signed_mae=("top3_signed_mae", "mean"),
            mean_top3_sign_accuracy=("top3_sign_accuracy", "mean"),
            convergence_rate=("converged", "mean"),
            rows=("ndcg_at_3", "size"),
        )
        .sort_values("mean_ndcg_at_3", ascending=False)
    )
    summary["claim_status"] = CLAIM_STATUS
    gate = audit_gate(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_composition_transition_ranking"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
