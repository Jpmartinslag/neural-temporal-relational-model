"""
run_phase15_300ep.py — 300-epoch continuation for winning variants (DEC-052 authorized).

Continues from existing ep150 checkpoints (no full retrain):
  - TEMPORAL_MASKED_NLL_CLAMPED  (reconstruction winner)
  - GRAPH_MULTITASK_NLL_CLAMPED  (best graph variant by val_loss)

Controls evaluated at inference time (no additional training):
  - nogr      : winning model with adj_s=0, adj_t=0 (no-graph ablation)
  - permuted  : winning model with randomly permuted adj_s/adj_t (null graph)

Seeds, scenarios, masks: same as DEC-051 (5 seeds, novel_lag2/novel_highvar, mcar_30/block_30).

Outputs (in --output-dir/phase15_300ep/):
  zero_shot_300ep.json    — per-seed results with mae, mae_ffill, mae_nogr, mae_permuted
  run_summary_300ep.json  — aggregate table + gate assessments

Usage:
  python -m src.modeles.synthetic.phase15_stable_objective.run_phase15_300ep \\
      --source-dir data/processed/synthetic_benchmark/phase15_stable_objective \\
      --output-dir data/processed/synthetic_benchmark/phase15_stable_objective \\
      --device cpu
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.optim as optim

from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.phase11_generalization.trainer import (
    load_checkpoint,
    checkpoint_hash as _state_hash,
    N_SECTORS,
    N_TERRITORIES,
    HIDDEN_DIM,
    DROPOUT,
)
from src.modeles.synthetic.phase11_generalization.splits import NOVEL_TEST_SCENARIOS  # noqa: F401 (used in evaluate_300ep)
from src.modeles.synthetic.phase15_stable_objective.pretrain_runner_v2 import (
    generate_d2_datasets,
    _build_val_entries,
    _compute_variant_loss,
    _compute_val_loss,
    D2_SEED_START,
    N_PRETRAIN_DATASETS,
)
from src.modeles.synthetic.phase15_stable_objective.graph_heads import GraphAuxHeads
from src.modeles.synthetic.phase15_stable_objective.evaluator_v2 import (
    _ffill_baseline,
    _nogr_baseline,
    _predict,
    EVAL_SCENARIOS,
    EVAL_MASKS,
    EVAL_SEEDS,
)
from src.modeles.synthetic.phase15_stable_objective.loss_functions import log_sigma_stats
from src.data.synthetic.generate_herald_synthetic import generate_dataset
from sklearn.metrics import roc_auc_score

# ── Constants (frozen) ────────────────────────────────────────────────────────
EPOCH_300: int = 300
CONTINUE_FROM: int = 150          # start from ep150 checkpoints
CONTINUE_EPOCHS: int = EPOCH_300 - CONTINUE_FROM  # 150 more epochs
CONTINUATION_LR: float = 5e-4    # lower lr for fine continuation
CONTINUATION_PATIENCE: int = 30   # more patience at this stage

WINNER_VARIANTS: list[str] = [
    "TEMPORAL_MASKED_NLL_CLAMPED",
    "GRAPH_MULTITASK_NLL_CLAMPED",
]

PERMUTED_RNG_SEED: int = 9999     # fixed for reproducible permuted control


def _save_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(path)


def _checkpoint_hash(path: Path) -> str:
    state = torch.load(str(path), map_location="cpu", weights_only=True)
    return _state_hash(state)


def _load_ep150(source_dir: Path, variant: str, device: str) -> HERALDGraphImputerLagged:
    ckpt_path = source_dir / f"model_{variant}_ep{CONTINUE_FROM}.pt"
    if not ckpt_path.exists():
        ckpt_path = source_dir / "checkpoints" / f"model_{variant}_ep{CONTINUE_FROM}.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"ep150 checkpoint not found: {ckpt_path}")
    model = load_checkpoint(ckpt_path, device)
    print(f"  Loaded {ckpt_path.name} (hash {_checkpoint_hash(ckpt_path)[:10]})")
    return model


def _load_heads_ep150(source_dir: Path, variant: str, device: str) -> GraphAuxHeads | None:
    if "GRAPH_MULTITASK" not in variant:
        return None
    heads_path = source_dir / f"heads_{variant}_ep{CONTINUE_FROM}.pt"
    if not heads_path.exists():
        heads_path = source_dir / "checkpoints" / f"heads_{variant}_ep{CONTINUE_FROM}.pt"
    if not heads_path.exists():
        print(f"  [WARN] heads checkpoint not found at {heads_path}, reinitialising")
        return GraphAuxHeads(N_SECTORS).to(device)
    state = torch.load(str(heads_path), map_location=device, weights_only=True)
    heads = GraphAuxHeads(N_SECTORS).to(device)
    heads.load_state_dict(state)
    return heads


def continue_training(
    variant: str,
    source_dir: Path,
    output_dir: Path,
    device: str = "cpu",
    n_datasets: int = N_PRETRAIN_DATASETS,
) -> dict:
    """Continue from ep150 checkpoint to 300 epochs. Returns manifest entry."""
    ckpt_out = output_dir / f"model_{variant}_ep300.pt"
    if ckpt_out.exists():
        print(f"  [SKIP] {ckpt_out.name} already exists")
        model = load_checkpoint(ckpt_out, device)
        val_entries = _build_val_entries()
        val_loss = _compute_val_loss(model, val_entries, device)
        return {
            "checkpoint_path": str(ckpt_out),
            "checkpoint_hash": _checkpoint_hash(ckpt_out),
            "best_epoch": EPOCH_300,
            "best_val_loss": val_loss,
            "variant": variant,
            "epoch_budget": EPOCH_300,
            "heads_path": str(output_dir / f"heads_{variant}_ep300.pt")
                          if (output_dir / f"heads_{variant}_ep300.pt").exists() else None,
        }

    t0 = time.time()
    model = _load_ep150(source_dir, variant, device)
    heads = _load_heads_ep150(source_dir, variant, device)

    entries = generate_d2_datasets(n_datasets, D2_SEED_START)
    val_entries = _build_val_entries()

    params = list(model.parameters())
    if heads is not None:
        params = params + list(heads.parameters())
    optimizer = optim.Adam(params, lr=CONTINUATION_LR)

    best_val = _compute_val_loss(model, val_entries, device)
    best_epoch = CONTINUE_FROM
    best_state = copy.deepcopy(model.state_dict())
    best_heads_state = copy.deepcopy(heads.state_dict()) if heads else None
    no_improve = 0

    print(f"  Starting continuation from ep{CONTINUE_FROM}, val_loss={best_val:.4f}")

    for ep_local in range(CONTINUE_EPOCHS):
        global_ep = CONTINUE_FROM + ep_local
        model.train()
        if heads:
            heads.train()

        ep_rng = np.random.default_rng(1000 + global_ep)  # offset avoids D2-gen rng collision
        order = ep_rng.permutation(len(entries))
        for idx in order:
            optimizer.zero_grad()
            loss = _compute_variant_loss(model, heads, entries[idx], device, variant, ep_rng)
            if torch.isnan(loss) or torch.isinf(loss):
                continue
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
            optimizer.step()

        val_loss = _compute_val_loss(model, val_entries, device)
        if val_loss < best_val - 1e-6:
            best_val = val_loss
            best_epoch = global_ep
            best_state = copy.deepcopy(model.state_dict())
            if heads:
                best_heads_state = copy.deepcopy(heads.state_dict())
            no_improve = 0
            marker = " *"
        else:
            no_improve += 1
            marker = ""
        if (ep_local + 1) % 25 == 0 or no_improve == 0:
            print(f"    ep{global_ep}: val={val_loss:.4f}{marker} (no_improve={no_improve})")
        if no_improve >= CONTINUATION_PATIENCE:
            print(f"    Early stop at ep{global_ep}")
            break

    model.load_state_dict(best_state)
    torch.save(model.state_dict(), ckpt_out)
    if heads is not None and best_heads_state is not None:
        heads.load_state_dict(best_heads_state)
        heads_path = output_dir / f"heads_{variant}_ep300.pt"
        torch.save(heads.state_dict(), heads_path)

    runtime = time.time() - t0
    print(f"  Done. best_epoch={best_epoch}, best_val={best_val:.4f}, {runtime:.0f}s")
    return {
        "checkpoint_path": str(ckpt_out),
        "checkpoint_hash": _checkpoint_hash(ckpt_out),
        "best_epoch": best_epoch,
        "best_val_loss": best_val,
        "runtime_s": runtime,
        "variant": variant,
        "epoch_budget": EPOCH_300,
        "heads_path": str(output_dir / f"heads_{variant}_ep300.pt") if heads else None,
    }


def _permuted_adj(adj: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Row-and-column permutation of adj (preserves sparsity pattern, destroys structure)."""
    n = adj.shape[0]
    perm = rng.permutation(n)
    return adj[np.ix_(perm, perm)]


