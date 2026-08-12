"""HERALD 91: the HERALD 90 signal tournament, rebuilt against its own audit.

HERALD 90 found one candidate signal and blocked the multisignal stage. An audit then
found eleven defects in how that conclusion was reached. This module fixes the ones that
change the arithmetic, and is explicit about the one that cannot be fixed with the data
in hand.

What changed, and why each change matters
-----------------------------------------

**Likelihoods.** HERALD 90 fitted every signal by ordinary least squares on log levels and
compared sums of squared error. Counts, a positive continuous amount and a bounded rate do
not share an error model, so those numbers were not comparable across signals. Each signal
now carries its own: Negative-Binomial deviance for counts, Gamma deviance for payroll,
Gaussian deviance on the logit scale for the unemployment rate. Every result is reported as
deviance **relative to that signal's own null model**, which is the only way a headcount
number and a rate number can be put in the same table.

**Breaks by source.** The Urssaf 2021 and 2023 breaks belong to Urssaf series only; the
Insee 2018Q1 field extension belongs to the unemployment rate only; COVID is a common shock
and is carried separately by every signal. HERALD 90 applied one shared set of indicators
to everything, which both over-corrected some series and under-corrected others.

**B4 is now a different model.** In HERALD 90 `B4_national_only` was built with the same
columns as `B0_local`, so the two were numerically identical and the comparison was empty.
B4 now drops local history entirely and keeps only the aggregate, which is what the arm was
meant to isolate.

**Placebo draws are a null distribution, not replicates.** HERALD 90 reported "5/5 seeds"
where the data, the folds and the true commuting matrix were all identical and only the
placebo changed. That is pseudoreplication. Placebo draws now build an explicit null
distribution, the observed statistic is placed inside it, and the three counts -- temporal
origins, placebo draws, model seeds -- are reported separately and never merged.

**More origins.** Scoring only the last five annual or eight quarterly steps left the
estimate resting on very few temporal units. Every origin with a sufficient training window
is now scored.

**Sectors where they exist.** Urssaf and the unemployment rate are published at ZE level
with no sector dimension at all, so `TOTAL` is a property of the source, not a choice. SIDE
creations, SIDE stocks and FLORES do carry sectors, and those are run at sector level too.

What could not be fixed
-----------------------

The panel carries **one release date per source for its whole history** -- 2025 or 2026 for
series starting in 1998. Historical vintages were not published in a form this project can
recover, so no as-of join is possible. This analysis is therefore
``RETROSPECTIVE_FINAL_VINTAGE_ANALYSIS``: alignment is causal by observation period, but the
*values* are the final revised ones. It cannot support a prospective ex-ante claim, and
revision risk is unquantified. That limitation is declared, not worked around.
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

VINTAGE_POLICY = "RETROSPECTIVE_FINAL_VINTAGE_ANALYSIS"

# `family` selects the likelihood. `breaks` names which nuisance indicators belong to
# this signal; COVID is common and is added to all of them.
SIGNALS: dict[str, dict[str, Any]] = {
    "urssaf_private_headcount_raw": {
        "family": "negative_binomial", "freq": "Q", "breaks": ("urssaf",),
        "seasonal": True, "sectors": False,
        "label": "Urssaf private salaried headcount, not seasonally adjusted"},
    "urssaf_private_payroll_raw": {
        "family": "gamma", "freq": "Q", "breaks": ("urssaf",),
        "seasonal": True, "sectors": False,
        "label": "Urssaf gross payroll, not seasonally adjusted"},
    "urssaf_employer_establishments": {
        "family": "negative_binomial", "freq": "A", "breaks": ("urssaf",),
        "seasonal": False, "sectors": False,
        "label": "Urssaf employer establishments"},
    "local_unemployment_rate_sa": {
        "family": "logit_gaussian", "freq": "Q", "breaks": ("insee_unemployment",),
        "seasonal": False, "sectors": False,
        "label": "Insee localised unemployment rate, publisher-adjusted"},
    "establishment_creations": {
        "family": "negative_binomial", "freq": "A", "breaks": (),
        "seasonal": False, "sectors": True,
        "label": "Insee SIDE establishment creations"},
    "active_establishment_stock": {
        "family": "negative_binomial", "freq": "A", "breaks": (),
        "seasonal": False, "sectors": True,
        "label": "Insee SIDE economically active establishment stock"},
}

BREAK_YEARS = {
    "urssaf": (2021, 2023),              # DSN individual records; apprentices included
    "insee_unemployment": (2018,),       # field extended to all salaried employment
}
COVID_YEARS = (2020, 2021)

ARMS = ("B0_local", "B1_commuting", "B2_permuted", "B3_random_degree", "B4_national_only")


# ── Loading ──────────────────────────────────────────────────────────────────

def canonical_zones() -> list[str]:
    with CLEAN_PANEL.open(newline="") as handle:
        return sorted({row["ze2020"].zfill(4) for row in csv.DictReader(handle)})


def load_signal(measure: str, zones: list[str], sector: str = "TOTAL") -> dict[str, Any]:
    """One signal as (period, zone), observed cells only, gaps preserved as NaN."""
    index = {zone: position for position, zone in enumerate(zones)}
    cells: dict[tuple[tuple[int, int], int], float] = {}
    releases: set[str] = set()
    with PANEL.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["measure"] != measure or row["sector"] != sector:
                continue
            if row["availability_mask"] != "1" or row["ze2020"] not in index:
                continue
            period = (int(row["year"]), int(row["quarter"]) if row["quarter"] else 0)
            cells[(period, index[row["ze2020"]])] = float(row["value"])
            releases.add(row["release_date"])
    periods = sorted({key[0] for key in cells})
    grid = np.full((len(periods), len(zones)), np.nan)
    position = {period: i for i, period in enumerate(periods)}
    for (period, zone), value in cells.items():
        grid[position[period], zone] = value
    return {"measure": measure, "sector": sector, "periods": periods, "values": grid,
            "mask": np.isfinite(grid), "release_dates": sorted(releases),
            "vintage_policy": VINTAGE_POLICY}


def commuting_matrix(zones: list[str], decision_year: int = 2019) -> np.ndarray:
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


# ── Deviance families ────────────────────────────────────────────────────────

def _nb_deviance(y, mu, phi):
    y = np.asarray(y, float); mu = np.maximum(np.asarray(mu, float), 1e-9)
    phi = max(float(phi), 1e-6)
    with np.errstate(divide="ignore", invalid="ignore"):
        first = np.where(y > 0, y * np.log(np.maximum(y, 1e-9) / mu), 0.0)
        second = (y + phi) * np.log((y + phi) / (mu + phi))
    return float(2.0 * np.sum(first - second))


def _gamma_deviance(y, mu, _phi=None):
    y = np.maximum(np.asarray(y, float), 1e-9); mu = np.maximum(np.asarray(mu, float), 1e-9)
    return float(2.0 * np.sum(-np.log(y / mu) + (y - mu) / mu))


def _gaussian_deviance(y, mu, _phi=None):
    residual = np.asarray(y, float) - np.asarray(mu, float)
    return float(np.sum(residual ** 2))


DEVIANCE = {"negative_binomial": _nb_deviance, "gamma": _gamma_deviance,
            "logit_gaussian": _gaussian_deviance}


def _link_forward(values, family):
    """Map observations onto the scale the linear predictor lives on."""
    if family == "logit_gaussian":
        p = np.clip(np.asarray(values, float) / 100.0, 1e-4, 1 - 1e-4)
        return np.log(p / (1 - p))
    return np.log(np.maximum(np.asarray(values, float), 1e-6))


def _link_inverse(eta, family):
    if family == "logit_gaussian":
        return 100.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
    return np.exp(np.clip(eta, -30, 30))


# ── Design ───────────────────────────────────────────────────────────────────

def build_design(signal: dict[str, Any], meta: dict[str, Any],
                 neighbour: np.ndarray | None, arm: str) -> dict[str, Any]:
    """One-step-ahead design. Only ``B4_national_only`` drops local history.

    Every arm except B4 carries the same baseline, so a placebo can never win by
    supplying aggregate information the baseline lacks. B4 exists to answer a different
    question -- how much of the movement is purely national -- and is therefore the one
    arm that is *meant* to differ in its baseline.
    """
    values, mask, periods = signal["values"], signal["mask"], signal["periods"]
    family = meta["family"]
    usable = mask[:-1] & mask[1:]
    scale = _link_forward(values, family)
    lag1 = scale[:-1]
    change = np.full_like(lag1, np.nan)
    change[1:] = scale[1:-1] - scale[:-2]
    target_raw = values[1:]

    national = np.full(len(lag1), np.nan)
    for t in range(len(lag1)):
        row = lag1[t][usable[t]]
        national[t] = row.mean() if row.size else np.nan
    national_change = np.full(len(lag1), 0.0)
    national_change[1:] = np.diff(np.nan_to_num(national))

    target_years = np.asarray([period[0] for period in periods[1:]])
    quarters = np.asarray([period[1] for period in periods[:-1]])
    ones = np.ones_like(lag1)

    def spread(vector):
        return np.repeat(np.asarray(vector, float)[:, None], lag1.shape[1], axis=1)

    # The lagged level enters as an *offset*, not as a free coefficient. A free
    # coefficient on a log level near 8 makes the IRLS step matrix badly conditioned and
    # the fitted deviance explodes: the first version of this module scored the local
    # baseline at 1739 times its own null. With the level carried as an offset the model
    # is a growth model, which is both what the question asks and numerically stable.
    offset = lag1 if arm != "B4_national_only" else np.zeros_like(lag1)
    if arm == "B4_national_only":
        columns = [ones, spread(national), spread(national_change)]
    else:
        columns = [ones, np.nan_to_num(change), spread(national), spread(national_change)]
    if meta["seasonal"]:
        for quarter in (1, 2, 3):
            columns.append(spread((quarters == quarter).astype(float)))
    for family_name in meta["breaks"]:
        for year in BREAK_YEARS[family_name]:
            columns.append(spread((target_years >= year).astype(float)))
    for year in COVID_YEARS:
        columns.append(spread((target_years == year).astype(float)))
    if neighbour is not None:
        centred = np.where(usable, np.nan_to_num(change), 0.0)
        columns.append(np.stack([neighbour @ centred[t] for t in range(len(centred))]))

    return {"x": np.stack(columns, axis=-1), "y": target_raw, "usable": usable,
            "offset": offset, "target_years": target_years, "family": family,
            "has_neighbour": neighbour is not None}


def _irls_weights(mu: np.ndarray, family: str,
                  dispersion: float | None = None) -> np.ndarray:
    """Return GLM IRLS weights on the log-link scale.

    ``dispersion`` is the NB size parameter ``phi`` in
    ``Var(Y) = mu + mu**2 / phi``. Treating NB counts as Poisson would use
    ``weight = mu`` and silently give high-volume cells too much leverage.
    """
    mu = np.maximum(np.asarray(mu, float), 1e-9)
    if family == "negative_binomial":
        if dispersion is None or not np.isfinite(dispersion) or dispersion <= 0:
            raise ValueError("negative_binomial IRLS requires a positive fixed dispersion")
        return mu / (1.0 + mu / float(dispersion))
    if family == "gamma":
        return np.ones_like(mu)
    raise ValueError(f"IRLS weights are not defined for {family!r}")


def _irls(x, y, family, offset, dispersion: float | None = None, steps=30):
    """IRLS with a fixed offset and, for NB, a fixed training-only dispersion."""
    if family == "logit_gaussian":
        z = _link_forward(y, family) - offset
        gram = x.T @ x + 1e-8 * np.eye(x.shape[1])
        return np.linalg.solve(gram, x.T @ z)
    beta = np.zeros(x.shape[1])
    for _ in range(steps):
        mu = np.exp(np.clip(offset + x @ beta, -30, 30))
        weight = _irls_weights(mu, family, dispersion)
        working = x @ beta + (y - mu) / np.maximum(mu, 1e-9)
        wx = x * weight[:, None]
        gram = wx.T @ x + 1e-8 * np.eye(x.shape[1])
        try:
            step = np.linalg.solve(gram, wx.T @ working)
        except np.linalg.LinAlgError:
            break
        if not np.all(np.isfinite(step)) or np.max(np.abs(step - beta)) < 1e-10:
            beta = step if np.all(np.isfinite(step)) else beta
            break
        beta = step
    return beta


def estimate_nb_dispersion(design: dict[str, Any], train: list[int]) -> float:
    """Estimate one NB size parameter from the training-only persistence null.

    The estimate deliberately ignores every candidate neighbour graph. ``run_signal``
    computes it once per origin from B0 and passes the same frozen value to B0, B1, B4
    and every placebo, so graph arms cannot improve their score by choosing a different
    noise scale.
    """
    if design["family"] != "negative_binomial":
        raise ValueError("NB dispersion requested for a non-NB design")
    x = np.concatenate([design["x"][t][design["usable"][t], :1] for t in train])
    y = np.concatenate([design["y"][t][design["usable"][t]] for t in train])
    off = np.concatenate([design["offset"][t][design["usable"][t]] for t in train])
    # Poisson is used only to obtain a graph-free mean for this moment estimate.
    beta = np.zeros(1)
    for _ in range(30):
        mu = np.exp(np.clip(off + x @ beta, -30, 30))
        working = x @ beta + (y - mu) / np.maximum(mu, 1e-9)
        weight = mu
        wx = x * weight[:, None]
        step = np.linalg.solve(wx.T @ x + 1e-8 * np.eye(1), wx.T @ working)
        if np.max(np.abs(step - beta)) < 1e-10:
            beta = step
            break
        beta = step
    mu = np.exp(np.clip(off + x @ beta, -30, 30))
    numerator = float(np.sum((y - mu) ** 2 - mu))
    alpha = numerator / max(float(np.sum(mu ** 2)), 1e-12)
    return 1.0 / alpha if alpha > 1e-9 else 1e6


def fit_score(design: dict[str, Any], train: list[int], score: int,
              dispersion: float | None = None,
              allow_local_dispersion: bool = False) -> dict[str, float]:
    """Fit on training periods and score once with a frozen noise scale.

    For a Negative-Binomial design the dispersion must be supplied. The earlier fallback
    silently re-estimated it from the design in hand, which is graph-free but *design*-
    specific: ``B4_national_only`` carries a different offset, so a forgetful caller would
    have scored it under a different noise scale from the arm it is compared against. The
    invariant the whole comparison rests on -- one frozen dispersion per fold, shared by
    every arm -- cannot be left to the caller's memory.

    ``allow_local_dispersion`` exists for the estimation path itself and for exploratory
    single-arm probes; nothing in ``run_signal`` uses it.
    """
    family = design["family"]
    x = np.concatenate([design["x"][t][design["usable"][t]] for t in train])
    y = np.concatenate([design["y"][t][design["usable"][t]] for t in train])
    off = np.concatenate([design["offset"][t][design["usable"][t]] for t in train])
    if family == "negative_binomial":
        if dispersion is None:
            if not allow_local_dispersion:
                raise ValueError(
                    "negative_binomial scoring requires an explicit frozen dispersion; "
                    "pass the value estimated once per origin, or set "
                    "allow_local_dispersion=True to opt out deliberately")
            dispersion = estimate_nb_dispersion(design, train)
        phi = float(dispersion)
    else:
        phi = None
    beta = _irls(x, y, family, off, dispersion=phi)
    ok = design["usable"][score]
    mu = _link_inverse(design["offset"][score][ok] + design["x"][score][ok] @ beta, family)
    observed = design["y"][score][ok]
    if family == "logit_gaussian":
        deviance = _gaussian_deviance(_link_forward(observed, family),
                                      _link_forward(mu, family))
    else:
        deviance = DEVIANCE[family](observed, mu, phi)
    return {"deviance": deviance, "n": int(ok.sum()), "dispersion": phi,
            "neighbour_beta": float(beta[-1]) if design["has_neighbour"] else 0.0}


def null_deviance(design: dict[str, Any], train: list[int], score: int,
                  dispersion: float | None = None) -> float:
    """Intercept-only deviance, the denominator that makes signals comparable."""
    # The null keeps the offset -- it is the "no model beyond persistence" reference --
    # and drops every regressor except the intercept.
    intercept = {**design, "x": design["x"][..., :1], "has_neighbour": False}
    return fit_score(intercept, train, score, dispersion=dispersion)["deviance"]


# ── Controls ─────────────────────────────────────────────────────────────────

def derangement(matrix: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(matrix)
    for _ in range(2000):
        permutation = rng.permutation(n)
        if not np.any(permutation == np.arange(n)):
            return matrix[permutation][:, permutation]
    raise RuntimeError("no derangement found")


def degree_matched_random(matrix: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros_like(matrix)
    n = len(matrix)
    for i in range(n):
        weights = matrix[i][matrix[i] > 0]
        if not weights.size:
            continue
        targets = rng.choice([j for j in range(n) if j != i], size=len(weights),
                             replace=False)
        out[i, targets] = rng.permutation(weights)
    total = out.sum(1, keepdims=True)
    return np.divide(out, total, out=np.zeros_like(out), where=total > 0)


# ── The tournament ───────────────────────────────────────────────────────────

# A quarterly series can spare twelve periods before scoring; an annual one cannot.
# Using a single window silently dropped both SIDE signals, whose whole history is
# fourteen and eleven years, and would have left the historical reference untested.
MIN_TRAIN = {"Q": 12, "A": 8}


def run_signal(zones: list[str], measure: str, commuting: np.ndarray,
               placebo_draws: int = 40, min_train: int | None = None,
               sector: str = "TOTAL") -> dict[str, Any]:
    """Score every eligible origin, then place the observed statistic in a null.

    The placebo draws are a *null distribution*, not repetitions of the experiment. The
    reported p-value is the share of placebo graphs that do at least as well as observed
    commuting, and the number of temporal origins is reported beside it because that is
    the count of genuinely distinct units.
    """
    meta = SIGNALS[measure]
    if min_train is None:
        min_train = MIN_TRAIN[meta["freq"]]
    signal = load_signal(measure, zones, sector)
    if len(signal["periods"]) < min_train + 3:
        return {"signal": measure, "sector": sector, "status": "too_short",
                "n_periods": len(signal["periods"])}

    designs = {
        "B0_local": build_design(signal, meta, None, "B0_local"),
        "B1_commuting": build_design(signal, meta, commuting, "B1_commuting"),
        "B4_national_only": build_design(signal, meta, None, "B4_national_only"),
    }
    n_steps = len(designs["B0_local"]["y"])
    origins = [t for t in range(min_train, n_steps)]

    # Estimate one graph-free NB size on training data per origin, then freeze it for
    # every competing graph. Candidate arms cannot choose their own noise scale.
    dispersion_by_origin = {
        t: (estimate_nb_dispersion(designs["B0_local"], list(range(t)))
            if meta["family"] == "negative_binomial" else None)
        for t in origins
    }

    def total(design):
        return float(np.sum([fit_score(design, list(range(t)), t,
                                       dispersion=dispersion_by_origin[t])["deviance"]
                             for t in origins]))

    observed = {name: total(design) for name, design in designs.items()}
    observed["null_model"] = float(np.sum([
        null_deviance(designs["B0_local"], list(range(t)), t,
                      dispersion=dispersion_by_origin[t]) for t in origins]))

    per_origin_true = [fit_score(designs["B1_commuting"], list(range(t)), t,
                                 dispersion=dispersion_by_origin[t])["deviance"]
                       for t in origins]
    per_origin_base = [fit_score(designs["B0_local"], list(range(t)), t,
                                 dispersion=dispersion_by_origin[t])["deviance"]
                       for t in origins]
    # Where does the advantage actually live? Sensitivity to the rebound is a property of
    # the *gain*, not of how many scored origins happen to fall in 2020-2021: a signal can
    # score ten origins and owe its whole advantage to one of them.
    origin_years = [int(designs["B0_local"]["target_years"][t]) for t in origins]
    per_origin_gain = [base - true for base, true in zip(per_origin_base, per_origin_true)]
    total_gain = float(np.sum(np.maximum(per_origin_gain, 0.0)))
    covid_gain = float(np.sum([max(gain, 0.0) for gain, year
                               in zip(per_origin_gain, origin_years)
                               if year in COVID_YEARS or year in (2022,)]))
    covid_gain_share = covid_gain / total_gain if total_gain > 0 else 0.0

    permuted_totals, random_totals, wins_permuted = [], [], []
    for draw in range(placebo_draws):
        permuted = build_design(signal, meta, derangement(commuting, 5000 + draw),
                                "B2_permuted")
        randomised = build_design(signal, meta,
                                  degree_matched_random(commuting, 9000 + draw),
                                  "B3_random_degree")
        permuted_totals.append(total(permuted))
        random_totals.append(total(randomised))
        per_origin_permuted = [fit_score(permuted, list(range(t)), t,
                                         dispersion=dispersion_by_origin[t])["deviance"]
                               for t in origins]
        wins_permuted.append([a < b for a, b in zip(per_origin_true, per_origin_permuted)])

    permuted_totals = np.asarray(permuted_totals)
    random_totals = np.asarray(random_totals)
    true_total = observed["B1_commuting"]
    # Empirical p-value with the +1 correction. With B draws the smallest attainable
    # value is 1/(B+1), never zero: forty placebo graphs cannot license "p = 0".
    p_permuted = float((np.sum(permuted_totals <= true_total) + 1) / (placebo_draws + 1))
    p_random = float((np.sum(random_totals <= true_total) + 1) / (placebo_draws + 1))
    origin_win_rate = np.asarray(wins_permuted).mean(0)

    observed_statistic, null_statistics = permutation_statistics(
        permuted_totals, true_total)

    return {
        "signal": measure, "sector": sector, "status": "scored",
        "family": meta["family"], "frequency": meta["freq"],
        "vintage_policy": VINTAGE_POLICY,
        "replication_units": {
            "temporal_origins": len(origins),
            "placebo_draws": placebo_draws,
            "model_seeds": 0,
            "note": "placebo draws form a null distribution; they are not replicates",
        },
        "deviance": observed,
        "relative_to_null": {name: value / max(observed["null_model"], 1e-12)
                             for name, value in observed.items()},
        "gain_vs_local": (observed["B0_local"] - true_total) / max(observed["B0_local"], 1e-12),
        "gain_vs_national_only": (observed["B4_national_only"] - true_total)
                                 / max(observed["B4_national_only"], 1e-12),
        "gain_vs_permuted_median": float(
            (np.median(permuted_totals) - true_total) / max(np.median(permuted_totals), 1e-12)),
        "gain_vs_random_median": float(
            (np.median(random_totals) - true_total) / max(np.median(random_totals), 1e-12)),
        "p_value_vs_permuted": p_permuted,
        "p_value_vs_degree_matched_random": p_random,
        "p_value_floor": 1.0 / (placebo_draws + 1),
        "observed_statistic": observed_statistic,
        "null_statistics": [float(value) for value in null_statistics],
        "maxT_statistic": "standardised_deviance_improvement",
        "nb_dispersion_by_origin": {
            str(int(t)): (None if dispersion_by_origin[t] is None
                          else float(dispersion_by_origin[t])) for t in origins},
        "origins_where_commuting_wins_over_median_placebo": int(
            np.sum(origin_win_rate > 0.5)),
        "n_origins": len(origins),
        "scored_origin_years": origin_years,
        "covid_origin_share": float(np.mean(
            [year in COVID_YEARS for year in origin_years])),
        "covid_window_gain_share": covid_gain_share,
        "per_origin_gain": [float(value) for value in per_origin_gain],
        "b0_equals_b4": bool(abs(observed["B0_local"] - observed["B4_national_only"])
                             < 1e-9),
        "mean_neighbour_beta": float(np.mean(
            [fit_score(designs["B1_commuting"], list(range(t)), t,
                       dispersion=dispersion_by_origin[t])["neighbour_beta"]
             for t in origins])),
    }


def permutation_statistics(null_totals: np.ndarray,
                           observed_total: float) -> tuple[float, np.ndarray]:
    """Place observed and permuted deviances on one common standardised scale."""
    totals = np.asarray(null_totals, float)
    if totals.ndim != 1 or totals.size < 2:
        raise ValueError("at least two permutation totals are required")
    centre = float(np.mean(totals))
    scale = float(np.std(totals, ddof=1))
    if not np.isfinite(scale) or scale <= 1e-12:
        raise ValueError("permutation statistic has zero or invalid scale")
    observed = (centre - float(observed_total)) / scale
    null = (centre - totals) / scale
    return float(observed), np.asarray(null, float)


def joint_maxT(results: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Family-wise adjusted p-values across signals, by the maxT permutation method.

    Draw ``b`` uses the same territorial relabelling for every signal. Each signal first
    standardises observed and permuted deviances with one common centre and scale. Taking
    the maximum at each draw therefore controls the family while avoiding domination by a
    high-variance signal. Forty draws remain exploratory; confirmatory use needs more.
    """
    scored = {name: entry for name, entry in results.items()
              if entry.get("status") == "scored"}
    if not scored:
        return {}
    draws = min(len(entry["null_statistics"]) for entry in scored.values())
    joint = np.max([[entry["null_statistics"][b] for b in range(draws)]
                    for entry in scored.values()], axis=0)
    return {name: float((np.sum(joint >= entry["observed_statistic"]) + 1) / (draws + 1))
            for name, entry in scored.items()}


