"""
utility_target.py — Oracle utility target computation for DEC-054.

The oracle correction computes what the graph contribution WOULD be if we
knew the true relations. This is used to supervise the UtilityGate during
training, teaching it to open where graph information is genuinely useful.

FROZEN before results (DEC-054).
"""

from __future__ import annotations

import numpy as np

# ── Frozen constants ──────────────────────────────────────────────────────────
UTILITY_THRESHOLD_TRAIN: float = 0.0   # any positive gain = useful
LAMBDA_RELATION: float = 0.05          # shared relation head loss weight


def compute_oracle_correction(
    panel: np.ndarray,        # (n_T, n_S, n_Y)
    obs_mask: np.ndarray,     # (n_T, n_S, n_Y) 1=observed
    true_relations: list,     # list[TrueRelation]
) -> np.ndarray:
    """
    Compute the oracle graph correction from true_relations.

    For each relation r:
        src = panel[:, r.source_sector, y-r.lag] * obs_mask[:, r.source_sector, y-r.lag]
        if r.nonlinear: src = tanh(src)
        correction[:, r.target_sector, y] += r.weight * src

    The obs_mask zeroes out unobserved source values, ensuring no future
    information is used beyond what is specified by the lag.

    For y < r.lag: correction is 0 (no history available yet).

    Returns
    -------
    correction : np.ndarray, shape (n_T, n_S, n_Y), float32
    """
    n_T, n_S, n_Y = panel.shape
    correction = np.zeros((n_T, n_S, n_Y), dtype=np.float32)

    for r in true_relations:
        src_s = r.source_sector
        tgt_s = r.target_sector
        lag = r.lag
        weight = r.weight
        nonlinear = r.nonlinear

        # Validate indices
        if not (0 <= src_s < n_S and 0 <= tgt_s < n_S and src_s != tgt_s):
            continue

        for y in range(lag, n_Y):
            # Source values at (y - lag), masked to observed only
            src_vals = (
                panel[:, src_s, y - lag].astype(np.float32)
                * obs_mask[:, src_s, y - lag].astype(np.float32)
            )
            if nonlinear:
                src_vals = np.tanh(src_vals)
            correction[:, tgt_s, y] += weight * src_vals

    return correction


def make_utility_target(
    panel: np.ndarray,           # (n_T, n_S, n_Y)
    obs_mask: np.ndarray,        # (n_T, n_S, n_Y) 1=observed
    y_temporal: np.ndarray,      # (n_T, n_S, n_Y) temporal prediction
    y_oracle: np.ndarray,        # y_temporal + oracle_correction
    loss_mask: np.ndarray,       # (n_T, n_S, n_Y) float32: 1=missing (training cells)
    threshold: float = UTILITY_THRESHOLD_TRAIN,
) -> tuple[np.ndarray, float, dict]:
    """
    Compute binary utility target for gate supervision.

    A cell is "useful" if oracle prediction reduces absolute error vs temporal:
        utility_gain = |panel - y_temporal| - |panel - y_oracle|
        utility_target = (utility_gain > threshold) AND is_training_missing_cell

    Parameters
    ----------
    panel       : true values
    obs_mask    : 1=observed (training cells are where loss_mask=1, i.e. obs_mask=0)
    y_temporal  : backbone prediction
    y_oracle    : oracle-corrected prediction (y_temporal + oracle_correction)
    loss_mask   : 1=missing training cell (the cells we supervise the gate on)
    threshold   : minimum utility gain to count as useful (default 0.0)

    Returns
    -------
    utility_target : np.ndarray float32, shape (n_T, n_S, n_Y)
                     binary {0, 1}, only non-zero on loss_mask cells
    prevalence     : float, fraction of loss_mask cells that are useful
    stats          : dict with mean_gain, frac_positive, n_useful, n_total
    """
    panel_f = panel.astype(np.float32)
    y_temporal_f = y_temporal.astype(np.float32)
    y_oracle_f = y_oracle.astype(np.float32)
    loss_mask_f = loss_mask.astype(np.float32)

    # Utility gain: positive = oracle helps
    utility_gain = np.abs(panel_f - y_temporal_f) - np.abs(panel_f - y_oracle_f)

    # Binary target: useful where gain > threshold AND it is a training missing cell
    is_useful = (utility_gain > threshold).astype(np.float32)
    utility_target = (is_useful * loss_mask_f).astype(np.float32)

    # Stats (only on loss_mask cells)
    n_total = int(loss_mask_f.sum())
    n_useful = int(utility_target.sum())
    prevalence = n_useful / n_total if n_total > 0 else 0.0

    gain_at_missing = utility_gain[loss_mask_f > 0.5] if n_total > 0 else np.array([0.0])
    stats = {
        "mean_gain": float(gain_at_missing.mean()),
        "frac_positive": float((gain_at_missing > threshold).mean()),
        "n_useful": n_useful,
        "n_total": n_total,
    }

    return utility_target, prevalence, stats


def pos_weight_for_utility(
    utility_target: np.ndarray,
    loss_mask: np.ndarray,
) -> float:
    """
    Compute positive class weight for BCE loss balancing.

    Returns n_neg / n_pos, clipped to [1, 20].
    """
    mask = loss_mask > 0.5
    if not mask.any():
        return 1.0

    tgt_at_mask = utility_target[mask]
    n_pos = float(tgt_at_mask.sum())
    n_neg = float((1.0 - tgt_at_mask).sum())

    if n_pos < 1.0:
        return 20.0  # no positives → max weight

    pw = n_neg / n_pos
    return float(np.clip(pw, 1.0, 20.0))
