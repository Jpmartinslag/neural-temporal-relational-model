"""
run_dec053.py — Orchestrator for DEC-053 decoupled graph experiment.

Loads a frozen temporal backbone from a Phase 15 checkpoint, trains
GraphRelationHead + GraphMessageExpert + UtilityGate (≤75 epochs),
evaluates 3 modes across seeds {1000,2000,3000} × masks {MCAR,block},
runs fixture tests, evaluates gates D1-D10, writes results JSON.

Usage:
    python -m src.modeles.synthetic.phase16_decoupled.run_dec053 \
        --backbone_path <path/to/model.pt> \
        --n_sectors <int> \
        --out_dir data/processed/phase16_dec053

Safety:
    - backbone is frozen (no gradient)
    - does not retrain the temporal backbone
    - does not modify any Phase 15 files
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.optim as optim

from src.data.synthetic.generate_herald_synthetic import (
    TrueRelation,
    SyntheticConfig,
    generate_dataset,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.phase16_decoupled.evaluator import (
    evaluate_analytic_graph,
    evaluate_fixture_results,
    evaluate_gated_graph_assist,
    evaluate_temporal_reconstruction,
)
from src.modeles.synthetic.phase16_decoupled.fixtures import ALL_FIXTURES
from src.modeles.synthetic.phase16_decoupled.gates_dec053 import (
    evaluate_all_gates,
    format_gate_report,
)
from src.modeles.synthetic.phase16_decoupled.gated_model import GatedGraphModel
from src.modeles.synthetic.phase16_decoupled.loss_functions import decoupled_total_loss

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Frozen hyperparameters ────────────────────────────────────────────────────
MAX_EPOCHS: int = 75
LR: float = 1e-3
BATCH_SIZE: int = 1          # one synthetic dataset per step
SEEDS: list[int] = [1000, 2000, 3000]
MASK_KEYS: list[str] = ["mcar", "block"]
MCAR_RATE: float = 0.30
BLOCK_FRAC: float = 0.30
EARLY_STOP_PATIENCE: int = 10
DEVICE: str = "cpu"          # local experiment, no GPU requirement
N_SECTORS: int = 5           # default; override via --n_sectors


# ── Synthetic data generation ─────────────────────────────────────────────────

def _make_mcar_mask(
    panel: np.ndarray, seed: int, rate: float = MCAR_RATE
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.random(panel.shape) > rate).astype(np.float32)


def _make_block_mask(
    panel: np.ndarray, seed: int, frac: float = BLOCK_FRAC
) -> np.ndarray:
    n_T, n_S, n_Y = panel.shape
    rng = np.random.default_rng(seed + 999)
    mask = np.ones((n_T, n_S, n_Y), dtype=np.float32)
    n_block_years = max(1, int(n_Y * frac))
    for t in range(n_T):
        for s in range(n_S):
            start = rng.integers(0, n_Y - n_block_years + 1)
            mask[t, s, start:start + n_block_years] = 0.0
    return mask


def _gen_dataset(seed: int, n_sectors: int, n_territories: int) -> dict:
    """Generate one synthetic panel matching backbone dimensions."""
    cfg = SyntheticConfig(seed=seed, n_territories=n_territories,
                          n_sectors=n_sectors, n_years=20, frac_nonlinear=0.5)
    return generate_dataset(cfg)


# ── Backbone loading ──────────────────────────────────────────────────────────

def _load_backbone(backbone_path: Path) -> tuple[HERALDGraphImputerLagged, int, int]:
    """Load backbone; infer n_sectors and n_territories from state dict."""
    state = torch.load(backbone_path, map_location="cpu", weights_only=False)
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    # Infer dimensions from parameter shapes
    n_S = state["log_sect_attn_lag1"].shape[0]
    n_T = state["log_terr_attn"].shape[0]
    hidden = state["net.0.weight"].shape[0]
    model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T, hidden_dim=hidden)
    model.load_state_dict(state)
    model.eval()
    return model, n_S, n_T


def _fresh_backbone(n_sectors: int, n_territories: int) -> HERALDGraphImputerLagged:
    """Create a randomly-initialised backbone for fixture testing."""
    m = HERALDGraphImputerLagged(n_sectors=n_sectors, n_territories=n_territories, hidden_dim=32)
    m.eval()
    return m


# ── Training loop ─────────────────────────────────────────────────────────────

def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _train_one(
    model: GatedGraphModel,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    device: str,
    max_epochs: int = MAX_EPOCHS,
    seed: int = 1000,
) -> list[dict]:
    _set_seed(seed)
    params = (
        list(model.graph_relation_head.parameters())
        + list(model.graph_expert.parameters())
        + list(model.gate.parameters())
    )
    opt = optim.Adam(params, lr=LR)
    loss_mask = torch.from_numpy((obs_mask == 0).astype(np.float32)).to(device)
    history = []
    best_loss = math.inf
    patience_count = 0

    for epoch in range(max_epochs):
        model.train()
        opt.zero_grad()
        out = model.forward_tensors(panel, obs_mask, device)
        total_loss, components = decoupled_total_loss(
            out["y_pred"], out["y_temporal"], out["gate"],
            panel, loss_mask, model, true_relations, device,
            compute_utility=False,   # never compute utility during local experiment
        )
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()

        epoch_loss = components["total"]
        history.append({"epoch": epoch, **components})

        if epoch_loss < best_loss - 1e-5:
            best_loss = epoch_loss
            patience_count = 0
        else:
            patience_count += 1
        if patience_count >= EARLY_STOP_PATIENCE:
            log.info(f"Early stop at epoch {epoch} (best loss {best_loss:.4f})")
            break

    return history


# ── Per-seed evaluation ───────────────────────────────────────────────────────

def _eval_seed_mask(
    model: GatedGraphModel,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    true_relations: list,
    sector_adj: np.ndarray | None,
    scenario: str,
    mask_key: str,
    seed: int,
    device: str,
) -> dict:
    model.eval()
    analytic = evaluate_analytic_graph(model, true_relations, sector_adj)
    temporal = evaluate_temporal_reconstruction(model, panel, obs_mask, device)
    gated = evaluate_gated_graph_assist(model, panel, obs_mask, true_relations,
                                         sector_adj, device, seed=seed)
    return {
        "scenario": scenario,
        "mask_key": mask_key,
        "seed": seed,
        **analytic,
        **temporal,
        **{k: v for k, v in gated.items() if k not in temporal},
    }


# ── Fixture evaluation (D3-D6) ────────────────────────────────────────────────

def _eval_fixtures(device: str) -> dict:
    """
    Run fixtures F1-F6. Uses a fresh backbone per fixture (fixture panels have
    n_sectors=3 / n_territories=5, different from the pre-trained backbone).
    Structural properties (gate opening/closing, logit direction) do not depend
    on pre-trained temporal quality.
    """
    fixture_results: dict = {}
    d3_deltas = []

    for make_fn in ALL_FIXTURES:
        panel, obs_mask, true_relations, sector_adj, territory_adj, name = make_fn()
        n_S_fix, n_T_fix = panel.shape[1], panel.shape[0]
        fix_backbone = _fresh_backbone(n_S_fix, n_T_fix)
        fix_model = GatedGraphModel(fix_backbone, n_S_fix, max_residual_frac=0.15).to(device)
        _train_one(fix_model, panel, obs_mask, true_relations, device,
                   max_epochs=MAX_EPOCHS, seed=42)
        res = evaluate_fixture_results(
            fix_model, panel, obs_mask, true_relations, sector_adj, name, device
        )
        fixture_results[name] = res
        if "gate_zero_identity_max_delta" in res:
            d3_deltas.append(res["gate_zero_identity_max_delta"])

    # Aggregate D3 across fixtures
    if d3_deltas:
        fixture_results["gate_zero_identity_max_delta"] = max(d3_deltas)

    return fixture_results


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = DEVICE

    backbone_path = Path(args.backbone_path)
    log.info(f"Loading backbone from {backbone_path}")
    backbone, n_S, n_T = _load_backbone(backbone_path)
    backbone.eval()
    log.info(f"Backbone: n_sectors={n_S}, n_territories={n_T}")

    all_results = []
    t0 = time.time()

    for seed in SEEDS:
        log.info(f"Generating synthetic data seed={seed}")
        data = _gen_dataset(seed, n_sectors=n_S, n_territories=n_T)
        panel: np.ndarray = data["panel"]
        true_relations: list = data["true_relations"]
        sector_adj: np.ndarray = data.get("sector_adj")

        for mask_key in MASK_KEYS:
            log.info(f"  seed={seed} mask={mask_key}")
            if mask_key == "mcar":
                obs_mask = _make_mcar_mask(panel, seed)
            else:
                obs_mask = _make_block_mask(panel, seed)

            model = GatedGraphModel(backbone, n_S).to(device)
            history = _train_one(model, panel, obs_mask, true_relations, device,
                                  max_epochs=MAX_EPOCHS, seed=seed)

            r = _eval_seed_mask(model, panel, obs_mask, true_relations, sector_adj,
                                 scenario="standard", mask_key=mask_key, seed=seed,
                                 device=device)
            r["n_epochs_trained"] = len(history)
            r["final_loss"] = history[-1]["total"] if history else float("nan")
            all_results.append(r)
            log.info(f"    mae_gated={r.get('mae_gated', float('nan')):.4f} "
                     f"mae_temporal={r.get('mae_temporal', float('nan')):.4f} "
                     f"auc={r.get('edge_auc_directed', float('nan')):.3f}")

    elapsed = time.time() - t0
    log.info(f"Main experiment done in {elapsed:.1f}s. Running fixture tests...")

    fixture_results = _eval_fixtures(device)

    eval_results = {"all_results": all_results}
    gates = evaluate_all_gates(eval_results, fixture_results)

    # Serialize gate results
    gate_dict = {}
    for gid, gr in gates.items():
        gate_dict[gid] = {
            "verdict": gr.verdict,
            "description": gr.description,
            "evidence": {
                k: (float(v) if isinstance(v, (float, int)) and not isinstance(v, bool)
                    else (v if not isinstance(v, dict) or all(
                        isinstance(x, (str, int, float, bool, type(None)))
                        for x in v.values()
                    ) else str(v)))
                for k, v in gr.evidence.items()
            },
        }

    results_out = {
        "experiment": "DEC-053",
        "n_epochs_max": MAX_EPOCHS,
        "seeds": SEEDS,
        "mask_keys": MASK_KEYS,
        "n_sectors": n_S,
        "n_territories": n_T,
        "backbone_path": str(backbone_path),
        "elapsed_seconds": elapsed,
        "all_results": all_results,
        "fixture_results": fixture_results,
        "gates": gate_dict,
        "gate_report": format_gate_report(gates),
    }

    out_path = out_dir / "dec053_results.json"
    with open(out_path, "w") as f:
        json.dump(results_out, f, indent=2, default=str)
    log.info(f"Results written to {out_path}")

    print("\n" + format_gate_report(gates))
    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")
    n_fail = sum(1 for g in gates.values() if g.verdict == "FAIL")
    print(f"\nGates: {n_pass}/10 PASS, {n_fail}/10 FAIL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEC-053 decoupled graph experiment")
    parser.add_argument("--backbone_path", required=True,
                        help="Path to Phase 15 model checkpoint (.pt)")
    parser.add_argument("--n_sectors", type=int, default=None,
                        help="Ignored — n_sectors is inferred from the backbone checkpoint")
    parser.add_argument("--out_dir", default="data/processed/phase16_dec053",
                        help="Output directory for results")
    main(parser.parse_args())
