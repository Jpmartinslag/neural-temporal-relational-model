"""HERALD 94, Layer 1: the arms that decide whether a composite signal carries information.

Five arms on identical data, folds, seeds, origins and masks:

``best_single``      one feature, chosen inside the training window and then frozen.
``ridge_linear``     ridge over the whole feature table: the linear span.
``ridge_composite``  ridge over the table together with the two *product* composites.
``mlp_nonlinear``    one hidden layer, width eight, tanh.
``duplicated``       ridge over the table with the best single feature repeated.

``best_single`` is selected on the training window alone. Selecting it on the evaluation
origins would give the floor an advantage no other arm has, and a failure to beat it would
then be uninterpretable.

**Why a one-hidden-layer tanh network.** It nests ``ridge_linear`` exactly -- replace the
activation by the identity and ``f(x) = (sum_h a_h w_h)' x + c`` is a linear map -- so the
comparison between the two is a *nested-model* one: any surplus is curvature and any deficit
is optimisation. Its marginal effects are analytic, and so are its interactions:

    f(x)              = sum_h a_h tanh(w_h' x + b_h) + c
    d f / d x_j       = sum_h a_h (1 - tanh^2(u_h)) w_hj
    d2 f / d x_j d x_k = sum_h a_h (-2 tanh(u_h) (1 - tanh^2(u_h))) w_hj w_hk

The second identity is the reason for the choice. "Which components create the gain" is
answered by a closed-form quantity read off the fitted parameters, not by an attribution
heuristic layered on top of an opaque model. Kernel ridge was rejected because the kernel is
of order ``10^9`` entries at this grid size and yields no per-feature marginal effect;
gradient boosting because its response surface is piecewise constant, so ``d f / d x_j``
vanishes almost everywhere and the requested partial-effect curves would be artefacts of the
split points.

The network is written here in NumPy rather than delegated to a framework. Full batch, a
fixed initialisation from the task seed, and Adam with declared constants make the fit
bitwise reproducible, which the previous stage had to recover the hard way after
``index_add`` gave two different answers for the same run.
"""
from __future__ import annotations

from typing import Any

import numpy as np

HIDDEN = 8
EPOCHS = 1500
LEARNING_RATE = 0.02
WEIGHT_DECAY = 1e-4
MONITOR_EVERY = 25
# Expanding-window folds inside the training window, used identically by both arms.
N_BLOCKS = 5
# Extended to 1e5 before the grid ran. A penalty grid must not stop at the point where the
# arm would still like to go further: if the selection lands on the largest value on offer,
# the arm was cut short and the comparison would be about the grid rather than about the
# model. The smoke showed the linear arm losing to a single feature, so the possibility had
# to be excluded rather than assumed away. Whether the boundary is reached is reported.
RIDGE_ALPHAS = (1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0, 1e3, 1e4, 1e5)
# Chosen on the same temporal holdout, by the same rule, as the ridge penalty above.
MLP_WEIGHT_DECAYS = (1e-4, 1e-3, 1e-2, 1e-1, 1.0)
ARMS = ("best_single", "ridge_linear", "ridge_composite", "mlp_nonlinear", "duplicated")


# ── design matrices ──────────────────────────────────────────────────────────

def assemble_rows(table: dict[str, Any], target: np.ndarray, periods: list[int],
                  columns: tuple[int, ...] | None = None) -> dict[str, np.ndarray]:
    """Rows are ``(period, zone)`` pairs: features at ``p - 1``, realised target at ``p``.

    A row survives only where the target is observed. The availability channels travel
    beside the features as extra columns, so "missing" is information the arm receives
    rather than a value it must guess at.
    """
    features, available = table["features"], table["available"]
    index = list(columns) if columns is not None else list(range(features.shape[2]))
    blocks, targets, keys = [], [], []
    for period in periods:
        if period - 1 < 0:
            continue
        row = np.concatenate([features[period - 1][:, index],
                              available[period - 1][:, index]], axis=1)
        observed = np.isfinite(target[period])
        blocks.append(row[observed])
        targets.append(target[period][observed])
        keys.append(np.stack([np.full(int(observed.sum()), period),
                              np.nonzero(observed)[0]], axis=1))
    if not blocks:
        empty = np.zeros((0, 2 * len(index)))
        return {"x": empty, "y": np.zeros(0), "keys": np.zeros((0, 2), int),
                "column_index": np.asarray(index, int)}
    return {"x": np.concatenate(blocks), "y": np.concatenate(targets),
            "keys": np.concatenate(keys), "column_index": np.asarray(index, int)}


