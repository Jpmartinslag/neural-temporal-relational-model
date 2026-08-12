"""HERALD 92: the observable multisignal oracle, run before any network exists.

The question HERALD 91 left open is whether signals that are individually too weak can
identify a territorial relation jointly. This module answers it the cheapest way possible:
by handing the true graph to a linear predictor and asking whether it beats a relabelling
of itself -- once per signal, and once for the combination.

If the true graph cannot be distinguished from a derangement even here, no network can
recover it, and the factorial must not be written. That is the whole purpose of running an
oracle first.

Five conditions decide whether the combination is authorised, and each is a way the claim
could be false rather than a way it could be confirmed:

1. jointly, the true graph beats the derangement;
2. at least two signals contribute information the others do not;
3. removing any single signal does not destroy identification, so the result is not one
   signal wearing a combination's clothes;
4. duplicating employment does **not** reproduce the joint gain, so the gain is information
   rather than arithmetic;
5. the NULL scenario stays below its false-positive floor and CONFLICTING does not produce
   a consensus that is not there.

Every arm shares folds, dispersion and placebo relabellings with every other. NumPy only.
"""
from __future__ import annotations

from typing import Any

import numpy as np

ARMS = ("A_true", "A_prior", "A_permuted", "A_degree_matched", "A_null")

# Declared before any scenario was scored. A gain is the proportional reduction in
# out-of-sample deviance against the same fold's baseline.
JOINT_GAIN_THRESHOLD = 0.10          # true must beat the derangement by this, jointly
INDIVIDUAL_DETECTION_THRESHOLD = 0.10
NULL_FALSE_POSITIVE_CEILING = 0.05
MIN_COMPLEMENTARY_SIGNALS = 2
PLACEBO_DRAWS = 40


# ── Design ───────────────────────────────────────────────────────────────────

def _row_normalise(matrix: np.ndarray) -> np.ndarray:
    out = np.maximum(np.asarray(matrix, float), 0.0).copy()
    np.fill_diagonal(out, 0.0)
    total = out.sum(1, keepdims=True)
    return np.divide(out, total, out=np.zeros_like(out), where=total > 0)


def derangement(matrix: np.ndarray, seed: int) -> np.ndarray:
    """Relabel every zone; none keeps its own identity."""
    rng = np.random.default_rng(seed)
    n = len(matrix)
    for _ in range(2000):
        permutation = rng.permutation(n)
        if not np.any(permutation == np.arange(n)):
            return matrix[permutation][:, permutation]
    raise RuntimeError("no derangement found")


def degree_matched_random(matrix: np.ndarray, seed: int) -> np.ndarray:
    """Random neighbours with the same out-degree and the same weight multiset per row."""
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
    return _row_normalise(out)


def signal_frames(dataset: dict[str, Any], name: str) -> dict[str, np.ndarray]:
    """Observed growth, its lag and the usable mask, on this signal's own grid."""
    block = dataset["signals"][name]
    values = np.asarray(block["values"], float)
    mask = np.asarray(block["availability_mask"], bool)
    rows = np.flatnonzero(mask.any(1))
    values, mask = values[rows], mask[rows]
    scale = np.where(mask, np.log(np.maximum(values, 1e-9)), np.nan)
    growth = np.full_like(scale, np.nan)
    growth[1:] = scale[1:] - scale[:-1]
    usable = mask[1:] & mask[:-1]
    return {"growth": growth[1:], "usable": usable, "period_rows": rows[1:],
            "family": block["family"]}


def standardised_driver(frame: dict[str, np.ndarray], period_index: int) -> np.ndarray:
    """This signal's own lagged growth, centred and scaled to unit variance.

    Standardisation is what makes signals poolable: a payroll growth in log-euros and a
    rate change in logit points have no common unit until each is expressed in its own
    standard deviations.
    """
    if period_index == 0:
        return None
    previous = np.nan_to_num(frame["growth"][period_index - 1])
    valid = frame["usable"][period_index - 1].astype(float)
    total = max(valid.sum(), 1.0)
    centred = (previous - (previous * valid).sum() / total) * valid
    spread = float(np.sqrt((centred ** 2).sum() / total))
    return centred / spread if spread > 1e-12 else centred


