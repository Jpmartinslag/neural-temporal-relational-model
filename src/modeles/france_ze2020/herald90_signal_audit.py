"""HERALD 90 stage 1: what the French labour signals actually contain.

HERALD 89 stopped because annual establishment creations, on their own, do not carry
enough observable signal for even an oracle to separate the true commuting graph from a
deranged one. The median French cell holds about 83 creations a year; its sampling noise
is larger than any relational effect calibrated at a quarter of the latent movement.

This module asks a different question before any model is written: do the *dense* labour
signals -- private headcount, payroll, employer establishments, the localised unemployment
rate -- carry predictive information that flows along observed commuting?

Two parts, both NumPy and both cheap:

* :func:`audit_signals` measures what each signal really offers on the 280 zones --
  coverage, volume, zeros, gaps, and the methodological breaks that must be modelled as
  nuisance rather than read as territorial dynamics;
* :func:`tournament` compares five paired models per signal, where only the neighbour term
  changes: none, true commuting, a fixed derangement, degree-matched random neighbours,
  and the national mean.

Nothing here trains a network. The tournament exists to decide whether a network is worth
running at all.
"""
from __future__ import annotations

import collections
import csv
import gzip
import pathlib
from typing import Any

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
PANEL = REPO / "data" / "processed" / "france_ze2020" / "fr_ze2020_multisource_long_panel_v1.csv"
COMMUTING = REPO / "data" / "processed" / "france_ze2020" / "fr_ze2020_commuting_strict_ex_ante_edges.csv.gz"
CLEAN_PANEL = REPO / "data" / "processed" / "france_ze2020" / "fr_ze2020_clean_panel.csv"

# Signals under test. `kind` drives the likelihood: counts get a log link and a
# Negative-Binomial deviance, rates get a logit-scale Gaussian error.
SIGNALS = {
    "urssaf_private_headcount_raw": {"freq": "Q", "kind": "count",
                                     "label": "Urssaf private salaried headcount"},
    "urssaf_private_payroll_raw": {"freq": "Q", "kind": "positive",
                                   "label": "Urssaf gross payroll"},
    "urssaf_employer_establishments": {"freq": "A", "kind": "count",
                                       "label": "Urssaf employer establishments"},
    "local_unemployment_rate_sa": {"freq": "Q", "kind": "rate",
                                   "label": "Insee localised unemployment rate"},
    "establishment_creations": {"freq": "A", "kind": "count",
                                "label": "SIDE establishment creations"},
}

# Documented Urssaf breaks: 100% individual DSN records from June 2021, apprentices
# included from June 2023. They are nuisance regressors, never territorial events.
URSSAF_BREAK_YEARS = (2021, 2023)
COVID_YEARS = (2020, 2021)

ARMS = ("B0_local", "B1_commuting", "B2_permuted", "B3_random_degree",
        "B4_national_only")


# ── Loading ──────────────────────────────────────────────────────────────────

def canonical_zones() -> list[str]:
    with CLEAN_PANEL.open(newline="") as handle:
        return sorted({row["ze2020"].zfill(4) for row in csv.DictReader(handle)})


def load_signal(measure: str, zones: list[str], sector: str = "TOTAL"
                ) -> dict[str, Any]:
    """Return one signal as a dense (period, zone) array plus its availability mask.

    Only rows the panel marks observed are read, so a gap stays a gap. Release dates
    travel with the values and are applied later by the fold logic, never here.
    """
    index = {zone: position for position, zone in enumerate(zones)}
    values: dict[tuple[int, int], float] = {}
    releases: dict[tuple[int, int], str] = {}
    with PANEL.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["measure"] != measure or row["sector"] != sector:
                continue
            zone = row["ze2020"]
            if zone not in index:
                continue
            period = (int(row["year"]), int(row["quarter"]) if row["quarter"] else 0)
            if row["availability_mask"] != "1":
                continue
            values[(period, index[zone])] = float(row["value"])
            releases[period] = row["release_date"]
    periods = sorted({key[0] for key in values})
    grid = np.full((len(periods), len(zones)), np.nan)
    position = {period: i for i, period in enumerate(periods)}
    for (period, zone_index), value in values.items():
        grid[position[period], zone_index] = value
    return {"measure": measure, "periods": periods, "values": grid,
            "mask": np.isfinite(grid),
            "release_date": {period: releases[period] for period in periods}}


def commuting_matrix(zones: list[str], decision_year: int = 2019) -> np.ndarray:
    """Row-normalised observed commuting, using only snapshots released by the year."""
    index = {zone: position for position, zone in enumerate(zones)}
    matrix = np.zeros((len(zones), len(zones)))
    with gzip.open(COMMUTING, "rt", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["decision_year"]) != decision_year:
                continue
            source, target = row["source_ze2020"].zfill(4), row["target_ze2020"].zfill(4)
            if source in index and target in index and source != target:
                matrix[index[source], index[target]] = float(row["edge_weight"])
    np.fill_diagonal(matrix, 0.0)
    total = matrix.sum(1, keepdims=True)
    return np.divide(matrix, total, out=np.zeros_like(matrix), where=total > 0)