def standardise(train_x: np.ndarray) -> dict[str, np.ndarray]:
    centre = train_x.mean(0)
    spread = train_x.std(0)
    spread = np.where(spread > 1e-9, spread, 1.0)
    return {"centre": centre, "spread": spread}


def apply_scaler(x: np.ndarray, scaler: dict[str, np.ndarray]) -> np.ndarray:
    return (x - scaler["centre"]) / scaler["spread"]


# ── linear arms ──────────────────────────────────────────────────────────────

def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> dict[str, np.ndarray]:
    n_features = x.shape[1]
    gram = x.T @ x + alpha * np.eye(n_features)
    beta = np.linalg.solve(gram, x.T @ (y - y.mean()))
    return {"beta": beta, "intercept": float(y.mean())}


def expanding_folds(periods: np.ndarray, n_blocks: int = N_BLOCKS) -> list[tuple]:
    """Expanding-window folds over the training periods: fit on the past, check on the next block.

    A **single** contiguous tail was the first design, and it selected the regularisation
    backwards. The training window ends on 2020-2022 -- COVID and the methodological breaks --
    so a lone tail fold asks which penalty best fits an atypical era and answers accordingly.
    On the pilot the tail ranked the network's five weight decays in exactly the reverse of
    their true out-of-sample order, choosing the one that overfitted hardest.

    Several blocks spread across the training window ask the question the evaluation actually
    poses: how does a model fitted on the past do on periods it has not seen. Each fold is
    strictly forward -- the check block always follows its training block -- so no fold ever
    validates on periods that its own fit had in scope.
    """
    unique = np.unique(periods)
    if len(unique) < 2 * n_blocks:
        return []
    edges = np.array_split(unique, n_blocks)
    folds = []
    for index in range(1, len(edges)):
        past = np.concatenate(edges[:index])
        check = edges[index]
        folds.append((np.isin(periods, past), np.isin(periods, check)))
    return folds


def choose_alpha(x: np.ndarray, y: np.ndarray, periods: np.ndarray | None = None) -> float:
    """The ridge penalty, selected on the training window alone, never on the evaluation origins.

    Uses the same folds, by the same rule, as the network's weight decay. A random split
    would let a zone's neighbouring periods sit on both sides and would report a penalty
    tuned to interpolation rather than to forecasting.
    """
    folds = expanding_folds(periods) if periods is not None else []
    if not folds:
        return 1.0
    scores = []
    for alpha in RIDGE_ALPHAS:
        losses = [float(np.mean((predict_ridge(x[check], fit_ridge(x[train], y[train], alpha))
                                 - y[check]) ** 2))
                  for train, check in folds]
        scores.append(losses)
    return float(RIDGE_ALPHAS[one_standard_error_rule(scores)])


def one_standard_error_rule(fold_losses: list[list[float]]) -> int:
    """Index of the most regularised candidate within one standard error of the best.

    Candidates must be ordered from weakest to strongest regularisation.

    Choosing the outright minimum of the mean fold loss is the obvious rule and it is not
    the right one here. The folds cover different economic eras, their losses differ by more
    than the gap between neighbouring candidates, and the mean is then dominated by whichever
    era happens to be easiest. The classical remedy is to treat every candidate whose loss
    lies within one standard error of the best as indistinguishable from it, and among those
    to take the most regularised -- which is the safe direction when the evaluation window is
    a later era than the training window, as it always is in a forecasting design.

    Adopted on that reasoning, and on the pilot behaviour of the smoke seeds. It is not
    tuned to the final grid: doing so would be calibrating on the final seeds.
    """
    means = np.array([np.mean(losses) for losses in fold_losses])
    best = int(np.argmin(means))
    spread = np.std(fold_losses[best], ddof=1) / max(np.sqrt(len(fold_losses[best])), 1.0)
    threshold = means[best] + spread
    eligible = np.nonzero(means <= threshold)[0]
    return int(eligible.max()) if len(eligible) else best


