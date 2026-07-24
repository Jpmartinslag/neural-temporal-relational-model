"""Evaluate masked reconstruction on observed temporal ZE-sector compositions."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
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
PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
SEEDS = [42, 43, 44, 45, 46]
EVAL_YEARS = list(range(2017, 2026))
FOLDS = list(range(5))
SPLIT_SEED = 20260724
CLAIM_STATUS = "temporal_bipartite_reconstruction_preflight_not_imputation"
VIEWS = [
    "temporal_persistence",
    "sector_mean_closure",
    "ridge_bipartite",
    "mlp_bipartite",
    "mlp_history_only",
    "mlp_current_only",
    "mlp_sector_shuffle",
    "mlp_temporal_shuffle",
    "random_closure",
]

CURRENT_COLUMNS = [f"current_{sector}" for sector in SECTORS]
VISIBLE_COLUMNS = [f"visible_{sector}" for sector in SECTORS]
LAG_COLUMNS = [f"lag_{sector}" for sector in SECTORS]
TARGET_COLUMNS = [f"target_{sector}" for sector in SECTORS]
FULL_FEATURES = CURRENT_COLUMNS + VISIBLE_COLUMNS + LAG_COLUMNS + TARGET_COLUMNS
HISTORY_FEATURES = LAG_COLUMNS + TARGET_COLUMNS
CURRENT_FEATURES = CURRENT_COLUMNS + VISIBLE_COLUMNS + TARGET_COLUMNS


def assign_ze_folds(zones: list[str]) -> dict[str, int]:
    ordered = np.array(sorted({str(zone).zfill(4) for zone in zones}))
    shuffled = np.random.default_rng(SPLIT_SEED).permutation(ordered)
    return {zone: int(index % len(FOLDS)) for index, zone in enumerate(shuffled)}


def _stable_rng(seed: int, *parts: object) -> np.random.Generator:
    payload = "|".join([str(seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(payload.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def load_share_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_csv(path, dtype={"ze2020": str})
    panel["ze2020"] = panel["ze2020"].str.zfill(4)
    key = ["ze2020", "year", "sector_code"]
    if panel.duplicated(key).any():
        raise ValueError("Duplicate ZE-year-sector observations")
    if set(panel["sector_code"]) != set(SECTORS):
        raise ValueError("Unexpected A10 sector vocabulary")
    if not panel["mask_sector_available"].eq(1).all():
        raise ValueError("DEC-079 requires complete observed source compositions")
    shares = panel.pivot(
        index=["ze2020", "year"], columns="sector_code", values="sector_share"
    ).reindex(columns=SECTORS)
    values = shares.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite sector share")
    if not np.allclose(values.sum(axis=1), 1.0, atol=1e-10):
        raise ValueError("ZE-year sector shares do not sum to one")
    return shares.sort_index()


def choose_hidden(profile: np.ndarray, seed: int, zone: str, year: int) -> tuple[int, ...]:
    valid = [
        combo
        for combo in itertools.combinations(range(len(SECTORS)), 3)
        if float(profile[list(combo)].sum()) > 0
    ]
    if not valid:
        raise ValueError(f"No positive hidden triple for {zone}/{year}")
    rng = _stable_rng(seed, "mask", zone, year)
    return valid[int(rng.integers(len(valid)))]


def build_samples(
    shares: pd.DataFrame,
    zones: list[str],
    years: list[int],
    *,
    seed: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    available = set(shares.index)
    for year in years:
        for zone in sorted(zones):
            if (zone, year) not in available or (zone, year - 1) not in available:
                continue
            current = shares.loc[(zone, year), SECTORS].to_numpy(dtype=float)
            lag = shares.loc[(zone, year - 1), SECTORS].to_numpy(dtype=float)
            hidden = choose_hidden(current, seed, zone, year)
            visible = np.ones(len(SECTORS), dtype=float)
            visible[list(hidden)] = 0.0
            masked = current * visible
            remaining = float(current[list(hidden)].sum())
            group_id = f"{zone}|{year}"
            for target_index in hidden:
                row: dict[str, object] = {
                    "ze2020": zone,
                    "year": year,
                    "sector_code": SECTORS[target_index],
                    "target_index": target_index,
                    "group_id": group_id,
                    "remaining_mass": remaining,
                    "target_share": current[target_index],
                    "target_allocation": current[target_index] / remaining,
                    "lag_target_share": lag[target_index],
                }
                row.update(dict(zip(CURRENT_COLUMNS, masked)))
                row.update(dict(zip(VISIBLE_COLUMNS, visible)))
                row.update(dict(zip(LAG_COLUMNS, lag)))
                row.update(
                    {
                        column: float(index == target_index)
                        for index, column in enumerate(TARGET_COLUMNS)
                    }
                )
                rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No masked reconstruction samples")
    counts = frame.groupby("group_id").size()
    if not counts.eq(3).all():
        raise ValueError("Every ZE-year must have exactly three hidden sectors")
    hidden_payload = np.array(
        [
            frame.loc[index, f"current_{sector}"]
            for index, sector in zip(frame.index, frame["sector_code"])
        ]
    )
    hidden_mask = np.array(
        [
            frame.loc[index, f"visible_{sector}"]
            for index, sector in zip(frame.index, frame["sector_code"])
        ]
    )
    if not np.allclose(hidden_payload, 0.0) or not np.allclose(hidden_mask, 0.0):
        raise AssertionError("Hidden current values are visible to the model")
    return frame.sort_values(["year", "ze2020", "sector_code"]).reset_index(drop=True)


def shuffle_current_sector_identity(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = frame.copy()
    for group_id, indices in out.groupby("group_id", sort=True).groups.items():
        idx = list(indices)
        permutation = _stable_rng(seed, "sector_shuffle", group_id).permutation(
            len(SECTORS)
        )
        current = out.loc[idx[0], CURRENT_COLUMNS].to_numpy(dtype=float)[permutation]
        visible = out.loc[idx[0], VISIBLE_COLUMNS].to_numpy(dtype=float)[permutation]
        out.loc[idx, CURRENT_COLUMNS] = np.tile(current, (len(idx), 1))
        out.loc[idx, VISIBLE_COLUMNS] = np.tile(visible, (len(idx), 1))
    return out


def shuffle_lag_profiles(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = frame.copy()
    groups = out[["group_id", "year", *LAG_COLUMNS]].drop_duplicates("group_id")
    replacements: dict[str, np.ndarray] = {}
    for year, year_groups in groups.groupby("year", sort=True):
        ordered = year_groups.sort_values("group_id")
        permutation = _stable_rng(seed, "temporal_shuffle", year).permutation(len(ordered))
        values = ordered[LAG_COLUMNS].to_numpy(dtype=float)[permutation]
        replacements.update(dict(zip(ordered["group_id"], values)))
    for group_id, indices in out.groupby("group_id", sort=True).groups.items():
        idx = list(indices)
        out.loc[idx, LAG_COLUMNS] = np.tile(replacements[group_id], (len(idx), 1))
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
    if model_kind == "ridge":
        model = Pipeline(
            [("scale", StandardScaler()), ("model", Ridge(alpha=1.0))]
        )
        model.fit(train[features], train["target_allocation"])
        return model.predict(test[features]), 0, True
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
        model.fit(train[features], train["target_allocation"])
    fitted = model.named_steps["model"]
    converged = not any(issubclass(item.category, ConvergenceWarning) for item in caught)
    return model.predict(test[features]), int(fitted.n_iter_), converged


def project_hidden_predictions(test: pd.DataFrame, raw: np.ndarray) -> pd.DataFrame:
    scored = test[
        [
            "ze2020",
            "year",
            "sector_code",
            "group_id",
            "remaining_mass",
            "target_share",
            "target_allocation",
        ]
    ].copy()
    scored["positive_score"] = np.maximum(np.asarray(raw, dtype=float), 1e-12)
    denominator = scored.groupby("group_id")["positive_score"].transform("sum")
    scored["predicted_allocation"] = scored["positive_score"] / denominator
    scored["predicted_share"] = (
        scored["remaining_mass"] * scored["predicted_allocation"]
    )
    predicted_mass = scored.groupby("group_id")["predicted_share"].sum()
    true_mass = scored.groupby("group_id")["remaining_mass"].first()
    scored["composition_error"] = scored["group_id"].map(
        (predicted_mass - true_mass).abs()
    )
    return scored


def metric_row(
    scored: pd.DataFrame,
    *,
    view: str,
    seed: int,
    eval_year: int,
    fold: int,
    epochs: int,
    converged: bool,
    checksum: str,
) -> dict[str, object]:
    error = scored["predicted_share"] - scored["target_share"]
    allocation_error = scored["predicted_allocation"] - scored["target_allocation"]
    return {
        "view": view,
        "seed": seed,
        "eval_year": eval_year,
        "ze_fold": fold,
        "masked_mae": float(error.abs().mean()),
        "masked_rmse": float(np.sqrt(np.mean(np.square(error)))),
        "allocation_mae": float(allocation_error.abs().mean()),
        "n_hidden_cells": int(len(scored)),
        "n_ze_year_groups": int(scored["group_id"].nunique()),
        "max_composition_error": float(scored["composition_error"].max()),
        "epochs": epochs,
        "converged": bool(converged),
        "target_key_sha256": checksum,
        "train_test_ze_overlap": 0,
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
    train = build_samples(
        shares, train_zones, list(range(2013, eval_year + 1)), seed=seed
    )
    test = build_samples(shares, test_zones, [eval_year], seed=seed)
    keys = test[
        [
            "ze2020",
            "year",
            "sector_code",
            "target_share",
            "remaining_mass",
        ]
    ].astype(str)
    checksum = hashlib.sha256(
        "\n".join(keys.agg("|".join, axis=1).sort_values()).encode()
    ).hexdigest()

    train_snapshot = shares.loc[
        [(zone, eval_year) for zone in train_zones], SECTORS
    ].mean(axis=0)
    baseline_raw = {
        "temporal_persistence": test["lag_target_share"].to_numpy(dtype=float),
        "sector_mean_closure": test["sector_code"].map(train_snapshot).to_numpy(float),
        "random_closure": np.array(
            [
                _stable_rng(seed, "random", eval_year, fold, key).random()
                for key in keys.agg("|".join, axis=1)
            ]
        ),
    }
    rows = []
    for view, raw in baseline_raw.items():
        rows.append(
            metric_row(
                project_hidden_predictions(test, raw),
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
        "ridge_bipartite": (train, test, FULL_FEATURES, "ridge"),
        "mlp_bipartite": (train, test, FULL_FEATURES, "mlp"),
        "mlp_history_only": (train, test, HISTORY_FEATURES, "mlp"),
        "mlp_current_only": (train, test, CURRENT_FEATURES, "mlp"),
        "mlp_sector_shuffle": (
            shuffle_current_sector_identity(train, seed),
            shuffle_current_sector_identity(test, seed),
            FULL_FEATURES,
            "mlp",
        ),
        "mlp_temporal_shuffle": (
            shuffle_lag_profiles(train, seed),
            shuffle_lag_profiles(test, seed),
            FULL_FEATURES,
            "mlp",
        ),
    }
    for view, (train_view, test_view, features, kind) in model_specs.items():
        raw, epochs, converged = fit_predict(
            train_view,
            test_view,
            features=features,
            model_kind=kind,
            seed=seed + eval_year * 100 + fold,
            max_epochs=max_epochs,
        )
        rows.append(
            metric_row(
                project_hidden_predictions(test, raw),
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
        raise ValueError("Duplicate reconstruction metric keys")
    numeric = ["masked_mae", "masked_rmse", "allocation_mae"]
    if not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite reconstruction metrics")
    return metrics.sort_values(key).reset_index(drop=True)


def audit_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    full = metrics[metrics["view"] == "mlp_bipartite"][
        keys + ["masked_mae"]
    ].rename(columns={"masked_mae": "full"})
    controls = [view for view in VIEWS if view != "mlp_bipartite"]
    comparisons: dict[str, dict[str, float | int]] = {}
    for control in controls:
        other = metrics[metrics["view"] == control][keys + ["masked_mae"]].rename(
            columns={"masked_mae": "control"}
        )
        paired = full.merge(other, on=keys, validate="one_to_one")
        lift = paired["control"] - paired["full"]
        comparisons[control] = {
            "mean_mae_lift": float(lift.mean()),
            "paired_win_rate": float((lift > 0).mean()),
            "n_pairs": int(len(paired)),
        }

    yearly = metrics[
        metrics["view"].isin(
            ["mlp_bipartite", "ridge_bipartite", "mlp_history_only", "mlp_current_only"]
        )
    ].groupby(["eval_year", "view"])["masked_mae"].mean().unstack()
    yearly_complete_wins = int(
        (
            (yearly["mlp_bipartite"] < yearly["ridge_bipartite"])
            & (yearly["mlp_bipartite"] < yearly["mlp_history_only"])
            & (yearly["mlp_bipartite"] < yearly["mlp_current_only"])
        ).sum()
    ) if set(["mlp_bipartite", "ridge_bipartite", "mlp_history_only", "mlp_current_only"]).issubset(yearly.columns) else 0

    seed_mae = metrics[metrics["view"] == "mlp_bipartite"].groupby("seed")[
        "masked_mae"
    ].mean()
    seed_cv = float(seed_mae.std(ddof=0) / seed_mae.mean()) if len(seed_mae) > 1 else 0.0
    expected_groups = len(SEEDS) * len(EVAL_YEARS) * len(FOLDS)
    integrity = {
        "all_metrics_finite": bool(
            np.isfinite(
                metrics[["masked_mae", "masked_rmse", "allocation_mae"]].to_numpy(float)
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
        "three_hidden_per_group": bool(
            metrics["n_hidden_cells"].eq(3 * metrics["n_ze_year_groups"]).all()
        ),
        "composition_preserved": bool(metrics["max_composition_error"].le(1e-10).all()),
        "zero_ze_overlap": bool(metrics["train_test_ze_overlap"].eq(0).all()),
        "full_configuration": len(metrics) == len(VIEWS) * expected_groups,
    }
    required_aggregate = [
        "ridge_bipartite",
        "temporal_persistence",
        "sector_mean_closure",
    ]
    required_pairwise = [
        "ridge_bipartite",
        "mlp_history_only",
        "mlp_current_only",
        "mlp_sector_shuffle",
        "mlp_temporal_shuffle",
    ]
    gate_pass = (
        all(integrity.values())
        and all(comparisons[view]["mean_mae_lift"] > 0 for view in required_aggregate)
        and all(
            comparisons[view]["mean_mae_lift"] > 0
            and comparisons[view]["paired_win_rate"] >= 0.60
            for view in required_pairwise
        )
        and yearly_complete_wins >= 6
        and seed_cv <= 0.20
    )
    return {
        "gate_pass": bool(gate_pass),
        "integrity": integrity,
        "comparisons": comparisons,
        "years_beating_ridge_and_both_ablations": yearly_complete_wins,
        "mlp_bipartite_seed_mae_cv": seed_cv,
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
            mean_masked_mae=("masked_mae", "mean"),
            mean_masked_rmse=("masked_rmse", "mean"),
            mean_allocation_mae=("allocation_mae", "mean"),
            convergence_rate=("converged", "mean"),
            rows=("masked_mae", "size"),
        )
        .sort_values("mean_masked_mae")
    )
    summary["claim_status"] = CLAIM_STATUS
    gate = audit_gate(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_temporal_bipartite_reconstruction"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