def _edge_auc(model: HERALDGraphImputerLagged, true_relations: list, device: str) -> float:
    """Edge presence AUC from model attention.

    true_relations is a list[TrueRelation] with .source_sector, .target_sector attributes.
    Builds a binary presence matrix then computes AUC vs model's max(lag1, lag2) attention.
    """
    try:
        lag1 = model.log_sect_attn_lag1.detach().cpu().numpy()
        lag2 = model.log_sect_attn_lag2.detach().cpu().numpy()
        scores = np.maximum(lag1, lag2)
        n_S = scores.shape[0]

        # Build binary presence adj from list[TrueRelation]
        presence = np.zeros((n_S, n_S), dtype=int)
        for r in true_relations:
            presence[r.source_sector, r.target_sector] = 1

        mask_diag = ~np.eye(n_S, dtype=bool)
        y_score = scores[mask_diag]
        y_true = presence[mask_diag]

        if len(np.unique(y_true)) < 2:
            return float("nan")
        return float(roc_auc_score(y_true, y_score))
    except Exception:
        return float("nan")


def evaluate_300ep(
    variant: str,
    ckpt_path: Path,
    device: str,
) -> list[dict]:
    """
    Evaluate a 300-epoch checkpoint zero-shot on NOVEL_TEST_SCENARIOS × NOVEL_TEST_SEEDS × NOVEL_TEST_MASKS.
    For each result, records:
      mae, mae_ffill, mae_nogr (zeroed adj), mae_permuted (shuffled adj),
      log_sigma_min, log_sigma_max, edge_auc
    """
    import dataclasses
    results = []
    perm_rng = np.random.default_rng(PERMUTED_RNG_SEED)

    for scenario_name in EVAL_SCENARIOS:
        base_cfg = NOVEL_TEST_SCENARIOS[scenario_name]
        for seed in EVAL_SEEDS:
            cfg = dataclasses.replace(base_cfg, seed=seed)
            ds = generate_dataset(cfg)
            panel = ds["panel"]
            true_relations = ds.get("true_relations", {})

            for mask_key in EVAL_MASKS:
                if mask_key not in ds["masks"]:
                    continue
                obs_mask = ds["masks"][mask_key]
                adj_s = ds["sector_adj"]
                adj_t = ds["territory_adj"]

                model = load_checkpoint(ckpt_path, device)
                model.eval()

                structural_mask = np.isfinite(panel).astype(np.float32)
                eval_mask = structural_mask * (1 - obs_mask)
                cells = eval_mask == 1
                if cells.sum() == 0:
                    continue

                # Main prediction
                pred_mean, pred_log_sigma = _predict(model, panel, obs_mask, adj_s, adj_t, device)
                mae = float(np.abs(pred_mean[cells] - panel[cells]).mean())

                # log_sigma stats
                ls_t = torch.from_numpy(pred_log_sigma)
                ls_min = float(ls_t.min())
                ls_max = float(ls_t.max())

                # Baselines
                mae_ffill = _ffill_baseline(panel, obs_mask, eval_mask)

                mae_nogr = _nogr_baseline(model, panel, obs_mask, adj_s, adj_t, eval_mask, device)

                perm_s = _permuted_adj(adj_s, perm_rng)
                perm_t = _permuted_adj(adj_t, perm_rng)
                pm_perm, _ = _predict(model, panel, obs_mask, perm_s, perm_t, device)
                mae_permuted = float(np.abs(pm_perm[cells] - panel[cells]).mean())

                # Edge AUC
                edge_auc = _edge_auc(model, true_relations, device)

                results.append({
                    "variant": variant,
                    "epoch_budget": EPOCH_300,
                    "scenario": scenario_name,
                    "seed": seed,
                    "mask_key": mask_key,
                    "mae": mae,
                    "mae_ffill": mae_ffill,
                    "mae_nogr": mae_nogr,
                    "mae_permuted": mae_permuted,
                    "log_sigma_min": ls_min,
                    "log_sigma_max": ls_max,
                    "edge_auc": edge_auc,
                    "beats_ffill": mae < mae_ffill,
                    "beats_nogr": mae < mae_nogr,
                    "beats_permuted": mae < mae_permuted,
                })

    return results