def predict_ridge(x: np.ndarray, fitted: dict[str, np.ndarray]) -> np.ndarray:
    return x @ fitted["beta"] + fitted["intercept"]


def select_best_single(x: np.ndarray, y: np.ndarray, n_features: int) -> int:
    """The single column with the lowest in-training squared error, availability aside.

    Only the feature half of the design is eligible: an availability channel is a statement
    about publication, and letting the floor be a publication indicator would make the
    comparison one about the calendar.
    """
    best, best_loss = 0, float("inf")
    for column in range(n_features):
        single = x[:, [column]]
        fitted = fit_ridge(single, y, 1e-6)
        loss = float(np.mean((predict_ridge(single, fitted) - y) ** 2))
        if loss < best_loss:
            best, best_loss = column, loss
    return best


# ── the non-linear arm ───────────────────────────────────────────────────────

def initialise_mlp(n_features: int, hidden: int, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    scale = 1.0 / np.sqrt(n_features)
    return {"w1": rng.normal(0.0, scale, size=(n_features, hidden)),
            "b1": np.zeros(hidden),
            "w2": rng.normal(0.0, 1.0 / np.sqrt(hidden), size=hidden),
            "b2": 0.0}


def mlp_forward(params: dict[str, Any], x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    activation = np.tanh(x @ params["w1"] + params["b1"])
    return activation @ params["w2"] + params["b2"], activation


def fit_mlp(x: np.ndarray, y: np.ndarray, hidden: int, seed: int,
            epochs: int = EPOCHS, learning_rate: float = LEARNING_RATE,
            weight_decay: float = WEIGHT_DECAY,
            monitor: tuple[np.ndarray, np.ndarray] | None = None) -> dict[str, Any]:
    params = initialise_mlp(x.shape[1], hidden, seed)
    params["b2"] = float(y.mean())
    moment = {key: np.zeros_like(np.asarray(value, float)) for key, value in params.items()}
    velocity = {key: np.zeros_like(np.asarray(value, float)) for key, value in params.items()}
    history: list[float] = []
    holdout_history: list[float] = []
    best_params, best_epoch, best_loss = None, epochs, float("inf")
    n_rows = max(len(y), 1)
    for step in range(1, epochs + 1):
        prediction, activation = mlp_forward(params, x)
        residual = prediction - y
        history.append(float(np.mean(residual ** 2)))
        upstream = 2.0 * residual / n_rows
        grad = {
            "w2": activation.T @ upstream + weight_decay * params["w2"],
            "b2": float(upstream.sum()),
        }
        inner = np.outer(upstream, params["w2"]) * (1.0 - activation ** 2)
        grad["w1"] = x.T @ inner + weight_decay * params["w1"]
        grad["b1"] = inner.sum(0)
        for key in params:
            gradient = np.asarray(grad[key], float)
            moment[key] = 0.9 * moment[key] + 0.1 * gradient
            velocity[key] = 0.999 * velocity[key] + 0.001 * gradient ** 2
            corrected_m = moment[key] / (1.0 - 0.9 ** step)
            corrected_v = velocity[key] / (1.0 - 0.999 ** step)
            update = learning_rate * corrected_m / (np.sqrt(corrected_v) + 1e-8)
            params[key] = params[key] - (float(update) if key == "b2" else update)
        if monitor is not None and step % MONITOR_EVERY == 0:
            loss = float(np.mean((mlp_forward(params, monitor[0])[0] - monitor[1]) ** 2))
            holdout_history.append(loss)
            if loss < best_loss:
                best_loss, best_epoch = loss, step
                best_params = {key: (value if key == "b2" else value.copy())
                               for key, value in params.items()}
    if best_params is not None:
        params = best_params
    return {"params": params, "loss_history": history,
            "holdout_history": holdout_history,
            "best_epoch": best_epoch, "best_holdout_mse": best_loss,
            "weight_decay": weight_decay,
            "parameters": int(x.shape[1] * hidden + 2 * hidden + 1)}


def predict_mlp(x: np.ndarray, fitted: dict[str, Any]) -> np.ndarray:
    return mlp_forward(fitted["params"], x)[0]


def fit_mlp_selected(x: np.ndarray, y: np.ndarray, hidden: int, seed: int,
                     epochs: int = EPOCHS,
                     periods: np.ndarray | None = None) -> dict[str, Any]:
    """Fit with weight decay and stopping epoch chosen on the same folds as the ridge penalty.

    Giving the non-linear arm a fixed penalty while the linear one tunes its own would decide
    the comparison inside the fitting procedure rather than in the data -- and the pilot
    showed which way it would fall. At a fixed decay of 1e-4 the network drove its training
    loss to 0.00075 and its out-of-sample error to more than twice the ridge's. The network
    has the greater capacity, so it needs the regularisation *more*, not less.
    """
    folds = expanding_folds(periods) if periods is not None else []
    if not folds:
        return fit_mlp(x, y, hidden, seed, epochs=epochs)
    trace, per_decay, stops_per_decay = [], [], []
    for decay in MLP_WEIGHT_DECAYS:
        losses, stops = [], []
        for train, check in folds:
            candidate = fit_mlp(x[train], y[train], hidden, seed, epochs=epochs,
                                weight_decay=decay, monitor=(x[check], y[check]))
            losses.append(candidate["best_holdout_mse"])
            stops.append(candidate["best_epoch"])
        per_decay.append(losses)
        stops_per_decay.append(stops)
        trace.append({"weight_decay": decay, "fold_mse": losses,
                      "mean_mse": float(np.mean(losses)), "stop_epochs": stops})
    chosen = one_standard_error_rule(per_decay)
    best_decay = MLP_WEIGHT_DECAYS[chosen]
    best_epochs = int(np.median(stops_per_decay[chosen]))
    best_loss = float(np.mean(per_decay[chosen]))
    # Refit on the whole training window at the selected decay and epoch count. The folds
    # have served their purpose, and withholding history from the final fit would penalise
    # the arm for the selection it was required to make.
    final = fit_mlp(x, y, hidden, seed, epochs=max(best_epochs, MONITOR_EVERY),
                    weight_decay=best_decay)
    final["selection"] = {"weight_decay": best_decay, "epochs": best_epochs,
                          "mean_fold_mse": best_loss, "trace": trace}
    return final


def marginal_effects(params: dict[str, Any], x: np.ndarray) -> np.ndarray:
    """``d f / d x_j`` at every row, exactly. Shape ``(n_rows, n_features)``."""
    _, activation = mlp_forward(params, x)
    derivative = (1.0 - activation ** 2) * params["w2"]
    return derivative @ params["w1"].T


def mixed_partial(params: dict[str, Any], x: np.ndarray, first: int,
                  second: int) -> np.ndarray:
    """``d2 f / d x_first d x_second`` at every row, exactly.

    For one hidden layer the second derivative of the activation is
    ``tanh''(u) = -2 tanh(u) (1 - tanh^2(u))``, and the mixed partial is a weighted sum of
    products of first-layer weights. Nothing else contributes, so this is the interaction --
    not a proxy for it.
    """
    _, activation = mlp_forward(params, x)
    curvature = -2.0 * activation * (1.0 - activation ** 2) * params["w2"]
    return (curvature * params["w1"][first] * params["w1"][second]).sum(1)


def interaction_strength(params: dict[str, Any], x: np.ndarray) -> np.ndarray:
    """Mean ``|d2 f / d x_j d x_k|`` over the rows. Shape ``(n_features, n_features)``.

    For one hidden layer this is exact, not an approximation: the second derivative of
    ``tanh`` is ``-2 tanh(u) (1 - tanh^2(u))``, so the mixed partial is a weighted outer
    product of the first-layer weights and nothing else contributes.
    """
    _, activation = mlp_forward(params, x)
    curvature = -2.0 * activation * (1.0 - activation ** 2) * params["w2"]
    weights = params["w1"]
    width = weights.shape[0]
    total = np.zeros((width, width))
    # The absolute value cannot be factored out of the sum over hidden units, so the mixed
    # partial is materialised per row and averaged. Chunked, because the full array would be
    # rows x features x features and does not need to exist at once.
    chunk = max(1, int(2e7 // max(width * width, 1)))
    for start in range(0, len(x), chunk):
        block = curvature[start:start + chunk]
        total += np.abs(np.einsum("nh,jh,kh->njk", block, weights, weights,
                                  optimize=True)).sum(0)
    return total / max(len(x), 1)


def partial_effect_curve(params: dict[str, Any], x: np.ndarray, column: int,
                         n_points: int = 21) -> dict[str, np.ndarray]:
    """Response to one feature with every other held at its median."""
    base = np.median(x, axis=0)
    low, high = np.quantile(x[:, column], [0.02, 0.98])
    sweep = np.linspace(low, high, n_points)
    grid = np.repeat(base[None, :], n_points, axis=0)
    grid[:, column] = sweep
    response, _ = mlp_forward(params, grid)
    return {"x": sweep, "y": response}


def interaction_surface(params: dict[str, Any], x: np.ndarray, first: int, second: int,
                        n_points: int = 15) -> dict[str, np.ndarray]:
    base = np.median(x, axis=0)
    axis_a = np.linspace(*np.quantile(x[:, first], [0.05, 0.95]), n_points)
    axis_b = np.linspace(*np.quantile(x[:, second], [0.05, 0.95]), n_points)
    grid = np.repeat(base[None, :], n_points * n_points, axis=0)
    mesh_a, mesh_b = np.meshgrid(axis_a, axis_b, indexing="ij")
    grid[:, first] = mesh_a.ravel()
    grid[:, second] = mesh_b.ravel()
    response, _ = mlp_forward(params, grid)
    return {"axis_first": axis_a, "axis_second": axis_b,
            "surface": response.reshape(n_points, n_points)}


# ── controls ─────────────────────────────────────────────────────────────────

def permute_within_period(x: np.ndarray, keys: np.ndarray, columns: list[int],
                          seed: int) -> np.ndarray:
    """Permute the named columns across zones **within each period**.

    Every marginal distribution, every cross-sectional moment and every period effect is
    preserved exactly; the only thing destroyed is the alignment between the permuted
    columns and the rest of the row. A gain that survives this was never an interaction, and
    this is the decisive control of the stage.
    """
    rng = np.random.default_rng(seed)
    out = x.copy()
    for period in np.unique(keys[:, 0]):
        rows = np.nonzero(keys[:, 0] == period)[0]
        order = rng.permutation(len(rows))
        out[np.ix_(rows, columns)] = out[np.ix_(rows[order], columns)]
    return out


def permute_across_periods(x: np.ndarray, keys: np.ndarray, seed: int) -> np.ndarray:
    """Destroy the temporal alignment: shuffle each zone's rows over periods."""
    rng = np.random.default_rng(seed)
    out = x.copy()
    for zone in np.unique(keys[:, 1]):
        rows = np.nonzero(keys[:, 1] == zone)[0]
        out[rows] = out[rows[rng.permutation(len(rows))]]
    return out


def permute_zones(x: np.ndarray, seed: int) -> np.ndarray:
    """Shuffle whole rows: signal identities no longer belong to their own zone."""
    rng = np.random.default_rng(seed)
    return x[rng.permutation(len(x))]


# ── metrics ──────────────────────────────────────────────────────────────────

def loss_of(prediction: np.ndarray, target: np.ndarray) -> dict[str, float]:
    residual = prediction - target
    variance = float(np.var(target)) if len(target) else float("nan")
    return {
        "mse": float(np.mean(residual ** 2)) if len(target) else float("nan"),
        "mae": float(np.mean(np.abs(residual))) if len(target) else float("nan"),
        "r2": float(1.0 - np.mean(residual ** 2) / variance) if variance > 1e-18
              else float("nan"),
        "n": int(len(target)),
    }


def gain_over(reference: float, candidate: float) -> float:
    """Fraction of the reference's squared error removed. Positive means better."""
    if not np.isfinite(reference) or reference <= 0.0:
        return float("nan")
    return float(1.0 - candidate / reference)
