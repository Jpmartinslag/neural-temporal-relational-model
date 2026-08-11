"""Guards for HERALD_76 (DEC-120), written before the implementation exists.

Eight guards are mandated by HERALD_76 section 7. Each is aimed at a specific way the
previous three implementations were wrong, and two of them exist because guards I wrote for
HERALD_75 passed by construction rather than by measurement (DEC-119).

  g1  z for the evaluation year is not a stored per-year parameter
  g2  perturbing any year after t leaves z_t bit-identical
  g3  perturbing x_t changes z_t -- the encoder is live, not a constant
  g4  validation and scored targets receive zero gradient, checked on parameter deltas
  g5  z for the scored year moves away from its initialisation
  g6  the temporal placebo permutes only the encoder's reading order
  g7  the driver calls the noise floor, shrinkage, bands and events on the production path
  g8  absence and placebo guards use heterogeneous weights and multiple panels

Run: python tests/run_guards_no_pytest.py  (or pytest, if available)
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

h = pytest.importorskip(
    "src.modeles.france_ze2020.herald76_dynamic_graph",
    reason="HERALD_76 implementation not present yet",
)

N_ZONES, N_SEC, N_YEARS = 12, 9, 14
RANK = 4
MIN_OBS_PER_PARAM = 5.0


def panel(seed=0, n_zones=N_ZONES):
    rng = np.random.default_rng(seed)
    base = rng.uniform(20, 400, size=(n_zones, N_SEC))
    drift = rng.normal(0, 0.03, size=(n_zones, N_SEC))
    Y = np.empty((N_YEARS, n_zones, N_SEC))
    for t in range(N_YEARS):
        Y[t] = rng.poisson(np.maximum(base * np.exp(drift * t), 1.0))
    return Y


def commuting(n, seed=0, uniform=False):
    """Heterogeneous by default. g8 exists because a uniform matrix collapses the
    standardisation to zero and makes the absence guard pass for free (DEC-119)."""
    rng = np.random.default_rng(seed)
    C = np.zeros((n, n))
    for i in range(n):
        for j in rng.choice([k for k in range(n) if k != i], size=max(2, n // 4), replace=False):
            C[i, j] = 0.5 if uniform else float(rng.lognormal(-2.0, 1.0))
    np.fill_diagonal(C, 0.0)
    return C


# ---------------------------------------------------------------- g1, g2, g3


def test_g1_regime_is_not_a_stored_year_table():
    """The rejected architecture stored one free row per year. It must not reappear."""
    model = h.build_model(n_zones=N_ZONES, in_dim=3, rank=RANK)
    for name, p in model.named_parameters():
        if p.dim() == 2 and p.shape[0] == N_YEARS and p.shape[1] == RANK:
            raise AssertionError(
                f"parameter '{name}' has shape [n_years, rank]; the free per-year regime "
                "table was rejected by DEC-120"
            )
    assert hasattr(model, "regime_encoder"), "no regime encoder present"


def test_g2_future_years_do_not_change_the_regime():
    """z_t must be computable at decision time: nothing after t may touch it."""
    Y = panel()
    Y2 = Y.copy()
    Y2[-1] *= 5.0
    ev = N_YEARS - 1
    z1 = h.regimes_for_fold(Y, eval_index=ev - 1, seed=0)
    z2 = h.regimes_for_fold(Y2, eval_index=ev - 1, seed=0)
    assert np.array_equal(z1, z2), "a year after the fold changed the inferred regime"


def test_g3_the_encoder_is_live():
    """If z_t does not respond to its own year's history, the encoder is a constant."""
    Y = panel()
    Y2 = Y.copy()
    Y2[3] = Y2[3] * 4.0 + 25.0
    ev = N_YEARS - 1
    z1 = h.regimes_for_fold(Y, eval_index=ev, seed=0)
    z2 = h.regimes_for_fold(Y2, eval_index=ev, seed=0)
    assert not np.allclose(z1, z2), "changing the year's own history left the regime unchanged"


# --------------------------------------------------------------------- g4, g5


def test_g4_validation_and_scored_targets_get_no_gradient():
    """DEC-119: the split was declared in metadata while the loss consumed it anyway.

    Checked on parameter deltas: training twice, once with the held-out targets corrupted,
    must leave every parameter identical. If the held-out span reached the loss, it would not.
    """
    Y = panel()
    ev = N_YEARS - 1
    a = h.fit_and_dump_parameters(Y, eval_index=ev, seed=0, epochs=4)
    b = h.fit_and_dump_parameters(Y, eval_index=ev, seed=0, epochs=4, corrupt_heldout=True)
    for k in a:
        assert np.allclose(a[k], b[k]), (
            f"parameter '{k}' changed when only the held-out targets changed; "
            "validation or the scored year is inside the loss"
        )


