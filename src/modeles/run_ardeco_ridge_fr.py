"""Causal France-NUTS3 Ridge benchmark with ARDECO SNETZ features.

This experiment answers a narrow question before any neural reopening:

    Does regional sector-employment information add out-of-sample value to the
    canonical two-lag AR-Ridge?

Forecast year t uses ARDECO observations through t-1 only.  Each candidate is
also tested against fold-specific temporal permutations that use only source
years strictly before t.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


BASE = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = BASE / "data/processed/european_panel/fr_nuts3_panel.csv"
DEFAULT_ARDECO = (
    BASE / "data/raw/european_panel/ardeco/snetz/ardeco_snetz_combined.csv"
)
DEFAULT_OUTPUT = (
    BASE / "data/processed/ardeco_extension/ardeco_ridge_fr_results.json"
)

EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
SECTOR_MAP = {
    "B-E": "BE",
    "F": "FZ",
    "G-I": "GI",
    "J": "JZ",
    "K": "KZ",
    "L": "LZ",
    "M_N": "MN",
    "O-Q": "OQ",
    "R-U": "RU",
}
SECTORS = list(SECTOR_MAP.values())
FEATURE_FAMILIES = ("level", "growth", "share", "joint")
RIDGE_ALPHA = 10.0
N_PERMUTATIONS = 99
BASE_SEED = 42027


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    denom = float(np.abs(y_true[valid]).sum())
    if not valid.any() or denom <= 0:
        return float("nan")
    return float(np.abs(y_true[valid] - y_pred[valid]).sum() / denom)


def prepare_ardeco(ardeco: pd.DataFrame) -> pd.DataFrame:
    required = {"COUNTRY_REQUEST", "TERRITORY_ID", "YEAR", "SECTOR", "VALUE"}
    missing = required.difference(ardeco.columns)
    if missing:
        raise ValueError(f"ARDECO missing columns: {sorted(missing)}")

    frame = ardeco[
        ardeco["COUNTRY_REQUEST"].astype(str).eq("FR")
        & ardeco["SECTOR"].isin(SECTOR_MAP)
    ].copy()
    frame["region_id"] = frame["TERRITORY_ID"].astype(str)
    frame["source_year"] = pd.to_numeric(frame["YEAR"], errors="raise").astype(int)
    frame["sector_a10"] = frame["SECTOR"].map(SECTOR_MAP)
    frame["employment_ths"] = pd.to_numeric(frame["VALUE"], errors="coerce")
    key = ["region_id", "source_year", "sector_a10"]
    if frame.duplicated(key).any():
        raise ValueError("Duplicate ARDECO region-year-sector rows")

    wide = frame.pivot(index=["region_id", "source_year"], columns="sector_a10",
                       values="employment_ths").reindex(columns=SECTORS)
    wide.columns = [f"emp_{sector}" for sector in wide.columns]
    wide = wide.reset_index().sort_values(["region_id", "source_year"])

    employment_cols = [f"emp_{sector}" for sector in SECTORS]
    for column in employment_cols:
        wide[f"log_{column}"] = np.log1p(wide[column])
        wide[f"growth_{column}"] = (
            wide.groupby("region_id")[column].pct_change(fill_method=None)
        )
    total = wide[employment_cols].sum(axis=1, min_count=len(employment_cols))
    for column in employment_cols:
        wide[f"share_{column}"] = wide[column] / total.replace(0, np.nan)
    return wide


def prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    required = {
        "region_id", "year", "target_births", "lag1_births", "lag2_births"
    }
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"France panel missing columns: {sorted(missing)}")
    frame = panel.copy()
    frame["region_id"] = frame["region_id"].astype(str)
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
    return frame.sort_values(["year", "region_id"]).reset_index(drop=True)


def build_model_table(panel: pd.DataFrame, ardeco_wide: pd.DataFrame) -> pd.DataFrame:
    """Join target year t to ARDECO source year t-1."""
    frame = prepare_panel(panel)
    frame["source_year"] = frame["year"] - 1
    merged = frame.merge(
        ardeco_wide,
        on=["region_id", "source_year"],
        how="left",
        validate="many_to_one",
    )
    merged["ardeco_observation_before_target"] = (
        merged["source_year"] < merged["year"]
    )
    return merged


def family_columns(family: str) -> list[str]:
    if family == "level":
        return [f"log_emp_{sector}" for sector in SECTORS]
    if family == "growth":
        return [f"growth_emp_{sector}" for sector in SECTORS]
    if family == "share":
        return [f"share_emp_{sector}" for sector in SECTORS]
    if family == "joint":
        return (
            family_columns("level")
            + family_columns("growth")
            + family_columns("share")
        )
    if family == "baseline":
        return []
    raise ValueError(f"Unknown feature family: {family}")


def temporally_permute_ardeco(
    table: pd.DataFrame,
    eval_year: int,
    family: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Permute source-year blocks without using any year >= eval_year.

    The same source-year mapping is applied to every region, preserving each
    year's spatial covariance while destroying alignment with forecast years.
    """
    columns = family_columns(family)
    out = table.copy()
    eligible_rows = out[out["source_year"] < eval_year]
    complete_by_year = eligible_rows.groupby("source_year")[columns].apply(
        lambda frame: bool(np.isfinite(frame.to_numpy(dtype=float)).all())
    )
    eligible_years = sorted(
        int(year) for year in complete_by_year[complete_by_year].index
    )
    if len(eligible_years) < 2:
        raise ValueError(
            f"Too few complete ARDECO years for {family}/{eval_year}: "
            f"{eligible_years}"
        )
    permuted = list(rng.permutation(eligible_years))
    year_map = dict(zip(eligible_years, permuted, strict=True))

    lookup = out[["region_id", "source_year"] + columns].copy()
    lookup = lookup.rename(
        columns={"source_year": "_permuted_source_year", **{
            column: f"_permuted_{column}" for column in columns
        }}
    )
    out["_permuted_source_year"] = out["source_year"].map(year_map)
    out = out.merge(
        lookup,
        on=["region_id", "_permuted_source_year"],
        how="left",
        validate="many_to_one",
    )
    for column in columns:
        out[column] = out[f"_permuted_{column}"]
    drop = ["_permuted_source_year"] + [f"_permuted_{column}" for column in columns]
    return out.drop(columns=drop)


