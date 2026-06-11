"""HERALD — One-fold smoke test for the frugal dual-graph model.

Purpose
-------
Local execution sanity only. Uses the FR/2021 fold, one seed, at most 20
epochs, and compares four control variants:

  1. temporal encoder without graphs;
  2. territory graph only;
  3. learned sector graph only;
  4. full dual graph.

It validates that each variant runs, produces finite losses and gradients,
emits all required outputs, and never touches the target year in the feature
sequence (leakage check). It does NOT authorize any scientific claim: no
metric reported here is a result, only a liveness signal.

Run (mlearning env):
  /home/jpdark/miniconda3/envs/mlearning/bin/python \
    -m src.modeles.run_dual_graph_smoke
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from src.modeles.dual_graph_models import (
    build_dual_graph_model,
    compute_class_weights,
    compute_pos_weight,
    count_parameters,
    dual_graph_loss,
)

BASE = Path(__file__).resolve().parents[2]
FOLD = BASE / "data/processed/dual_graph_tensors/fr_2021.npz"
EVAL_YEAR = 2021
SEED = 42
MAX_EPOCHS = 20

VARIANTS = {
    "no_graph": dict(use_territory_graph=False, use_sector_graph=False),
    "territory_only": dict(use_territory_graph=True, use_sector_graph=False),
    "sector_only": dict(use_territory_graph=False, use_sector_graph=True),
    "dual_graph": dict(use_territory_graph=True, use_sector_graph=True),
}


def _load_fold(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    return {key: data[key] for key in data.files}


def _to_tensors(fold: dict[str, np.ndarray]) -> tuple[dict, dict]:
    f = lambda a: torch.tensor(np.asarray(a))  # noqa: E731
    batch = {
        "features_seq": f(fold["features_seq"]).float(),
        "feature_mask_seq": f(fold["feature_mask_seq"]),
        "territory_adj_seq": f(fold["territory_adj_seq"]).float(),
        "territory_adj_mask": f(fold["territory_adj_mask"]),
    }
    targets = {
        "target_log_growth": f(fold["target_log_growth"]).float(),
        "target_regime": f(fold["target_regime"]).long(),
        "target_recovery": f(fold["target_recovery"]).long(),
        "target_emergence": f(fold["target_emergence"]).long(),
        "target_mask": f(fold["target_mask"]),
    }
    return batch, targets


def _slice(d: dict, idx) -> dict:
    return {k: v[idx] for k, v in d.items()}


def _assert_no_leakage(fold: dict[str, np.ndarray]) -> None:
    max_src = int(fold["observation_years"].max())
    if max_src >= EVAL_YEAR:
        raise RuntimeError(
            f"LEAKAGE: max source year {max_src} >= eval_year {EVAL_YEAR}"
        )
    print(f"  leakage check: max source year {max_src} < eval_year {EVAL_YEAR}  OK")


def _train_variant(name: str, flags: dict, batch: dict, targets: dict,
                  train_idx, eval_idx) -> dict:
    torch.manual_seed(SEED)
    model = build_dual_graph_model(hidden_dim=8, **flags)
    n_params = count_parameters(model)

    tr_batch, tr_targets = _slice(batch, train_idx), _slice(targets, train_idx)
    ev_batch, ev_targets = _slice(batch, eval_idx), _slice(targets, eval_idx)

    # Class weights and positive weights from TRAINING labels only.
    cw = compute_class_weights(tr_targets["target_regime"], 3)
    rpw = compute_pos_weight(tr_targets["target_recovery"])
    epw = compute_pos_weight(tr_targets["target_emergence"])

    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    model.train()
    finite_losses = True
    finite_grads = True
    for _ in range(MAX_EPOCHS):
        opt.zero_grad()
        out = model(
            tr_batch["features_seq"], tr_batch["feature_mask_seq"],
            tr_batch["territory_adj_seq"], tr_batch["territory_adj_mask"],
        )
        losses = dual_graph_loss(
            out, tr_targets, tr_targets["target_mask"],
            class_weights=cw, recovery_pos_weight=rpw, emergence_pos_weight=epw,
        )
        if not torch.isfinite(losses["total"]):
            finite_losses = False
            break
        losses["total"].backward()
        for p in model.parameters():
            if p.grad is not None and not torch.isfinite(p.grad).all():
                finite_grads = False
        opt.step()

    # Eval on held-out outer year (no gradient).
    model.eval()
    with torch.no_grad():
        out = model(
            ev_batch["features_seq"], ev_batch["feature_mask_seq"],
            ev_batch["territory_adj_seq"], ev_batch["territory_adj_mask"],
        )
        ev_losses = dual_graph_loss(
            out, ev_targets, ev_targets["target_mask"],
            class_weights=cw, recovery_pos_weight=rpw, emergence_pos_weight=epw,
        )
        m = ev_targets["target_mask"].bool() & torch.isfinite(
            ev_targets["target_log_growth"]
        )
        mae = float(
            (out["pred_log_growth"][m] - ev_targets["target_log_growth"][m]).abs().mean()
        )
        outputs_finite = all(torch.isfinite(v).all() for v in out.values())
        required = {
            "pred_log_growth", "regime_logits", "recovery_logits",
            "emergence_logits", "node_embeddings", "territory_embeddings",
            "sector_embeddings", "sector_adj_learned",
        }
        outputs_complete = required.issubset(out.keys())

    return {
        "name": name,
        "n_params": n_params,
        "finite_losses": finite_losses,
        "finite_grads": finite_grads,
        "outputs_finite": outputs_finite,
        "outputs_complete": outputs_complete,
        "eval_total": float(ev_losses["total"]),
        "eval_growth_mae": mae,
    }


def main() -> None:
    print(f"Dual-graph smoke test — fold {FOLD.name}, seed {SEED}, "
          f"<= {MAX_EPOCHS} epochs")
    if not FOLD.exists():
        raise FileNotFoundError(f"Missing fold tensor: {FOLD}")

    fold = _load_fold(FOLD)
    _assert_no_leakage(fold)
    batch, targets = _to_tensors(fold)

    B = batch["features_seq"].shape[0]
    train_idx = list(range(B - 1))   # historical samples
    eval_idx = [B - 1]               # outer evaluation year
    print(f"  samples: {B} (train {len(train_idx)}, eval 1)")
    print(f"  shapes: features {tuple(batch['features_seq'].shape)}, "
          f"territory_adj {tuple(batch['territory_adj_seq'].shape)}")

    results = []
    for name, flags in VARIANTS.items():
        print(f"\n[{name}]")
        res = _train_variant(name, flags, batch, targets, train_idx, eval_idx)
        results.append(res)
        print(f"  params={res['n_params']}  finite_losses={res['finite_losses']}  "
              f"finite_grads={res['finite_grads']}  "
              f"outputs_finite={res['outputs_finite']}  "
              f"outputs_complete={res['outputs_complete']}")
        print(f"  eval_total={res['eval_total']:.5f}  "
              f"eval_growth_mae={res['eval_growth_mae']:.5f}")

    print("\n" + "=" * 64)
    print(f"{'variant':<16}{'params':>8}{'eval_total':>14}{'growth_mae':>14}")
    for r in results:
        print(f"{r['name']:<16}{r['n_params']:>8}"
              f"{r['eval_total']:>14.5f}{r['eval_growth_mae']:>14.5f}")
    print("=" * 64)

    all_ok = all(
        r["finite_losses"] and r["finite_grads"] and r["outputs_finite"]
        and r["outputs_complete"] and r["n_params"] <= 10_000
        for r in results
    )
    print(f"\nSMOKE {'PASS' if all_ok else 'FAIL'} — liveness only, no scientific claim.")
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
