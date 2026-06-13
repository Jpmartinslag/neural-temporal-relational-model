"""
graph_metrics.py — Graph preservation metrics for DEC-047.

Measures changes in learned graph structure before and after few-shot adaptation.
These are computed on the attention matrices, not the imputed values.

Key invariant: attention matrices are (n_S, n_S) after softmax.
True edges are represented as directed pairs (source, target) in true_relations.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score

from src.modeles.synthetic.evaluate_imputation import compute_edge_recovery_metrics

AUC_DEGRADATION_THRESHOLD: float = 0.05  # A6 gate: AUC must not drop more than this


def _build_binary_edge_matrix(true_relations: list, n_sectors: int) -> np.ndarray:
    """Build binary (n_S, n_S) matrix from true relations. Symmetric: mark both directions."""
    mat = np.zeros((n_sectors, n_sectors), dtype=np.float32)
    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        if s < n_sectors and t < n_sectors and s != t:
            mat[t, s] = 1.0  # attention convention: mat[target, source]
    return mat


def _safe_auc(scores_flat: np.ndarray, labels_flat: np.ndarray) -> float:
    """Safe AUC computation — returns 0.5 if only one class present."""
    if labels_flat.sum() == 0 or labels_flat.sum() == len(labels_flat):
        return 0.5
    try:
        return float(roc_auc_score(labels_flat, scores_flat))
    except Exception:
        return 0.5


def _safe_auprc(scores_flat: np.ndarray, labels_flat: np.ndarray) -> float:
    """Safe AUPRC — returns baseline (pos fraction) if only one class."""
    if labels_flat.sum() == 0:
        return 0.0
    if labels_flat.sum() == len(labels_flat):
        return 1.0
    try:
        return float(average_precision_score(labels_flat, scores_flat))
    except Exception:
        return float("nan")


def _precision_at_k(scores: np.ndarray, labels: np.ndarray, k: int) -> float:
    """Precision at top-k predicted scores."""
    if k <= 0:
        return float("nan")
    top_k = np.argsort(scores)[-k:]
    return float(labels[top_k].mean())


def compute_graph_preservation(
    attn_before: np.ndarray,   # (n_S, n_S) attention matrix before adaptation
    attn_after: np.ndarray,    # (n_S, n_S) attention matrix after adaptation
    true_relations: list,
    n_sectors: int,
) -> dict:
    """
    Compute graph preservation metrics comparing attention before and after adaptation.

    Returns:
    - attn_correlation: Pearson correlation of flattened attention before/after
    - mean_weight_change: mean absolute change in attention weights
    - jaccard_top_k: Jaccard of top-k attention indices (k = n_true_edges)
    - auc_before: edge AUC before adaptation (attention vs true edges)
    - auc_after: edge AUC after adaptation
    - auprc_before: AUPRC before
    - auprc_after: AUPRC after
    - precision_at_k_before, precision_at_k_after
    - auc_change: auc_after - auc_before
    - graph_preserved: bool — True if auc_change >= -AUC_DEGRADATION_THRESHOLD
    """
    assert attn_before.shape == attn_after.shape == (n_sectors, n_sectors)

    edge_mat = _build_binary_edge_matrix(true_relations, n_sectors)
    k = int(edge_mat.sum())  # n_true_edges

    # Flatten off-diagonal for scoring
    mask_offdiag = ~np.eye(n_sectors, dtype=bool)
    scores_before = attn_before[mask_offdiag]
    scores_after = attn_after[mask_offdiag]
    labels = edge_mat[mask_offdiag]

    # Correlation of attention matrices
    before_flat = attn_before.ravel()
    after_flat = attn_after.ravel()
    if before_flat.std() > 1e-10 and after_flat.std() > 1e-10:
        attn_correlation = float(np.corrcoef(before_flat, after_flat)[0, 1])
    else:
        attn_correlation = 1.0 if np.allclose(before_flat, after_flat) else float("nan")

    mean_weight_change = float(np.abs(attn_after - attn_before).mean())

    # Jaccard of top-k indices
    if k > 0:
        top_k_before = set(np.argsort(scores_before)[-k:].tolist())
        top_k_after = set(np.argsort(scores_after)[-k:].tolist())
        jaccard = len(top_k_before & top_k_after) / len(top_k_before | top_k_after)
    else:
        jaccard = float("nan")

    auc_before = _safe_auc(scores_before, labels)
    auc_after = _safe_auc(scores_after, labels)
    auprc_before = _safe_auprc(scores_before, labels)
    auprc_after = _safe_auprc(scores_after, labels)
    pak_before = _precision_at_k(scores_before, labels, k)
    pak_after = _precision_at_k(scores_after, labels, k)

    auc_change = auc_after - auc_before
    graph_preserved = auc_change >= -AUC_DEGRADATION_THRESHOLD

    return {
        "attn_correlation": attn_correlation,
        "mean_weight_change": float(mean_weight_change),
        "jaccard_top_k": float(jaccard) if not np.isnan(jaccard) else None,
        "auc_before": float(auc_before),
        "auc_after": float(auc_after),
        "auprc_before": float(auprc_before),
        "auprc_after": float(auprc_after),
        "precision_at_k_before": float(pak_before) if not np.isnan(pak_before) else None,
        "precision_at_k_after": float(pak_after) if not np.isnan(pak_after) else None,
        "auc_change": float(auc_change),
        "graph_preserved": bool(graph_preserved),
        "n_true_edges": k,
    }
