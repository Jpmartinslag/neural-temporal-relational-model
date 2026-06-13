"""
evaluate_imputation.py

Evaluation metrics for the HERALD synthetic benchmark (DEC-039).
All metrics are computed ONLY on masked (hidden) cells.
"""

from __future__ import annotations

import dataclasses

import numpy as np
from sklearn.metrics import roc_auc_score


@dataclasses.dataclass
class ImputationMetrics:
    mae: float
    rmse: float
    pearson_r: float
    sign_accuracy: float       # % of hidden cells with correct sign
    n_evaluated: int           # number of masked cells evaluated


@dataclasses.dataclass
class EdgeRecoveryMetrics:
    auc: float                 # AUC of learned weights vs true edges
    precision_at_k: float      # precision at k = n_true_edges
    recall_at_k: float
    f1_at_k: float
    sign_accuracy: float       # fraction of true edges with correct sign
    n_true_edges: int


@dataclasses.dataclass
class CalibrationMetrics:
    coverage_50: float         # empirical coverage of 50% interval
    coverage_80: float
    coverage_90: float
    mean_width_90: float       # mean width of 90% interval (sharpness)


def compute_imputation_metrics(
    true_panel: np.ndarray,       # (n_T, n_S, n_Y) — ground truth
    imputed_panel: np.ndarray,    # (n_T, n_S, n_Y) — predictions
    mask: np.ndarray,             # (n_T, n_S, n_Y) — 1=observed, 0=hidden
) -> ImputationMetrics:
    """Evaluate at hidden positions only."""
    hidden = mask == 0
    if hidden.sum() == 0:
        return ImputationMetrics(0.0, 0.0, 1.0, 1.0, 0)

    true_h = true_panel[hidden]
    pred_h = imputed_panel[hidden]
    err = true_h - pred_h

    mae = float(np.abs(err).mean())
    rmse = float(np.sqrt((err ** 2).mean()))

    # Pearson r
    if len(true_h) > 1 and true_h.std() > 1e-10 and pred_h.std() > 1e-10:
        pearson_r = float(np.corrcoef(true_h, pred_h)[0, 1])
    else:
        pearson_r = float("nan")

    # Sign accuracy (both must be non-zero)
    nonzero = (true_h != 0)
    if nonzero.sum() > 0:
        sign_acc = float((np.sign(true_h[nonzero]) == np.sign(pred_h[nonzero])).mean())
    else:
        sign_acc = float("nan")

    return ImputationMetrics(mae, rmse, pearson_r, sign_acc, int(hidden.sum()))


def compute_edge_recovery_metrics(
    true_relations: list,                 # list of TrueRelation
    n_sectors: int,
    learned_attn: np.ndarray,            # (n_S, n_S) learned attention weights
) -> EdgeRecoveryMetrics:
    """
    Compare learned sector attention weights to ground-truth directed edges.
    Treat the problem as binary classification: edge vs no-edge.
    """
    # Build ground-truth binary matrix
    true_adj = np.zeros((n_sectors, n_sectors))
    true_sign = {}
    for rel in true_relations:
        if rel.source_sector < n_sectors and rel.target_sector < n_sectors:
            true_adj[rel.source_sector, rel.target_sector] = 1
            true_sign[(rel.source_sector, rel.target_sector)] = rel.weight

    # Flatten (exclude diagonal)
    rows, cols = np.where(~np.eye(n_sectors, dtype=bool))
    y_true = true_adj[rows, cols]
    y_score = learned_attn[rows, cols]

    n_true = int(y_true.sum())
    if n_true == 0 or n_true == len(y_true):
        auc = float("nan")
    else:
        try:
            auc = float(roc_auc_score(y_true, y_score))
        except Exception:
            auc = float("nan")

    # Precision/recall at k = n_true_edges
    k = max(1, n_true)
    top_k_idx = np.argsort(y_score)[::-1][:k]
    pred_binary = np.zeros(len(y_true))
    pred_binary[top_k_idx] = 1

    tp = float((pred_binary * y_true).sum())
    precision = tp / k
    recall = tp / max(n_true, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)

    # Sign accuracy on truly present edges
    sign_acc = float("nan")
    sign_hits = []
    for (s, t), true_w in true_sign.items():
        learned_w = learned_attn[s, t]
        # Map learned weight relative to row mean: positive = above average
        row_mean = learned_attn[s].mean()
        learned_sign = 1 if learned_w > row_mean else -1
        true_sign_val = 1 if true_w > 0 else -1
        sign_hits.append(learned_sign == true_sign_val)
    if sign_hits:
        sign_acc = float(np.mean(sign_hits))

    return EdgeRecoveryMetrics(auc, precision, recall, f1, sign_acc, n_true)


def compute_calibration_metrics(
    true_panel: np.ndarray,       # (n_T, n_S, n_Y)
    pred_mean: np.ndarray,        # (n_T, n_S, n_Y)
    pred_std: np.ndarray,         # (n_T, n_S, n_Y)
    mask: np.ndarray,             # 1=observed, 0=hidden
) -> CalibrationMetrics:
    """
    Compute coverage at 50%, 80%, 90% intervals for hidden cells.
    Assumes Gaussian predictive distribution: mean ± z*std.
    """
    hidden = mask == 0
    if hidden.sum() == 0:
        return CalibrationMetrics(float("nan"), float("nan"), float("nan"), float("nan"))

    true_h = true_panel[hidden]
    mu = pred_mean[hidden]
    sigma = pred_std[hidden]

    if sigma.max() < 1e-10:
        return CalibrationMetrics(float("nan"), float("nan"), float("nan"), float("nan"))

    def coverage_at_level(z: float) -> float:
        lower = mu - z * sigma
        upper = mu + z * sigma
        return float(((true_h >= lower) & (true_h <= upper)).mean())

    cov_50 = coverage_at_level(0.674)
    cov_80 = coverage_at_level(1.282)
    cov_90 = coverage_at_level(1.645)
    width_90 = float((2 * 1.645 * sigma).mean())

    return CalibrationMetrics(cov_50, cov_80, cov_90, width_90)


def check_no_leakage(panel: np.ndarray, mask: np.ndarray) -> dict:
    """
    Verify that temporal features are causal (never use future values for year y).

    Strategy: modify the panel at year y+1 for all hidden cells, recompute
    temporal features for year y, and verify they are unchanged.
    This is a property of the feature function, not the model.
    """
    from src.modeles.synthetic.imputation_baselines import _build_temporal_features
    import numpy as np

    n_T, n_S, n_Y = panel.shape
    if n_Y < 3:
        return {"leakage_check": "skipped_too_short", "passed": True}

    # Perturb future values and check that causal features at past year are unchanged
    panel_perturbed = panel.copy()
    check_year = n_Y // 2
    # Perturb year check_year + 1 with large values
    panel_perturbed[:, :, check_year + 1:] += 999.0

    feats_original = _build_temporal_features(panel, mask).reshape(n_T, n_S, n_Y, 7)
    feats_perturbed = _build_temporal_features(panel_perturbed, mask).reshape(n_T, n_S, n_Y, 7)

    # Features at year <= check_year should be identical despite future perturbation
    diff_past = np.abs(
        feats_original[:, :, :check_year + 1, :] - feats_perturbed[:, :, :check_year + 1, :]
    ).max()

    passed = bool(diff_past < 1e-6)
    return {
        "leakage_check": "causal_temporal_features",
        "max_diff_at_past_years": float(diff_past),
        "perturbed_future_years": list(range(check_year + 1, n_Y)),
        "passed": passed,
    }