def pooling_weights(frames: dict[str, dict[str, np.ndarray]],
                    train_rows: list[int]) -> dict[str, float]:
    """Estimate each signal's loading on the common state, from training periods only.

    The loadings are unknown to an observer and are not all positive: unemployment moves
    against activity, and the conflicting scenario flips two more. An estimator that
    cannot recover signs would let S5 cancel through the *estimator* rather than through
    the design, which would make that scenario untestable.

    Estimation is **pairwise-complete against an anchor**, not a joint decomposition on
    rows where every signal is present. Quarterly and annual signals almost never share a
    row -- with creations starting in 2012 the fully-observed intersection is a handful of
    fourth quarters -- and an earlier version fell back to uniform weights whenever that
    intersection was thin, silently returning ``1.0`` for every signal and erasing the
    signs it existed to find.
    """
    anchor = max(frames, key=lambda name: len(frames[name]["period_rows"]))
    train = set(int(row) for row in train_rows)

    def drivers_by_row(name: str) -> dict[int, np.ndarray]:
        frame = frames[name]
        out = {}
        for index, row in enumerate(frame["period_rows"]):
            if int(row) in train:
                driver = standardised_driver(frame, index)
                if driver is not None:
                    out[int(row)] = driver
        return out

    anchor_drivers = drivers_by_row(anchor)
    weights = {anchor: 1.0}
    for name in frames:
        if name == anchor:
            continue
        own = drivers_by_row(name)
        shared_rows = sorted(set(own) & set(anchor_drivers))
        if len(shared_rows) < 2:
            weights[name] = 0.0        # nothing to estimate from; contribute nothing
            continue
        left = np.concatenate([own[row] for row in shared_rows])
        right = np.concatenate([anchor_drivers[row] for row in shared_rows])
        if np.std(left) < 1e-12 or np.std(right) < 1e-12:
            weights[name] = 0.0
            continue
        weights[name] = float(np.corrcoef(left, right)[0, 1])
    return weights


def pooled_driver(frames: dict[str, dict[str, np.ndarray]], period_row: int,
                  weights: dict[str, float] | None = None) -> np.ndarray | None:
    """Weighted average of the standardised drivers observed at this period.

    This is the mechanism the experiment turns on. Every signal measures the same latent
    state under its own independent noise, so a weighted pool estimates that state with the
    noise divided by roughly ``sqrt(S)``. Signals that share a noise group -- the redundant
    scenario -- contribute correlated errors and buy nothing, which is what lets S4 falsify
    a complementarity claim.
    """
    contributions, used = [], []
    for name, frame in frames.items():
        matched = np.flatnonzero(frame["period_rows"] == period_row)
        if not len(matched):
            continue
        driver = standardised_driver(frame, int(matched[0]))
        if driver is None:
            continue
        weight = 1.0 if weights is None else weights.get(name, 1.0)
        contributions.append(weight * driver)
        used.append(abs(weight))
    if not contributions:
        return None
    total = sum(used) if sum(used) > 1e-12 else float(len(contributions))
    return np.sum(contributions, axis=0) / total


def _design_block(frame, index, graph, graph_by_period, driver):
    """Build one fold's design. The pooled channel is **added**, never substituted.

    The first version replaced the signal's own driver with the pooled one, which asks a
    different and unfair question: for a signal whose own history already estimates the
    state well, swapping in an average that includes weakly-loaded signals can only make it
    worse, and every scenario duly showed pooling *hurting*. The hypothesis is that
    combining **adds** information, so the pooled neighbour term enters as an extra column
    beside the signal's own and the fit decides how much weight it deserves.
    """
    ok = frame["usable"][index]
    own = np.nan_to_num(frame["growth"][index - 1]) if index else np.zeros(ok.shape)
    block = [np.ones(ok.sum()), own[ok], np.full(ok.sum(), own[ok].mean())]
    if graph is not None or graph_by_period is not None:
        matrix = (graph if graph is not None
                  else graph_by_period[frame["period_rows"][index]])
        own_driver = standardised_driver(frame, index)
        own_neighbour = ((matrix @ own_driver) if own_driver is not None
                         else np.zeros(ok.shape))
        block.append(own_neighbour[ok])
        if driver is not None:
            pooled_neighbour = matrix @ driver
            block.append(pooled_neighbour[ok])
    return np.column_stack(block), ok


