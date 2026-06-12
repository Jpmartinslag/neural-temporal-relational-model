"""Build signed lagged sector-to-sector association graphs for HERALD.

For each country and rolling window, the model asks whether lagged growth in a
source sector adds information about current growth in a target sector after
controlling for the target sector's own lag. Territory and year means are
removed before estimation. Edges express predictive precedence, not structural
economic causality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = (
    BASE
    / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
)
DEFAULT_OUT = BASE / "data/processed/herald_observatory_v02/sector_precedence"
SEED = 42
WINDOW_YEARS = 6
MIN_SAMPLES = 60
FDR_Q = 0.05
MIN_ABS_BETA = 0.10
MIN_DELTA_R2 = 0.005
MIN_SIGN_STABILITY = 0.70


def empirical_p(observed: float, null: list[float]) -> float:
    values = np.asarray([v for v in null if np.isfinite(v)], dtype=float)
    if not np.isfinite(observed) or len(values) == 0:
        return np.nan
    return float((1 + np.sum(np.abs(values) >= abs(observed))) / (len(values) + 1))


def bh_fdr(pvalues: pd.Series) -> pd.Series:
    values = pvalues.to_numpy(dtype=float)
    result = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        return pd.Series(result, index=pvalues.index)
    order = valid[np.argsort(values[valid])]
    ranked = values[order] * len(order) / np.arange(1, len(order) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    result[order] = np.minimum(ranked, 1.0)
    return pd.Series(result, index=pvalues.index)


def two_way_demean(values: np.ndarray, territories: np.ndarray, years: np.ndarray) -> np.ndarray:
    """Remove territory and year means with alternating projections."""
    out = values.astype(float).copy()
    for _ in range(8):
        previous = out.copy()
        for labels in (territories, years):
            for label in np.unique(labels):
                mask = labels == label
                out[mask] -= np.mean(out[mask], axis=0)
        if np.max(np.abs(out - previous)) < 1e-10:
            break
    return out


def fit_partial_edge(samples: pd.DataFrame) -> dict[str, float]:
    """Fit target_t ~ target_t-1 + source_t-1 after two-way demeaning."""
    columns = ["target_growth", "target_lag", "source_lag"]
    valid = samples[columns].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) < MIN_SAMPLES:
        return {"n_samples": len(valid), "beta": np.nan, "delta_r2": np.nan}
    matrix = two_way_demean(
        valid[columns].to_numpy(dtype=float),
        samples.loc[valid.index, "territory_id"].astype(str).to_numpy(),
        samples.loc[valid.index, "observation_year"].to_numpy(),
    )
    std = matrix.std(axis=0, ddof=1)
    if np.any(std < 1e-12):
        return {"n_samples": len(valid), "beta": np.nan, "delta_r2": np.nan}
    target, own, source = (matrix / std).T
    baseline = np.column_stack([np.ones(len(target)), own])
    full = np.column_stack([np.ones(len(target)), own, source])
    pred_base = baseline @ np.linalg.lstsq(baseline, target, rcond=None)[0]
    coef_full = np.linalg.lstsq(full, target, rcond=None)[0]
    pred_full = full @ coef_full
    total = float(np.sum((target - target.mean()) ** 2))
    if total <= 0:
        return {"n_samples": len(valid), "beta": np.nan, "delta_r2": np.nan}
    r2_base = 1 - float(np.sum((target - pred_base) ** 2)) / total
    r2_full = 1 - float(np.sum((target - pred_full) ** 2)) / total
    return {
        "n_samples": len(valid),
        "beta": float(coef_full[2]),
        "delta_r2": float(r2_full - r2_base),
    }


def pair_samples(
    panel: pd.DataFrame,
    source_sector: str,
    target_sector: str,
    start_year: int,
    end_year: int,
    exclude_years: frozenset[int] = frozenset(),
) -> pd.DataFrame:
    """Align source(t-1), target(t-1), and target(t) within territory."""
    keys = ["territory_id", "observation_year"]
    usable = panel[
        panel["observation_mask"].eq(1)
        & panel["structural_mask"].eq(1)
        & panel["observation_year"].between(start_year - 1, end_year)
        & ~panel["observation_year"].isin(exclude_years)
    ]
    source = usable[usable["sector_id"].eq(source_sector)][
        keys + ["velocity"]
    ].rename(columns={"velocity": "source_lag"})
    source["observation_year"] += 1
    target_lag = usable[usable["sector_id"].eq(target_sector)][
        keys + ["velocity"]
    ].rename(columns={"velocity": "target_lag"})
    target_lag["observation_year"] += 1
    target = usable[
        usable["sector_id"].eq(target_sector)
        & usable["observation_year"].between(start_year, end_year)
    ][keys + ["velocity"]].rename(columns={"velocity": "target_growth"})
    return (
        target.merge(target_lag, on=keys, how="inner", validate="one_to_one")
        .merge(source, on=keys, how="inner", validate="one_to_one")
        .sort_values(keys)
        .reset_index(drop=True)
    )


def permute_source_within_year(samples: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    permuted = samples.copy()
    for _, index in permuted.groupby("observation_year").groups.items():
        positions = np.asarray(list(index))
        permuted.loc[positions, "source_lag"] = rng.permutation(
            permuted.loc[positions, "source_lag"].to_numpy()
        )
    return permuted


def bootstrap_sign_stability(
    samples: pd.DataFrame,
    observed_beta: float,
    rng: np.random.Generator,
    n_bootstraps: int,
) -> float:
    territories = samples["territory_id"].astype(str).unique()
    signs = []
    expected = np.sign(observed_beta)
    for _ in range(n_bootstraps):
        selected = rng.choice(territories, size=len(territories), replace=True)
        frames = []
        for sample_id, territory in enumerate(selected):
            frame = samples[samples["territory_id"].astype(str).eq(territory)].copy()
            frame["territory_id"] = f"{territory}__{sample_id}"
            frames.append(frame)
        result = fit_partial_edge(pd.concat(frames, ignore_index=True))
        if np.isfinite(result["beta"]):
            signs.append(np.sign(result["beta"]) == expected)
    return float(np.mean(signs)) if signs else np.nan


def evaluate_edge(
    samples: pd.DataFrame,
    rng: np.random.Generator,
    n_permutations: int,
    n_bootstraps: int,
) -> dict[str, float]:
    observed = fit_partial_edge(samples)
    if not np.isfinite(observed["beta"]):
        return {
            **observed,
            "p_perm": np.nan,
            "bootstrap_sign_stability": np.nan,
        }
    null = [
        fit_partial_edge(permute_source_within_year(samples, rng))["beta"]
        for _ in range(n_permutations)
    ]
    return {
        **observed,
        "p_perm": empirical_p(observed["beta"], null),
        "bootstrap_sign_stability": bootstrap_sign_stability(
            samples, observed["beta"], rng, n_bootstraps
        ),
    }


def build(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    n_permutations: int,
    n_bootstraps: int,
    window_years: int = WINDOW_YEARS,
) -> dict:
    required = {
        "country", "territory_id", "observation_year", "sector_id", "velocity",
        "observation_mask", "structural_mask",
    }
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    rng = np.random.default_rng(SEED)
    rows = []
    sectors = sorted(panel["sector_id"].unique())
    for scenario, excluded in [
        ("main", frozenset()),
        ("without_2020", frozenset({2020})),
    ]:
        for country, country_panel in panel.groupby("country"):
            years = sorted(country_panel["observation_year"].unique())
            for end_year in years:
                start_year = end_year - window_years + 1
                if len([y for y in years if start_year <= y <= end_year and y not in excluded]) < 4:
                    continue
                family_start = len(rows)
                for source in sectors:
                    for target in sectors:
                        if source == target:
                            continue
                        samples = pair_samples(
                            country_panel, source, target, start_year, end_year, excluded
                        )
                        result = evaluate_edge(
                            samples, rng, n_permutations, n_bootstraps
                        )
                        rows.append({
                            "scenario": scenario,
                            "country": country,
                            "window_start": start_year,
                            "window_end": end_year,
                            "lag_years": 1,
                            "source_sector": source,
                            "target_sector": target,
                            **result,
                        })
                family_index = range(family_start, len(rows))
                family = pd.Series(
                    [rows[index]["p_perm"] for index in family_index],
                    index=list(family_index),
                )
                qvalues = bh_fdr(family)
                for index, qvalue in qvalues.items():
                    rows[index]["q_fdr"] = qvalue

    edges = pd.DataFrame(rows)
    edges["association_sign"] = np.where(
        edges["beta"].gt(0), "positive",
        np.where(edges["beta"].lt(0), "negative", "unavailable"),
    )
    edges["promoted_exploratory_edge"] = (
        edges["q_fdr"].le(FDR_Q)
        & edges["beta"].abs().ge(MIN_ABS_BETA)
        & edges["delta_r2"].ge(MIN_DELTA_R2)
        & edges["bootstrap_sign_stability"].ge(MIN_SIGN_STABILITY)
    ).astype(int)

    main = edges[edges["scenario"].eq("main")].copy()
    sensitivity = edges[edges["scenario"].eq("without_2020")][
        ["country", "window_end", "source_sector", "target_sector",
         "association_sign", "promoted_exploratory_edge"]
    ].rename(columns={
        "association_sign": "association_sign_without_2020",
        "promoted_exploratory_edge": "promoted_without_2020",
    })
    comparison = main.merge(
        sensitivity,
        on=["country", "window_end", "source_sector", "target_sector"],
        how="left",
    )
    comparison["covid_robust_edge"] = (
        comparison["promoted_exploratory_edge"].eq(1)
        & comparison["promoted_without_2020"].eq(1)
        & comparison["association_sign"].eq(
            comparison["association_sign_without_2020"]
        )
    ).astype(int)

    out_dir.mkdir(parents=True, exist_ok=True)
    edges.to_csv(out_dir / "sector_precedence_all_edges.csv", index=False)
    comparison.to_csv(out_dir / "sector_precedence_main_with_sensitivity.csv", index=False)
    latest = comparison.loc[
        comparison.groupby("country")["window_end"].transform("max").eq(
            comparison["window_end"]
        )
    ]
    latest.to_csv(out_dir / "sector_precedence_latest.csv", index=False)
    country_summary = (
        comparison.groupby(["scenario", "country"], dropna=False)
        if "scenario" in comparison.columns
        else None
    )
    del country_summary
    summary = {
        "method": "two-way-demeaned lag-1 partial regression",
        "interpretation": "predictive precedence association, not structural causality",
        "window_years": window_years,
        "n_permutations": n_permutations,
        "n_bootstraps": n_bootstraps,
        "thresholds": {
            "fdr_q": FDR_Q,
            "min_abs_beta": MIN_ABS_BETA,
            "min_delta_r2": MIN_DELTA_R2,
            "min_bootstrap_sign_stability": MIN_SIGN_STABILITY,
            "min_samples": MIN_SAMPLES,
        },
        "rows": int(len(edges)),
        "countries": sorted(edges["country"].unique().tolist()),
        "promoted_main": int(main["promoted_exploratory_edge"].sum()),
        "covid_robust_edges": int(comparison["covid_robust_edge"].sum()),
        "decision": (
            "SECTOR_PRECEDENCE_PROTOTYPE_READY"
            if comparison.groupby("country")["covid_robust_edge"].sum().gt(0).sum() >= 2
            else "SECTOR_PRECEDENCE_NOT_PROMOTED"
        ),
    }
    (out_dir / "sector_precedence_decision.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n-permutations", type=int, default=999)
    parser.add_argument("--n-bootstraps", type=int, default=500)
    parser.add_argument("--window-years", type=int, default=WINDOW_YEARS)
    parser.add_argument("--confirm-full-run", action="store_true")
    args = parser.parse_args()
    if not args.confirm_full_run and (
        args.n_permutations > 19 or args.n_bootstraps > 19
    ):
        raise SystemExit(
            "Full run requires --confirm-full-run. For smoke use "
            "--n-permutations 9 --n-bootstraps 9."
        )
    panel = pd.read_csv(args.panel, dtype={"territory_id": str}, low_memory=False)
    summary = build(
        panel,
        args.out_dir,
        n_permutations=args.n_permutations,
        n_bootstraps=args.n_bootstraps,
        window_years=args.window_years,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