def fit_predict_fold(
    table: pd.DataFrame,
    eval_year: int,
    family: str,
    alpha: float = RIDGE_ALPHA,
) -> dict[str, Any]:
    feature_columns = ["lag1_births", "lag2_births"] + family_columns(family)
    train = table[table["year"] < eval_year].copy()
    test = table[table["year"] == eval_year].copy()
    if test.empty:
        raise ValueError(f"No test rows for eval_year={eval_year}")

    X_train = train[feature_columns].to_numpy(dtype=float)
    y_train = train["target_births"].to_numpy(dtype=float)
    X_test = test[feature_columns].to_numpy(dtype=float)
    y_test = test["target_births"].to_numpy(dtype=float)

    valid_train = np.isfinite(X_train).all(axis=1) & np.isfinite(y_train)
    valid_test = np.isfinite(X_test).all(axis=1) & np.isfinite(y_test)
    if not valid_train.any() or not valid_test.all():
        raise ValueError(
            f"Incomplete fold {eval_year}/{family}: "
            f"train={valid_train.sum()}/{len(train)}, "
            f"test={valid_test.sum()}/{len(test)}"
        )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train[valid_train])
    model = Ridge(alpha=alpha)
    model.fit(X_train_scaled, y_train[valid_train])
    prediction = np.clip(model.predict(scaler.transform(X_test)), 0.0, None)
    return {
        "eval_year": int(eval_year),
        "family": family,
        "wmape": wmape(y_test, prediction),
        "n_train": int(valid_train.sum()),
        "n_test": int(valid_test.sum()),
        "train_max_year": int(train.loc[valid_train, "year"].max()),
        "ardeco_max_source_year": int(
            train.loc[valid_train, "source_year"].max()
        ),
        "leakage_ok": bool(
            train.loc[valid_train, "year"].max() < eval_year
            and train.loc[valid_train, "source_year"].max() < eval_year
            and test["source_year"].max() < eval_year
        ),
    }