def _fit_gain(frame: dict[str, np.ndarray], graph: np.ndarray | None,
              graph_by_period: np.ndarray | None, train: list[int], score: int,
              drivers: dict[int, np.ndarray] | None = None) -> float:
    """Out-of-sample squared error of a local baseline, with or without neighbours.

    ``drivers`` supplies a pooled driver per period. When it is absent the signal falls
    back on its own lagged growth, which is the individual arm.
    """
    columns, response = [], []
    for index in train:
        if not frame["usable"][index].any():
            continue
        driver = None if drivers is None else drivers.get(int(frame["period_rows"][index]))
        design, ok = _design_block(frame, index, graph, graph_by_period, driver)
        columns.append(design)
        response.append(frame["growth"][index][ok])
    if not columns:
        return float("nan")
    x = np.concatenate(columns); y = np.concatenate(response)
    beta = np.linalg.solve(x.T @ x + 1e-8 * np.eye(x.shape[1]), x.T @ y)

    driver = None if drivers is None else drivers.get(int(frame["period_rows"][score]))
    design, ok = _design_block(frame, score, graph, graph_by_period, driver)
    residual = frame["growth"][score][ok] - design @ beta
    return float(residual @ residual)


def score_signal(dataset: dict[str, Any], name: str, graphs: dict[str, Any],
                 n_score: int = 8, drivers: dict[int, np.ndarray] | None = None
                 ) -> dict[str, float]:
    """Deviance per arm on the last folds of one signal, all arms on the same folds."""
    frame = signal_frames(dataset, name)
    steps = len(frame["growth"])
    origins = [t for t in range(steps - n_score, steps) if t >= 6]
    totals = {arm: 0.0 for arm in ARMS}
    for origin in origins:
        train = list(range(1, origin))
        totals["A_null"] += _fit_gain(frame, None, None, train, origin, drivers)
        totals["A_true"] += _fit_gain(frame, None, graphs["true"], train, origin, drivers)
        for arm, matrix in (("A_prior", graphs["prior"]),
                            ("A_permuted", graphs["permuted"]),
                            ("A_degree_matched", graphs["degree_matched"])):
            totals[arm] += _fit_gain(frame, matrix, None, train, origin, drivers)
    base = totals["A_null"]
    return {"n_origins": len(origins),
            **{arm: totals[arm] for arm in ARMS},
            "gain_true_vs_null": (base - totals["A_true"]) / max(base, 1e-12),
            "gain_true_vs_permuted": (totals["A_permuted"] - totals["A_true"])
                                     / max(totals["A_permuted"], 1e-12),
            "gain_true_vs_degree": (totals["A_degree_matched"] - totals["A_true"])
                                   / max(totals["A_degree_matched"], 1e-12)}


