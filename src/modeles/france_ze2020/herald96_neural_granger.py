"""HERALD 96: a frozen local baseline, a residual target, and a Neural Granger / NAVAR arm.

The audit that opened this stage found that HERALD's relational arm was never required to
carry anything. A node head sat beside it and absorbed the task, the local temporal features
removed 11-24 % of the error on their own, and the scorer's only gradient came from a
forecasting likelihood that the local path could satisfy by itself. So the arm here is built
the other way round:

* the local baseline is fitted, then **frozen**, and its parameters take no gradient;
* the relational arm predicts the **residual** the frozen baseline leaves behind;
* the arm has **no node head and no local path**. The only route from input to prediction
  passes through another zone. If it predicts nothing, it has found nothing, and no local
  skill can disguise that;
* the edge score is the **measured out-of-sample contribution** of the source, not an
  internal attention weight. HERALD 93's score was an internal quantity that never had to
  correspond to anything, and it did not.

The arm is additive by construction, in the NAVAR sense:

    residual_hat[t, target] = sum over candidate sources s of  c[s -> target, t]
    c[s -> target, t]       = g(history_s[t], history_target[t])

``g`` is one shared function. There is no free per-pair parameter and no zone identity, so a
pair cannot be memorised; what the arm learns is a rule about trajectories. Because the
prediction is a plain sum of per-source terms, each term *is* that source's contribution, and
attributing the prediction needs no attribution method.

The group penalty acts on the contributions themselves, ``lambda * sum_p ||c_p||_2``, which
switches a useless source off rather than shrinking every source a little. Penalising outputs
rather than weights is what keeps the shared function shared.

Multi-horizon: 1, 2 and 4 steps. At one step the target's own recent history explains most of
what is explainable, so a one-step objective lets the arm look successful for local reasons.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.modeles.france_ze2020 import herald94_composite as arms
from src.modeles.france_ze2020 import herald94_temporal_features as feat

HORIZONS = (1, 2, 4)
HIDDEN = 8
FORBIDDEN_WIDTH = 256
# Twelve hundred epochs, and the number matters: at three hundred the arm had not yet
# reached a positive residual gain on the smoke seed, and at twelve hundred it did. Fixed
# here rather than selected per task.
EPOCHS = 1200
# A learning rate of 0.05 diverged on the smoke seed, returning a residual gain of -108.
LEARNING_RATE = 0.02
# Small, and applied to the *mean* pair norm so that it does not vary with support size.
# Calibrated on the smoke seed 9951 alone; the final seeds were never used for it.
GROUP_PENALTY = 1e-3
SIMILARITY_K = 10
COMMUTING_K = 40
PRIMARY_SIGNAL = "headcount"


# ── frozen baseline and the residual target ──────────────────────────────────

def fit_frozen_baseline(table: dict, target: np.ndarray, train_periods: list[int]) -> dict:
    """The HERALD 94 local baseline, fitted once and then frozen.

    Returns the fitted coefficients and the scaler. Nothing downstream may modify either; a
    guard checks the parameter vector is bit-identical before and after relational training.
    """
    columns = tuple(table["base_index"])
    rows = arms.assemble_rows(table, target, train_periods, columns)
    scaler = arms.standardise(rows["x"])
    design = arms.apply_scaler(rows["x"], scaler)
    alpha = arms.choose_alpha(design, rows["y"], rows["keys"][:, 0])
    fitted = arms.fit_ridge(design, rows["y"], alpha)
    return {"beta": fitted["beta"], "intercept": fitted["intercept"], "alpha": alpha,
            "scaler": scaler, "columns": columns,
            "checksum": float(np.abs(fitted["beta"]).sum())}


def baseline_prediction(baseline: dict, table: dict, target: np.ndarray,
                        periods: list[int]) -> dict[str, np.ndarray]:
    rows = arms.assemble_rows(table, target, periods, baseline["columns"])
    design = arms.apply_scaler(rows["x"], baseline["scaler"])
    prediction = design @ baseline["beta"] + baseline["intercept"]
    return {"prediction": prediction, "y": rows["y"], "keys": rows["keys"]}


def residual_target(baseline: dict, table: dict, target: np.ndarray,
                    periods: list[int]) -> dict[str, np.ndarray]:
    """``residual[t] = observed[t] - baseline_local[t]``, on the rows the baseline scored."""
    scored = baseline_prediction(baseline, table, target, periods)
    return {"residual": scored["y"] - scored["prediction"], "keys": scored["keys"],
            "observed": scored["y"], "baseline": scored["prediction"]}


def residual_field(baseline: dict, table: dict, target: np.ndarray,
                   n_periods: int, n_zones: int, periods: list[int]) -> np.ndarray:
    """The residual laid back out as ``(T, N)``, NaN where the target was not observed."""
    out = np.full((n_periods, n_zones), np.nan)
    block = residual_target(baseline, table, target, periods)
    for value, (period, zone) in zip(block["residual"], block["keys"]):
        out[int(period), int(zone)] = value
    return out


# ── candidate supports ───────────────────────────────────────────────────────

def commuting_support(commuting: np.ndarray, k: int = COMMUTING_K) -> np.ndarray:
    n = len(commuting)
    support = np.zeros((n, n), bool)
    for target in range(n):
        incoming = commuting[:, target].copy()
        incoming[target] = -np.inf
        order = np.argsort(-incoming)[:k]
        support[order, target] = incoming[order] > 0
    return support


def causal_similarity(view: dict[str, Any], decision_period: int,
                      signal: str = PRIMARY_SIGNAL) -> np.ndarray:
    """Similarity between zones, from released observations only, up to ``decision_period``.

    Correlation of year-over-year growth over the released history. This is what an observer
    can compute; it is *not* the latent profile similarity the truth was drawn from, and a
    guard measures the gap rather than assuming it.
    """
    block = view["signals"][signal]
    growth = feat.signal_features(signal, np.asarray(block["values"], float),
                                  np.asarray(block["availability_mask"], bool),
                                  block.get("family", ""))["growth"]
    usable = growth[:decision_period + 1]
    filled = np.where(np.isfinite(usable), usable, np.nan)
    centred = filled - np.nanmean(filled, axis=0, keepdims=True)
    centred = np.nan_to_num(centred, nan=0.0)
    norm = np.linalg.norm(centred, axis=0, keepdims=True)
    similarity = (centred / np.maximum(norm, 1e-12)).T @ (centred / np.maximum(norm, 1e-12))
    np.fill_diagonal(similarity, -np.inf)
    return similarity


def similarity_support(similarity: np.ndarray, k: int = SIMILARITY_K) -> np.ndarray:
    n = len(similarity)
    support = np.zeros((n, n), bool)
    for target in range(n):
        order = np.argsort(-similarity[:, target])[:k]
        support[order, target] = True
    np.fill_diagonal(support, False)
    return support


def all_pairs_support(n: int) -> np.ndarray:
    support = np.ones((n, n), bool)
    np.fill_diagonal(support, False)
    return support


def build_supports(commuting: np.ndarray, similarity: np.ndarray,
                   n: int, include_all_pairs: bool) -> dict[str, np.ndarray]:
    """The four supports compared. Types are carried for reporting, never as a value."""
    commuting_only = commuting_support(commuting)
    similarity_only = similarity_support(similarity)
    supports = {
        "commuting_only": commuting_only,
        "similarity_only": similarity_only,
        # The union is typed: each edge remembers which generator proposed it, and that label
        # is used for reporting alone. Passing it to the scorer would reintroduce exactly the
        # defect this stage exists to avoid.
        "typed_union": commuting_only | similarity_only,
    }
    if include_all_pairs:
        supports["all_pairs"] = all_pairs_support(n)
    return supports


def edge_types(supports: dict[str, np.ndarray], pairs: np.ndarray) -> dict[str, np.ndarray]:
    return {"from_commuting": supports["commuting_only"][pairs[0], pairs[1]],
            "from_similarity": supports["similarity_only"][pairs[0], pairs[1]]}


# ── the arm ──────────────────────────────────────────────────────────────────

def pair_features(table: dict, pairs: np.ndarray, periods: list[int],
                  signal: str = PRIMARY_SIGNAL) -> dict[str, np.ndarray]:
    """``(n_periods * n_pairs, 2F)``: the source's own features beside the target's.

    Only the primary signal's block is used, which keeps the design affordable at all-pairs
    size and is declared rather than discovered: the arm is being tested for whether it can
    find a relation at all, not for how many signals it can absorb.
    """
    columns = [index for index, name in enumerate(table["columns"])
               if name.startswith(f"{signal}.")]
    features = table["features"][:, :, columns]
    blocks = []
    for period in periods:
        source = features[period - 1][pairs[0]]
        target = features[period - 1][pairs[1]]
        blocks.append(np.concatenate([source, target], axis=1))
    return {"x": np.stack(blocks), "n_pairs": len(pairs[0]), "periods": list(periods)}


def initialise(n_features: int, hidden: int, n_horizons: int, seed: int,
               fan_in: float = 1.0) -> dict:
    """``fan_in`` is the mean number of sources arriving at a target zone.

    The prediction is a *sum* of ``fan_in`` contributions, so each contribution must start at
    ``O(1 / fan_in)`` for the sum to start at ``O(1)``. Without this the arm begins with a
    prediction forty times the residual it is meant to explain, and the first pilot returned
    a residual gain of -179. This is an initialisation scale forced by the additive form, not
    an architectural choice: the width, the depth and the activation are unchanged.
    """
    if hidden >= FORBIDDEN_WIDTH:
        raise ValueError(f"width {hidden} is not permitted in this study")
    rng = np.random.default_rng(seed)
    output_scale = 1.0 / (np.sqrt(hidden) * max(fan_in, 1.0))
    return {"w1": rng.normal(0.0, 1.0 / np.sqrt(n_features), size=(n_features, hidden)),
            "b1": np.zeros(hidden),
            "w2": rng.normal(0.0, output_scale, size=(hidden, n_horizons)),
            "b2": np.zeros(n_horizons)}


def contributions(params: dict, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``c[period, pair, horizon]`` and the hidden activation, for one shared function."""
    activation = np.tanh(x @ params["w1"] + params["b1"])
    return activation @ params["w2"] + params["b2"], activation