# ── Stage 1a: the audit table ────────────────────────────────────────────────

def audit_signals(zones: list[str]) -> list[dict[str, Any]]:
    rows = []
    for measure, meta in SIGNALS.items():
        loaded = load_signal(measure, zones)
        values, mask = loaded["values"], loaded["mask"]
        observed = values[mask]
        years = sorted({period[0] for period in loaded["periods"]})
        zone_coverage = mask.any(0).sum()
        rows.append({
            "signal": measure,
            "label": meta["label"],
            "source": ("Urssaf" if measure.startswith("urssaf")
                       else "Insee" if "unemployment" in measure else "Insee SIDE"),
            "frequency": meta["freq"],
            "kind": meta["kind"],
            "year_min": years[0], "year_max": years[-1], "n_periods": len(loaded["periods"]),
            "zones_covered": int(zone_coverage),
            "cell_coverage_pct": round(100.0 * mask.mean(), 2),
            "median": float(np.median(observed)) if observed.size else None,
            "q25": float(np.quantile(observed, 0.25)) if observed.size else None,
            "q75": float(np.quantile(observed, 0.75)) if observed.size else None,
            "zeros_pct": round(100.0 * float((observed == 0).mean()), 3) if observed.size else None,
            "missing_pct": round(100.0 * float((~mask).mean()), 3),
            "known_breaks": ("Urssaf 2021 DSN, 2023 apprentices"
                             if measure.startswith("urssaf") else
                             "Insee 2018Q1 field extension" if "unemployment" in measure
                             else "none declared"),
        })
    return rows


# ── Stage 1b: the paired tournament ──────────────────────────────────────────