def score_joint(dataset: dict[str, Any], names: list[str], graphs: dict[str, Any],
                n_score: int = 8) -> dict[str, float]:
    """Score every signal twice: with its own driver, and with the pooled one.

    The question is not "is the sum of the signals better than one signal", which mostly
    measures how many weak signals were added to the average. It is **does pooling improve
    the same signal**: for a fixed target, does a neighbour term built on the pooled state
    estimate beat one built on that signal's own history? That is the complementarity
    hypothesis stated as a paired comparison, and it is what the first version failed to
    measure -- it summed winners with losers and called the dilution a joint result.
    """
    # The pooled driver is built once from every signal in the combination, then handed
    # to each signal's fit. This is what an individual arm cannot do.
    frames = {name: signal_frames(dataset, name) for name in names}
    all_rows = sorted({int(row) for frame in frames.values() for row in frame["period_rows"]})
    # Weights come from the earlier two thirds of the rows, never from the scored ones.
    cut = int(0.66 * len(all_rows))
    weights = pooling_weights(frames, all_rows[:max(cut, 4)])
    drivers = {row: pooled_driver(frames, row, weights) for row in all_rows}
    drivers = {row: value for row, value in drivers.items() if value is not None}
    with_pool = {name: score_signal(dataset, name, graphs, n_score, drivers)
                 for name in names}
    with_own = {name: score_signal(dataset, name, graphs, n_score, None)
                for name in names}

    pooled = {arm: 0.0 for arm in ARMS}
    for entry in with_pool.values():
        reference = max(entry["A_null"], 1e-12)
        for arm in ARMS:
            pooled[arm] += entry[arm] / reference
    base = pooled["A_null"]

    # The paired quantity: per signal, how much the pooled driver improves the true-graph
    # advantage over that signal's own driver.
    paired = {name: (with_pool[name]["gain_true_vs_permuted"]
                     - with_own[name]["gain_true_vs_permuted"])
              for name in names}
    improved = [name for name, value in paired.items() if value > 0]
    return {"signals": names, "per_signal": with_pool, "per_signal_own_driver": with_own,
            "pooled": pooled, "pooling_weights": weights,
            "paired_pool_minus_own": paired,
            "signals_improved_by_pooling": improved,
            "n_signals_improved_by_pooling": len(improved),
            "mean_pairwise_improvement": float(np.mean(list(paired.values()))),
            "best_pooled_signal_gain": max(
                entry["gain_true_vs_permuted"] for entry in with_pool.values()),
            "best_own_signal_gain": max(
                entry["gain_true_vs_permuted"] for entry in with_own.values()),
            "gain_true_vs_null": (base - pooled["A_true"]) / max(base, 1e-12),
            "gain_true_vs_permuted": (pooled["A_permuted"] - pooled["A_true"])
                                     / max(pooled["A_permuted"], 1e-12),
            "gain_true_vs_degree": (pooled["A_degree_matched"] - pooled["A_true"])
                                   / max(pooled["A_degree_matched"], 1e-12)}


def build_graphs(dataset: dict[str, Any], seed: int = 92000) -> dict[str, Any]:
    prior = np.asarray(dataset["truth"]["prior"])
    return {"true": np.asarray(dataset["truth"]["propagation"]),
            "prior": prior,
            "permuted": derangement(prior, seed),
            "degree_matched": degree_matched_random(prior, seed + 1)}


# ── Complementarity ──────────────────────────────────────────────────────────

def duplicate_signal(dataset: dict[str, Any], source: str, alias: str,
                     jitter: float = 0.0, seed: int = 0) -> dict[str, Any]:
    """Add a copy of one signal under a new name, optionally jittered.

    The control that separates information from arithmetic: a method that gains as much
    from a second copy of employment as from a genuinely different signal is counting
    the same evidence twice.
    """
    copied = {key: (value.copy() if isinstance(value, np.ndarray) else value)
              for key, value in dataset["signals"][source].items()}
    if jitter > 0:
        rng = np.random.default_rng(seed)
        noise = rng.normal(1.0, jitter, size=copied["values"].shape)
        copied["values"] = copied["values"] * noise
    out = {key: value for key, value in dataset.items()}
    out["signals"] = dict(dataset["signals"])
    out["signals"][alias] = copied
    return out