def summarize_candidate(
    family: str,
    observed_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    null_mean_wmapes: list[float],
) -> dict[str, Any]:
    observed = np.array([row["wmape"] for row in observed_rows], dtype=float)
    baseline = np.array([row["wmape"] for row in baseline_rows], dtype=float)
    observed_mean = float(observed.mean())
    baseline_mean = float(baseline.mean())
    relative_improvement = float((baseline_mean - observed_mean) / baseline_mean)
    yearly_relative = (baseline - observed) / baseline
    null = np.asarray(null_mean_wmapes, dtype=float)
    p_perm = float((1 + np.sum(null <= observed_mean)) / (1 + len(null)))

    checks = {
        "improves_mean_at_least_1pct": relative_improvement >= 0.01,
        "wins_at_least_3_of_5_years": int(np.sum(observed < baseline)) >= 3,
        "worst_year_degradation_at_most_10pct": float(yearly_relative.min()) >= -0.10,
        "beats_temporal_permutations_p_le_005": p_perm <= 0.05,
        "all_leakage_checks_pass": all(row["leakage_ok"] for row in observed_rows),
    }
    return {
        "family": family,
        "baseline_mean_wmape": baseline_mean,
        "mean_wmape": observed_mean,
        "relative_improvement_vs_baseline": relative_improvement,
        "winning_years": int(np.sum(observed < baseline)),
        "worst_year_relative_improvement": float(yearly_relative.min()),
        "temporal_null_mean_wmape": float(null.mean()),
        "temporal_null_std_wmape": float(null.std(ddof=1)),
        "p_temporal": p_perm,
        "checks": checks,
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "by_year": observed_rows,
    }


def run_benchmark(
    panel_path: Path = DEFAULT_PANEL,
    ardeco_path: Path = DEFAULT_ARDECO,
    output_path: Path = DEFAULT_OUTPUT,
    eval_years: list[int] = EVAL_YEARS,
    n_permutations: int = N_PERMUTATIONS,
    seed: int = BASE_SEED,
) -> dict[str, Any]:
    panel = pd.read_csv(panel_path, low_memory=False)
    ardeco = pd.read_csv(ardeco_path, low_memory=False)
    table = build_model_table(panel, prepare_ardeco(ardeco))

    baseline_rows = [
        fit_predict_fold(table, year, "baseline") for year in eval_years
    ]
    candidates: dict[str, Any] = {}
    for family_idx, family in enumerate(FEATURE_FAMILIES):
        observed_rows = [
            fit_predict_fold(table, year, family) for year in eval_years
        ]
        null_means: list[float] = []
        for permutation in range(n_permutations):
            permutation_rows = []
            for year in eval_years:
                rng = np.random.default_rng(
                    seed + 10_000 * family_idx + 100 * permutation + year
                )
                permuted = temporally_permute_ardeco(
                    table, year, family, rng
                )
                permutation_rows.append(
                    fit_predict_fold(permuted, year, family)["wmape"]
                )
            null_means.append(float(np.mean(permutation_rows)))
        candidates[family] = summarize_candidate(
            family, observed_rows, baseline_rows, null_means
        )

    passed = [family for family, result in candidates.items()
              if result["decision"] == "PASS"]
    result = {
        "decision": (
            "ARDECO_RIDGE_PROMOTED" if passed else "ARDECO_RIDGE_NOT_PROMOTED"
        ),
        "passed_families": passed,
        "config": {
            "eval_years": eval_years,
            "ridge_alpha": RIDGE_ALPHA,
            "n_permutations": n_permutations,
            "seed": seed,
            "base_features": ["lag1_births", "lag2_births"],
            "ardeco_source_lag": "target_year - 1",
        },
        "baseline": {
            "mean_wmape": float(
                np.mean([row["wmape"] for row in baseline_rows])
            ),
            "by_year": baseline_rows,
        },
        "candidates": candidates,
        "data_audit": {
            "rows": int(len(table)),
            "regions": int(table["region_id"].nunique()),
            "target_years": sorted(int(year) for year in table["year"].unique()),
            "ardeco_source_years": sorted(
                int(year) for year in table["source_year"].dropna().unique()
            ),
            "all_source_years_before_targets": bool(
                table["ardeco_observation_before_target"].all()
            ),
        },
        "sources": {
            "panel": str(panel_path),
            "panel_sha256": file_sha256(panel_path),
            "ardeco": str(ardeco_path),
            "ardeco_sha256": file_sha256(ardeco_path),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--ardeco", type=Path, default=DEFAULT_ARDECO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-permutations", type=int, default=N_PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=BASE_SEED)
    args = parser.parse_args()
    result = run_benchmark(
        panel_path=args.panel,
        ardeco_path=args.ardeco,
        output_path=args.output,
        n_permutations=args.n_permutations,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
