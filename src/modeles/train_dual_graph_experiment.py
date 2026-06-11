"""HERALD — Scientific trainer for the dual-graph experiment (contract FROZEN_V2).

Implements the rolling-origin protocol, the eleven controls (C0–C10), the
four-task loss, the per fold/seed metric suite, and the fail-closed gate of
``reports/HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md`` §8–§9.

This module is *machinery*. Importing it runs nothing. ``main()`` can launch a
run but the full study is gated behind explicit flags; a separate pilot
(``run_dual_graph_pilot.py``) exercises the path on one fold.

Design invariants
-----------------
  - external rolling-origin over folds 2021–2025;
  - inner validation is strictly temporal — the latest historical sample is the
    inner-validation year, earlier samples are inner-train; regions are NEVER
    split randomly;
  - normalization is already frozen in the tensors (per-fold, training-only);
  - early stopping uses the inner-validation metric, never the outer fold;
  - class/positive weights come from inner-train labels only;
  - permutation controls reorder *structure*, not only names, and use only
    historical (causal) data inside the fold; each permutation seed and mapping
    is recorded. Null controls (C7 territory, C8 sector) keep targets canonical;
    a joint relabeling of features+adjacency+targets is degenerate and rejected;
  - the old observable L1 layer and any ZE2020 edge file are never loaded;
  - WMAPE is never used for growth;
  - outputs are written atomically; thresholds are frozen before any run.

Shape conventions: B samples, T=5 steps, R regions, S sectors, F=6 features.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)

from src.modeles.dual_graph_models import (
    LOSS_COEFFICIENTS,
    build_dual_graph_model,
    compute_class_weights,
    compute_pos_weight,
    count_parameters,
    dual_graph_loss,
)

BASE = Path(__file__).resolve().parents[2]
TENSOR_DIR = BASE / "data/processed/dual_graph_tensors"
MANIFEST = TENSOR_DIR / "manifest.json"
DEFAULT_OUT = BASE / "data/processed/dual_graph_s1"

# Feature channel layout (matches build_dual_graph_tensors FEATURE_NAMES).
BASE_FEATURES = [0, 1, 2]        # sector growth, share, log births
ARDECO_FEATURES = [3, 4, 5]      # log employment, employment growth, share

# ---------------------------------------------------------------------------
# Frozen hyper-parameters (fixed BEFORE any full run; contract §6/§7).
# ---------------------------------------------------------------------------

HYPERPARAMS = {
    "hidden_dim": 8,
    "sector_embed_dim": 4,
    "dropout": 0.3,
    "lr": 1e-3,
    "weight_decay": 1e-4,
    "max_epochs": 200,
    "patience": 20,
    "ridge_alpha": 10.0,
    "loss_coef": dict(LOSS_COEFFICIENTS),
    "topk_sector": 3,
    "precision_k": [5, 10, 20],
    "early_stop_metric": "inner_val_mae",
    "huber_delta": 1.0,
}

SEEDS = [42, 43, 44, 45, 46]
EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]

# Frozen gate thresholds (contract §9; never edited after observing results).
GATE = {
    "mae_improve_frac": 0.01,
    "macro_f1_margin": 0.02,
    "min_folds": 3,
    "jaccard_min": 0.50,
    "max_fold_regression": 0.10,
    "exclude_year": 2021,
}

# Control registry. C0/C1 are baselines; C2–C10 are equal-capacity neural runs.
CONTROLS: dict[str, dict] = {
    "C0_persistence": {"kind": "persistence"},
    "C1_ridge": {"kind": "ridge"},
    "C2_no_graph": {"kind": "neural", "territory": False, "sector": False},
    "C3_territory_only": {"kind": "neural", "territory": True, "sector": False},
    "C4_sector_only": {"kind": "neural", "territory": False, "sector": True},
    "C5_dual": {"kind": "neural", "territory": True, "sector": True},
    "C6_territory_temporal_perm": {
        "kind": "neural", "territory": True, "sector": True, "perm": "territory_temporal"},
    # C7 (contract §8.8 "territory-label permutation"): valid territory null —
    # permute ONLY the territory adjacency (P A Pᵀ), targets/features canonical.
    "C7_territory_graph_perm": {
        "kind": "neural", "territory": True, "sector": True, "perm": "territory_graph"},
    # C8 (contract §8.9 "sector-label permutation"): valid sector null — permute
    # the sector-graph-relevant inputs, targets canonical. The naive joint
    # relabeling (PX, PAPᵀ, PY) is degenerate and is rejected (see apply_control).
    "C8_sector_identity_perm": {
        "kind": "neural", "territory": True, "sector": True, "perm": "sector_identity"},
    "C9_no_ardeco": {
        "kind": "neural", "territory": True, "sector": True, "perm": "drop_ardeco"},
    "C10_ardeco_temporal_perm": {
        "kind": "neural", "territory": True, "sector": True, "perm": "ardeco_temporal"},
}
CONTROL_ORDER = list(CONTROLS)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def set_all_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def perm_seed(base_seed: int, eval_year: int, control: str) -> int:
    """Deterministic, recorded permutation seed for a (seed, fold, control)."""
    return base_seed * 100_003 + eval_year * 101 + (CONTROL_ORDER.index(control) + 1)


# ---------------------------------------------------------------------------
# Fold loading and temporal split
# ---------------------------------------------------------------------------

def load_fold(eval_year: int) -> dict[str, np.ndarray]:
    path = TENSOR_DIR / f"fr_{eval_year}.npz"
    if not path.exists():
        raise FileNotFoundError(f"Missing fold tensor: {path}")
    data = np.load(path, allow_pickle=True)
    return {k: data[k] for k in data.files}


def temporal_split(fold: dict[str, np.ndarray]) -> dict:
    """Inner rolling-origin split. Returns indices + a leakage record.

    The last sample (index B-1) is the OUTER evaluation year. The latest
    historical sample (B-2) is the inner-validation year; earlier samples are
    inner-train. Proves max(train_year) < val_year < outer_year.
    """
    sample_years = [int(y) for y in fold["sample_years"]]
    B = len(sample_years)
    if B < 3:
        raise ValueError(f"Need >=3 samples for temporal inner split; got {B}")
    outer_idx = B - 1
    val_idx = B - 2
    train_idx = list(range(0, B - 2))

    outer_year = sample_years[outer_idx]
    val_year = sample_years[val_idx]
    train_years = [sample_years[i] for i in train_idx]
    # Max feature observation year per sample is stored in observation_years.
    obs_years = np.asarray(fold["observation_years"])  # (B, T)
    max_obs_outer = int(obs_years[outer_idx].max())

    record = {
        "sample_years": sample_years,
        "train_idx": train_idx,
        "val_idx": val_idx,
        "outer_idx": outer_idx,
        "train_years": train_years,
        "val_year": val_year,
        "outer_year": outer_year,
        "max_feature_obs_year_outer": max_obs_outer,
        "leakage_ok": bool(
            (max(train_years) < val_year < outer_year)
            and max_obs_outer < outer_year
        ),
    }
    if not record["leakage_ok"]:
        raise RuntimeError(f"LEAKAGE in temporal split: {record}")
    return record


# ---------------------------------------------------------------------------
# Control / permutation transforms (operate on a copy; record the mapping)
# ---------------------------------------------------------------------------

def _to_tensor_fold(fold: dict[str, np.ndarray]) -> dict[str, torch.Tensor]:
    out = {
        "features_seq": torch.tensor(np.asarray(fold["features_seq"])).float(),
        "feature_mask_seq": torch.tensor(np.asarray(fold["feature_mask_seq"])),
        "territory_adj_seq": torch.tensor(np.asarray(fold["territory_adj_seq"])).float(),
        "territory_adj_mask": torch.tensor(np.asarray(fold["territory_adj_mask"])),
        "target_log_growth": torch.tensor(np.asarray(fold["target_log_growth"])).float(),
        "target_regime": torch.tensor(np.asarray(fold["target_regime"])).long(),
        "target_recovery": torch.tensor(np.asarray(fold["target_recovery"])).long(),
        "target_emergence": torch.tensor(np.asarray(fold["target_emergence"])).long(),
        "target_mask": torch.tensor(np.asarray(fold["target_mask"])),
    }
    return out


def apply_control(
    fold_t: dict[str, torch.Tensor],
    control: str,
    seed: int,
    eval_year: int,
) -> tuple[dict[str, torch.Tensor], dict]:
    """Return a transformed copy of the fold tensors plus a permutation record.

    Null controls reorder *structure* relative to canonical economic information,
    never targets, and stay within the fold's causal sequence data. A joint
    relabeling that co-permutes features, adjacency AND targets is degenerate
    (a similarity transform that preserves the achievable loss); C7 and C8 below
    therefore keep targets canonical and break only the structure↔identity
    alignment. The post-transform guard rejects any accidental target change.
    """
    spec = CONTROLS[control]
    data = {k: v.clone() for k, v in fold_t.items()}
    record = {"control": control, "perm_kind": spec.get("perm", "none")}
    pkind = spec.get("perm")
    if pkind is None:
        return data, record

    pseed = perm_seed(seed, eval_year, control)
    rng = np.random.default_rng(pseed)
    record["perm_seed"] = pseed

    B, T, R, S, F = data["features_seq"].shape

    if pkind == "territory_temporal":
        tau = rng.permutation(T)
        data["territory_adj_seq"] = data["territory_adj_seq"][:, tau]
        data["territory_adj_mask"] = data["territory_adj_mask"][:, tau]
        record["permutation"] = tau.tolist()

    elif pkind == "territory_graph":
        # C7 — territory null: permute ONLY the territory adjacency by P A Pᵀ
        # (similarity on both region axes). Node features, targets and masks
        # stay canonical, so the graph now connects the wrong economic nodes.
        # A permutation similarity preserves degrees, weights and density; the
        # model has no per-region parameter, so the break is not relabelable.
        P = torch.as_tensor(rng.permutation(R), dtype=torch.long)
        adj = data["territory_adj_seq"]
        data["territory_adj_seq"] = adj.index_select(-2, P).index_select(-1, P)
        record["permutation"] = P.tolist()
        record["mode"] = "territory_adjacency_similarity_PAPt"
        record["targets_canonical"] = True

    elif pkind == "sector_identity":
        # C8 — sector null: permute the sector axis of the graph-relevant inputs
        # (node features + the territory graph's sector axis, kept internally
        # aligned) by σ, while TARGETS and target_mask stay canonical. The
        # position-indexed sector embedding and learned sector graph now align
        # with economic sector σ(s) but must predict economic sector s — the
        # sector identity↔learned-structure correspondence is broken and cannot
        # be undone by relabeling parameters (targets are pinned).
        sig = torch.as_tensor(rng.permutation(S), dtype=torch.long)
        data["features_seq"] = data["features_seq"].index_select(3, sig)
        data["feature_mask_seq"] = data["feature_mask_seq"].index_select(3, sig)
        data["territory_adj_seq"] = data["territory_adj_seq"].index_select(2, sig)
        data["territory_adj_mask"] = data["territory_adj_mask"].index_select(2, sig)
        record["permutation"] = sig.tolist()
        record["mode"] = "sector_feature_and_territory_sector_axis"
        record["targets_canonical"] = True

    elif pkind == "drop_ardeco":
        feats = data["features_seq"].clone()
        fmask = data["feature_mask_seq"].clone()
        feats[..., ARDECO_FEATURES] = 0.0
        fmask[..., ARDECO_FEATURES] = 0
        data["features_seq"] = feats
        data["feature_mask_seq"] = fmask
        record["dropped_features"] = ARDECO_FEATURES

    elif pkind == "ardeco_temporal":
        tau = rng.permutation(T)
        feats = data["features_seq"].clone()
        fmask = data["feature_mask_seq"].clone()
        feats[..., ARDECO_FEATURES] = feats[:, tau][..., ARDECO_FEATURES]
        fmask[..., ARDECO_FEATURES] = fmask[:, tau][..., ARDECO_FEATURES]
        data["features_seq"] = feats
        data["feature_mask_seq"] = fmask
        record["permutation"] = tau.tolist()

    else:
        raise ValueError(f"Unknown permutation kind: {pkind}")

    # Reject degenerate co-permutation: a valid null NEVER moves the targets or
    # the target mask. (Joint relabeling of features+adjacency+targets is a
    # similarity transform that preserves the achievable loss — not a null.)
    if not targets_unchanged(fold_t, data):
        raise ValueError(
            f"degenerate null in {control}: targets were permuted; they must "
            "stay canonical (contract §8 valid-null requirement)")
    record["targets_unchanged"] = True
    return data, record


TARGET_KEYS = ("target_log_growth", "target_regime", "target_recovery",
               "target_emergence", "target_mask")


def targets_unchanged(reference: dict, transformed: dict) -> bool:
    """True iff every supervised target (and target mask) is bit-identical.

    Used to detect and reject a degenerate null that co-permutes the targets.
    """
    return all(torch.equal(transformed[k], reference[k]) for k in TARGET_KEYS)


# ---------------------------------------------------------------------------
# Metrics (pure)
# ---------------------------------------------------------------------------

def regression_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict:
    m = mask.astype(bool) & np.isfinite(pred) & np.isfinite(target)
    if m.sum() == 0:
        return {"mae": None, "median_ae": None, "spearman": None,
                "sign_accuracy": None, "n": 0}
    p, t = pred[m], target[m]
    err = np.abs(p - t)
    if np.std(p) < 1e-12 or np.std(t) < 1e-12:
        rho = 0.0
    else:
        rho = float(spearmanr(p, t).statistic)
    sign_acc = float((np.sign(p) == np.sign(t)).mean())
    return {
        "mae": float(err.mean()),
        "median_ae": float(np.median(err)),
        "spearman": rho if np.isfinite(rho) else 0.0,
        "sign_accuracy": sign_acc,
        "n": int(m.sum()),
    }


def regime_metrics(logits: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict:
    valid = mask.astype(bool) & (target >= 0)
    if valid.sum() == 0:
        return {"macro_f1": None, "balanced_accuracy": None,
                "f1_per_class": None, "confusion_matrix": None, "n": 0}
    pred = logits.argmax(axis=-1)[valid]
    true = target[valid]
    labels = [0, 1, 2]
    return {
        "macro_f1": float(f1_score(true, pred, labels=labels, average="macro",
                                   zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(true, pred)),
        "f1_per_class": [float(x) for x in f1_score(
            true, pred, labels=labels, average=None, zero_division=0)],
        "confusion_matrix": confusion_matrix(true, pred, labels=labels).tolist(),
        "n": int(valid.sum()),
    }


def _precision_recall_ndcg_at_k(scores: np.ndarray, y: np.ndarray, k: int) -> dict:
    n = len(y)
    k_eff = min(k, n)
    order = np.argsort(-scores)[:k_eff]
    top_y = y[order]
    n_pos = int(y.sum())
    precision = float(top_y.sum() / k_eff) if k_eff > 0 else 0.0
    recall = float(top_y.sum() / n_pos) if n_pos > 0 else 0.0
    # NDCG with binary relevance.
    gains = top_y / np.log2(np.arange(2, k_eff + 2))
    dcg = float(gains.sum())
    ideal_hits = min(n_pos, k_eff)
    idcg = float((np.ones(ideal_hits) / np.log2(np.arange(2, ideal_hits + 2))).sum()) \
        if ideal_hits > 0 else 0.0
    ndcg = float(dcg / idcg) if idcg > 0 else 0.0
    return {"precision": precision, "recall": recall, "ndcg": ndcg}


def binary_metrics(logits: np.ndarray, target: np.ndarray, mask: np.ndarray,
                   k_list: list[int], with_ranking: bool = True) -> dict:
    valid = mask.astype(bool) & (target >= 0)
    if valid.sum() == 0:
        return {"aucpr": None, "prevalence": None, "n": 0, "at_k": {}}
    scores = 1.0 / (1.0 + np.exp(-logits[valid]))
    y = target[valid].astype(int)
    prevalence = float(y.mean())
    if y.sum() == 0 or y.sum() == len(y):
        aucpr = None
    else:
        aucpr = float(average_precision_score(y, scores))
    out = {"aucpr": aucpr, "prevalence": prevalence, "n": int(valid.sum()), "at_k": {}}
    if with_ranking:
        for k in k_list:
            out["at_k"][str(k)] = _precision_recall_ndcg_at_k(scores, y, k)
    return out


def extract_topk_edges(sector_adj: np.ndarray, k: int) -> dict:
    """Top-k undirected sector relations from a learned (S,S) adjacency."""
    S = sector_adj.shape[-1]
    a = sector_adj.copy()
    np.fill_diagonal(a, 0.0)
    edges = set()
    for i in range(S):
        order = np.argsort(-a[i])[:k]
        for j in order:
            if a[i, j] > 0:
                edges.add((min(i, int(j)), max(i, int(j))))
    total = S * (S - 1) / 2
    return {
        "edges": sorted(edges),
        "n_edges": len(edges),
        "density": float(len(edges) / total) if total > 0 else 0.0,
        "mean_weight": float(a[a > 0].mean()) if (a > 0).any() else 0.0,
    }


def jaccard(edges_a: list, edges_b: list) -> float:
    sa, sb = {tuple(e) for e in edges_a}, {tuple(e) for e in edges_b}
    if not sa and not sb:
        return 1.0
    union = sa | sb
    return float(len(sa & sb) / len(union)) if union else 1.0


def mean_seed_jaccard(topk_by_seed: list[dict]) -> float:
    edge_sets = [t["edges"] for t in topk_by_seed if t]
    if len(edge_sets) < 2:
        return 0.0
    vals = []
    for i in range(len(edge_sets)):
        for j in range(i + 1, len(edge_sets)):
            vals.append(jaccard(edge_sets[i], edge_sets[j]))
    return float(np.mean(vals)) if vals else 0.0


# ---------------------------------------------------------------------------
# Baselines (C0 persistence, C1 sector Ridge)
# ---------------------------------------------------------------------------

def _denorm_log_births(fold_t: dict, sample_idx: int, t: int,
                       means: np.ndarray, stds: np.ndarray) -> np.ndarray:
    """De-normalise log-births (feature 2) at step t for one sample → (R,S)."""
    norm = fold_t["features_seq"][sample_idx, t, :, :, 2].numpy()
    mask = fold_t["feature_mask_seq"][sample_idx, t, :, :, 2].numpy().astype(bool)
    raw = norm * stds[2] + means[2]
    raw = np.where(mask, raw, np.nan)
    return raw


def persistence_predict(fold_t: dict, split: dict, means, stds) -> np.ndarray:
    """Predict outer log-growth as the previous observed log-growth."""
    o = split["outer_idx"]
    T = fold_t["features_seq"].shape[1]
    lb_last = _denorm_log_births(fold_t, o, T - 1, means, stds)
    lb_prev = _denorm_log_births(fold_t, o, T - 2, means, stds)
    return lb_last - lb_prev


def _node_design(features_sample: torch.Tensor) -> np.ndarray:
    """Flatten one sample (T,R,S,F) → (R*S, T*F) design matrix, NaN→0."""
    T, R, S, F = features_sample.shape
    x = features_sample.permute(1, 2, 0, 3).reshape(R * S, T * F).numpy()
    return np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)


def ridge_predict(fold_t: dict, split: dict, alpha: float) -> np.ndarray:
    """Sector Ridge on the same causal features. Fit on inner-train, predict outer."""
    feats = fold_t["features_seq"]
    tgt = fold_t["target_log_growth"]
    tmask = fold_t["target_mask"].bool() & torch.isfinite(tgt)

    X_list, y_list = [], []
    for s in split["train_idx"] + [split["val_idx"]]:
        X = _node_design(feats[s])
        y = tgt[s].reshape(-1).numpy()
        m = tmask[s].reshape(-1).numpy()
        X_list.append(X[m])
        y_list.append(y[m])
    X_tr = np.concatenate(X_list, axis=0)
    y_tr = np.concatenate(y_list, axis=0)
    model = Ridge(alpha=alpha)
    model.fit(X_tr, y_tr)

    o = split["outer_idx"]
    R, S = tgt.shape[1], tgt.shape[2]
    pred = model.predict(_node_design(feats[o])).reshape(R, S)
    return pred


# ---------------------------------------------------------------------------
# Neural training (one control, one fold, one seed)
# ---------------------------------------------------------------------------

def _forward(model, data, idx):
    return model(
        data["features_seq"][idx], data["feature_mask_seq"][idx],
        data["territory_adj_seq"][idx], data["territory_adj_mask"][idx],
    )


def _slice_targets(data, idx):
    return {
        "target_log_growth": data["target_log_growth"][idx],
        "target_regime": data["target_regime"][idx],
        "target_recovery": data["target_recovery"][idx],
        "target_emergence": data["target_emergence"][idx],
        "target_mask": data["target_mask"][idx],
    }


def train_neural(data, spec, split, seed, hp) -> dict:
    """Train one neural control with temporal early stopping; predict outer."""
    set_all_seeds(seed)
    model = build_dual_graph_model(
        hidden_dim=hp["hidden_dim"], use_territory_graph=spec["territory"],
        use_sector_graph=spec["sector"], sector_embed_dim=hp["sector_embed_dim"],
        dropout=hp["dropout"],
    )
    n_params = count_parameters(model)
    opt = torch.optim.Adam(model.parameters(), lr=hp["lr"],
                           weight_decay=hp["weight_decay"])

    tr_idx = split["train_idx"]
    val_idx = [split["val_idx"]]
    out_idx = [split["outer_idx"]]

    tr_tg = _slice_targets(data, tr_idx)
    val_tg = _slice_targets(data, val_idx)

    # Class/positive weights from inner-train only.
    cw = compute_class_weights(tr_tg["target_regime"], 3)
    rpw = compute_pos_weight(tr_tg["target_recovery"])
    epw = compute_pos_weight(tr_tg["target_emergence"])

    best_val = float("inf")
    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    best_epoch = 0
    patience = hp["patience"]
    bad = 0
    history = []

    for epoch in range(hp["max_epochs"]):
        model.train()
        opt.zero_grad()
        out = _forward(model, data, tr_idx)
        losses = dual_graph_loss(out, tr_tg, tr_tg["target_mask"],
                                 class_weights=cw, recovery_pos_weight=rpw,
                                 emergence_pos_weight=epw, coef=hp["loss_coef"])
        if not torch.isfinite(losses["total"]):
            return {"status": "nonfinite_train", "n_params": n_params}
        losses["total"].backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            vout = _forward(model, data, val_idx)
            vpred = vout["pred_log_growth"][0].numpy()
            vt = val_tg["target_log_growth"][0].numpy()
            vm = val_tg["target_mask"][0].numpy()
            val_mae = regression_metrics(vpred, vt, vm)["mae"]
        if val_mae is None or not np.isfinite(val_mae):
            return {"status": "nonfinite_val", "n_params": n_params}
        history.append(float(val_mae))

        if val_mae < best_val - 1e-9:
            best_val = val_mae
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        out = _forward(model, data, out_idx)
    out_np = {k: v[0].numpy() for k, v in out.items()}
    if not all(np.isfinite(v).all() for v in out_np.values()):
        return {"status": "nonfinite_outputs", "n_params": n_params}

    sector_adj_mean = out["sector_adj_learned"][0].mean(dim=0).numpy()  # (S,S)
    return {
        "status": "ok",
        "n_params": n_params,
        "best_epoch": best_epoch,
        "best_val_mae": float(best_val),
        "stopped_epoch": len(history),
        "val_history": history,
        "outputs": out_np,
        "sector_adj_mean": sector_adj_mean,
    }


# ---------------------------------------------------------------------------
# Per (fold, control, seed) evaluation
# ---------------------------------------------------------------------------

def evaluate_run(fold_t, fold, control, seed, eval_year, split, hp) -> dict:
    spec = CONTROLS[control]
    data, perm_record = apply_control(fold_t, control, seed, eval_year)
    means = np.asarray(fold["feature_means"])
    stds = np.asarray(fold["feature_stds"])

    o = split["outer_idx"]
    tgt_lg = data["target_log_growth"][o].numpy()
    tmask = data["target_mask"][o].numpy()

    result = {
        "control": control, "eval_year": eval_year, "seed": seed,
        "kind": spec["kind"], "permutation": perm_record,
        "metrics": {}, "status": "ok",
    }

    if spec["kind"] == "persistence":
        pred = persistence_predict(data, split, means, stds)
        result["metrics"]["regression"] = regression_metrics(pred, tgt_lg, tmask)
        result["n_params"] = 0
        return result

    if spec["kind"] == "ridge":
        pred = ridge_predict(data, split, hp["ridge_alpha"])
        result["metrics"]["regression"] = regression_metrics(pred, tgt_lg, tmask)
        result["n_params"] = None
        return result

    run = train_neural(data, spec, split, seed, hp)
    result["n_params"] = run["n_params"]
    if run["status"] != "ok":
        result["status"] = run["status"]   # fail-closed: propagate, no metrics
        return result

    out = run["outputs"]
    result["best_epoch"] = run["best_epoch"]
    result["stopped_epoch"] = run["stopped_epoch"]
    result["best_val_mae"] = run["best_val_mae"]
    result["metrics"]["regression"] = regression_metrics(
        out["pred_log_growth"], tgt_lg, tmask)
    result["metrics"]["regime"] = regime_metrics(
        out["regime_logits"], data["target_regime"][o].numpy(), tmask)
    result["metrics"]["recovery"] = binary_metrics(
        out["recovery_logits"], data["target_recovery"][o].numpy(), tmask,
        hp["precision_k"])
    result["metrics"]["emergence"] = binary_metrics(
        out["emergence_logits"], data["target_emergence"][o].numpy(), tmask,
        hp["precision_k"])
    result["learned_graph"] = extract_topk_edges(
        run["sector_adj_mean"], hp["topk_sector"])
    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _mean(values: list) -> Optional[float]:
    vals = [v for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(vals)) if vals else None


def aggregate(results: list[dict], controls: list[str], folds: list[int]) -> dict:
    """Aggregate per-run results by control × fold (mean over seeds) and overall."""
    agg: dict = {}
    for control in controls:
        agg[control] = {"by_fold": {}, "overall": {}}
        per_fold_mae, per_fold_f1 = {}, {}
        rec_pass_folds, beat_terr_folds, beat_sect_folds = 0, 0, 0
        for fold in folds:
            runs = [r for r in results
                    if r["control"] == control and r["eval_year"] == fold
                    and r["status"] == "ok"]
            mae = _mean([r["metrics"].get("regression", {}).get("mae") for r in runs])
            f1 = _mean([r["metrics"].get("regime", {}).get("macro_f1")
                        for r in runs if "regime" in r["metrics"]])
            rec_aucpr = _mean([r["metrics"].get("recovery", {}).get("aucpr")
                               for r in runs if "recovery" in r["metrics"]])
            rec_prev = _mean([r["metrics"].get("recovery", {}).get("prevalence")
                              for r in runs if "recovery" in r["metrics"]])
            jacc = mean_seed_jaccard(
                [r.get("learned_graph") for r in runs if r.get("learned_graph")])
            agg[control]["by_fold"][str(fold)] = {
                "mae": mae, "macro_f1": f1, "recovery_aucpr": rec_aucpr,
                "recovery_prevalence": rec_prev, "seed_jaccard": jacc,
                "n_seeds": len(runs),
            }
            per_fold_mae[fold] = mae
            per_fold_f1[fold] = f1
        agg[control]["overall"] = {
            "mae": _mean(list(per_fold_mae.values())),
            "macro_f1": _mean(list(per_fold_f1.values())),
            "mean_seed_jaccard": _mean(
                [agg[control]["by_fold"][str(f)]["seed_jaccard"] for f in folds]),
        }
    return agg


# ---------------------------------------------------------------------------
# Fail-closed gate (pure)
# ---------------------------------------------------------------------------

def _fold_value(agg, control, fold, key):
    return agg.get(control, {}).get("by_fold", {}).get(str(fold), {}).get(key)


def apply_gate(agg: dict, folds: list[int], gate: dict = GATE) -> dict:
    """Pure fail-closed gate (contract §9). Any missing/NaN ⇒ criterion fails.

    Control roles (explicit, no implicit metric or direction):
      dual           = C5_dual
      ridge          = C1_ridge
      no_graph       = C2_no_graph
      territory_null = C7_territory_graph_perm   (valid territory null, §8.8)
      sector_null    = C8_sector_identity_perm   (valid sector null, §8.9)

    Criterion 4 registered metric: per-fold primary regression MAE
    (mean over seeds), direction = lower is better; "dual beats null" iff
    MAE(dual) < MAE(null) in a fold.

    The "≥3/5 folds" rule scales for subsets: for a subset of n folds it
    requires ``ceil(min_folds/len(folds) * n)`` folds (3/5 → 3/5 full, 3/4
    without 2021).
    """
    dual, ridge, nog = "C5_dual", "C1_ridge", "C2_no_graph"
    terr_null, sect_null = "C7_territory_graph_perm", "C8_sector_identity_perm"
    n_total = len(folds)

    def ok(x):
        return x is not None and np.isfinite(x)

    def overall(c, k):
        return agg.get(c, {}).get("overall", {}).get(k)

    def need_folds(subset):
        if len(subset) == n_total:
            return gate["min_folds"]
        return int(np.ceil(gate["min_folds"] / n_total * len(subset)))

    def subset_mean(control, key, subset):
        return _mean([_fold_value(agg, control, f, key) for f in subset])

    def crit_mae(subset):
        d = subset_mean(dual, "mae", subset)
        ri = subset_mean(ridge, "mae", subset)
        ng = subset_mean(nog, "mae", subset)
        if not (ok(d) and ok(ri) and ok(ng)):
            return False
        return (d <= (1 - gate["mae_improve_frac"]) * ri
                and d <= (1 - gate["mae_improve_frac"]) * ng)

    def crit_f1(subset):
        d = subset_mean(dual, "macro_f1", subset)
        ng = subset_mean(nog, "macro_f1", subset)
        sn = subset_mean(sect_null, "macro_f1", subset)
        if not (ok(d) and ok(ng) and ok(sn)):
            return False
        return (d >= ng + gate["macro_f1_margin"]
                and d >= sn + gate["macro_f1_margin"])

    def crit_recovery(subset):
        cnt = 0
        for f in subset:
            d = _fold_value(agg, dual, f, "recovery_aucpr")
            prev = _fold_value(agg, dual, f, "recovery_prevalence")
            ng = _fold_value(agg, nog, f, "recovery_aucpr")
            if ok(d) and ok(prev) and ok(ng) and d > prev and d > ng:
                cnt += 1
        return cnt >= need_folds(subset)

    def crit_graph_beats(subset):
        cnt_t, cnt_s = 0, 0
        for f in subset:
            d = _fold_value(agg, dual, f, "mae")
            t = _fold_value(agg, terr_null, f, "mae")
            s = _fold_value(agg, sect_null, f, "mae")
            if ok(d) and ok(t) and d < t:
                cnt_t += 1
            if ok(d) and ok(s) and d < s:
                cnt_s += 1
        need = need_folds(subset)
        return cnt_t >= need and cnt_s >= need

    full = list(folds)
    no2021 = [f for f in folds if f != gate["exclude_year"]]

    c1 = crit_mae(full)
    c2 = crit_f1(full)
    c3 = crit_recovery(full)
    c4 = crit_graph_beats(full)
    c5_val = overall(dual, "mean_seed_jaccard")
    c5 = ok(c5_val) and c5_val >= gate["jaccard_min"]

    # c6: no fold regresses MAE > 10% vs the no-graph encoder.
    c6 = True
    for f in full:
        d = _fold_value(agg, dual, f, "mae")
        ng = _fold_value(agg, nog, f, "mae")
        if not (ok(d) and ok(ng)) or d > (1 + gate["max_fold_regression"]) * ng:
            c6 = False
            break

    # c7: criteria 1–4 still hold without 2021.
    c7 = (crit_mae(no2021) and crit_f1(no2021)
          and crit_recovery(no2021) and crit_graph_beats(no2021))

    criteria = {
        "c1_mae_improve": bool(c1),
        "c2_macro_f1_margin": bool(c2),
        "c3_recovery_aucpr_folds": bool(c3),
        "c4_graph_beats_nulls_folds": bool(c4),
        "c5_seed_jaccard": bool(c5),
        "c6_no_fold_regression": bool(c6),
        "c7_holds_without_2021": bool(c7),
    }
    decision = "DUAL_GRAPH_S1_PASS" if all(criteria.values()) else "DUAL_GRAPH_S1_FAIL"
    return {
        "criteria": criteria,
        "decision": decision,
        "jaccard_value": c5_val if ok(c5_val) else None,
        "control_roles": {
            "dual": dual, "ridge": ridge, "no_graph": nog,
            "territory_null": terr_null, "sector_null": sect_null,
        },
        "criterion4_metric": "primary_regression_mae",
        "criterion4_direction": "lower_is_better",
    }


# ---------------------------------------------------------------------------
# Atomic output + manifest
# ---------------------------------------------------------------------------

def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"Unserialisable: {type(o)}")


def atomic_write_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2, default=_json_default)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", "-C", str(BASE), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def build_manifest(folds, controls, seeds, hp, out_dir) -> dict:
    tensor_meta = {}
    if MANIFEST.exists():
        tm = json.loads(MANIFEST.read_text())
        tensor_meta = {f["eval_year"]: f.get("sha256") for f in tm.get("folds", [])}
    return {
        "git_commit": _git_commit(),
        "tensor_dir": str(TENSOR_DIR),
        "tensor_checksums": {str(k): v for k, v in tensor_meta.items()},
        "folds": folds,
        "controls": controls,
        "seeds": seeds,
        "hyperparameters": {k: v for k, v in hp.items() if k != "loss_coef"} | {
            "loss_coef": hp["loss_coef"]},
        "gate_thresholds": {k: v for k, v in GATE.items()},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
        "out_dir": str(out_dir),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_experiment(out_dir: Path, folds=None, controls=None, seeds=None,
                  hp=None, write=True) -> dict:
    folds = folds or EVAL_YEARS
    controls = controls or CONTROL_ORDER
    seeds = seeds or SEEDS
    hp = hp or HYPERPARAMS
    out_dir = Path(out_dir)

    results, leakage_audit = [], {}
    t0 = time.time()
    for eval_year in folds:
        fold = load_fold(eval_year)
        fold_t = _to_tensor_fold(fold)
        split = temporal_split(fold)
        leakage_audit[str(eval_year)] = {
            k: split[k] for k in
            ("train_years", "val_year", "outer_year",
             "max_feature_obs_year_outer", "leakage_ok")
        }
        for control in controls:
            for seed in seeds:
                res = evaluate_run(fold_t, fold, control, seed, eval_year, split, hp)
                results.append(res)
                if write:
                    atomic_write_json(
                        out_dir / "per_run" /
                        f"{control}__fr{eval_year}__seed{seed}.json", res)

    agg = aggregate(results, controls, folds)
    gate = apply_gate(agg, folds)
    manifest = build_manifest(folds, controls, seeds, hp, out_dir)
    runtime = time.time() - t0

    summary = {
        "runtime_seconds": runtime,
        "n_runs": len(results),
        "aggregated": agg,
        "gate": gate,
        "leakage_audit": leakage_audit,
    }
    if write:
        atomic_write_json(out_dir / "manifest.json", manifest)
        atomic_write_json(out_dir / "leakage_audit.json", leakage_audit)
        atomic_write_json(out_dir / "summary_aggregated.json", summary)
        atomic_write_json(out_dir / "gate_result.json", gate)
    return {"results": results, "aggregated": agg, "gate": gate,
            "manifest": manifest, "leakage_audit": leakage_audit,
            "runtime_seconds": runtime}


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual-graph scientific trainer")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--folds", type=int, nargs="+", default=EVAL_YEARS)
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--controls", type=str, nargs="+", default=CONTROL_ORDER)
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument("--patience", type=int, default=None)
    parser.add_argument("--confirm-full-run", action="store_true",
                        help="Required to launch the full study locally.")
    args = parser.parse_args()

    hp = dict(HYPERPARAMS)
    if args.max_epochs is not None:
        hp["max_epochs"] = args.max_epochs
    if args.patience is not None:
        hp["patience"] = args.patience

    full = (args.folds == EVAL_YEARS and args.seeds == SEEDS
            and args.controls == CONTROL_ORDER)
    if full and not args.confirm_full_run:
        raise SystemExit(
            "Full study requires --confirm-full-run. Use the pilot for liveness.")

    out = run_experiment(args.out_dir, args.folds, args.controls, args.seeds, hp)
    print(f"runtime={out['runtime_seconds']:.1f}s  gate={out['gate']['decision']}")
    for k, v in out["gate"]["criteria"].items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")


if __name__ == "__main__":
    main()
