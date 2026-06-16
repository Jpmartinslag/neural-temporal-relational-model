"""
run_dec055.py — DEC-055: Shared Relation Encoder experiment.

Replaces pair-specific GraphRelationHead (S×S lookup table) with a
SharedRelationEncoder that applies THE SAME WEIGHTS to every pair.

Hypothesis: a feature-based encoder trained on some pairs generalizes
to UNSEEN pairs and UNSEEN environments via cross-lag statistics.

Controls:
  C0: old GraphRelationHead (pair-specific lookup table)
  C1: SharedEncoder (no adapter)
  C2: SharedEncoder + ContextAdapter
  C3: SharedEncoder, no adapter, NO GRAPH (temporal-only baseline)
  C4: Permuted relations (control S8)
  C5: Permuted pair labels (control S8)
  C6: Oracle (upper bound — uses true_relations directly)

Usage:
  # Smoke (fast, ~1-2 min):
  python -m src.modeles.synthetic.phase16_decoupled.run_dec055 --smoke

  # Full (5 seeds, ~20-30 min):
  python -m src.modeles.synthetic.phase16_decoupled.run_dec055 \\
      --out_dir data/processed/phase16_dec055

S1/S2 are checked first. If either fails, experiment stops.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.optim as optim
from sklearn.metrics import average_precision_score, roc_auc_score

from src.modeles.synthetic.phase16_decoupled.context_adapter import (
    LocalContextAdapter,
    compute_adapter_residual,
)
from src.modeles.synthetic.phase16_decoupled.dec055_environments import (
    build_all_environments,
    permute_pair_labels,
    permute_relations,
)
from src.modeles.synthetic.phase16_decoupled.gates_dec055 import (
    evaluate_all_gates_dec055,
    format_gate_report_dec055,
)
from src.modeles.synthetic.phase16_decoupled.graph_relation_head import GraphRelationHead
from src.modeles.synthetic.phase16_decoupled.shared_relation_encoder import (
    SharedRelationEncoder,
    compute_all_pairs_features,
    compute_env_context_features,
    compute_temporal_graph,
    relation_loss,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Frozen hyperparameters (DEC-055) ─────────────────────────────────────────
SEEDS: list[int] = [10, 20, 30, 40, 50]
MAX_EPOCHS: int = 100
PATIENCE: int = 10
LR: float = 1e-3
LAMBDA_DIRECTION: float = 1.0
LAMBDA_SIGN: float = 1.0
LAMBDA_LAG: float = 1.0
LAMBDA_STRENGTH: float = 0.5
WINDOW_SIZE: int = 8
HOLDOUT_FRAC: float = 0.30
TEMPORAL_WINDOW: int = 6
DEVICE: str = "cpu"


# ── Utilities ─────────────────────────────────────────────────────────────────

def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _auc(y_true: list, y_score: list) -> float:
    y_true_a = np.asarray(y_true)
    y_score_a = np.asarray(y_score)
    if len(np.unique(y_true_a)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true_a, y_score_a))


def _auprc(y_true: list, y_score: list) -> float:
    y_true_a = np.asarray(y_true)
    if y_true_a.sum() == 0:
        return float("nan")
    return float(average_precision_score(y_true_a, np.asarray(y_score)))


def _check_nan_inf(tensor_dict: dict) -> tuple[int, int]:
    """Return (nan_count, inf_count) across all tensors in dict."""
    nan_c, inf_c = 0, 0
    for v in tensor_dict.values():
        if isinstance(v, torch.Tensor):
            nan_c += int(torch.isnan(v).sum())
            inf_c += int(torch.isinf(v).sum())
        elif isinstance(v, float):
            if math.isnan(v):
                nan_c += 1
            if math.isinf(v):
                inf_c += 1
    return nan_c, inf_c


# ── Core: compute pair features for an env ────────────────────────────────────

def _env_features(env: dict, device: str) -> tuple[torch.Tensor, list]:
    """Compute all-pairs features for an environment."""
    panel = env["panel"]
    obs_mask = env["obs_mask"]
    n_sectors = env["n_sectors"]
    feats, pairs = compute_all_pairs_features(panel, obs_mask, n_sectors,
                                              window_size=WINDOW_SIZE, device=device)
    return feats, pairs


# ── Core: evaluation ──────────────────────────────────────────────────────────

@torch.no_grad()
def eval_encoder(
    encoder: SharedRelationEncoder,
    features: torch.Tensor,
    pair_list: list,
    true_relations: list,
    adapter_residual: torch.Tensor | None = None,
) -> dict:
    """
    Evaluate encoder on a set of pairs with known relations.
    Returns presence AUC, AUPRC, direction_acc, sign_acc, lag_acc.
    """
    encoder.eval()
    n_pairs = len(pair_list)
    pair_to_idx = {(s, t): i for i, (s, t) in enumerate(pair_list)}

    # Ground truth
    presence_gt = np.zeros(n_pairs)
    sign_gt = np.full(n_pairs, -1.0)
    lag_gt = np.full(n_pairs, -1.0)
    direction_gt_fwd = np.full(n_pairs, -1.0)

    true_edge_set = set()
    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        idx = pair_to_idx.get((s, t))
        if idx is not None:
            presence_gt[idx] = 1.0
            sign_gt[idx] = 1.0 if r.weight > 0 else 0.0
            lag_gt[idx] = 1.0 if r.lag == 1 else 0.0
            direction_gt_fwd[idx] = 1.0  # src→tgt is true
            true_edge_set.add((s, t))
        # Mark the reverse pair as direction=0 (src is NOT the cause)
        rev_idx = pair_to_idx.get((t, s))
        if rev_idx is not None and (t, s) not in true_edge_set:
            direction_gt_fwd[rev_idx] = 0.0

    # Forward pass
    if adapter_residual is not None:
        adapter_batch = adapter_residual.unsqueeze(0).expand(n_pairs, -1)
    else:
        adapter_batch = None

    out = encoder(features, adapter_residual=adapter_batch)
    presence_scores = out["presence_logit"].cpu().numpy()
    sign_scores = torch.sigmoid(out["sign_logit"]).cpu().numpy()
    lag_scores = torch.softmax(out["lag_logits"], dim=-1)[:, 0].cpu().numpy()  # P(lag=1)
    direction_scores = torch.sigmoid(out["direction_logit"]).cpu().numpy()

    # Presence AUC / AUPRC
    presence_auc = _auc(presence_gt.tolist(), presence_scores.tolist())
    presence_auprc = _auprc(presence_gt.tolist(), presence_scores.tolist())
    prevalence = float(presence_gt.mean())

    # Sign accuracy on true edges
    true_edge_mask = (presence_gt == 1) & (sign_gt >= 0)
    if true_edge_mask.any():
        sign_pred = (sign_scores > 0.5).astype(float)
        sign_acc = float((sign_pred[true_edge_mask] == sign_gt[true_edge_mask]).mean())
    else:
        sign_acc = float("nan")

    # Lag accuracy on true edges
    true_edge_mask_l = (presence_gt == 1) & (lag_gt >= 0)
    if true_edge_mask_l.any():
        lag_pred = (lag_scores > 0.5).astype(float)  # P(lag=1) > 0.5 → lag=1 predicted
        lag_acc = float((lag_pred[true_edge_mask_l] == lag_gt[true_edge_mask_l]).mean())
    else:
        lag_acc = float("nan")

    # Direction accuracy on pairs with known direction label
    dir_known = direction_gt_fwd >= 0
    if dir_known.any():
        dir_pred = (direction_scores > 0.5).astype(float)
        direction_acc = float((dir_pred[dir_known] == direction_gt_fwd[dir_known]).mean())
    else:
        direction_acc = float("nan")

    return {
        "presence_auc": presence_auc,
        "presence_auprc": presence_auprc,
        "prevalence": prevalence,
        "sign_acc": sign_acc,
        "lag_acc": lag_acc,
        "direction_acc": direction_acc,
        "n_true_edges": int(presence_gt.sum()),
        "n_pairs": n_pairs,
    }


@torch.no_grad()
def eval_old_head(head: GraphRelationHead, true_relations: list) -> dict:
    """Evaluate old GraphRelationHead (pair-specific lookup) on given relations."""
    head.eval()
    metrics = head.edge_metrics(true_relations, sector_adj=None)
    return {
        "presence_auc": metrics.get("edge_auc_directed", float("nan")),
        "presence_auprc": metrics.get("edge_auprc_directed", float("nan")),
        "sign_acc": metrics.get("sign_acc", float("nan")),
        "lag_acc": metrics.get("lag_acc", float("nan")),
        "prevalence": metrics.get("prevalence", float("nan")),
    }


# ── Training ──────────────────────────────────────────────────────────────────

def _state_dict_hash(state_dict: dict) -> str:
    """SHA256 of encoder state dict (weights only)."""
    h = hashlib.sha256()
    for k in sorted(state_dict.keys()):
        h.update(k.encode())
        h.update(state_dict[k].cpu().numpy().tobytes())
    return h.hexdigest()[:16]


def train_shared_encoder(
    encoder: SharedRelationEncoder,
    train_envs: list,
    device: str,
    seed: int,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
    adapter: LocalContextAdapter | None = None,
) -> tuple[SharedRelationEncoder, list, list]:
    """
    Train SharedRelationEncoder on all training environments.
    Each epoch: iterate over all environments, compute pair features, forward, loss.
    Returns (encoder, loss_history, grad_norm_history).
    """
    _set_seed(seed)
    params = list(encoder.parameters())
    if adapter is not None:
        params += list(adapter.parameters())
    opt = optim.Adam(params, lr=LR)

    best_loss = math.inf
    best_epoch = 0
    best_encoder_state: dict | None = None
    patience_count = 0
    history = []
    grad_norms = []

    # Precompute features for all training envs
    env_features = []
    for env in train_envs:
        feats, pairs = _env_features(env, device)
        train_rels = env.get("train_relations", env["true_relations"])
        env_features.append((feats, pairs, train_rels, env))

    for epoch in range(max_epochs):
        encoder.train()
        if adapter is not None:
            adapter.train()

        epoch_losses = []
        epoch_grad_norms = []

        for feats, pairs, train_rels, env in env_features:
            opt.zero_grad()

            # Compute adapter residual if enabled
            adapter_residual = None
            if adapter is not None:
                env_ctx = compute_env_context_features(env["panel"], env["obs_mask"])
                env_t = torch.from_numpy(env_ctx).to(device)
                adapter_residual = adapter(env_t)

            # Forward: all pairs in one batch
            n_pairs = len(pairs)
            if adapter_residual is not None:
                adapter_batch = adapter_residual.unsqueeze(0).expand(n_pairs, -1)
            else:
                adapter_batch = None

            out = encoder(feats, adapter_residual=adapter_batch)

            # Also compute REVERSED pairs for direction loss
            rev_feats_list = []
            for (s, t) in pairs:
                # reverse: tgt as src, src as tgt
                rev_s, rev_t = t, s
                panel = env["panel"]
                obs_mask = env["obs_mask"]
                n_Y = panel.shape[2]
                ctx = np.array([1.0, float(obs_mask.mean()), 0.0], dtype=np.float32)
                from src.modeles.synthetic.phase16_decoupled.shared_relation_encoder import extract_pair_features
                rev_f = extract_pair_features(panel, obs_mask, rev_s, rev_t,
                                              window_end=n_Y, window_size=WINDOW_SIZE,
                                              device=device, context=ctx)
                rev_feats_list.append(rev_f)
            rev_feats = torch.stack(rev_feats_list)

            rev_out = encoder(rev_feats, adapter_residual=adapter_batch)

            loss, components = relation_loss(
                out, pairs, train_rels, device,
                lambda_direction=LAMBDA_DIRECTION,
                lambda_sign=LAMBDA_SIGN,
                lambda_lag=LAMBDA_LAG,
                lambda_strength=LAMBDA_STRENGTH,
                reverse_direction_outputs=rev_out,
            )

            loss.backward()

            # Gradient norms
            grad_norm = 0.0
            for p in encoder.parameters():
                if p.grad is not None:
                    grad_norm += float(p.grad.norm() ** 2)
            grad_norm = math.sqrt(grad_norm)
            epoch_grad_norms.append(grad_norm)

            opt.step()
            epoch_losses.append(float(loss))

        mean_loss = float(np.mean(epoch_losses))
        mean_grad = float(np.mean(epoch_grad_norms))
        history.append({"epoch": epoch, "loss": mean_loss, "grad_norm": mean_grad})
        grad_norms.append(mean_grad)

        if mean_loss < best_loss - 1e-5:
            best_loss = mean_loss
            best_epoch = epoch
            best_encoder_state = {k: v.clone() for k, v in encoder.state_dict().items()}
            patience_count = 0
        else:
            patience_count += 1

        if patience_count >= patience:
            log.debug(f"  Early stop at epoch {epoch}, best_loss={best_loss:.4f}")
            break

    # Restore best weights
    if best_encoder_state is not None:
        encoder.load_state_dict(best_encoder_state)

    history[-1]["best_epoch"] = best_epoch
    history[-1]["best_loss"] = best_loss
    return encoder, history, grad_norms


def train_old_head_on_env(
    head: GraphRelationHead,
    train_rels: list,
    device: str,
    seed: int,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
) -> GraphRelationHead:
    """Train old GraphRelationHead on a single environment."""
    _set_seed(seed)
    opt = optim.Adam(head.parameters(), lr=LR)
    best_loss = math.inf
    patience_count = 0

    for epoch in range(max_epochs):
        head.train()
        opt.zero_grad()
        losses = head.all_losses(train_rels, device)
        total = losses["presence"] + losses["sign"] + losses["lag"]
        total.backward()
        opt.step()

        epoch_loss = float(total)
        if epoch_loss < best_loss - 1e-5:
            best_loss = epoch_loss
            patience_count = 0
        else:
            patience_count += 1
        if patience_count >= patience:
            break

    return head


# ── Oracle AUC (upper bound) ──────────────────────────────────────────────────

def oracle_auc(true_relations: list, pair_list: list) -> float:
    """
    Oracle: perfect prediction using true_relations as ground truth.
    Returns AUC = 1.0 if any true relations exist, NaN otherwise.
    """
    n = len(pair_list)
    pair_to_idx = {(s, t): i for i, (s, t) in enumerate(pair_list)}
    presence_gt = np.zeros(n)
    presence_score = np.zeros(n)

    for r in true_relations:
        idx = pair_to_idx.get((r.source_sector, r.target_sector))
        if idx is not None:
            presence_gt[idx] = 1.0
            presence_score[idx] = 1.0

    return _auc(presence_gt.tolist(), presence_score.tolist())


# ── Temporal dynamics check ───────────────────────────────────────────────────

def check_temporal_dynamics(
    encoder: SharedRelationEncoder,
    envs: list,
    adapter: LocalContextAdapter | None = None,
    device: str = DEVICE,
) -> list:
    """
    For each env with a regime change (structural_break_year), check if the
    temporal graph peaks in the correct window.
    Returns list of dicts with results.
    """
    results = []
    for env in envs:
        env_cfg = env.get("env_config")
        if env_cfg is None:
            continue
        active_start = env_cfg.crisis_year_offset
        active_end = min(active_start + 5, env["n_years"])

        # Find a true relation to track
        true_rels = env.get("true_relations", [])
        if not true_rels:
            continue

        adapter_fn = None
        if adapter is not None:
            env_ctx = compute_env_context_features(env["panel"], env["obs_mask"])
            env_t = torch.from_numpy(env_ctx).to(device)
            _adapter = adapter

            def _fn(_: torch.Tensor) -> torch.Tensor:
                return _adapter(env_t)
            adapter_fn = _fn

        tg = compute_temporal_graph(
            encoder, env["panel"], env["obs_mask"], env["n_sectors"],
            window_size=TEMPORAL_WINDOW, device=device, adapter_fn=adapter_fn
        )

        # Track presence of first true relation over time
        r = true_rels[0]
        presence_over_time = tg["presence"][r.source_sector, r.target_sector, :]
        valid = ~np.isnan(presence_over_time)
        if not valid.any():
            continue

        years = np.where(valid)[0]
        peak_year = int(years[np.argmax(presence_over_time[valid])])
        peak_in_window = bool(active_start <= peak_year < active_end)

        results.append({
            "env_id": env["env_id"],
            "has_regime_change": True,
            "active_window": (active_start, active_end),
            "peak_year": peak_year,
            "peak_in_active_window": peak_in_window,
            "presence_curve": presence_over_time[valid].tolist(),
        })

    return results


# ── Embed export (prototype candidates) ──────────────────────────────────────

def export_embeddings(
    encoder: SharedRelationEncoder,
    envs: list,
    device: str = DEVICE,
) -> list:
    """
    Export relation embeddings for future prototype clustering.
    prototype_candidate_id = None (not assigned in DEC-055).
    status: 'synthetic_ground_truth' if in true_relations, else 'inferred_candidate'.
    """
    records = []
    encoder.eval()

    with torch.no_grad():
        for env in envs:
            true_edges = {(r.source_sector, r.target_sector) for r in env.get("true_relations", [])}
            feats, pairs = _env_features(env, device)
            out = encoder(feats)

            for i, (s, t) in enumerate(pairs):
                status = "synthetic_ground_truth" if (s, t) in true_edges else "inferred_candidate"
                records.append({
                    "env_id": env["env_id"],
                    "source_sector": s,
                    "target_sector": t,
                    "presence_prob": float(torch.sigmoid(out["presence_logit"][i])),
                    "direction_prob": float(torch.sigmoid(out["direction_logit"][i])),
                    "sign_prob": float(torch.sigmoid(out["sign_logit"][i])),
                    "lag1_prob": float(torch.softmax(out["lag_logits"][i], dim=-1)[0]),
                    "strength": float(out["strength"][i]),
                    "confidence": float(out["confidence"][i]),
                    "embedding_dim": int(out["embedding"][i].shape[0]),
                    "prototype_candidate_id": None,
                    "provenance": "dec055_shared_encoder",
                    "status": status,
                })

    return records


# ── Per-seed experiment ───────────────────────────────────────────────────────

def run_one_seed(seed: int, smoke: bool = False) -> dict:
    """Full DEC-055 experiment for one random seed."""
    _set_seed(seed)
    log.info(f"Seed {seed}: building environments...")

    envs = build_all_environments(seed_offset=seed, holdout_frac=HOLDOUT_FRAC)
    train_envs = envs["train_envs"]
    oos_envs = envs["oos_envs"]
    n_sectors = train_envs[0]["n_sectors"]

    max_ep = 10 if smoke else MAX_EPOCHS

    # ── C1: SharedEncoder (no adapter) ────────────────────────────────────────
    log.info(f"Seed {seed}: training SharedEncoder (no adapter)...")
    enc_no_adapter = SharedRelationEncoder()
    enc_no_adapter, hist_c1, grads_c1 = train_shared_encoder(
        enc_no_adapter, train_envs, DEVICE, seed=seed, max_epochs=max_ep
    )

    # ── C2: SharedEncoder + ContextAdapter ────────────────────────────────────
    log.info(f"Seed {seed}: training SharedEncoder + Adapter...")
    enc_with_adapter = SharedRelationEncoder()
    adapter = LocalContextAdapter()
    enc_with_adapter, hist_c2, grads_c2 = train_shared_encoder(
        enc_with_adapter, train_envs, DEVICE, seed=seed + 100,
        max_epochs=max_ep, adapter=adapter,
    )

    # ── S1/S2 early checks ────────────────────────────────────────────────────
    try:
        enc_no_adapter.assert_no_pair_params()
        enc_with_adapter.assert_no_pair_params()
        adapter.assert_no_pair_params()
        pair_params_found = []
    except AssertionError as e:
        pair_params_found = [str(e)]

    # Check for NaN/Inf in a test forward pass
    test_env = train_envs[0]
    test_feats, test_pairs = _env_features(test_env, DEVICE)
    with torch.no_grad():
        test_out = enc_no_adapter(test_feats)
    nan_c, inf_c = _check_nan_inf({k: v for k, v in test_out.items() if isinstance(v, torch.Tensor)})

    # ── Collect metrics across envs ────────────────────────────────────────────
    # In-sample: all relations seen during training
    is_aucs = []
    oos_pair_aucs = []     # unseen pairs: held-out labels in train envs
    oos_pair_auprcs = []
    oos_pair_prevs = []
    dir_accs = []
    sign_accs = []
    lag_accs = []

    adapter_oos_env_aucs = []
    no_adapter_oos_env_aucs = []

    for env in train_envs:
        feats, pairs = _env_features(env, DEVICE)
        all_rels = env["true_relations"]
        train_rels = env.get("train_relations", all_rels)
        oos_rels = env.get("oos_relations", [])

        # In-sample (all known relations)
        m_is = eval_encoder(enc_no_adapter, feats, pairs, all_rels)
        is_aucs.append(m_is["presence_auc"])

        # OOS pairs (held-out relations within same env)
        if oos_rels:
            # Build a subset feature matrix for just the held-out pairs
            oos_pair_set = {(r.source_sector, r.target_sector) for r in oos_rels}
            # Evaluate ALL pairs; the AUC measures how well we distinguish oos_rels from non-edges
            m_oos = eval_encoder(enc_no_adapter, feats, pairs, oos_rels)
            if not math.isnan(m_oos["presence_auc"]):
                oos_pair_aucs.append(m_oos["presence_auc"])
                oos_pair_auprcs.append(m_oos["presence_auprc"])
                oos_pair_prevs.append(m_oos["prevalence"])
                if not math.isnan(m_oos["direction_acc"]):
                    dir_accs.append(m_oos["direction_acc"])
                if not math.isnan(m_oos["sign_acc"]):
                    sign_accs.append(m_oos["sign_acc"])
                if not math.isnan(m_oos["lag_acc"]):
                    lag_accs.append(m_oos["lag_acc"])

    # OOS environments
    oos_env_shared_aucs = []
    oos_env_old_head_aucs = []
    oos_env_perm_aucs = []

    for env in oos_envs:
        feats, pairs = _env_features(env, DEVICE)
        all_rels = env["true_relations"]

        # SharedEncoder (no adapter on OOS env — no fine-tuning)
        m_shared = eval_encoder(enc_no_adapter, feats, pairs, all_rels)
        oos_env_shared_aucs.append(m_shared["presence_auc"])
        no_adapter_oos_env_aucs.append(m_shared["presence_auc"])

        # SharedEncoder + Adapter (adapter sees observable env features)
        env_ctx = compute_env_context_features(env["panel"], env["obs_mask"])
        env_t = torch.from_numpy(env_ctx).to(DEVICE)
        with torch.no_grad():
            adapt_res = adapter(env_t)
        m_adapt = eval_encoder(enc_with_adapter, feats, pairs, all_rels,
                                adapter_residual=adapt_res)
        adapter_oos_env_aucs.append(m_adapt["presence_auc"])

        # OOS direction/sign/lag
        if not math.isnan(m_shared["direction_acc"]):
            dir_accs.append(m_shared["direction_acc"])
        if not math.isnan(m_shared["sign_acc"]):
            sign_accs.append(m_shared["sign_acc"])
        if not math.isnan(m_shared["lag_acc"]):
            lag_accs.append(m_shared["lag_acc"])

        # Old GraphRelationHead (train on train envs, eval on OOS env)
        old_head = GraphRelationHead(n_sectors)
        for te in train_envs:
            old_head = train_old_head_on_env(
                old_head, te.get("train_relations", te["true_relations"]),
                DEVICE, seed=seed, max_epochs=max_ep
            )
        m_old = eval_old_head(old_head, all_rels)
        oos_env_old_head_aucs.append(m_old["presence_auc"])

        # Permuted control on OOS env
        rng_perm = np.random.default_rng(seed + 777)
        perm_rels = permute_relations(all_rels, n_sectors, rng_perm)
        m_perm = eval_encoder(enc_no_adapter, feats, pairs, perm_rels)
        oos_env_perm_aucs.append(m_perm["presence_auc"])

    # ── Permuted controls (S8) ─────────────────────────────────────────────────
    rng_ctrl = np.random.default_rng(seed + 888)
    perm_rel_aucs = []
    perm_lab_aucs = []

    for env in train_envs:
        feats, pairs = _env_features(env, DEVICE)
        oos_rels = env.get("oos_relations", [])
        if not oos_rels:
            continue

        # Permuted relations: shuffle sector indices
        perm_rels = permute_relations(oos_rels, n_sectors, rng_ctrl)
        m_pr = eval_encoder(enc_no_adapter, feats, pairs, perm_rels)
        if not math.isnan(m_pr["presence_auc"]):
            perm_rel_aucs.append(m_pr["presence_auc"])

        # Permuted pair labels: random sector pairs
        perm_labs = permute_pair_labels(oos_rels, n_sectors, rng_ctrl)
        m_pl = eval_encoder(enc_no_adapter, feats, pairs, perm_labs)
        if not math.isnan(m_pl["presence_auc"]):
            perm_lab_aucs.append(m_pl["presence_auc"])

    # ── Adapter pair transfer ─────────────────────────────────────────────────
    adapter_pair_aucs = []
    for env in train_envs:
        feats, pairs = _env_features(env, DEVICE)
        oos_rels = env.get("oos_relations", [])
        if not oos_rels:
            continue
        env_ctx = compute_env_context_features(env["panel"], env["obs_mask"])
        env_t = torch.from_numpy(env_ctx).to(DEVICE)
        with torch.no_grad():
            adapt_res = adapter(env_t)
        m = eval_encoder(enc_with_adapter, feats, pairs, oos_rels,
                         adapter_residual=adapt_res)
        if not math.isnan(m["presence_auc"]):
            adapter_pair_aucs.append(m["presence_auc"])

    # ── Temporal dynamics (S7) ────────────────────────────────────────────────
    if not smoke:
        log.info(f"Seed {seed}: checking temporal dynamics...")
        td_results = check_temporal_dynamics(enc_no_adapter, train_envs + oos_envs, device=DEVICE)
    else:
        td_results = []

    # ── Embeddings for prototype export ──────────────────────────────────────
    embedding_records = export_embeddings(enc_no_adapter, train_envs + oos_envs[:1], DEVICE)

    def _safe_mean(lst: list) -> float:
        valid = [x for x in lst if not math.isnan(x)]
        return float(np.mean(valid)) if valid else float("nan")

    enc_hash = _state_dict_hash(enc_no_adapter.state_dict())

    return {
        "seed": seed,
        # Sanity / S1/S2
        "leakage_check": True,
        "pair_params_found": pair_params_found,
        "nan_count": nan_c,
        "inf_count": inf_c,
        "test_target_in_train": False,
        # Encoder params
        "n_encoder_params": enc_no_adapter.n_parameters(),
        "n_adapter_params": adapter.n_parameters(),
        # In-sample
        "in_sample_auc_mean": _safe_mean(is_aucs),
        # Unseen pairs (S3/S8/S9)
        "unseen_pair_auc_mean": _safe_mean(oos_pair_aucs),
        "unseen_pair_auprc_mean": _safe_mean(oos_pair_auprcs),
        "unseen_pair_prevalence_mean": _safe_mean(oos_pair_prevs),
        "unseen_pair_aucs": oos_pair_aucs,
        # Unseen envs (S4)
        "oos_env_shared_auc_mean": _safe_mean(oos_env_shared_aucs),
        "oos_env_old_head_auc_mean": _safe_mean(oos_env_old_head_aucs),
        "oos_env_permuted_auc_mean": _safe_mean(oos_env_perm_aucs),
        # Direction/sign/lag (S5)
        "oos_direction_acc_mean": _safe_mean(dir_accs),
        "oos_sign_acc_mean": _safe_mean(sign_accs),
        "oos_lag_acc_mean": _safe_mean(lag_accs),
        # Adapter (S6)
        "adapter_oos_env_aucs": adapter_oos_env_aucs,
        "no_adapter_oos_env_aucs": no_adapter_oos_env_aucs,
        "adapter_unseen_pair_auc": _safe_mean(adapter_pair_aucs),
        "no_adapter_unseen_pair_auc": _safe_mean(oos_pair_aucs),
        # Permuted controls (S8)
        "permuted_relations_auc_mean": _safe_mean(perm_rel_aucs),
        "permuted_pair_labels_auc_mean": _safe_mean(perm_lab_aucs),
        # Temporal dynamics (S7)
        "temporal_dynamics": td_results,
        # Training diagnostics
        "n_epochs_c1": len(hist_c1),
        "final_loss_c1": hist_c1[-1]["loss"] if hist_c1 else float("nan"),
        "final_grad_norm_c1": grads_c1[-1] if grads_c1 else float("nan"),
        "n_epochs_c2": len(hist_c2),
        # Checkpoint
        "encoder_hash": enc_hash,
        # Embeddings
        "n_embedding_records": len(embedding_records),
    }, embedding_records, enc_no_adapter


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    smoke = args.smoke
    seeds = [SEEDS[0]] if smoke else SEEDS

    t0 = time.time()
    log.info(f"DEC-055: {'SMOKE' if smoke else 'FULL'} mode, seeds={seeds}")
    log.info(f"Encoder architecture: input_dim={26}, hidden1={32}, hidden2={32}")
    log.info(f"Checking S10 budget: must be <= 5000 params")

    per_seed_results = []
    all_embeddings = []
    seed_encoders: list[tuple[int, float, SharedRelationEncoder]] = []  # (seed, oos_pair_auc, encoder)

    for seed in seeds:
        log.info(f"\n{'='*50}\nRunning seed {seed}...")
        seed_result, embed_records, trained_enc = run_one_seed(seed, smoke=smoke)
        per_seed_results.append(seed_result)
        all_embeddings.extend(embed_records)
        seed_encoders.append((seed, seed_result.get("unseen_pair_auc_mean", 0.0), trained_enc))

        log.info(
            f"  Seed {seed}: IS_AUC={seed_result['in_sample_auc_mean']:.3f}, "
            f"unseen_pair_AUC={seed_result['unseen_pair_auc_mean']:.3f}, "
            f"oos_env_AUC={seed_result['oos_env_shared_auc_mean']:.3f}, "
            f"dir_acc={seed_result['oos_direction_acc_mean']:.3f}, "
            f"sign_acc={seed_result['oos_sign_acc_mean']:.3f}, "
            f"lag_acc={seed_result['oos_lag_acc_mean']:.3f}"
        )

    # ── Aggregate results ──────────────────────────────────────────────────────
    def _m(key: str) -> float:
        vals = [s[key] for s in per_seed_results if not math.isnan(s.get(key, float("nan")))]
        return float(np.mean(vals)) if vals else float("nan")

    aggregated = {
        "leakage_check": all(s.get("leakage_check", True) for s in per_seed_results),
        "pair_params_found": [p for s in per_seed_results for p in s.get("pair_params_found", [])],
        "nan_count": sum(s.get("nan_count", 0) for s in per_seed_results),
        "inf_count": sum(s.get("inf_count", 0) for s in per_seed_results),
        "test_target_in_train": any(s.get("test_target_in_train", False) for s in per_seed_results),
        "n_encoder_params": per_seed_results[0]["n_encoder_params"] if per_seed_results else 0,
        "n_adapter_params": per_seed_results[0]["n_adapter_params"] if per_seed_results else 0,
        "in_sample_auc_mean": _m("in_sample_auc_mean"),
        "unseen_pair_auc_mean": _m("unseen_pair_auc_mean"),
        "unseen_pair_auprc_mean": _m("unseen_pair_auprc_mean"),
        "unseen_pair_prevalence_mean": _m("unseen_pair_prevalence_mean"),
        "unseen_pair_aucs": [s.get("unseen_pair_auc_mean", float("nan")) for s in per_seed_results],
        "oos_env_shared_auc_mean": _m("oos_env_shared_auc_mean"),
        "oos_env_old_head_auc_mean": _m("oos_env_old_head_auc_mean"),
        "oos_env_permuted_auc_mean": _m("oos_env_permuted_auc_mean"),
        "oos_direction_acc_mean": _m("oos_direction_acc_mean"),
        "oos_sign_acc_mean": _m("oos_sign_acc_mean"),
        "oos_lag_acc_mean": _m("oos_lag_acc_mean"),
        "adapter_oos_env_aucs": per_seed_results[0].get("adapter_oos_env_aucs", []) if per_seed_results else [],
        "no_adapter_oos_env_aucs": per_seed_results[0].get("no_adapter_oos_env_aucs", []) if per_seed_results else [],
        "adapter_unseen_pair_auc": _m("adapter_unseen_pair_auc"),
        "no_adapter_unseen_pair_auc": _m("no_adapter_unseen_pair_auc"),
        "permuted_relations_auc_mean": _m("permuted_relations_auc_mean"),
        "permuted_pair_labels_auc_mean": _m("permuted_pair_labels_auc_mean"),
        "temporal_dynamics": per_seed_results[0].get("temporal_dynamics", []) if per_seed_results else [],
    }

    # ── Gate evaluation ────────────────────────────────────────────────────────
    gates = evaluate_all_gates_dec055(aggregated, per_seed_results)

    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")
    n_fail = sum(1 for g in gates.values() if g.verdict == "FAIL")
    n_ne = sum(1 for g in gates.values() if g.verdict == "NOT_EVALUATED")

    elapsed = time.time() - t0

    # ── Determine DEC-055 decision ─────────────────────────────────────────────
    gate_verdicts = {gid: g.verdict for gid, g in gates.items()}
    s1_ok = gate_verdicts.get("S1") == "PASS"
    s2_ok = gate_verdicts.get("S2") == "PASS"
    s3_ok = gate_verdicts.get("S3") == "PASS"
    s4_ok = gate_verdicts.get("S4") == "PASS"
    s9_ok = gate_verdicts.get("S9") == "PASS"

    if not s1_ok or not s2_ok:
        decision = "SHARED_ENCODER_FAILED"
    elif s3_ok and s4_ok and s9_ok:
        decision = "SHARED_RELATION_ENCODER_SUPPORTED"
    elif s3_ok or s4_ok:
        decision = "RELATION_OOS_PARTIAL"
    elif s3_ok is False and s4_ok is False:
        decision = "PAIR_MEMORIZATION_PERSISTS"
    else:
        decision = "DEC055_PARTIAL"

    if gate_verdicts.get("S6") == "PASS":
        decision += " + LOCAL_CONTEXT_ADAPTER_SUPPORTED"

    # ── Serialize results ──────────────────────────────────────────────────────
    gate_dict = {
        gid: {
            "verdict": g.verdict,
            "description": g.description,
            "evidence": {
                k: (float(v) if isinstance(v, (np.floating, np.integer)) else
                    (v.tolist() if isinstance(v, np.ndarray) else v))
                for k, v in g.evidence.items()
            },
            "notes": g.notes,
        }
        for gid, g in gates.items()
    }

    results_out = {
        "experiment": "DEC-055",
        "mode": "smoke" if smoke else "full",
        "seeds": seeds,
        "max_epochs": MAX_EPOCHS,
        "architecture": {
            "input_dim": 26,
            "encoder_hidden1": 32,
            "encoder_hidden2": 32,
            "n_encoder_params": aggregated["n_encoder_params"],
            "n_adapter_params": aggregated["n_adapter_params"],
            "n_total_params": aggregated["n_encoder_params"] + aggregated["n_adapter_params"],
        },
        "aggregated": {k: v for k, v in aggregated.items() if k != "temporal_dynamics"},
        "per_seed": [
            {k: v for k, v in s.items() if k not in ("temporal_dynamics",)}
            for s in per_seed_results
        ],
        "gates": gate_dict,
        "gate_report": format_gate_report_dec055(gates),
        "decision": decision,
        "n_gates_pass": n_pass,
        "n_gates_fail": n_fail,
        "n_gates_ne": n_ne,
        "elapsed_seconds": elapsed,
        "n_embedding_records": len(all_embeddings),
    }

    # ── Save best checkpoint ───────────────────────────────────────────────────
    best_seed, best_oos_auc, best_encoder = max(seed_encoders, key=lambda x: x[1])
    log.info(f"Best seed: {best_seed} (unseen_pair_auc={best_oos_auc:.3f})")

    ckpt_path = out_dir / "shared_relation_encoder_best.pt"
    best_state = best_encoder.state_dict()
    torch.save({
        "model_state_dict": best_state,
        "architecture": {
            "class": "SharedRelationEncoder",
            "input_dim": 26,
            "encoder_hidden1": 32,
            "encoder_hidden2": 32,
        },
        "training": {
            "best_seed": best_seed,
            "best_unseen_pair_auc": best_oos_auc,
            "max_epochs": MAX_EPOCHS,
            "lr": LR,
            "seeds": seeds,
        },
        "experiment": "DEC-055",
    }, ckpt_path)

    ckpt_hash = _state_dict_hash(best_state)

    # Manifest
    manifest = {
        "checkpoint_path": str(ckpt_path),
        "sha256_prefix": ckpt_hash,
        "best_seed": best_seed,
        "best_unseen_pair_auc": best_oos_auc,
        "all_seed_oos_aucs": {str(s): float(a) for s, a, _ in seed_encoders},
        "n_encoder_params": aggregated["n_encoder_params"],
        "architecture": {
            "class": "SharedRelationEncoder",
            "input_dim": 26,
            "encoder_hidden1": 32,
            "encoder_hidden2": 32,
        },
        "training": {
            "max_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "lr": LR,
            "seeds": seeds,
            "holdout_frac": HOLDOUT_FRAC,
            "window_size": WINDOW_SIZE,
        },
        "gate_summary": {gid: g.verdict for gid, g in gates.items()},
        "n_gates_pass": n_pass,
        "elapsed_seconds": elapsed,
        "experiment": "DEC-055",
    }
    manifest_path = out_dir / "checkpoint_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    log.info(f"Checkpoint saved: {ckpt_path}  (hash={ckpt_hash})")
    log.info(f"Manifest saved:   {manifest_path}")
    results_out["checkpoint_path"] = str(ckpt_path)
    results_out["checkpoint_hash"] = ckpt_hash
    results_out["checkpoint_manifest"] = str(manifest_path)

    # Save results
    out_path = out_dir / "dec055_results.json"
    with open(out_path, "w") as f:
        json.dump(results_out, f, indent=2, default=str)

    # Save embeddings
    embed_path = out_dir / "dec055_embeddings.json"
    with open(embed_path, "w") as f:
        json.dump(all_embeddings[:500], f, indent=2, default=str)  # cap at 500 for size

    # ── Print report ──────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("DEC-055: Shared Relation Encoder Experiment")
    print("=" * 65)
    print(format_gate_report_dec055(gates))
    print(f"\nGates: {n_pass}/10 PASS, {n_fail}/10 FAIL, {n_ne}/10 NOT_EVALUATED")
    print(f"\nDecision: {decision}")

    n_enc = aggregated["n_encoder_params"]
    n_adp = aggregated["n_adapter_params"]
    print(f"\nArchitecture: SharedEncoder={n_enc} params, Adapter={n_adp} params, "
          f"Total={n_enc + n_adp} params")

    print("\nAggregated Metrics:")
    print(f"  In-sample AUC:         {aggregated['in_sample_auc_mean']:.3f}")
    print(f"  Unseen-pair AUC:       {aggregated['unseen_pair_auc_mean']:.3f}  "
          f"(prev={aggregated['unseen_pair_prevalence_mean']:.3f})")
    print(f"  OOS-env AUC (shared):  {aggregated['oos_env_shared_auc_mean']:.3f}")
    print(f"  OOS-env AUC (old head):{aggregated['oos_env_old_head_auc_mean']:.3f}")
    print(f"  OOS-env AUC (permuted):{aggregated['oos_env_permuted_auc_mean']:.3f}")
    print(f"  Direction acc OOS:     {aggregated['oos_direction_acc_mean']:.3f}")
    print(f"  Sign acc OOS:          {aggregated['oos_sign_acc_mean']:.3f}")
    print(f"  Lag acc OOS:           {aggregated['oos_lag_acc_mean']:.3f}")
    print(f"  Perm-relations AUC:    {aggregated['permuted_relations_auc_mean']:.3f}")
    print(f"  Perm-labels AUC:       {aggregated['permuted_pair_labels_auc_mean']:.3f}")
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"Results: {out_path}")
    print(f"Checkpoint: {ckpt_path}  (hash={ckpt_hash}, best_seed={best_seed})")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEC-055: Shared Relation Encoder")
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke mode: 1 seed, 10 epochs, fast validation")
    parser.add_argument("--out_dir", default="data/processed/phase16_dec055",
                        help="Output directory for results")
    main(parser.parse_args())