def _design(signal: dict[str, Any], neighbour: np.ndarray | None,
            breaks: bool = True) -> dict[str, np.ndarray]:
    """Build one-step-ahead features. Everything is dated at or before ``t``.

    The local baseline already carries the national mean, so a placebo can never win by
    smuggling in aggregate information the baseline lacks.
    """
    values, mask = signal["values"], signal["mask"]
    periods = signal["periods"]
    usable = mask[:-1] & mask[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        level = np.where(mask, np.log(np.maximum(values, 1e-6)), np.nan)
    lag1 = level[:-1]
    change = np.full_like(lag1, np.nan)
    change[1:] = level[1:-1] - level[:-2]
    target = level[1:]

    national = np.full(len(lag1), np.nan)
    for t in range(len(lag1)):
        row = lag1[t][usable[t]]
        national[t] = row.mean() if row.size else np.nan

    quarters = np.asarray([period[1] for period in periods[:-1]])
    target_years = np.asarray([period[0] for period in periods[1:]])

    columns = [np.ones_like(lag1), lag1, np.nan_to_num(change),
               np.repeat(national[:, None], lag1.shape[1], axis=1)]
    for q in (1, 2, 3):
        columns.append(np.repeat((quarters == q).astype(float)[:, None],
                                 lag1.shape[1], axis=1))
    if breaks:
        for year in URSSAF_BREAK_YEARS + COVID_YEARS:
            columns.append(np.repeat((target_years == year).astype(float)[:, None],
                                     lag1.shape[1], axis=1))
    if neighbour is not None:
        centred = np.where(usable, np.nan_to_num(change), 0.0)
        neighbour_term = np.stack([neighbour @ centred[t] for t in range(len(centred))])
        columns.append(neighbour_term)
    return {"x": np.stack(columns, axis=-1), "y": target, "usable": usable,
            "target_years": target_years, "has_neighbour": neighbour is not None}


def _fit_score(design: dict[str, np.ndarray], train: list[int], score: int
               ) -> dict[str, float]:
    rows = [design["x"][t][design["usable"][t]] for t in train]
    response = [design["y"][t][design["usable"][t]] for t in train]
    x = np.concatenate(rows); y = np.concatenate(response)
    gram = x.T @ x + 1e-8 * np.eye(x.shape[1])
    beta = np.linalg.solve(gram, x.T @ y)
    ok = design["usable"][score]
    prediction = design["x"][score][ok] @ beta
    residual = design["y"][score][ok] - prediction
    return {"sse": float(residual @ residual), "n": int(ok.sum()),
            "mse": float((residual ** 2).mean()),
            "neighbour_beta": float(beta[-1]) if design["has_neighbour"] else 0.0}


def degree_matched_random(commuting: np.ndarray, seed: int) -> np.ndarray:
    """Random neighbours with the same out-degree and the same weight multiset per row."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(commuting)
    n = len(commuting)
    for i in range(n):
        weights = commuting[i][commuting[i] > 0]
        if not weights.size:
            continue
        candidates = rng.choice([j for j in range(n) if j != i],
                                size=len(weights), replace=False)
        out[i, candidates] = rng.permutation(weights)
    total = out.sum(1, keepdims=True)
    return np.divide(out, total, out=np.zeros_like(out), where=total > 0)


def derangement(commuting: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(commuting)
    for _ in range(1000):
        permutation = rng.permutation(n)
        if not np.any(permutation == np.arange(n)):
            break
    else:
        raise RuntimeError("no derangement found")
    return commuting[permutation][:, permutation]


def tournament(zones: list[str], measure: str, commuting: np.ndarray,
               seeds: tuple[int, ...], n_score_periods: int = 8) -> dict[str, Any]:
    """Five arms, identical folds, only the neighbour term changes."""
    signal = load_signal(measure, zones)
    if len(signal["periods"]) < 12:
        return {"signal": measure, "status": "too_short",
                "n_periods": len(signal["periods"])}
    neighbours = {
        "B0_local": None,
        "B1_commuting": commuting,
        "B4_national_only": None,
    }
    designs = {name: _design(signal, matrix) for name, matrix in neighbours.items()}
    designs["B4_national_only"] = _design(signal, None, breaks=True)

    folds: list[dict[str, Any]] = []
    n_steps = len(designs["B0_local"]["y"])
    score_positions = list(range(n_steps - n_score_periods, n_steps))
    for seed in seeds:
        permuted = derangement(commuting, seed)
        random_graph = degree_matched_random(commuting, seed + 7)
        designs["B2_permuted"] = _design(signal, permuted)
        designs["B3_random_degree"] = _design(signal, random_graph)
        for position in score_positions:
            train = list(range(position))
            if len(train) < 8:
                continue
            entry = {"seed": seed, "score_position": position,
                     "target_year": int(designs["B0_local"]["target_years"][position])}
            for arm in ARMS:
                entry[arm] = _fit_score(designs[arm], train, position)
            folds.append(entry)

    def total(arm: str) -> float:
        return float(np.sum([fold[arm]["sse"] for fold in folds]))

    base = total("B0_local")
    result = {"signal": measure, "status": "scored", "n_folds": len(folds),
              "n_observations": int(np.sum([fold["B0_local"]["n"] for fold in folds])),
              "sse": {arm: total(arm) for arm in ARMS}}
    result["gain_vs_local"] = {
        arm: (base - total(arm)) / max(base, 1e-12) for arm in ARMS}
    result["commuting_vs_permuted"] = (
        (total("B2_permuted") - total("B1_commuting")) / max(total("B2_permuted"), 1e-12))
    result["commuting_vs_random"] = (
        (total("B3_random_degree") - total("B1_commuting"))
        / max(total("B3_random_degree"), 1e-12))
    per_fold = [fold["B1_commuting"]["sse"] < fold["B2_permuted"]["sse"] for fold in folds]
    result["folds_favouring_commuting"] = int(sum(per_fold))
    result["fold_share_favouring_commuting"] = float(np.mean(per_fold)) if per_fold else 0.0
    by_year = collections.defaultdict(list)
    for fold, favours in zip(folds, per_fold):
        by_year[fold["target_year"]].append(favours)
    result["by_target_year"] = {year: float(np.mean(v)) for year, v in sorted(by_year.items())}
    result["mean_neighbour_beta"] = float(np.mean(
        [fold["B1_commuting"]["neighbour_beta"] for fold in folds]))
    return result


def relation_informative(result: dict[str, Any], min_fold_share: float = 0.80
                         ) -> dict[str, Any]:
    """The pre-registered direction gate, stated before any result was read."""
    if result.get("status") != "scored":
        return {"verdict": "NOT_SCORED", "passes": False}
    checks = {
        "beats_permuted": result["commuting_vs_permuted"] > 0,
        "beats_degree_matched_random": result["commuting_vs_random"] > 0,
        "beats_local_baseline": result["gain_vs_local"]["B1_commuting"] > 0,
        "direction_stable_across_folds":
            result["fold_share_favouring_commuting"] >= min_fold_share,
        "not_a_single_origin": sum(
            share > 0.5 for share in result["by_target_year"].values()) >= max(
                1, int(0.6 * len(result["by_target_year"]))),
    }
    return {"verdict": "RELATION_INFORMATIVE" if all(checks.values()) else "NOT_INFORMATIVE",
            "checks": checks, "passes": bool(all(checks.values()))}


MIN_INFORMATIVE_SIGNALS_FOR_FUSION = 2


def authorise_multisignal_oracle(verdicts: dict[str, dict]) -> dict[str, Any]:
    """Stage 1 -> stage 2 authorisation, computed rather than asserted.

    The multisignal hypothesis needs at least two signals that independently carry
    direction-stable relational information. With exactly one, there is nothing to fuse
    and the honest continuation is a single-signal line, which is a different claim.
    """
    informative = sorted(name for name, verdict in verdicts.items() if verdict["passes"])
    return {
        "informative_signals": informative,
        "n_informative": len(informative),
        "required": MIN_INFORMATIVE_SIGNALS_FOR_FUSION,
        "authorises_multisignal_oracle":
            len(informative) >= MIN_INFORMATIVE_SIGNALS_FOR_FUSION,
        "authorises_single_signal_followup": len(informative) >= 1,
    }
