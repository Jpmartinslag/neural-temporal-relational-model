"""
evaluate_imputation.py

Evaluation metrics for the HERALD synthetic benchmark (DEC-039/DEC-040).
All imputation metrics are computed ONLY on masked (hidden) cells.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
)


@dataclasses.dataclass
class ImputationMetrics:
    mae: float
    rmse: float
    pearson_r: float
    spearman_r: float          # rank correlation (robust to outliers)
    sign_accuracy: float       # % of hidden cells with correct sign
    n_evaluated: int           # number of masked cells evaluated


@dataclasses.dataclass
class EdgeRecoveryMetrics:
    auc: float                 # ROC-AUC of learned weights vs true edges
    precision_at_k: float      # precision at k = n_true_edges
    recall_at_k: float
    f1_at_k: float
    sign_accuracy: float       # fraction of true edges with correct sign
    lag_accuracy: float        # fraction of true edges with correct lag recovered
    false_positive_rate: float # FPR at k = n_true_edges
    n_true_edges: int


@dataclasses.dataclass
class CalibrationMetrics:
    coverage_50: float         # empirical coverage of 50% interval
    coverage_80: float
    coverage_90: float
    mean_width_90: float       # mean width of 90% interval (sharpness)


@dataclasses.dataclass
class StateMetrics:
    """Economic regime classification accuracy at hidden cells."""
    macro_f1: float
    balanced_accuracy: float
    aucpr_rare: float          # AUCPR for crisis (3) + recovery (4) classes
    n_evaluated: int


@dataclasses.dataclass
class BreakdownMetrics:
    """Per-slice MAE breakdown."""
    dimension: str             # 'sector', 'territory', or 'regime'
    labels: list
    mae_per_label: list[float]
    n_per_label: list[int]


def compute_imputation_metrics(
    true_panel: np.ndarray,       # (n_T, n_S, n_Y) — ground truth
    imputed_panel: np.ndarray,    # (n_T, n_S, n_Y) — predictions
    mask: np.ndarray,             # (n_T, n_S, n_Y) — 1=observed, 0=hidden
) -> ImputationMetrics:
    """Evaluate at hidden positions only."""
    hidden = mask == 0
    if hidden.sum() == 0:
        return ImputationMetrics(0.0, 0.0, 1.0, 1.0, 1.0, 0)

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

    # Spearman r
    if len(true_h) > 1:
        sr, _ = spearmanr(true_h, pred_h)
        spearman_r = float(sr) if not np.isnan(sr) else float("nan")
    else:
        spearman_r = float("nan")

    # Sign accuracy
    nonzero = (true_h != 0)
    if nonzero.sum() > 0:
        sign_acc = float((np.sign(true_h[nonzero]) == np.sign(pred_h[nonzero])).mean())
    else:
        sign_acc = float("nan")

    return ImputationMetrics(mae, rmse, pearson_r, spearman_r, sign_acc, int(hidden.sum()))


def compute_breakdown_metrics(
    true_panel: np.ndarray,
    imputed_panel: np.ndarray,
    mask: np.ndarray,
    regimes: np.ndarray | None = None,
) -> dict[str, BreakdownMetrics]:
    """MAE breakdown by sector, territory, and regime (if provided)."""
    n_T, n_S, n_Y = true_panel.shape
    hidden = mask == 0
    results: dict[str, BreakdownMetrics] = {}

    # By sector
    mae_s, n_s = [], []
    for s in range(n_S):
        h = hidden[:, s, :]
        if h.sum() == 0:
            mae_s.append(float("nan"))
            n_s.append(0)
        else:
            mae_s.append(float(np.abs(true_panel[:, s, :][h] - imputed_panel[:, s, :][h]).mean()))
            n_s.append(int(h.sum()))
    results["sector"] = BreakdownMetrics("sector", list(range(n_S)), mae_s, n_s)

    # By territory
    mae_t, n_t = [], []
    for t in range(n_T):
        h = hidden[t, :, :]
        if h.sum() == 0:
            mae_t.append(float("nan"))
            n_t.append(0)
        else:
            mae_t.append(float(np.abs(true_panel[t, :, :][h] - imputed_panel[t, :, :][h]).mean()))
            n_t.append(int(h.sum()))
    results["territory"] = BreakdownMetrics("territory", list(range(n_T)), mae_t, n_t)

    # By regime
    if regimes is not None:
        regime_labels = [0, 1, 2, 3, 4]
        mae_r, n_r = [], []
        for r in regime_labels:
            h = hidden & (regimes == r)
            if h.sum() == 0:
                mae_r.append(float("nan"))
                n_r.append(0)
            else:
                mae_r.append(float(np.abs(true_panel[h] - imputed_panel[h]).mean()))
                n_r.append(int(h.sum()))
        results["regime"] = BreakdownMetrics(
            "regime", ["stagnation", "growth", "decline", "crisis", "recovery"], mae_r, n_r
        )

    return results


def compute_state_metrics(
    true_panel: np.ndarray,
    imputed_panel: np.ndarray,
    mask: np.ndarray,
    regimes: np.ndarray,
) -> StateMetrics:
    """
    Classify economic state from imputed panel at hidden cells.
    State = sign of (y[t] - y[t-1]) binned into: growth(1)/decline(2)/stagnation(0).
    Compare predicted state from imputed panel vs true state from true panel.
    Evaluated only on hidden cells where year > 0.
    """
    n_T, n_S, n_Y = true_panel.shape
    hidden = (mask == 0)

    true_state = []
    pred_state = []

    for t in range(n_T):
        for s in range(n_S):
            for y in range(1, n_Y):
                if hidden[t, s, y]:
                    ts = int(regimes[t, s, y])
                    # Predict state from imputed panel: sign of imputed change
                    diff = imputed_panel[t, s, y] - true_panel[t, s, y - 1]
                    if diff > 0.1:
                        ps = 1  # growth
                    elif diff < -0.1:
                        ps = 2  # decline
                    else:
                        ps = 0  # stagnation
                    # Merge crisis/recovery to growth/decline for 3-class problem
                    if ts == 3:
                        ts = 2  # crisis → decline
                    elif ts == 4:
                        ts = 1  # recovery → growth
                    true_state.append(ts)
                    pred_state.append(ps)

    if len(true_state) < 2:
        return StateMetrics(float("nan"), float("nan"), float("nan"), 0)

    y_t = np.array(true_state)
    y_p = np.array(pred_state)

    classes = sorted(set(y_t))
    if len(classes) < 2:
        return StateMetrics(float("nan"), float("nan"), float("nan"), len(y_t))

    mf1 = float(f1_score(y_t, y_p, average="macro", labels=classes, zero_division=0))
    bac = float(balanced_accuracy_score(y_t, y_p))

    # AUCPR for rare classes (original 3=crisis, 4=recovery — already mapped to 2,1)
    aucpr = float("nan")
    # Use the raw regimes to identify rare-class positions
    rare_hidden = hidden & ((regimes == 3) | (regimes == 4))
    n_rare = int(rare_hidden.sum())
    if n_rare > 0 and (rare_hidden.sum() < mask.sum()):
        y_rare_true = (regimes[hidden] >= 3).astype(int)
        # Score: how extreme is the predicted change (abs diff relative to stagnation)
        pred_abs = np.abs(np.array([
            imputed_panel[t, s, y] - true_panel[t, s, max(y - 1, 0)]
            for t in range(n_T) for s in range(n_S) for y in range(n_Y)
            if hidden[t, s, y]
        ]))
        try:
            aucpr = float(average_precision_score(y_rare_true, pred_abs))
        except Exception:
            aucpr = float("nan")

    return StateMetrics(mf1, bac, aucpr, len(y_t))


def compute_edge_recovery_metrics(
    true_relations: list,                 # list of TrueRelation
    n_sectors: int,
    learned_attn: np.ndarray,            # (n_S, n_S) learned attention weights
) -> EdgeRecoveryMetrics:
    """
    Compare learned sector attention weights to ground-truth directed edges.
    Binary classification: edge vs no-edge at off-diagonal positions.
    Also checks sign and lag recovery at top-k predicted edges.
    """
    # Build ground-truth adjacency and metadata
    true_adj = np.zeros((n_sectors, n_sectors))
    true_sign_map: dict[tuple, float] = {}
    true_lag_map: dict[tuple, int] = {}
    for rel in true_relations:
        if rel.source_sector < n_sectors and rel.target_sector < n_sectors:
            true_adj[rel.source_sector, rel.target_sector] = 1
            true_sign_map[(rel.source_sector, rel.target_sector)] = rel.weight
            true_lag_map[(rel.source_sector, rel.target_sector)] = rel.lag

    rows, cols = np.where(~np.eye(n_sectors, dtype=bool))
    y_true = true_adj[rows, cols]
    y_score = learned_attn[rows, cols]

    n_true = int(y_true.sum())
    n_off = len(y_true)

    if n_true == 0 or n_true == n_off:
        auc = float("nan")
    else:
        try:
            auc = float(roc_auc_score(y_true, y_score))
        except Exception:
            auc = float("nan")

    # Precision / recall at k = n_true_edges
    k = max(1, n_true)
    top_k_idx = np.argsort(y_score)[::-1][:k]
    pred_binary = np.zeros(n_off)
    pred_binary[top_k_idx] = 1

    tp = float((pred_binary * y_true).sum())
    fp = float(((pred_binary == 1) & (y_true == 0)).sum())
    fn = float(((pred_binary == 0) & (y_true == 1)).sum())
    tn = float(((pred_binary == 0) & (y_true == 0)).sum())

    precision = tp / max(tp + fp, 1e-8)
    recall = tp / max(tp + fn, 1e-8)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    fpr = fp / max(fp + tn, 1e-8)

    # Sign accuracy on truly present edges
    sign_hits = []
    lag_hits = []
    for (s, t_), true_w in true_sign_map.items():
        learned_w = learned_attn[s, t_]
        row_mean = learned_attn[s].mean()
        learned_sign = 1 if learned_w > row_mean else -1
        true_sign_val = 1 if true_w > 0 else -1
        sign_hits.append(learned_sign == true_sign_val)
    sign_acc = float(np.mean(sign_hits)) if sign_hits else float("nan")

    # Lag accuracy: for edges in top-k, check if the predicted row has the right lag
    # Without explicit lag head, we report NaN (lag not directly learnable from attn alone)
    lag_acc = float("nan")  # learnable only with explicit lag-head architecture

    return EdgeRecoveryMetrics(
        auc=auc,
        precision_at_k=precision,
        recall_at_k=recall,
        f1_at_k=f1,
        sign_accuracy=sign_acc,
        lag_accuracy=lag_acc,
        false_positive_rate=fpr,
        n_true_edges=n_true,
    )


def compute_calibration_metrics(
    true_panel: np.ndarray,
    pred_mean: np.ndarray,
    pred_std: np.ndarray,
    mask: np.ndarray,
) -> CalibrationMetrics:
    """Coverage at 50/80/90% intervals for hidden cells. Gaussian predictive dist."""
    hidden = mask == 0
    if hidden.sum() == 0:
        return CalibrationMetrics(float("nan"), float("nan"), float("nan"), float("nan"))

    true_h = true_panel[hidden]
    mu = pred_mean[hidden]
    sigma = pred_std[hidden]

    if sigma.max() < 1e-10:
        return CalibrationMetrics(float("nan"), float("nan"), float("nan"), float("nan"))

    def coverage(z: float) -> float:
        return float(((true_h >= mu - z * sigma) & (true_h <= mu + z * sigma)).mean())

    return CalibrationMetrics(coverage(0.674), coverage(1.282), coverage(1.645),
                              float((2 * 1.645 * sigma).mean()))


def check_no_leakage(panel: np.ndarray, mask: np.ndarray) -> dict:
    """
    Verify that temporal features are strictly causal (no future values used).
    Perturbs years > check_year and verifies features at years ≤ check_year unchanged.
    """
    from src.modeles.synthetic.imputation_baselines import _build_temporal_features

    n_T, n_S, n_Y = panel.shape
    if n_Y < 3:
        return {"leakage_check": "skipped_too_short", "passed": True}

    panel_perturbed = panel.copy()
    check_year = n_Y // 2
    panel_perturbed[:, :, check_year + 1:] += 999.0

    feats_orig = _build_temporal_features(panel, mask).reshape(n_T, n_S, n_Y, 7)
    feats_pert = _build_temporal_features(panel_perturbed, mask).reshape(n_T, n_S, n_Y, 7)

    diff_past = float(np.abs(
        feats_orig[:, :, :check_year + 1, :] - feats_pert[:, :, :check_year + 1, :]
    ).max())

    return {
        "leakage_check": "causal_temporal_features",
        "max_diff_at_past_years": diff_past,
        "perturbed_future_years": list(range(check_year + 1, n_Y)),
        "passed": diff_past < 1e-6,
    }