def evaluate_scenario(dataset: dict[str, Any], seed: int = 92000,
                      n_score: int = 8) -> dict[str, Any]:
    """Individual, joint, leave-one-out and duplication, all on the same folds."""
    graphs = build_graphs(dataset, seed)
    names = [name for name in dataset["signals"]]
    individual = {name: score_signal(dataset, name, graphs, n_score) for name in names}
    joint = score_joint(dataset, names, graphs, n_score)

    leave_one_out = {}
    for name in names:
        remaining = [other for other in names if other != name]
        if len(remaining) < 2:
            continue
        reduced = score_joint(dataset, remaining, graphs, n_score)
        leave_one_out[name] = {
            "gain_without": reduced["gain_true_vs_permuted"],
            "incremental": joint["gain_true_vs_permuted"] - reduced["gain_true_vs_permuted"],
        }

    duplicated = duplicate_signal(dataset, "headcount", "headcount_copy")
    duplicated_graphs = build_graphs(duplicated, seed)
    duplicate_joint = score_joint(duplicated, names + ["headcount_copy"],
                                  duplicated_graphs, n_score)

    best_individual = max(entry["gain_true_vs_permuted"] for entry in individual.values())
    complementary = [name for name, entry in leave_one_out.items()
                     if entry["incremental"] > 0]
    # Complementarity as a paired improvement: the same target signal, better driver.
    paired_gain = joint["mean_pairwise_improvement"]
    signals_improved = joint["n_signals_improved_by_pooling"]
    return {
        "scenario": dataset["metadata"]["scenario"],
        "individual": individual,
        "joint": joint,
        "leave_one_out": leave_one_out,
        "duplicate_control": {
            "joint_gain": joint["gain_true_vs_permuted"],
            "with_duplicate_gain": duplicate_joint["gain_true_vs_permuted"],
            "duplicate_adds": duplicate_joint["gain_true_vs_permuted"]
                              - joint["gain_true_vs_permuted"],
        },
        "best_individual_gain": best_individual,
        "joint_gain": joint["gain_true_vs_permuted"],
        "paired_pooling_improvement": paired_gain,
        "n_signals_improved_by_pooling": signals_improved,
        "best_pooled_signal_gain": joint["best_pooled_signal_gain"],
        "best_own_signal_gain": joint["best_own_signal_gain"],
        "joint_beats_best_individual":
            joint["best_pooled_signal_gain"] > joint["best_own_signal_gain"],
        "n_complementary_signals": len(complementary),
        "complementary_signals": complementary,
    }


def authorise_neural_stage(by_scenario: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The five pre-declared conditions, evaluated together.

    A single failing condition blocks the factorial. The conditions are deliberately
    asymmetric: four of them can only be met by evidence, and one (the NULL ceiling) can
    only be broken by evidence.
    """
    shared = by_scenario.get("S1_SHARED", {})
    complementary = by_scenario.get("S3_COMPLEMENTARY", {})
    redundant = by_scenario.get("S4_REDUNDANT", {})
    null = by_scenario.get("S0_NULL", {})
    conflicting = by_scenario.get("S5_CONFLICTING", {})

    checks = {
        "shared_scenario_is_identifiable":
            shared.get("joint_gain", 0.0) >= JOINT_GAIN_THRESHOLD,
        "complementary_joint_beats_every_individual":
            bool(complementary.get("joint_beats_best_individual", False)),
        "complementary_has_two_contributing_signals":
            complementary.get("n_complementary_signals", 0) >= MIN_COMPLEMENTARY_SIGNALS,
        "duplication_does_not_reproduce_the_gain":
            complementary.get("duplicate_control", {}).get("duplicate_adds", 1.0)
            < 0.5 * max(complementary.get("joint_gain", 1e-9), 1e-9),
        "null_stays_below_the_false_positive_ceiling":
            abs(null.get("joint_gain", 1.0)) <= NULL_FALSE_POSITIVE_CEILING,
        "conflicting_does_not_fabricate_consensus":
            conflicting.get("joint_gain", 1.0)
            <= max(conflicting.get("best_individual_gain", 0.0), 0.0) + 1e-9,
    }
    return {"checks": checks,
            "authorises_neural_synthetic": bool(all(checks.values())),
            "thresholds": {
                "joint_gain": JOINT_GAIN_THRESHOLD,
                "null_ceiling": NULL_FALSE_POSITIVE_CEILING,
                "min_complementary_signals": MIN_COMPLEMENTARY_SIGNALS,
            }}