def promote_width_arms(metrics: dict[str, dict[str, Any]],
                       dense_threshold: float = 0.30,
                       edge_threshold: float = 0.50) -> dict[str, Any]:
    """Select 32/128 follow-ups by absolute gates, never a forced top-three rank."""
    promoted: list[str] = []
    reasons: dict[str, list[str]] = {}
    for arm, result in metrics.items():
        arm_reasons = []
        if float(result.get("dense_correlation", -np.inf)) >= dense_threshold:
            arm_reasons.append("dense_correlation")
        if float(result.get("edge_f1", -np.inf)) >= edge_threshold:
            arm_reasons.append("edge_f1")
        complementary = bool(
            result.get("beats_best_individual", False)
            and result.get("leave_one_signal_out_positive", False)
            and result.get("null_rate_controlled", False)
            and not result.get("duplicated_signal_reproduces_gain", True))
        if complementary:
            arm_reasons.append("validated_complementarity")
        if arm_reasons:
            promoted.append(arm)
            reasons[arm] = arm_reasons
    controls = [name for name in ("R1", "R2") if promoted and name in metrics]
    return {
        "promoted": sorted(promoted),
        "controls_to_accompany_promoted": controls,
        "reasons": reasons,
        "promotion_authorised": bool(promoted),
        "rule": "absolute_gates_only_no_forced_ranking",
    }


