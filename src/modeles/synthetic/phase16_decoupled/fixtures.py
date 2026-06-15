"""
fixtures.py — Controlled micro-panels for functional testing (DEC-053).

Each fixture returns (panel, obs_mask, true_relations, sector_adj, territory_adj, name).
All panels: n_T=5 territories, n_S=3 sectors, n_Y=15 years.
TrueRelation is imported from the data generator to keep consistent types.
"""

from __future__ import annotations

import numpy as np
from src.data.synthetic.generate_herald_synthetic import TrueRelation

N_T, N_S, N_Y = 5, 3, 15
_RNG_SEED = 42


def _base_ar(rng: np.random.Generator, coef: float = 0.6, sigma: float = 0.2) -> np.ndarray:
    """Simple AR(1) panel (n_T, n_S, n_Y)."""
    panel = np.zeros((N_T, N_S, N_Y))
    panel[:, :, 0] = rng.standard_normal((N_T, N_S))
    for y in range(1, N_Y):
        panel[:, :, y] = coef * panel[:, :, y - 1] + rng.normal(0, sigma, (N_T, N_S))
    return panel


def _mcar_mask(rng: np.random.Generator, rate: float = 0.30) -> np.ndarray:
    """MCAR mask: 1=observed, 0=missing."""
    return (rng.random((N_T, N_S, N_Y)) > rate).astype(np.float32)


def _symm_adj(true_relations: list) -> np.ndarray:
    """Symmetrised binary sector adj from true_relations (mimics _sector_adj_from_relations)."""
    adj = np.zeros((N_S, N_S), dtype=np.float32)
    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        adj[t, s] = 1.0
        adj[s, t] = 1.0  # false reverse added by symmetrisation
    return adj


def _terr_adj() -> np.ndarray:
    """Trivial territory adjacency (fully connected, row-normalised)."""
    adj = np.ones((N_T, N_T), dtype=np.float32) - np.eye(N_T, dtype=np.float32)
    return adj / adj.sum(axis=1, keepdims=True).clip(min=1)


def make_f1_useful_graph() -> tuple:
    """
    F1 — Graph is useful.
    Sector 0 drives sector 1 at lag 1 with strong weight.
    Sector 1 has weak AR dynamics; knowing sector 0 history matters.
    Gate should open for sector 1 predictions.
    """
    rng = np.random.default_rng(_RNG_SEED)
    panel = _base_ar(rng, coef=0.7, sigma=0.1)   # sector 0 clean AR

    # Sector 1 = weak AR + strong sector-0 lag-1 influence
    for y in range(1, N_Y):
        panel[:, 1, y] = (
            0.2 * panel[:, 1, y - 1]
            + 0.9 * panel[:, 0, y - 1]     # strong cross-sector signal
            + rng.normal(0, 0.05, N_T)
        )
    # Sector 2 is pure AR, no graph involvement
    obs_mask = _mcar_mask(rng, rate=0.25)
    obs_mask[:, 1, -4:] = 0   # hide last 4 years of sector 1 to force reconstruction

    rels = [TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.9, nonlinear=False)]
    return panel, obs_mask, rels, _symm_adj(rels), _terr_adj(), "F1_useful_graph"


def make_f2_useless_graph() -> tuple:
    """
    F2 — Graph is useless.
    All sectors are independent AR(1), no cross-sector relations.
    Gate should remain near zero; gated ≈ temporal-only.
    """
    rng = np.random.default_rng(_RNG_SEED + 1)
    panel = _base_ar(rng, coef=0.6, sigma=0.3)
    obs_mask = _mcar_mask(rng, rate=0.30)
    rels: list = []
    return panel, obs_mask, rels, _symm_adj(rels), _terr_adj(), "F2_useless_graph"


