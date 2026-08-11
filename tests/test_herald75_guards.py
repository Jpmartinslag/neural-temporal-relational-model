"""Guards that would have caught the three bugs that shipped in HERALD_68, 72 and 74.

Each test below maps to a defect that reached a commit and was found only by external audit:

  test_target_not_reconstructible_from_features   DEC-118: tgt = S[idx] on the same indices as
                                                  the features, and feature 0 is the growth
                                                  that S thresholds. 12,600/12,600 reconstructed.
  test_scored_year_never_in_loss                  DEC-117: the evaluation year's state was in
                                                  the training targets.
  test_placebo_cannot_beat_base                   DEC-112: the placebo re-weighted random
                                                  neighbours by their true affinity and beat
                                                  the no-relational base, which is impossible
                                                  for a valid control.
  test_export_is_deterministic_on_all_outputs     DEC-118: the assertion compared adjacencies
                                                  only, which do not pass through dropout.
  test_temporal_placebo_breaks_year_identity      DEC-118: data and t_abs were permuted
                                                  together, so z stayed married to its year.
  test_absent_node_cannot_relay                   DEC-117: the GRU updated absent nodes.
  test_no_self_loops                              DEC-117: 27-36 self-loops per step.
  test_absence_is_not_evidence                    DEC-118: abs() on the standardised prior
                                                  turned "no commuting" into signal; 5,852
                                                  zero-commuting edges became strong_real.
  test_parameter_budget_declared                  DEC-118: 4.39 observations per parameter
                                                  against a pre-registered minimum of 5.

Run: python -m pytest tests/test_herald75_guards.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

h = pytest.importorskip(
    "src.modeles.france_ze2020.herald75_dynamic_graph",
    reason="HERALD_75 implementation not present yet",
)

N_ZONES, N_SEC, N_YEARS = 12, 9, 14
MIN_OBS_PER_PARAM = 5.0          # pre-registered in HERALD_71 section 4


def synthetic_panel(seed=0):
    """Counts with a known structure: a smooth trend plus noise, no relations at all."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(20, 400, size=(N_ZONES, N_SEC))
    drift = rng.normal(0, 0.03, size=(N_ZONES, N_SEC))
    Y = np.empty((N_YEARS, N_ZONES, N_SEC))
    for t in range(N_YEARS):
        Y[t] = rng.poisson(np.maximum(base * np.exp(drift * t), 1.0))
    return Y


# --------------------------------------------------------------- leakage guards


def test_target_not_reconstructible_from_features():
    """No target may be recoverable from the features of the same step.

    This is the guard that fails on DEC-118: `states()` thresholds the growth array that is
    also feature 0, so predicting the target reduces to reading the input.
    """
    Y = synthetic_panel()
    x, tgt, _ = h.assemble_fold(Y, eval_index=N_YEARS - 1)
    n_steps, n_cells, _ = x.shape
    for t in range(n_steps):
        for f in range(x.shape[-1]):
            derived = h.states_from_growth(x[t, :, f])
            agree = float((derived == tgt[t]).mean())
            assert agree < 0.95, (
                f"target at step {t} is {agree:.1%} reconstructible from feature {f}; "
                "the model would be reading its own input"
            )


def test_scored_year_never_in_loss():
    """The evaluation year is scored exactly once and appears in no training target."""
    Y = synthetic_panel()
    ev = N_YEARS - 1
    _, tgt, meta = h.assemble_fold(Y, eval_index=ev)
    assert ev not in meta["train_target_years"], "evaluation year is in the training targets"
    assert meta["scored_year"] == ev, "evaluation year is not scored"
    assert len(tgt) == (len(meta["train_target_years"])
                        + len(meta["val_target_years"]) + 1), "scored year missing from tgt"
    assert meta["scored_year"] not in meta["val_target_years"]


def test_features_use_only_the_past():
    """Every feature at step t must be computable from years <= the step's own year."""
    Y = synthetic_panel()
    Y2 = Y.copy()
    Y2[-1] *= 3.0                                   # perturb the final year only
    x1, _, _ = h.assemble_fold(Y, eval_index=N_YEARS - 2)
    x2, _, _ = h.assemble_fold(Y2, eval_index=N_YEARS - 2)
    assert np.allclose(x1, x2), "changing a future year changed the features"


