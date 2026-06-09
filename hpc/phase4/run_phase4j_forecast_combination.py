#!/usr/bin/env python3
"""Phase 4J-A: causal persistence/Ridge forecast combinations.

For each outer country and forecast year, Ridge is fitted on the other
countries through t-1. Combination weights are selected by nested rolling
LOCO validation using source countries only. The outer country's observations
never enter model fitting or weight selection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parents[2]
TARGET = "side_establishment_creations_official"
COUNTRIES = ("fr", "nl", "be", "pt")
FEATURES = (
    "side_lag_1",
    "side_lag_2",
    "side_lag_3",
    "growth_1y",
    "growth_2y",
)
EVAL_YEARS = tuple(range(2018, 2025))
WEIGHT_GRID = tuple(np.linspace(0.0, 1.0, 21))
CONFIGS = (
    "persistence",
    "ridge",
    "mean_50_50",
    "nested_weight",
    "nested_weight_fallback",
)


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = float(np.abs(y_true).sum())
    if denominator <= 0:
        raise ValueError("Non-positive WMAPE denominator")
    return float(np.abs(y_true - y_pred).sum() / denominator)


def fit_ridge(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    if train.empty or test.empty:
        raise ValueError("Ridge requires non-empty train and test frames")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_train = imputer.fit_transform(train[list(FEATURES)].to_numpy(dtype=float))
    x_test = imputer.transform(test[list(FEATURES)].to_numpy(dtype=float))
    x_train = scaler.fit_transform(x_train)
    x_test = scaler.transform(x_test)
    model = Ridge(alpha=1.0)
    model.fit(x_train, train[TARGET].to_numpy(dtype=float))
    return np.maximum(model.predict(x_test), 0.0)


def combine(
    persistence: np.ndarray,
    ridge: np.ndarray,
    ridge_weight: float,
) -> np.ndarray:
    return (1.0 - ridge_weight) * persistence + ridge_weight * ridge


def nested_source_predictions(
    panel: pd.DataFrame,
    outer_country: str,
    final_year: int,
) -> pd.DataFrame:
    source_countries = [country for country in COUNTRIES if country != outer_country]
    rows: list[dict] = []
    for inner_country in source_countries:
        fit_countries = [
            country for country in source_countries if country != inner_country
        ]
        for validation_year in range(2017, final_year):
            train = panel[
                panel["country"].isin(fit_countries)
                & (panel["target_year"] <= validation_year - 1)
            ]
            test = panel[
                (panel["country"] == inner_country)
                & (panel["target_year"] == validation_year)
            ]
            if train.empty or test.empty:
                continue
            ridge = fit_ridge(train, test)
            persistence = test["side_lag_1"].clip(lower=0.0).to_numpy(dtype=float)
            for row, pred_persistence, pred_ridge in zip(
                test.itertuples(index=False),
                persistence,
                ridge,
            ):
                rows.append(
                    {
                        "inner_country": inner_country,
                        "target_year": validation_year,
                        "y_true": float(getattr(row, TARGET)),
                        "persistence": float(pred_persistence),
                        "ridge": float(pred_ridge),
                    }
                )
    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError(
            f"No nested source predictions for {outer_country} year={final_year}"
        )
    return result


def balanced_nested_score(frame: pd.DataFrame, ridge_weight: float) -> float:
    work = frame.copy()
    work["prediction"] = combine(
        work["persistence"].to_numpy(dtype=float),
        work["ridge"].to_numpy(dtype=float),
        ridge_weight,
    )
    country_scores = []
    for _, country_frame in work.groupby("inner_country"):
        yearly_scores = [
            wmape(
                year_frame["y_true"].to_numpy(dtype=float),
                year_frame["prediction"].to_numpy(dtype=float),
            )
            for _, year_frame in country_frame.groupby("target_year")
        ]
        country_scores.append(float(np.mean(yearly_scores)))
    return float(np.mean(country_scores))


def select_weight(nested: pd.DataFrame) -> tuple[float, list[dict], bool]:
    candidates = [
        {
            "ridge_weight": float(weight),
            "source_balanced_wmape": balanced_nested_score(nested, float(weight)),
        }
        for weight in WEIGHT_GRID
    ]
    # Prefer less Ridge on exact ties: persistence is the safer model.
    candidates.sort(
        key=lambda item: (item["source_balanced_wmape"], item["ridge_weight"])
    )
    selected = candidates[0]
    persistence_score = next(
        item["source_balanced_wmape"]
        for item in candidates
        if item["ridge_weight"] == 0.0
    )
    passes_fallback = bool(
        selected["source_balanced_wmape"] <= 0.99 * persistence_score
    )
    return float(selected["ridge_weight"]), candidates, passes_fallback


def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    yearly_rows = []
    for (country, config, year), frame in predictions.groupby(
        ["country", "config", "target_year"]
    ):
        yearly_rows.append(
            {
                "country": country,
                "config": config,
                "target_year": int(year),
                "wmape": wmape(
                    frame["y_true"].to_numpy(dtype=float),
                    frame["y_pred"].to_numpy(dtype=float),
                ),
            }
        )
    yearly = pd.DataFrame(yearly_rows)
    country = (
        yearly.groupby(["country", "config"], as_index=False)
        .agg(
            mean_yearly_wmape=("wmape", "mean"),
            worst_year_wmape=("wmape", "max"),
        )
        .sort_values(["country", "mean_yearly_wmape"])
    )
    pooled_rows = []
    for config, frame in predictions.groupby("config"):
        pooled_rows.append(
            {
                "config": config,
                "pooled_wmape": wmape(
                    frame["y_true"].to_numpy(dtype=float),
                    frame["y_pred"].to_numpy(dtype=float),
                ),
            }
        )
    balanced = (
        country.groupby("config", as_index=False)
        .agg(
            country_balanced_wmape=("mean_yearly_wmape", "mean"),
            worst_country_wmape=("mean_yearly_wmape", "max"),
        )
        .merge(pd.DataFrame(pooled_rows), on="config", how="left")
        .sort_values("country_balanced_wmape")
    )
    return yearly, country, balanced


def build_decision(
    yearly: pd.DataFrame,
    country: pd.DataFrame,
    balanced: pd.DataFrame,
) -> dict:
    lookup = country.pivot(
        index="country",
        columns="config",
        values="mean_yearly_wmape",
    )
    worst_lookup = country.pivot(
        index="country",
        columns="config",
        values="worst_year_wmape",
    )
    component_best = lookup[["persistence", "ridge"]].min(axis=1)
    component_best_worst = worst_lookup[["persistence", "ridge"]].min(axis=1)
    yearly_pivot = yearly.pivot(
        index=["country", "target_year"],
        columns="config",
        values="wmape",
    )
    yearly_pivot["component_best"] = yearly_pivot[["persistence", "ridge"]].min(axis=1)
    balanced_lookup = balanced.set_index("config")
    persistence = float(
        balanced_lookup.loc["persistence", "country_balanced_wmape"]
    )
    candidate_results = {}
    for config in ("mean_50_50", "nested_weight", "nested_weight_fallback"):
        candidate = lookup[config]
        country_regression = candidate / component_best - 1.0
        worst_year_regression = (
            worst_lookup[config] / component_best_worst - 1.0
        )
        balanced_score = float(
            balanced_lookup.loc[config, "country_balanced_wmape"]
        )
        relative_gain = balanced_score / persistence - 1.0
        country_wins = int((candidate <= component_best).sum())
        year_wins = int(
            (yearly_pivot[config] <= yearly_pivot["component_best"]).sum()
        )
        persistence_year_wins = int(
            (yearly_pivot[config] <= yearly_pivot["persistence"]).sum()
        )
        ridge_year_wins = int(
            (yearly_pivot[config] <= yearly_pivot["ridge"]).sum()
        )
        candidate_results[config] = {
            "country_balanced_wmape": balanced_score,
            "equals_or_beats_best_component_countries": country_wins,
            "max_country_regression": float(country_regression.max()),
            "max_worst_year_regression": float(worst_year_regression.max()),
            "year_wins_vs_best_component": year_wins,
            "year_wins_vs_persistence": persistence_year_wins,
            "year_wins_vs_ridge": ridge_year_wins,
            "year_comparisons": int(len(yearly_pivot)),
            "relative_gain_vs_persistence": float(relative_gain),
            "country_count_pass": bool(country_wins >= 3),
            "country_safety_pass": bool(country_regression.max() <= 0.01),
            "provisional_global_1pct_pass": bool(relative_gain <= -0.01),
            "aggregate_gate_pass": bool(
                country_wins >= 3
                and country_regression.max() <= 0.01
                and relative_gain <= -0.01
            ),
        }
    passing = [
        config
        for config, result in candidate_results.items()
        if result["aggregate_gate_pass"]
    ]
    return {
        "phase": "4J-A",
        "protocol": "nested source-only rolling LOCO forecast combination",
        "primary_metric": "country-balanced mean yearly territorial WMAPE",
        "fixed_mean_is_pre_specified": True,
        "candidate_results": candidate_results,
        "passing_combinations": passing,
        "aggregate_gate_pass": bool(passing),
        "stability_gate_defined": False,
        "advance_to_stability_and_uncertainty_audit": bool(passing),
        "promote_as_final_baseline": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--panel",
        type=Path,
        default=Path("data/processed/phase4g/joint/panel_ze2020.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("hpc_results/herald_phase4j_a_local"),
    )
    args = parser.parse_args()
    panel_path = BASE / args.panel if not args.panel.is_absolute() else args.panel
    output_dir = (
        BASE / args.output_dir
        if not args.output_dir.is_absolute()
        else args.output_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(panel_path).sort_values(
        ["target_year", "node_idx"]
    ).reset_index(drop=True)

    prediction_rows: list[dict] = []
    selection_rows: list[dict] = []
    for outer_country in COUNTRIES:
        source_countries = [
            country for country in COUNTRIES if country != outer_country
        ]
        for year in EVAL_YEARS:
            train = panel[
                panel["country"].isin(source_countries)
                & (panel["target_year"] <= year - 1)
            ]
            test = panel[
                (panel["country"] == outer_country)
                & (panel["target_year"] == year)
            ]
            nested = nested_source_predictions(panel, outer_country, year)
            ridge_weight, candidates, passes_fallback = select_weight(nested)
            ridge = fit_ridge(train, test)
            persistence = test["side_lag_1"].clip(lower=0.0).to_numpy(dtype=float)
            values = {
                "persistence": persistence,
                "ridge": ridge,
                "mean_50_50": combine(persistence, ridge, 0.5),
                "nested_weight": combine(persistence, ridge, ridge_weight),
                "nested_weight_fallback": combine(
                    persistence,
                    ridge,
                    ridge_weight if passes_fallback else 0.0,
                ),
            }
            selection_rows.append(
                {
                    "outer_country": outer_country,
                    "target_year": year,
                    "ridge_weight": ridge_weight,
                    "fallback_accepted": passes_fallback,
                    "effective_ridge_weight": (
                        ridge_weight if passes_fallback else 0.0
                    ),
                    "nested_rows": int(len(nested)),
                    "weight_candidates_json": json.dumps(candidates),
                    "outer_target_used_for_selection": False,
                }
            )
            for config, prediction in values.items():
                for row, value in zip(test.itertuples(index=False), prediction):
                    prediction_rows.append(
                        {
                            "country": outer_country,
                            "target_year": year,
                            "ZE2020": int(row.ZE2020),
                            "ZE2020_local": int(row.ZE2020_local),
                            "config": config,
                            "y_true": float(getattr(row, TARGET)),
                            "y_pred": float(value),
                        }
                    )

    predictions = pd.DataFrame(prediction_rows)
    selections = pd.DataFrame(selection_rows)
    yearly, country, balanced = summarize(predictions)
    decision = build_decision(yearly, country, balanced)

    predictions.to_csv(output_dir / "phase4j_a_predictions.csv", index=False)
    selections.to_csv(output_dir / "phase4j_a_weight_selection.csv", index=False)
    yearly.to_csv(output_dir / "phase4j_a_yearly.csv", index=False)
    country.to_csv(output_dir / "phase4j_a_country.csv", index=False)
    balanced.to_csv(output_dir / "phase4j_a_balanced.csv", index=False)
    (output_dir / "phase4j_a_decision.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )
    print("=== COUNTRY ===")
    print(country.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("\n=== BALANCED / POOLED ===")
    print(balanced.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("\n=== DECISION ===")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