def make_f3_negative_relation() -> tuple:
    """
    F3 — Negative relation.
    Sector 0 DECREASES sector 1 at lag 1 (weight = -0.8).
    Sign should be recovered (sign_logit < 0 after training).
    """
    rng = np.random.default_rng(_RNG_SEED + 2)
    panel = _base_ar(rng, coef=0.5, sigma=0.1)
    for y in range(1, N_Y):
        panel[:, 1, y] = (
            0.3 * panel[:, 1, y - 1]
            - 0.8 * panel[:, 0, y - 1]     # negative weight
            + rng.normal(0, 0.05, N_T)
        )
    obs_mask = _mcar_mask(rng, rate=0.30)
    rels = [TrueRelation(source_sector=0, target_sector=1, lag=1, weight=-0.8, nonlinear=False)]
    return panel, obs_mask, rels, _symm_adj(rels), _terr_adj(), "F3_negative_relation"


def make_f4_lag2_relation() -> tuple:
    """
    F4 — Lag-2 relation.
    Sector 0 affects sector 1 at lag 2, NOT lag 1.
    lag_logit[1,0] should be negative after training (lag=2 preferred).
    """
    rng = np.random.default_rng(_RNG_SEED + 3)
    panel = _base_ar(rng, coef=0.5, sigma=0.1)
    for y in range(2, N_Y):
        panel[:, 1, y] = (
            0.2 * panel[:, 1, y - 1]
            + 0.8 * panel[:, 0, y - 2]     # lag-2 signal, not lag-1
            + rng.normal(0, 0.05, N_T)
        )
    obs_mask = _mcar_mask(rng, rate=0.30)
    rels = [TrueRelation(source_sector=0, target_sector=1, lag=2, weight=0.8, nonlinear=False)]
    return panel, obs_mask, rels, _symm_adj(rels), _terr_adj(), "F4_lag2_relation"


def make_f5_regime_window() -> tuple:
    """
    F5 — Regime window.
    Relation is active only during years 5–10 (structural break before and after).
    Gate should be larger in years 5–10 and smaller outside.
    """
    rng = np.random.default_rng(_RNG_SEED + 4)
    panel = _base_ar(rng, coef=0.5, sigma=0.15)
    for y in range(1, N_Y):
        cross = panel[:, 0, y - 1] * (0.8 if 5 <= y <= 10 else 0.0)
        panel[:, 1, y] = 0.3 * panel[:, 1, y - 1] + cross + rng.normal(0, 0.1, N_T)
    obs_mask = _mcar_mask(rng, rate=0.30)
    rels = [TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.8, nonlinear=False)]
    return panel, obs_mask, rels, _symm_adj(rels), _terr_adj(), "F5_regime_window"


def make_f6_asymmetric_directed() -> tuple:
    """
    F6 — Asymmetric directed.
    Only sector 0 → sector 1 exists. Sector 1 → sector 0 does NOT exist.
    The symmetric sector_adj adds the false reverse B→A.
    head should produce presence_logit[1,0] >> presence_logit[0,1].
    """
    rng = np.random.default_rng(_RNG_SEED + 5)
    panel = _base_ar(rng, coef=0.5, sigma=0.1)
    for y in range(1, N_Y):
        panel[:, 1, y] = (
            0.2 * panel[:, 1, y - 1]
            + 0.85 * panel[:, 0, y - 1]    # only 0→1
            + rng.normal(0, 0.05, N_T)
        )
    # Sector 0 is NOT affected by sector 1 (only AR)
    obs_mask = _mcar_mask(rng, rate=0.30)
    rels = [TrueRelation(source_sector=0, target_sector=1, lag=1, weight=0.85, nonlinear=False)]
    # Note: _symm_adj adds the false reverse [0,1]=[source=1,target=0] in the adj matrix
    return panel, obs_mask, rels, _symm_adj(rels), _terr_adj(), "F6_asymmetric_directed"


ALL_FIXTURES = [
    make_f1_useful_graph,
    make_f2_useless_graph,
    make_f3_negative_relation,
    make_f4_lag2_relation,
    make_f5_regime_window,
    make_f6_asymmetric_directed,
]