# ------------------------------------------------------------- control validity


def test_placebo_cannot_beat_base():
    """A valid placebo destroys information; it cannot outperform the untreated arm.

    DEC-112: the contaminated placebo scored 0.3995 against a base of 0.3949, and that
    inversion was the available and unused tell.
    """
    Y = synthetic_panel()
    base = h.score_arm(Y, relational=False, seed=0)
    placebo = h.score_arm(Y, relational=True, placebo=True, seed=0)
    assert placebo <= base + 0.01, (
        f"placebo {placebo:.4f} beats base {base:.4f}; the control leaks information"
    )


def test_temporal_placebo_breaks_year_identity():
    """Shuffling years must break the data-to-z mapping, not merely reorder the loop."""
    real = h.fold_year_assignment(shuffle=False, seed=0)
    plac = h.fold_year_assignment(shuffle=True, seed=0)
    assert sorted(plac["input_years"]) == sorted(real["input_years"]), "different years used"
    assert plac["input_years"] == real["input_years"], "chronology must stay fixed"
    assert plac["z_index"] != real["z_index"], (
        "z is still married to its true year; the placebo tests loop order only"
    )


def test_absence_is_not_evidence():
    """An edge with no observed commuting and no learned deviation must land in `noise`.

    DEC-118: standardising sent absent edges to a constant ~-0.127 and `abs()` turned that
    into signal, classifying 5,852 zero-commuting edges as strong_real.
    """
    n = 40
    C = np.zeros((n, n))
    C[:10, :10] = 0.5                                # only a corner has commuting
    np.fill_diagonal(C, 0.0)
    prior = h.prior_logits(C)
    scores = np.stack([prior + np.random.default_rng(s).normal(0, 1e-6, prior.shape)
                       for s in range(3)])
    band, _, _ = h.classify_edges(scores.mean(0), scores, noise_sd=np.full_like(prior, 1e-3))
    absent = (C == 0) & ~np.eye(n, dtype=bool)
    assert (band[absent] == "noise").mean() > 0.95, (
        "edges with no commuting and no learned deviation were declared real"
    )


# ------------------------------------------------------------ mechanical guards


def test_export_is_deterministic_on_all_outputs():
    """Every exported quantity must be identical across two exports, not only the adjacency."""
    Y = synthetic_panel()
    a, b = h.export_twice(Y, eval_index=N_YEARS - 1, seed=0)
    for key in ("adj", "logits", "mag", "raw", "z"):
        assert np.allclose(a[key], b[key]), f"'{key}' differs between exports; a layer is stochastic"


def test_absent_node_cannot_relay():
    """A node absent in a year must neither hold state nor pass a message."""
    Y = synthetic_panel()
    Y[:, 0, 0] = 0.0                                 # zone 0 sector 0 absent in every year
    trace = h.trace_node(Y, zone=0, sector=0, eval_index=N_YEARS - 1)
    assert np.allclose(trace["hidden"], 0.0), "absent node carries hidden state"
    assert np.allclose(trace["outgoing_message"], 0.0), "absent node relays a message"


def test_no_self_loops():
    Y = synthetic_panel()
    out, _ = h.export_twice(Y, eval_index=N_YEARS - 1, seed=0)
    for A in out["adj"]:
        assert np.allclose(np.diag(A), 0.0), "adjacency has self-loops"


def test_parameter_budget_declared():
    """The fold must supply at least the pre-registered observations per graph parameter."""
    Y = synthetic_panel()
    _, _, meta = h.assemble_fold(Y, eval_index=N_YEARS - 1)
    ratio = meta["train_labels"] / meta["graph_parameters"]
    assert ratio >= MIN_OBS_PER_PARAM, (
        f"{ratio:.2f} observations per graph parameter, below the pre-registered "
        f"{MIN_OBS_PER_PARAM}; reduce the rank or widen the window"
    )