def predict_residual(params: dict, x: np.ndarray, pairs: np.ndarray,
                     n_zones: int) -> tuple[np.ndarray, np.ndarray]:
    """Sum each target's incoming contributions. No local term is added anywhere."""
    contribution, _ = contributions(params, x)
    n_periods, _, n_horizons = contribution.shape
    prediction = np.zeros((n_periods, n_zones, n_horizons))
    np.add.at(prediction, (slice(None), pairs[1]), contribution)
    return prediction, contribution


def fit(params: dict, x: np.ndarray, pairs: np.ndarray, targets: np.ndarray,
        masks: np.ndarray, n_zones: int, epochs: int = EPOCHS,
        learning_rate: float = LEARNING_RATE,
        group_penalty: float = GROUP_PENALTY) -> dict:
    """Adam on the summed residual error plus a group penalty on the contributions.

    ``targets`` and ``masks`` are ``(n_periods, n_zones, n_horizons)``: the residual at each
    horizon, and whether it was observed.
    """
    moment = {key: np.zeros_like(value) for key, value in params.items()}
    velocity = {key: np.zeros_like(value) for key, value in params.items()}
    history = []
    denominator = max(float(masks.sum()), 1.0)
    for step in range(1, epochs + 1):
        contribution, activation = contributions(params, x)
        prediction = np.zeros_like(targets)
        np.add.at(prediction, (slice(None), pairs[1]), contribution)
        error = (prediction - targets) * masks
        loss = float((error ** 2).sum() / denominator)

        # Group penalty on the contribution of each pair across time and horizon,
        # **averaged** over pairs rather than summed.
        #
        # Summed, its weight grows with the size of the support, so the same nominal penalty
        # is a different pressure on a support of 3216 candidates than on one of 6320 -- and
        # this stage exists to compare supports of exactly those sizes. Comparing them under
        # different effective penalties would compare the penalties. Summed at 3e-3 it also
        # dominated the loss outright: the pilot returned a training gain of -1.71, worse
        # than predicting zero, while the same fit without it reached +0.024.
        norms = np.sqrt((contribution ** 2).sum(axis=(0, 2)) + 1e-12)
        loss = loss + group_penalty * float(norms.mean())
        history.append(loss)

        upstream = 2.0 * error / denominator
        grad_contribution = upstream[:, pairs[1], :]
        grad_contribution = grad_contribution + (group_penalty / len(norms)) * (
            contribution / norms[None, :, None])

        flat_c = grad_contribution.reshape(-1, grad_contribution.shape[-1])
        flat_a = activation.reshape(-1, activation.shape[-1])
        flat_x = x.reshape(-1, x.shape[-1])
        grad = {"w2": flat_a.T @ flat_c, "b2": flat_c.sum(0)}
        inner = (flat_c @ params["w2"].T) * (1.0 - flat_a ** 2)
        grad["w1"] = flat_x.T @ inner
        grad["b1"] = inner.sum(0)

        for key in params:
            moment[key] = 0.9 * moment[key] + 0.1 * grad[key]
            velocity[key] = 0.999 * velocity[key] + 0.001 * grad[key] ** 2
            params[key] = params[key] - learning_rate * (
                moment[key] / (1 - 0.9 ** step)) / (
                np.sqrt(velocity[key] / (1 - 0.999 ** step)) + 1e-8)
    n_parameters = sum(int(np.asarray(value).size) for value in params.values())
    return {"params": params, "loss_history": history, "parameters": n_parameters}


def edge_scores(params: dict, x: np.ndarray, n_pairs: int) -> np.ndarray:
    """The measured contribution of each source, out of sample.

    The root-mean-square of the pair's contribution over the evaluation origins. This is what
    the source actually did to the prediction, not what an internal weight says it should
    have done -- the correction of the defect the audit found in HERALD 93.
    """
    contribution, _ = contributions(params, x)
    return np.sqrt((contribution ** 2).mean(axis=(0, 2)))


def response_curve(params: dict, x: np.ndarray, column: int,
                   n_points: int = 21) -> dict[str, np.ndarray]:
    """How a contribution responds to one input, the rest held at their medians."""
    flat = x.reshape(-1, x.shape[-1])
    base = np.median(flat, axis=0)
    sweep = np.linspace(*np.quantile(flat[:, column], [0.02, 0.98]), n_points)
    grid = np.repeat(base[None, :], n_points, axis=0)
    grid[:, column] = sweep
    value, _ = contributions(params, grid[None, :, :])
    return {"x": sweep, "y": value[0]}