def verdict(result: dict[str, Any], alpha: float = 0.05,
            min_origin_share: float = 0.60,
            adjusted_p: float | None = None) -> dict[str, Any]:
    """Direction, calibration and significance, all declared before running.

    ``relational_arm_beats_the_null_model`` is the gate that HERALD 90 lacked and that the
    first HERALD 91 run exposed: a signal whose relational arm is still several times worse
    than a persistence-only null has not been shown to carry relational information, however
    large its advantage over its own broken baseline. SIDE creations reach ``B0/null =
    3.649``; beating that baseline by seven per cent is beating a model that should not have
    been used.
    """
    if result.get("status") != "scored":
        return {"verdict": "NOT_SCORED", "passes": False}
    relative = result["relative_to_null"]
    checks = {
        "relational_arm_beats_the_null_model": relative["B1_commuting"] < 1.0,
        "beats_permuted_null": result["p_value_vs_permuted"] <= alpha,
        "beats_degree_matched_null": result["p_value_vs_degree_matched_random"] <= alpha,
        "beats_local_baseline": result["gain_vs_local"] > 0,
        "majority_of_origins":
            result["origins_where_commuting_wins_over_median_placebo"]
            >= min_origin_share * result["n_origins"],
        "b4_is_a_distinct_model": not result["b0_equals_b4"],
    }
    if adjusted_p is not None:
        checks["survives_joint_maxT_correction"] = adjusted_p <= alpha

    # COVID sensitivity is a property of *where* the advantage sits, so it is measured
    # rather than assumed: a signal whose scored origins are dominated by 2020-2021 cannot
    # be distinguished from the rebound, whatever its p-value.
    # The COVID window is taken as 2020-2022: the shock and the rebound that followed it.
    # Two separate routes to being COVID-sensitive, and either is enough.
    #
    # By concentration: most of the advantage sits inside the window.
    # By design: too few scored origins to separate the window from the rest at all. SIDE
    # creations score five origins, 2021-2025, with no pre-COVID origin in the panel; there
    # is no arrangement of those five years that isolates the rebound, whatever the measured
    # concentration happens to be.
    covid_share = result.get("covid_window_gain_share", 0.0)
    origin_years = result.get("scored_origin_years", [])
    window = {2020, 2021, 2022}
    covid_exposed_by_design = (len(origin_years) < 8
                               and bool(window & set(origin_years))
                               and not any(year < 2020 for year in origin_years))
    covid_sensitive = covid_share >= 0.50 or covid_exposed_by_design

    per_signal_significant = (checks["beats_permuted_null"]
                              and checks["beats_degree_matched_null"])
    if all(checks.values()):
        label = "RELATION_INFORMATIVE"
    elif not checks["relational_arm_beats_the_null_model"]:
        # Worse than doing nothing. Any advantage shown is internal to a baseline that is
        # itself unusable, so no relational reading is available at all.
        label = ("COVID_SENSITIVE_EXPLORATORY" if covid_sensitive
                 else "BASELINE_WORSE_THAN_NULL")
    elif per_signal_significant and checks["beats_local_baseline"]:
        # Usable baseline and a signal that clears its own null, but failing either the
        # consistency check or the family-wise correction. Both failures are visible in
        # `checks`; neither is silently dropped.
        label = "WEAK_CANDIDATE"
    else:
        label = "NOT_INFORMATIVE"
    return {"verdict": label, "checks": checks, "passes": bool(all(checks.values())),
            "adjusted_p_value": adjusted_p,
            "covid_window_gain_share": covid_share,
            "covid_exposed_by_design": bool(covid_exposed_by_design),
            "covid_sensitive": bool(covid_sensitive)}
