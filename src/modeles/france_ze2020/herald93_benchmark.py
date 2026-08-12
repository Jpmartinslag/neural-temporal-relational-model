"""HERALD 93: four model families on one multisignal benchmark, judged on the same terms.

The question the oracle could answer was whether the information is *there*. This module
asks whether a method can *find* it, and whether the proposed method finds more of it than
the established ones. Four families, one per question:

``sparse_var``   Graphical Granger by group Lasso. Does a frugal classical method,
                 restricted to the same candidate support, recover the graph?
``mtgnn``        A learned adjacency trained purely for forecasting. Does a graph help
                 prediction, and does the graph it learns happen to be the true one?
``nri``          Neural Relational Inference on the same support. Does an architecture
                 built for relational recovery recover it?
``herald``       The proposal: per-signal encoders, a masked multisignal fusion, one shared
                 relational scorer, a commuting support, and abstention.

PCMCI+ was the other classical candidate and is not used: ``tigramite`` is not installed in
the cluster environment, and adding an unaudited dependency to obtain a second classical
method is worse than running one that can be read end to end. Group Lasso Granger is
available, stable and auditable, and it answers the same question. The choice is recorded
here, before any result.

**What every method receives, identically.** The same released observations, the same masks,
the same candidate support, the same folds, the same origins, the same seeds, and no edge
labels of any kind. ``A_true``, the latent state, the relational component and the typed
events exist only inside the evaluator. Where capacities genuinely differ -- MTGNN learns an
unconstrained adjacency, NRI a static one, HERALD a dynamic one on a restricted support --
the difference is declared in the per-method record rather than hidden.

**One objective for all four.** Every neural method minimises a masked Gaussian negative
log-likelihood on log-growth with a learned per-signal scale. The observation families of
the panel (negative binomial, gamma, logit) are handled where they belong, in the GLM
oracle and in the deviance metric; giving one architecture a better-specified likelihood
than another would be a capacity difference disguised as a result.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any

import numpy as np

try:  # torch is present in the cluster environment; the classical arm does not need it.
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised only on machines without torch
    torch = None
    nn = None

METHODS = ("persistence", "sparse_var", "mtgnn", "nri", "herald")
NEURAL_METHODS = ("mtgnn", "nri", "herald")

# Declared before any run.
DEFAULT_HIDDEN = 64
FORBIDDEN_WIDTH = 256
CONTEXT = 8               # periods of history the encoders see
TOP_K_PROPAGATION = 8     # neighbours kept for message passing, per target
# Log-growth sits around 0.03 to 0.05 while the mask channel is 0 or 1, so the observation
# channel entered the convolution an order of magnitude smaller than the flag beside it. For
# the two signals whose mask is nearly constant the input was therefore nearly constant, the
# rectifier saturated at initialisation and their encoders received exactly no gradient:
# the smoke reported headcount and unemployment as dead while the two sparsely published
# signals trained normally. The scale is a declared constant rather than an estimate, so it
# introduces no dependence on the data and cannot leak a future period.
GROWTH_SCALE = 20.0


# ── The observable view ──────────────────────────────────────────────────────

class PanelView:
    """Everything a method may see, and nothing else.

    Built from ``model_inputs``, so release dates and availability masks have already been
    applied and no cell from after the decision period is present. The truth is attached to
    a *separate* object that only the evaluator holds.
    """

    def __init__(self, released: dict[str, Any], support: np.ndarray,
                 signal_names: list[str]):
        self.names = signal_names
        blocks = [released["signals"][name] for name in signal_names]
        values = np.stack([np.asarray(block["values"], float) for block in blocks])
        masks = np.stack([np.asarray(block["availability_mask"], bool) for block in blocks])
        logs = np.where(masks, np.log(np.maximum(values, 1e-9)), np.nan)

        # Growth is the first difference of the log level at the signal's own frequency.
        # An annual series is published once a year, so differencing it at lag one would
        # produce nothing but gaps; the lag follows the publication frequency.
        self.lags = [4 if block["freq"] == "A" else 1 for block in blocks]
        n_signals, n_periods, n_zones = logs.shape
        growth = np.full((n_signals, n_periods, n_zones), np.nan)
        for index, lag in enumerate(self.lags):
            growth[index, lag:] = logs[index, lag:] - logs[index, :-lag]
        self.growth = growth
        self.observed = np.isfinite(growth)
        self.filled = np.nan_to_num(growth)
        self.n_signals, self.n_periods, self.n_zones = growth.shape
        self.support = support.astype(bool)
        np.fill_diagonal(self.support, False)

    def window(self, end: int, length: int = CONTEXT) -> tuple[np.ndarray, np.ndarray]:
        """History strictly before ``end``: channels [signals, length, zones]."""
        start = max(0, end - length)
        block = self.filled[:, start:end, :] * GROWTH_SCALE
        seen = self.observed[:, start:end, :]
        if block.shape[1] < length:
            pad = length - block.shape[1]
            block = np.concatenate([np.zeros((self.n_signals, pad, self.n_zones)), block], 1)
            seen = np.concatenate([np.zeros((self.n_signals, pad, self.n_zones), bool), seen], 1)
        return block, seen


def last_released_origin(view: "PanelView") -> int:
    """The most recent period for which every arm actually has a target.

    Signals are published with a one-year lag, so the four periods closest to a decision
    date carry no released observation at all. A probe or a training step aimed at one of
    them computes a loss over an empty mask, which is not a weak gradient but no gradient,
    and reads in a diagnostic exactly like a dead component.
    """
    for period in range(view.n_periods - 1, CONTEXT, -1):
        if view.observed[:, period, :].any():
            return period
    raise ValueError("no released period in this view")


def candidate_support(prior: np.ndarray, k: int = 40) -> np.ndarray:
    """The commuting support every method is restricted to. Prior, never a label.

    Used as the set of pairs a method is allowed to consider. It is never compared against
    for credit and never enters a loss: a method that simply returned the support would
    score at the prevalence, which is exactly what the AUPRC baseline reports.
    """
    matrix = np.asarray(prior, float).copy()
    np.fill_diagonal(matrix, 0.0)
    support = np.zeros(matrix.shape, bool)
    keep = min(k, matrix.shape[1] - 1)
    for row in range(matrix.shape[0]):
        order = np.argsort(-matrix[row])[:keep]
        support[row, order[matrix[row, order] > 0]] = True
    return support


# ── Metrics ──────────────────────────────────────────────────────────────────

def forecast_metrics(prediction: np.ndarray, target: np.ndarray, mask: np.ndarray,
                     persistence: np.ndarray) -> dict[str, float]:
    ok = mask & np.isfinite(target) & np.isfinite(prediction)
    if ok.sum() == 0:
        return {"mae": float("nan"), "wmape": float("nan"), "deviance": float("nan"),
                "skill_vs_persistence": float("nan"), "n": 0}
    error = np.abs(prediction[ok] - target[ok])
    base = np.abs(persistence[ok] - target[ok])
    denominator = np.abs(target[ok]).sum()
    return {
        "mae": float(error.mean()),
        "wmape": float(error.sum() / max(denominator, 1e-12)),
        "deviance": float(np.mean((prediction[ok] - target[ok]) ** 2)),
        "skill_vs_persistence": float(1.0 - error.mean() / max(base.mean(), 1e-12)),
        "n": int(ok.sum()),
    }


def _binary_truth(propagation: np.ndarray, period: int) -> np.ndarray:
    matrix = np.asarray(propagation[period]) != 0
    matrix = matrix.copy()
    np.fill_diagonal(matrix, False)
    return matrix


def average_precision(scores: np.ndarray, labels: np.ndarray) -> float:
    order = np.argsort(-scores)
    labels = labels[order]
    if labels.sum() == 0:
        return float("nan")
    cumulative = np.cumsum(labels)
    precision = cumulative / np.arange(1, labels.size + 1)
    return float((precision * labels).sum() / labels.sum())


def relational_metrics(scores: np.ndarray, truth: dict[str, Any], support: np.ndarray,
                       period: int, keep: int) -> dict[str, float]:
    """Recovery on the synthetic benchmark only. Never computed on France."""
    propagation = np.asarray(truth["propagation"])
    labels_matrix = _binary_truth(propagation, period)
    dense = np.asarray(truth["dense"][period], float)

    inside = support.copy()
    np.fill_diagonal(inside, False)
    flat_scores = scores[inside]
    flat_labels = labels_matrix[inside].astype(float)
    prevalence = float(flat_labels.mean()) if flat_labels.size else float("nan")

    # Predicted edge set: the same budget for every method, taken as the true edge count
    # inside the support so that precision and recall are comparable across methods rather
    # than reflecting a differently-sized guess.
    budget = int(labels_matrix[inside].sum()) if keep <= 0 else keep
    predicted = np.zeros_like(flat_labels, bool)
    if budget > 0 and flat_scores.size:
        cut = np.argsort(-flat_scores)[:budget]
        predicted[cut] = True
    true_positive = float((predicted & (flat_labels > 0)).sum())
    precision = true_positive / max(predicted.sum(), 1)
    recall = true_positive / max(flat_labels.sum(), 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)

    full = np.zeros_like(scores)
    full[inside] = flat_scores
    finite = np.isfinite(full) & np.isfinite(dense) & inside
    if finite.sum() > 8 and full[finite].std() > 0 and dense[finite].std() > 0:
        dense_correlation = float(np.corrcoef(full[finite], dense[finite])[0, 1])
    else:
        dense_correlation = float("nan")

    # Direction: among predicted pairs whose reverse is not a true edge, how often the
    # predicted orientation is the true one.
    predicted_matrix = np.zeros_like(labels_matrix)
    predicted_matrix[inside] = predicted
    asymmetric = labels_matrix & ~labels_matrix.T
    directed = predicted_matrix & (labels_matrix | labels_matrix.T)
    direction = (float((predicted_matrix & asymmetric).sum() / max(directed.sum(), 1))
                 if directed.sum() else float("nan"))

    outside = (~support) & ~np.eye(support.shape[0], dtype=bool)
    return {
        "edge_f1": float(f1), "precision": float(precision), "recall": float(recall),
        "dense_correlation": dense_correlation,
        "auprc": average_precision(flat_scores, flat_labels),
        "prevalence": prevalence,
        "direction_precision": direction,
        "predicted_added_edge_rate": float(
            (predicted_matrix & ~labels_matrix).sum() / max(predicted_matrix.sum(), 1)),
        "true_edges_outside_support": int((labels_matrix & outside).sum()),
        "budget": int(budget),
    }


def typed_event_metrics(scores_by_period: dict[int, np.ndarray], truth: dict[str, Any],
                        support: np.ndarray, periods: list[int],
                        keep: int) -> dict[str, float]:
    """Typed dated events: (period, source, target, birth|death), micro-averaged.

    A period whose truth does not move reports ``false_event_rate`` rather than an F1 of
    zero: with no event to find, an F1 is not defined and reporting zero would punish a
    method for the benchmark's calendar rather than for its behaviour.
    """
    propagation = np.asarray(truth["propagation"])
    hits = misses = false_alarms = 0
    static_periods = 0
    false_on_static = 0
    for period in periods:
        if period - 1 < 0 or period - 1 not in scores_by_period:
            continue
        now = _binary_truth(propagation, period)
        before = _binary_truth(propagation, period - 1)
        births = now & ~before & support
        deaths = before & ~now & support
        moved = int(births.sum() + deaths.sum())

        change = scores_by_period[period] - scores_by_period[period - 1]
        inside = support & ~np.eye(support.shape[0], dtype=bool)
        flat = change[inside]
        budget = keep if keep > 0 else max(moved, 1)
        predicted_birth = np.zeros_like(flat, bool)
        predicted_death = np.zeros_like(flat, bool)
        # A birth is claimed only where the score actually rose, a death only where it
        # actually fell. Taking the top of the ranking unconditionally meant that a method
        # whose score never moves still emitted a full budget of events, drawn from the
        # arbitrary order of a tie: a frozen prior scored an event F1 of 0.062 without
        # predicting anything at all.
        rose = np.flatnonzero(flat > 0)
        fell = np.flatnonzero(flat < 0)
        if rose.size:
            predicted_birth[rose[np.argsort(-flat[rose])[:budget]]] = True
        if fell.size:
            predicted_death[fell[np.argsort(flat[fell])[:budget]]] = True
        birth_matrix = np.zeros_like(now); birth_matrix[inside] = predicted_birth
        death_matrix = np.zeros_like(now); death_matrix[inside] = predicted_death

        if moved == 0:
            static_periods += 1
            false_on_static += int(birth_matrix.sum() + death_matrix.sum())
            continue
        hits += int((birth_matrix & births).sum() + (death_matrix & deaths).sum())
        misses += int((births & ~birth_matrix).sum() + (deaths & ~death_matrix).sum())
        false_alarms += int((birth_matrix & ~births).sum() + (death_matrix & ~deaths).sum())

    if hits + misses == 0:
        return {"event_f1": float("nan"), "n_events": 0,
                "static_periods": static_periods,
                "false_event_rate": float(false_on_static / max(static_periods, 1))}
    precision = hits / max(hits + false_alarms, 1)
    recall = hits / max(hits + misses, 1)
    return {
        "event_f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
        "event_precision": float(precision), "event_recall": float(recall),
        "n_events": int(hits + misses), "static_periods": static_periods,
        "false_event_rate": float(false_on_static / max(static_periods, 1)),
    }


# ── A. Classical: Graphical Granger by Lasso ─────────────────────────────────

def _soft_threshold(value: np.ndarray, amount: float) -> np.ndarray:
    return np.sign(value) * np.maximum(np.abs(value) - amount, 0.0)


def lasso_coordinate_descent(design: np.ndarray, target: np.ndarray, penalty: float,
                             iterations: int = 60) -> np.ndarray:
    """Plain coordinate descent. Written out so the classical arm has no hidden defaults."""
    n, p = design.shape
    beta = np.zeros(p)
    norms = (design ** 2).sum(0)
    residual = target.copy()
    for _ in range(iterations):
        largest = 0.0
        for j in range(p):
            if norms[j] <= 1e-12:
                continue
            partial = residual @ design[:, j] + norms[j] * beta[j]
            update = _soft_threshold(np.array(partial / n), penalty)[()] / (norms[j] / n)
            delta = update - beta[j]
            if delta != 0.0:
                residual -= design[:, j] * delta
                beta[j] = update
                largest = max(largest, abs(delta))
        if largest < 1e-7:
            break
    return beta


def fit_sparse_var(view: PanelView, train_end: int, penalty: float = 0.01) -> dict[str, Any]:
    """One group-Lasso regression per (target zone, signal), on the candidate support.

    The neighbour coefficient for a pair is aggregated across signals into a single edge
    score, so the classical arm answers the relational question at the same granularity as
    the neural ones.
    """
    started = time.time()
    n_zones = view.n_zones
    scores = np.zeros((n_zones, n_zones))
    coefficients: dict[tuple[int, int], dict] = {}
    parameters = 0
    for target_zone in range(n_zones):
        neighbours = np.flatnonzero(view.support[target_zone])
        if neighbours.size == 0:
            continue
        for signal in range(view.n_signals):
            lag = view.lags[signal]
            rows = np.arange(lag + 1, train_end)
            usable = view.observed[signal, rows, target_zone]
            if usable.sum() < 12:
                continue
            rows = rows[usable]
            target = view.growth[signal, rows, target_zone]
            own = view.filled[:, rows - 1, target_zone].T          # all signals, own zone
            neighbour = view.filled[signal][np.ix_(rows - 1, neighbours)]
            design = np.column_stack([own, neighbour])
            design_centre = design.mean(0)
            design = design - design_centre
            spread = design.std(0)
            design = design / np.where(spread > 1e-9, spread, 1.0)
            beta = lasso_coordinate_descent(design, target - target.mean(), penalty)
            parameters += beta.size
            scores[target_zone, neighbours] += np.abs(beta[view.n_signals:])
            coefficients[(target_zone, signal)] = {
                "beta": beta, "neighbours": neighbours, "centre": design_centre,
                "spread": spread, "intercept": float(target.mean())}
    return {"edge_scores": scores, "parameters": int(parameters),
            "coefficients": coefficients,
            "seconds": round(time.time() - started, 2), "epochs": 0}


def predict_sparse_var(view: PanelView, origin: int, fitted: dict) -> np.ndarray:
    """The forecast produced by the coefficients that produced the edge scores.

    Deliberately the *same* model: reporting a persistence forecast beside a Lasso graph
    would let the classical arm be judged on one object and credited for another, and would
    make its forecast indistinguishable from the persistence floor by construction.
    """
    coefficients = fitted["coefficients"]
    prediction = np.zeros((view.n_signals, view.n_zones))
    for (zone, signal), entry in coefficients.items():
        neighbours = entry["neighbours"]
        own = view.filled[:, origin - 1, zone]
        neighbour = view.filled[signal][origin - 1, neighbours]
        row = np.concatenate([own, neighbour])
        row = (row - entry["centre"]) / np.where(entry["spread"] > 1e-9,
                                                 entry["spread"], 1.0)
        prediction[signal, zone] = entry["intercept"] + float(row @ entry["beta"])
    return prediction


# ── Neural arms ──────────────────────────────────────────────────────────────

def _require_torch() -> None:
    if torch is None:
        raise RuntimeError("torch is required for the neural arms")


class TemporalEncoder(nn.Module if nn is not None else object):
    """Per-signal dilated causal convolution over (growth, mask).

    The mask is a channel, not a fill value: a missing cell enters as zero *and* as an
    explicit flag, so the network can tell "no growth" from "no observation". Feeding the
    zero alone is the defect the guards call ``absence_becomes_zero``.
    """

    def __init__(self, n_signals: int, hidden: int, context: int = CONTEXT):
        super().__init__()
        self.n_signals = n_signals
        self.context = context
        self.per_signal = nn.ModuleList([
            nn.Sequential(
                nn.Conv1d(2, hidden, kernel_size=3, dilation=1, padding=0),
                nn.GELU(),
                nn.Conv1d(hidden, hidden, kernel_size=3, dilation=2, padding=0),
                nn.GELU(),
            ) for _ in range(n_signals)])
        self.hidden = hidden

    def forward(self, block: "torch.Tensor", seen: "torch.Tensor") -> "torch.Tensor":
        """block/seen: [signals, time, zones] -> [signals, zones, hidden]."""
        out = []
        for index in range(self.n_signals):
            series = torch.stack([block[index], seen[index]], 0)      # [2, time, zones]
            series = series.permute(2, 0, 1)                          # [zones, 2, time]
            encoded = self.per_signal[index](series)                  # [zones, hidden, t']
            out.append(encoded[:, :, -1])
        return torch.stack(out, 0)


class MaskedFusion(nn.Module if nn is not None else object):
    """Gated mean over signals, with the gate multiplied by the signal's observed share.

    A signal that is not published in the window contributes nothing, and no signal is
    dropped by construction: the gate is learned, so a signal the data does not need is
    down-weighted rather than removed, and the per-signal gradient guard can still see it.
    """

    def __init__(self, n_signals: int, hidden: int):
        super().__init__()
        self.gate = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(),
                                  nn.Linear(hidden, 1))
        self.project = nn.Linear(hidden, hidden)

    def forward(self, encoded: "torch.Tensor", coverage: "torch.Tensor") -> "torch.Tensor":
        weights = torch.sigmoid(self.gate(encoded)).squeeze(-1) * coverage   # [S, zones]
        weights = weights / weights.sum(0, keepdim=True).clamp_min(1e-6)
        fused = (encoded * weights.unsqueeze(-1)).sum(0)
        return self.project(fused), weights


class SharedRelationalScorer(nn.Module if nn is not None else object):
    """One function for every pair. No per-pair parameter, no zone identity embedding.

    The score depends on the two zones' fused states and on the commuting prior weight for
    the pair, and on nothing that could identify *which* zones they are. A per-pair free
    parameter, or an embedding indexed by zone, would let the model memorise the answer
    rather than learn a rule that transfers.
    """

    def __init__(self, hidden: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3 * hidden + 1, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden // 2), nn.ReLU(),
            nn.Linear(hidden // 2, 1))

    def forward(self, state: "torch.Tensor", pairs: "torch.Tensor",
                prior: "torch.Tensor") -> "torch.Tensor":
        source = state[pairs[0]]
        target = state[pairs[1]]
        features = torch.cat([source, target, source * target, prior.unsqueeze(-1)], -1)
        return self.net(features).squeeze(-1)


class HeraldMultisignal(nn.Module if nn is not None else object):
    """The proposal.

    The relational arm carries no node-only path: it is built strictly from messages
    arriving from *other* zones, the diagonal is masked before any normalisation, and the
    target zone's own state never enters its own message. If it did, the relational arm
    could reproduce the node-only arm and the ablation would measure nothing.

    Top-k selects which neighbours propagate, and is applied with a straight-through
    estimator so the scorer still receives gradient for the edges it did not select. A hard
    top-k without it silently freezes most of the graph.
    """

    def __init__(self, n_signals: int, hidden: int, pairs: np.ndarray, prior: np.ndarray,
                 n_zones: int, top_k: int = TOP_K_PROPAGATION):
        super().__init__()
        if hidden >= FORBIDDEN_WIDTH:
            raise ValueError(f"width {hidden} is not permitted in this study")
        self.encoder = TemporalEncoder(n_signals, hidden)
        self.fusion = MaskedFusion(n_signals, hidden)
        self.scorer = SharedRelationalScorer(hidden)
        self.node_head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(),
                                       nn.Linear(hidden, n_signals))
        self.relational_head = nn.Linear(hidden, n_signals)
        self.abstain = nn.Sequential(nn.Linear(hidden, hidden // 2), nn.ReLU(),
                                     nn.Linear(hidden // 2, 1))
        self.log_scale = nn.Parameter(torch.zeros(n_signals))
        self.register_buffer("pairs", torch.as_tensor(pairs, dtype=torch.long))
        self.register_buffer("prior_weight", torch.as_tensor(prior, dtype=torch.float32))
        self.n_zones = n_zones
        self.top_k = top_k

    def edge_logits(self, block, seen, coverage):
        encoded = self.encoder(block, seen)
        state, gates = self.fusion(encoded, coverage)
        logits = self.scorer(state, self.pairs, self.prior_weight)
        return logits, state, gates, encoded

    def forward(self, block, seen, coverage):
        logits, state, gates, encoded = self.edge_logits(block, seen, coverage)
        weights = torch.sigmoid(logits)

        # Top-k per target zone, straight-through: the forward pass propagates only the
        # selected neighbours, the backward pass reaches every candidate.
        target = self.pairs[1]
        keep = torch.zeros_like(weights)
        for zone in range(self.n_zones):
            index = (target == zone).nonzero(as_tuple=True)[0]
            if index.numel() == 0:
                continue
            k = min(self.top_k, index.numel())
            chosen = index[torch.topk(weights[index], k).indices]
            keep[chosen] = 1.0
        selected = weights + (keep * weights - weights).detach()

        messages = torch.zeros(self.n_zones, state.shape[1], device=state.device)
        contribution = state[self.pairs[0]] * selected.unsqueeze(-1)
        messages = messages.index_add(0, self.pairs[1], contribution)
        degree = torch.zeros(self.n_zones, device=state.device).index_add(
            0, self.pairs[1], selected).clamp_min(1e-6)
        messages = messages / degree.unsqueeze(-1)

        node = self.node_head(state)
        relational = self.relational_head(messages)
        abstention = torch.sigmoid(self.abstain(state)).squeeze(-1)
        return {"prediction": node + relational, "node": node, "relational": relational,
                "edge_weight": weights, "abstention": abstention, "gates": gates,
                "state": state, "encoded": encoded}


class MTGNNLite(nn.Module if nn is not None else object):
    """Adjacency learned from node embeddings, trained only to forecast.

    This is the family's defining trait and is preserved: the graph is a by-product of a
    forecasting objective. Its recovered adjacency is reported, but a forecasting gain is
    never read as relational discovery on its own.
    """

    def __init__(self, n_signals: int, hidden: int, n_zones: int, support: np.ndarray,
                 top_k: int = TOP_K_PROPAGATION):
        super().__init__()
        if hidden >= FORBIDDEN_WIDTH:
            raise ValueError(f"width {hidden} is not permitted in this study")
        self.encoder = TemporalEncoder(n_signals, hidden)
        self.embed_source = nn.Parameter(torch.randn(n_zones, hidden // 2) * 0.05)
        self.embed_target = nn.Parameter(torch.randn(n_zones, hidden // 2) * 0.05)
        self.mix = nn.Linear(2 * hidden, hidden)
        self.head = nn.Linear(hidden, n_signals)
        self.log_scale = nn.Parameter(torch.zeros(n_signals))
        self.register_buffer("support", torch.as_tensor(support, dtype=torch.float32))
        self.alpha = 3.0
        self.top_k = top_k

    def adjacency(self) -> "torch.Tensor":
        product = self.embed_source @ self.embed_target.T
        raw = torch.relu(torch.tanh(self.alpha * (product - product.T)))
        raw = raw * self.support
        return raw

    def forward(self, block, seen, coverage):
        encoded = self.encoder(block, seen)
        state = encoded.mean(0)
        adjacency = self.adjacency()
        normalised = adjacency / adjacency.sum(1, keepdim=True).clamp_min(1e-6)
        mixed = normalised @ state
        combined = self.mix(torch.cat([state, mixed], -1)).relu()
        return {"prediction": self.head(combined), "edge_matrix": adjacency,
                "state": state, "encoded": encoded, "gates": coverage}


class NRILite(nn.Module if nn is not None else object):
    """Neural Relational Inference on the same candidate support.

    Two edge types, a static posterior per pair, and a decoder that predicts the next step
    from the messages the posterior admits. Restricting it to the commuting support is
    required for fairness: HERALD is restricted, so comparing against an NRI free to
    consider all pairs would compare supports, not methods.
    """

    def __init__(self, n_signals: int, hidden: int, pairs: np.ndarray, n_zones: int):
        super().__init__()
        if hidden >= FORBIDDEN_WIDTH:
            raise ValueError(f"width {hidden} is not permitted in this study")
        self.encoder = TemporalEncoder(n_signals, hidden)
        self.pair_net = nn.Sequential(nn.Linear(2 * hidden, hidden), nn.ReLU(),
                                      nn.Linear(hidden, 2))
        self.message = nn.Sequential(nn.Linear(2 * hidden, hidden), nn.ReLU())
        self.head = nn.Sequential(nn.Linear(2 * hidden, hidden), nn.ReLU(),
                                  nn.Linear(hidden, n_signals))
        self.log_scale = nn.Parameter(torch.zeros(n_signals))
        self.register_buffer("pairs", torch.as_tensor(pairs, dtype=torch.long))
        self.n_zones = n_zones

    def forward(self, block, seen, coverage):
        encoded = self.encoder(block, seen)
        state = encoded.mean(0)
        source, target = state[self.pairs[0]], state[self.pairs[1]]
        logits = self.pair_net(torch.cat([source, target], -1))
        posterior = torch.softmax(logits, -1)[:, 1]
        message = self.message(torch.cat([source, target], -1)) * posterior.unsqueeze(-1)
        aggregated = torch.zeros(self.n_zones, message.shape[1], device=state.device)
        aggregated = aggregated.index_add(0, self.pairs[1], message)
        prediction = self.head(torch.cat([state, aggregated], -1))
        return {"prediction": prediction, "edge_weight": posterior, "state": state,
                "encoded": encoded, "gates": coverage,
                "kl": float_kl(torch.softmax(logits, -1))}


def float_kl(posterior: "torch.Tensor") -> "torch.Tensor":
    prior = torch.full_like(posterior, 0.5)
    return (posterior * (posterior.clamp_min(1e-9).log()
                         - prior.log())).sum(-1).mean()


# ── Training loop, identical for all neural arms ─────────────────────────────

def masked_gaussian_nll(prediction, target, mask, log_scale):
    """[zones, signals] tensors; ``mask`` selects the cells that were actually published."""
    scale = log_scale.exp().clamp_min(1e-3)
    residual = (prediction - target) / scale
    element = 0.5 * residual ** 2 + log_scale
    return (element * mask).sum() / mask.sum().clamp_min(1.0)


def train_neural(name: str, model, view: PanelView, train_end: int, epochs: int,
                 seed: int, learning_rate: float = 5e-3) -> dict[str, Any]:
    _require_torch()
    torch.manual_seed(seed)
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    origins = [t for t in range(CONTEXT + 1, train_end)]
    started = time.time()
    history = []
    for epoch in range(epochs):
        total = 0.0
        for origin in origins:
            block_np, seen_np = view.window(origin)
            block = torch.as_tensor(block_np, dtype=torch.float32)
            seen = torch.as_tensor(seen_np, dtype=torch.float32)
            coverage = seen.mean(1)                                  # [signals, zones]
            target = torch.as_tensor(view.filled[:, origin, :].T, dtype=torch.float32)
            mask = torch.as_tensor(view.observed[:, origin, :].T, dtype=torch.float32)
            if mask.sum() == 0:
                continue
            output = model(block, seen, coverage)
            loss = masked_gaussian_nll(output["prediction"], target, mask, model.log_scale)
            if "kl" in output:
                loss = loss + 0.05 * output["kl"]
            optimiser.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimiser.step()
            total += float(loss)
        history.append(total / max(len(origins), 1))
    parameters = sum(p.numel() for p in model.parameters())
    return {"epochs": epochs, "seconds": round(time.time() - started, 2),
            "parameters": int(parameters), "loss_history": history}


def component_gradient_norms(model, view: PanelView, origin: int) -> dict[str, float]:
    """Per-component gradient norms, the probe that catches a dead arm.

    A relational arm that receives no gradient is not a weak relational arm, it is an arm
    that is not being trained, and the two look identical in a metric table.
    """
    _require_torch()
    block = torch.as_tensor(view.window(origin)[0], dtype=torch.float32)
    seen = torch.as_tensor(view.window(origin)[1], dtype=torch.float32)
    coverage = seen.mean(1)
    target = torch.as_tensor(view.filled[:, origin, :].T, dtype=torch.float32)
    mask = torch.as_tensor(view.observed[:, origin, :].T, dtype=torch.float32)
    model.zero_grad()
    output = model(block, seen, coverage)
    loss = masked_gaussian_nll(output["prediction"], target, mask, model.log_scale)
    if "kl" in output:
        loss = loss + 0.05 * output["kl"]
    loss.backward()
    norms = {}
    for label, module in (("encoder", getattr(model, "encoder", None)),
                          ("fusion", getattr(model, "fusion", None)),
                          ("scorer", getattr(model, "scorer", None)),
                          ("relational_head", getattr(model, "relational_head", None)),
                          ("node_head", getattr(model, "node_head", None)),
                          ("pair_net", getattr(model, "pair_net", None)),
                          ("embed_source", getattr(model, "embed_source", None))):
        if module is None:
            continue
        if isinstance(module, torch.nn.Parameter):
            norms[label] = float(module.grad.norm()) if module.grad is not None else 0.0
            continue
        total = 0.0
        for parameter in module.parameters():
            if parameter.grad is not None:
                total += float(parameter.grad.norm()) ** 2
        norms[label] = math.sqrt(total)
    # Per-signal encoder gradient: a signal ignored by the fusion shows up as a zero here.
    norms["coverage"] = [float(value) for value in coverage.mean(-1).detach().numpy()]
    if hasattr(model, "encoder") and hasattr(model.encoder, "per_signal"):
        per_signal = []
        for branch in model.encoder.per_signal:
            total = 0.0
            for parameter in branch.parameters():
                if parameter.grad is not None:
                    total += float(parameter.grad.norm()) ** 2
            per_signal.append(math.sqrt(total))
        norms["per_signal"] = per_signal
    model.zero_grad()
    return norms


def edge_matrix_from(model, view: PanelView, origin: int) -> np.ndarray:
    _require_torch()
    with torch.no_grad():
        block = torch.as_tensor(view.window(origin)[0], dtype=torch.float32)
        seen = torch.as_tensor(view.window(origin)[1], dtype=torch.float32)
        output = model(block, seen, seen.mean(1))
    matrix = np.zeros((view.n_zones, view.n_zones))
    if "edge_matrix" in output:
        return output["edge_matrix"].detach().numpy()
    pairs = model.pairs.numpy()
    matrix[pairs[0], pairs[1]] = output["edge_weight"].detach().numpy()
    return matrix


def forecast_with(model, view: PanelView, origin: int) -> np.ndarray:
    _require_torch()
    with torch.no_grad():
        block = torch.as_tensor(view.window(origin)[0], dtype=torch.float32)
        seen = torch.as_tensor(view.window(origin)[1], dtype=torch.float32)
        output = model(block, seen, seen.mean(1))
    return output["prediction"].detach().numpy().T          # [signals, zones]