def _aggregate(results: list[dict]) -> dict:
    """Aggregate by (variant, scenario, mask_key)."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in results:
        k = (r["variant"], r["scenario"], r["mask_key"])
        groups[k].append(r)

    agg = {}
    for k, rlist in groups.items():
        maes = [r["mae"] for r in rlist]
        ffills = [r["mae_ffill"] for r in rlist]
        nogrs = [r["mae_nogr"] for r in rlist]
        perms = [r["mae_permuted"] for r in rlist]
        aucs = [r["edge_auc"] for r in rlist if not np.isnan(r["edge_auc"])]
        agg[str(k)] = {
            "mae_mean": float(np.mean(maes)),
            "mae_std": float(np.std(maes)),
            "mae_ffill_mean": float(np.mean(ffills)),
            "mae_nogr_mean": float(np.mean(nogrs)),
            "mae_permuted_mean": float(np.mean(perms)),
            "n_beat_ffill": sum(r["beats_ffill"] for r in rlist),
            "n_beat_nogr": sum(r["beats_nogr"] for r in rlist),
            "n_beat_permuted": sum(r["beats_permuted"] for r in rlist),
            "n_seeds": len(rlist),
            "edge_auc_mean": float(np.mean(aucs)) if aucs else float("nan"),
        }
    return agg


def _print_summary(all_results: list[dict], manifests: dict) -> None:
    agg = _aggregate(all_results)
    print("\n" + "="*70)
    print("300-EPOCH ZERO-SHOT RESULTS")
    print("="*70)
    print(f"{'Key':<55} {'MAE':>6} {'ffill':>6} {'nogr':>6} {'perm':>6} {'AUC':>5}")
    print("-"*70)
    for k in sorted(agg):
        v = agg[k]
        print(f"{k:<55} {v['mae_mean']:6.4f} {v['mae_ffill_mean']:6.4f} "
              f"{v['mae_nogr_mean']:6.4f} {v['mae_permuted_mean']:6.4f} "
              f"{v['edge_auc_mean']:5.3f}")
    print()
    print("Seeds beating ffill / nogr / permuted (out of 5):")
    for k in sorted(agg):
        v = agg[k]
        print(f"  {k}: ffill={v['n_beat_ffill']}/5  nogr={v['n_beat_nogr']}/5  "
              f"perm={v['n_beat_permuted']}/5")

    # Compare with ep150 anchor: TEMPORAL_MASKED_NLL_CLAMPED novel_lag2 mcar_30
    anchor_key = "('TEMPORAL_MASKED_NLL_CLAMPED', 'novel_lag2', 'mcar_30')"
    if anchor_key in agg:
        v = agg[anchor_key]
        ep150_mae = 0.2327  # DEC-052 confirmed value
        delta = v['mae_mean'] - ep150_mae
        direction = "better" if delta < 0 else "worse"
        print(f"\nComparison vs ep150 anchor (TEMPORAL_MASKED novel_lag2 mcar_30):")
        print(f"  ep150 MAE = {ep150_mae:.4f}")
        print(f"  ep300 MAE = {v['mae_mean']:.4f}  (Δ={delta:+.4f}, {direction})")
        if abs(delta) < 0.002:
            print("  VERDICT: plateau reached at ep150 — 300 epochs provide no gain")
        elif delta < 0:
            print("  VERDICT: 300 epochs improve reconstruction (check for overfit via nogr/permuted)")
        else:
            print("  VERDICT: regression — ep150 was better; early-stop to ep150")


def main(args: argparse.Namespace) -> None:
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir) / "phase15_300ep"
    output_dir.mkdir(parents=True, exist_ok=True)
    device = args.device

    print(f"\n[300EP] Source dir: {source_dir}")
    print(f"[300EP] Output dir: {output_dir}")
    print(f"[300EP] Continuing {WINNER_VARIANTS} from ep{CONTINUE_FROM} → ep{EPOCH_300}")

    # Step 1: Continue training
    manifests: dict[str, dict] = {}
    for variant in WINNER_VARIANTS:
        print(f"\n[TRAIN] {variant}")
        entry = continue_training(variant, source_dir, output_dir, device)
        manifests[f"{variant}_ep300"] = entry

    _save_atomic(output_dir / "manifest_300ep.json", manifests)
    print("\n[300EP] Manifest saved.")

    # Step 2: Evaluate
    print("\n[EVAL] Zero-shot evaluation with controls...")
    all_results: list[dict] = []
    for variant in WINNER_VARIANTS:
        ckpt_path = output_dir / f"model_{variant}_ep300.pt"
        if not ckpt_path.exists():
            print(f"  SKIP {variant}: checkpoint not found")
            continue
        print(f"  {variant}...")
        results = evaluate_300ep(variant, ckpt_path, device)
        all_results.extend(results)
        print(f"    {len(results)} results")

    agg = _aggregate(all_results)
    _save_atomic(
        output_dir / "zero_shot_300ep.json",
        {
            "epoch_budget": EPOCH_300,
            "variants": WINNER_VARIANTS,
            "results": all_results,
            "summary": agg,
            "ep150_anchor_mae": 0.2327,
            "permuted_rng_seed": PERMUTED_RNG_SEED,
        }
    )

    _print_summary(all_results, manifests)

    # Final checkpoint hash check
    print("\n[300EP] Final checkpoint hashes:")
    for key, entry in manifests.items():
        p = Path(entry["checkpoint_path"])
        if p.exists():
            h = _checkpoint_hash(p)
            print(f"  {key}: {h[:16]}")

    print(f"\n[300EP] Done. Results in {output_dir}/zero_shot_300ep.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="300-epoch continuation for DEC-052 winners")
    parser.add_argument(
        "--source-dir",
        default="data/processed/synthetic_benchmark/phase15_stable_objective",
        help="Directory with ep150 checkpoints and manifest",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed/synthetic_benchmark/phase15_stable_objective",
        help="Parent of output subdirectory (results go into <output-dir>/phase15_300ep/)",
    )
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    main(args)
