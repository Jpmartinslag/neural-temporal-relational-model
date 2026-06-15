"""
oos_validator.py — Out-of-sample GraphRelationHead validation for DEC-054.

Protocol:
  1. For each train dataset, train a fresh head and evaluate in-sample.
  2. For each test dataset, train a fresh head (in-sample diagnostic for test data).
  3. Evaluate each TRAIN head on each TEST dataset's relations (true OOS).
  4. Compare to permuted null baseline.

This validates whether the head can generalise relation structure across
independently generated synthetic datasets.

FROZEN before results (DEC-054).
"""

from __future__ import annotations

import math
import random

import numpy as np
import torch
import torch.optim as optim

from src.modeles.synthetic.phase16_decoupled.graph_relation_head import GraphRelationHead


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def train_head_fresh(
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    n_sectors: int,
    device: str,
    max_epochs: int = 75,
    seed: int = 42,
) -> GraphRelationHead:
    """
    Train a fresh GraphRelationHead on the given (panel, obs_mask, true_relations).

    Uses Adam with presence BCE + sign BCE + lag BCE losses.
    Presence loss uses pos_weight for class imbalance.

    Returns trained GraphRelationHead.
    """
    _set_seed(seed)
    head = GraphRelationHead(n_sectors).to(device)
    opt = optim.Adam(head.parameters(), lr=1e-3)

    best_loss = math.inf
    patience_count = 0
    patience = 10

    for epoch in range(max_epochs):
        head.train()
        opt.zero_grad()

        losses = head.all_losses(true_relations, device)
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


def eval_head_on_relations(
    head: GraphRelationHead,
    true_relations: list,
    sector_adj: np.ndarray | None = None,
) -> dict:
    """
    Evaluate a GraphRelationHead on the given true_relations.

    Returns head.edge_metrics(true_relations, sector_adj) plus in_sample=False flag.
    """
    metrics = head.edge_metrics(true_relations, sector_adj)
    metrics["in_sample"] = False
    return metrics


def _permuted_head_auc(
    head: GraphRelationHead,
    true_relations: list,
    n_sectors: int,
    rng: np.random.Generator,
) -> float:
    """
    Compute edge AUC after permuting presence_logit rows and columns.
    This is the null baseline: random structure.
    """
    from sklearn.metrics import roc_auc_score

    perm = rng.permutation(n_sectors)
    orig = head.presence_logit.data.clone()
    with torch.no_grad():
        head.presence_logit.data = orig[perm, :][:, perm]
    metrics = head.edge_metrics(true_relations, None)
    with torch.no_grad():
        head.presence_logit.data = orig

    auc = metrics.get("edge_auc_directed", float("nan"))
    return float(auc)


def run_oos_head_validation(
    train_datasets: list,   # list of dicts: {panel, obs_mask, true_relations, sector_adj}
    test_datasets: list,    # list of dicts: same
    n_sectors: int,
    device: str,
    max_epochs: int = 75,
) -> dict:
    """
    Out-of-sample protocol for GraphRelationHead.

    Steps:
    1. For each train dataset: train a fresh head → evaluate in-sample (IS AUC).
    2. For each train head: evaluate on EACH test dataset's true_relations (OOS AUC).
    3. For each test dataset: train a fresh head on it → evaluate in-sample (test IS AUC).
       This is the upper-bound reference for what a head CAN learn from that test data.
    4. Compute permuted null baseline on test data.

    Returns:
        in_sample_aucs       : list of AUCs (one per train dataset, step 1)
        oos_aucs             : list of AUCs (train head vs test relations, step 2)
        test_in_sample_aucs  : list of AUCs (fresh head on test data, step 3)
        mean_in_sample_auc   : float
        mean_oos_auc         : float
        mean_test_in_sample_auc : float
        permuted_baseline    : mean AUC of permuted head on test data
        prevalences          : prevalences from test datasets
    """
    # ── Step 1: Train heads on train datasets ─────────────────────────────────
    train_heads = []
    in_sample_aucs = []

    for i, ds in enumerate(train_datasets):
        head = train_head_fresh(
            ds["panel"], ds["obs_mask"], ds["true_relations"],
            n_sectors, device, max_epochs=max_epochs, seed=100 + i,
        )
        metrics_is = head.edge_metrics(ds["true_relations"], ds.get("sector_adj"))
        auc_is = metrics_is.get("edge_auc_directed", float("nan"))
        in_sample_aucs.append(auc_is)
        train_heads.append(head)

    # ── Step 2: OOS evaluation — each train head on each test dataset ─────────
    oos_aucs = []
    for i, train_head in enumerate(train_heads):
        for j, ds_test in enumerate(test_datasets):
            metrics_oos = train_head.edge_metrics(
                ds_test["true_relations"], ds_test.get("sector_adj")
            )
            auc_oos = metrics_oos.get("edge_auc_directed", float("nan"))
            oos_aucs.append(auc_oos)

    # ── Step 3: Train fresh heads on test datasets ────────────────────────────
    test_in_sample_aucs = []
    test_heads = []
    for i, ds in enumerate(test_datasets):
        head_test = train_head_fresh(
            ds["panel"], ds["obs_mask"], ds["true_relations"],
            n_sectors, device, max_epochs=max_epochs, seed=200 + i,
        )
        metrics_test_is = head_test.edge_metrics(ds["true_relations"], ds.get("sector_adj"))
        auc_test_is = metrics_test_is.get("edge_auc_directed", float("nan"))
        test_in_sample_aucs.append(auc_test_is)
        test_heads.append(head_test)

    # ── Step 4: Permuted null baseline ────────────────────────────────────────
    perm_aucs = []
    rng = np.random.default_rng(42)
    for i, head_test in enumerate(test_heads):
        ds_test = test_datasets[i]
        perm_auc = _permuted_head_auc(
            head_test, ds_test["true_relations"], n_sectors, rng
        )
        perm_aucs.append(perm_auc)

    def _mean(lst: list) -> float:
        valid = [x for x in lst if not math.isnan(x)]
        return float(sum(valid) / len(valid)) if valid else float("nan")

    prevalences = []
    for ds_test in test_datasets:
        metrics = GraphRelationHead(n_sectors).edge_metrics(ds_test["true_relations"], None)
        prevalences.append(metrics.get("prevalence", float("nan")))

    return {
        "in_sample_aucs": in_sample_aucs,
        "oos_aucs": oos_aucs,
        "test_in_sample_aucs": test_in_sample_aucs,
        "mean_in_sample_auc": _mean(in_sample_aucs),
        "mean_oos_auc": _mean(oos_aucs),
        "mean_test_in_sample_auc": _mean(test_in_sample_aucs),
        "permuted_baseline": _mean(perm_aucs),
        "prevalences": prevalences,
        "mean_prevalence": _mean(prevalences),
        "n_train": len(train_datasets),
        "n_test": len(test_datasets),
    }