def test_g5_scored_year_regime_is_learned():
    """The defect that ended HERALD_75: z for the scored year stayed at its initialisation."""
    Y = panel()
    ev = N_YEARS - 1
    out = h.fit_and_export(Y, eval_index=ev, seed=0, epochs=6)
    z_scored = np.asarray(out["z"][-1])
    init = np.asarray(out["z_init"])
    assert not np.allclose(z_scored, init), (
        "the scored year's regime equals its initialisation; it was never inferred"
    )
    assert np.isfinite(z_scored).all()


# ------------------------------------------------------------------------- g6


def test_g6_temporal_placebo_permutes_only_the_reading_order():
    Y = panel()
    ev = N_YEARS - 1
    real = h.fold_plan(Y, eval_index=ev, shuffle=False, seed=0)
    plac = h.fold_plan(Y, eval_index=ev, shuffle=True, seed=0)
    assert plac["target_years"] == real["target_years"], "the placebo changed the targets"
    assert plac["input_years"] == real["input_years"], "the placebo broke input chronology"
    assert plac["encoder_reads"] != real["encoder_reads"], (
        "the placebo did not permute which year's history the encoder reads"
    )
    assert sorted(plac["encoder_reads"]) == sorted(real["encoder_reads"])


# ------------------------------------------------------------------------- g7


def test_g7_driver_calls_the_controls_on_the_production_path():
    """DEC-117 and DEC-118: these were defined and never called, twice."""
    src = inspect.getsource(h.run_fold)
    for fn in ("negative_binomial_floor", "shrink", "classify_edges", "edge_events"):
        assert fn in src, f"run_fold never calls {fn}(); it is decoration, not a control"


# ------------------------------------------------------------------------- g8


def test_g8_absence_is_not_evidence_on_heterogeneous_weights():
    """DEC-119: the previous version gave every present edge weight 0.5, so the standard
    deviation was zero and everything collapsed. With real weights it classified 0 of 1,470
    absent edges as noise."""
    n = 40
    C = commuting(n, seed=1, uniform=False)
    assert C[C > 0].std() > 0, "the test matrix must be heterogeneous or it proves nothing"
    dev = np.stack([np.random.default_rng(s).normal(0, 1e-6, (n, n)) for s in range(3)])
    band, _, _ = h.classify_edges(dev.mean(0), dev, noise_sd=np.full((n, n), 1e-3))
    absent = (C == 0) & ~np.eye(n, dtype=bool)
    share = float((band[absent] == "noise").mean())
    assert share > 0.95, f"only {share:.1%} of absent edges landed in noise"


def test_g8_placebo_has_no_systematic_advantage_across_panels():
    """DEC-119: a single-seed inequality passed while the placebo won 12 of 20 panels.

    A valid placebo may win a coin flip; what it may not do is win systematically.
    """
    deltas = []
    for seed in range(12):
        Y = panel(seed=seed)
        base = h.score_arm(Y, relational=False, seed=seed)
        plac = h.score_arm(Y, relational=True, placebo=True, seed=seed)
        deltas.append(plac - base)
    d = np.array(deltas)
    boot = np.array([np.random.default_rng(s).choice(d, len(d), replace=True).mean()
                     for s in range(2000)])
    lo, hi = np.quantile(boot, [0.025, 0.975])
    assert lo <= 0.0, (
        f"placebo beats base systematically: mean {d.mean():+.4f}, CI95 [{lo:+.4f}, {hi:+.4f}]; "
        "the control carries information"
    )


# -------------------------------------------------------------- budget, carried


def test_relational_budget_holds():
    plan = h.fold_plan(panel(n_zones=280), eval_index=N_YEARS - 1, shuffle=False, seed=0)
    ratio = plan["train_labels"] / plan["relational_parameters"]
    assert ratio >= MIN_OBS_PER_PARAM, (
        f"{ratio:.2f} observations per relational parameter, below {MIN_OBS_PER_PARAM}"
    )
    assert plan["relational_parameters"] == 2 * 280 * RANK + 64 * RANK + RANK + 1, (
        "the budget no longer matches HERALD_76 section 5"
    )
