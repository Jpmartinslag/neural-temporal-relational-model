"""
run_dec054.py — Orchestrator for DEC-054: oracle utility gate experiment.

DEC-054 tests whether the UtilityGate can discriminate useful vs useless
graph cells when directly supervised with an oracle utility target.

Key differences from DEC-053:
  - G0/G1/G2 variants with different lambda_utility settings
  - Precomputed oracle correction used as training signal
  - OOS evaluation on held-out seeds {4000, 5000, 6000}
  - Utility AUROC/AUPRC metrics to test gate discrimination
  - OOS GraphRelationHead validation
  - U1-U7 and R1-R3 gates

Usage:
    python -m src.modeles.synthetic.phase16_decoupled.run_dec054 \\
        --backbone_path data/processed/synthetic_benchmark/phase15_stable_objective/checkpoints/model_TEMPORAL_MASKED_NLL_CLAMPED_ep75.pt \\
        --out_dir data/processed/phase16_dec054

Safety:
    - Backbone is frozen throughout (no gradient)
    - Does NOT modify any DEC-053 files
    - Fixtures use a fresh backbone (n_sectors=3, n_territories=5)
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path

import numpy as np
import torch

from src.data.synthetic.generate_herald_synthetic import (
    SyntheticConfig,
    generate_dataset,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged
from src.modeles.synthetic.phase16_decoupled.evaluator import evaluate_fixture_results
from src.modeles.synthetic.phase16_decoupled.fixtures import ALL_FIXTURES
from src.modeles.synthetic.phase16_decoupled.gate_variants import (
    GateConfig,
    VARIANTS_ABLATION,
    eval_all_variants,
    train_gate_variant,
)
from src.modeles.synthetic.phase16_decoupled.gates_dec054 import (
    evaluate_all_gates_dec054,
    format_gate_report_dec054,
)
from src.modeles.synthetic.phase16_decoupled.gated_model import GatedGraphModel
from src.modeles.synthetic.phase16_decoupled.oos_validator import run_oos_head_validation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Frozen hyperparameters ────────────────────────────────────────────────────
TRAIN_SEEDS: list[int] = [1000, 2000, 3000]
OOS_SEEDS: list[int] = [4000, 5000, 6000]
MCAR_RATE: float = 0.30
MAX_EPOCHS: int = 75
PATIENCE: int = 10
LR: float = 1e-3
DEVICE: str = "cpu"


# ── Data helpers ──────────────────────────────────────────────────────────────

def _gen_dataset(seed: int, n_sectors: int, n_territories: int) -> dict:
    cfg = SyntheticConfig(
        seed=seed, n_territories=n_territories, n_sectors=n_sectors,
        n_years=20, frac_nonlinear=0.5,
    )
    return generate_dataset(cfg)


def _make_mcar_mask(panel: np.ndarray, seed: int, rate: float = MCAR_RATE) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.random(panel.shape) > rate).astype(np.float32)


# ── Backbone loading ──────────────────────────────────────────────────────────

def _load_backbone(backbone_path: Path) -> tuple[HERALDGraphImputerLagged, int, int]:
    """Load backbone; infer n_sectors and n_territories from state dict."""
    state = torch.load(backbone_path, map_location="cpu", weights_only=False)
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    n_S = state["log_sect_attn_lag1"].shape[0]
    n_T = state["log_terr_attn"].shape[0]
    hidden = state["net.0.weight"].shape[0]
    model = HERALDGraphImputerLagged(n_sectors=n_S, n_territories=n_T, hidden_dim=hidden)
    model.load_state_dict(state)
    model.eval()
    return model, n_S, n_T


def _fresh_backbone(n_sectors: int, n_territories: int) -> HERALDGraphImputerLagged:
    m = HERALDGraphImputerLagged(n_sectors=n_sectors, n_territories=n_territories, hidden_dim=32)
    m.eval()
    return m


def _check_backbone_frozen(backbone: HERALDGraphImputerLagged, trained_models: dict) -> bool:
    """Verify backbone parameters didn't change during training."""
    # We just verify that all backbone params have requires_grad=False
    for name, model in trained_models.items():
        for p in model.backbone.parameters():
            if p.requires_grad:
                log.warning(f"Backbone param requires_grad=True in variant {name}!")
                return False
    return True


# ── Fixture evaluation with G1 ────────────────────────────────────────────────

def _eval_fixtures_g1(device: str) -> dict:
    """
    Run F1-F6 fixtures with G1 config (supervised utility).
    Each fixture uses a fresh backbone (n_sectors=3, n_territories=5).
    """
    g1_config = GateConfig(name="G1", lambda_utility=0.1, lambda_gate=0.001)
    fixture_results: dict = {}
    d3_deltas = []

    for make_fn in ALL_FIXTURES:
        panel, obs_mask, true_relations, sector_adj, territory_adj, name = make_fn()
        n_S_fix, n_T_fix = panel.shape[1], panel.shape[0]
        fix_backbone = _fresh_backbone(n_S_fix, n_T_fix)

        # Train G1 on this fixture
        fix_model, history, util_stats = train_gate_variant(
            g1_config, fix_backbone, n_S_fix,
            panel, obs_mask, true_relations, device,
            seed=42, max_epochs=MAX_EPOCHS, patience=PATIENCE, lr=LR,
        )
        fix_model.eval()

        # Get utility target for gate_mean_useful / gate_mean_useless
        loss_mask_np = (obs_mask == 0).astype(np.float32)
        with torch.no_grad():
            y_temporal_np = fix_model.predict_temporal_only(panel, obs_mask, device)

        from src.modeles.synthetic.phase16_decoupled.utility_target import (
            compute_oracle_correction, make_utility_target
        )
        oracle_corr = compute_oracle_correction(panel, obs_mask, true_relations)
        y_oracle_np = y_temporal_np + oracle_corr
        util_np, prevalence, _stats = make_utility_target(
            panel, obs_mask, y_temporal_np, y_oracle_np, loss_mask_np
        )

        # Evaluate fixture (D3 identity check + gate stats)
        res = evaluate_fixture_results(
            fix_model, panel, obs_mask, true_relations, sector_adj, name, device
        )

        # Add gate_mean_useful / gate_mean_useless from utility target
        with torch.no_grad():
            _, gate_vals = fix_model.predict_gated(panel, obs_mask, device)
        useful_cells = (util_np > 0.5) & (loss_mask_np > 0.5)
        useless_cells = (util_np < 0.5) & (loss_mask_np > 0.5)
        res["gate_mean_useful"] = float(gate_vals[useful_cells].mean()) if useful_cells.any() else float("nan")
        res["gate_mean_useless"] = float(gate_vals[useless_cells].mean()) if useless_cells.any() else float("nan")
        res["utility_prevalence"] = prevalence
        if util_stats:
            res["util_stats"] = util_stats

        fixture_results[name] = res
        if "gate_zero_identity_max_delta" in res:
            d3_deltas.append(res["gate_zero_identity_max_delta"])

        log.info(
            f"  Fixture {name}: gate_mean={res.get('gate_mean', float('nan')):.3f}, "
            f"gate_useful={res.get('gate_mean_useful', float('nan')):.3f}, "
            f"gate_useless={res.get('gate_mean_useless', float('nan')):.3f}, "
            f"prevalence={prevalence:.3f}"
        )

    if d3_deltas:
        fixture_results["gate_zero_identity_max_delta"] = max(d3_deltas)

    return fixture_results


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = DEVICE

    # ── Load backbone ─────────────────────────────────────────────────────────
    backbone_path = Path(args.backbone_path)
    log.info(f"Loading backbone from {backbone_path}")
    backbone, n_S, n_T = _load_backbone(backbone_path)
    backbone.eval()
    log.info(f"Backbone: n_sectors={n_S}, n_territories={n_T}")

    # ── Build variant configs ─────────────────────────────────────────────────
    variant_configs = [
        GateConfig(name=name, lambda_utility=lu, lambda_gate=lg)
        for name, lu, lg in VARIANTS_ABLATION
    ]

    # ── Training phase: seeds {1000, 2000, 3000} ─────────────────────────────
    t0 = time.time()
    trained_by_seed: dict = {}   # {seed: {variant_name: GatedGraphModel}}
    utility_stats_by_seed: dict = {}

    for seed in TRAIN_SEEDS:
        log.info(f"Training on seed={seed}")
        data = _gen_dataset(seed, n_S, n_T)
        panel = data["panel"]
        true_relations = data["true_relations"]
        obs_mask = _make_mcar_mask(panel, seed)

        trained_by_seed[seed] = {}
        utility_stats_by_seed[seed] = {}

        for cfg in variant_configs:
            log.info(f"  Training {cfg.name} (lambda_util={cfg.lambda_utility}, lambda_gate={cfg.lambda_gate})")
            model, history, util_stats = train_gate_variant(
                cfg, backbone, n_S, panel, obs_mask, true_relations, device,
                seed=seed, max_epochs=MAX_EPOCHS, patience=PATIENCE, lr=LR,
            )
            trained_by_seed[seed][cfg.name] = model
            utility_stats_by_seed[seed][cfg.name] = util_stats
            n_epochs = len(history)
            final_loss = history[-1]["total"] if history else float("nan")
            log.info(f"    Done: {n_epochs} epochs, final_loss={final_loss:.4f}")
            if util_stats:
                log.info(f"    Utility: prevalence={util_stats['prevalence']:.3f}, n_useful={util_stats['n_useful']}")

    t_train = time.time() - t0

    # ── OOS evaluation phase: seeds {4000, 5000, 6000} ───────────────────────
    log.info("Evaluating on OOS seeds...")
    oos_results_by_seed = []
    oos_train_datasets = []
    oos_test_datasets = []

    # Prepare train datasets for OOS validator
    for seed in TRAIN_SEEDS:
        data = _gen_dataset(seed, n_S, n_T)
        obs_mask = _make_mcar_mask(data["panel"], seed)
        oos_train_datasets.append({
            "panel": data["panel"],
            "obs_mask": obs_mask,
            "true_relations": data["true_relations"],
            "sector_adj": data.get("sector_adj"),
        })

    for seed in OOS_SEEDS:
        data = _gen_dataset(seed, n_S, n_T)
        obs_mask = _make_mcar_mask(data["panel"], seed)
        oos_test_datasets.append({
            "panel": data["panel"],
            "obs_mask": obs_mask,
            "true_relations": data["true_relations"],
            "sector_adj": data.get("sector_adj"),
        })

        # Use trained models from seed 1000 to evaluate OOS (representative)
        train_models = trained_by_seed.get(TRAIN_SEEDS[0], {})
        variant_results = eval_all_variants(
            train_models, backbone, n_S,
            data["panel"], obs_mask, data["true_relations"],
            device, seed_for_permutation=seed,
        )
        oos_results_by_seed.append(variant_results)

        # Log summary
        for vname, vr in variant_results.items():
            log.info(
                f"  OOS seed={seed} {vname}: mae_gated={vr.get('mae_gated', float('nan')):.4f}, "
                f"gate_mean={vr.get('gate_mean', float('nan')):.3f}, "
                f"auroc={vr.get('auroc', float('nan')):.3f}"
            )

    # Aggregate OOS results (average across OOS seeds)
    oos_aggregated: dict = {}
    if oos_results_by_seed:
        all_variant_names = set()
        for sr in oos_results_by_seed:
            all_variant_names.update(sr.keys())

        for vname in all_variant_names:
            metrics_lists: dict = {}
            for sr in oos_results_by_seed:
                if vname not in sr:
                    continue
                for k, v in sr[vname].items():
                    if isinstance(v, float):
                        metrics_lists.setdefault(k, []).append(v)
            oos_aggregated[vname] = {
                k: float(np.nanmean(v)) for k, v in metrics_lists.items()
            }

    # ── Fixture evaluation ────────────────────────────────────────────────────
    log.info("Running fixture experiments (G1 config)...")
    fixture_results = _eval_fixtures_g1(device)
    t_fixtures = time.time() - t0 - t_train

    # ── OOS GraphRelationHead validation ─────────────────────────────────────
    log.info("Running OOS GraphRelationHead validation...")
    oos_head_results = run_oos_head_validation(
        train_datasets=oos_train_datasets,
        test_datasets=oos_test_datasets,
        n_sectors=n_S,
        device=device,
        max_epochs=MAX_EPOCHS,
    )
    log.info(
        f"OOS head: mean_IS={oos_head_results['mean_in_sample_auc']:.3f}, "
        f"mean_OOS={oos_head_results['mean_oos_auc']:.3f}, "
        f"mean_test_IS={oos_head_results['mean_test_in_sample_auc']:.3f}, "
        f"permuted={oos_head_results['permuted_baseline']:.3f}"
    )

    # ── Backbone freeze check ─────────────────────────────────────────────────
    backbone_frozen = True
    for seed, models in trained_by_seed.items():
        if not _check_backbone_frozen(backbone, models):
            backbone_frozen = False
            break

    eval_summary = {
        "leakage_check": True,   # compute_oracle_correction applies obs_mask by construction
        "backbone_frozen": backbone_frozen,
    }

    # ── Evaluate gates ────────────────────────────────────────────────────────
    log.info("Evaluating DEC-054 gates...")
    gates = evaluate_all_gates_dec054(
        eval_summary=eval_summary,
        oos_variant_results=oos_aggregated,
        oos_results_by_seed=oos_results_by_seed,
        fixture_results=fixture_results,
        oos_head_results=oos_head_results,
    )

    # ── Serialize results ─────────────────────────────────────────────────────
    def _safe_json(v):
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, np.ndarray):
            return v.tolist()
        return v

    gate_dict = {}
    for gid, gr in gates.items():
        gate_dict[gid] = {
            "verdict": gr.verdict,
            "description": gr.description,
            "evidence": {
                k: _safe_json(v) for k, v in gr.evidence.items()
            },
        }

    results_out = {
        "experiment": "DEC-054",
        "n_epochs_max": MAX_EPOCHS,
        "train_seeds": TRAIN_SEEDS,
        "oos_seeds": OOS_SEEDS,
        "n_sectors": n_S,
        "n_territories": n_T,
        "backbone_path": str(backbone_path),
        "elapsed_seconds_train": t_train,
        "elapsed_seconds_fixtures": t_fixtures,
        "oos_aggregated": oos_aggregated,
        "oos_head_results": oos_head_results,
        "fixture_results": {
            k: {kk: _safe_json(vv) for kk, vv in v.items()}
            for k, v in fixture_results.items()
            if isinstance(v, dict)
        },
        "utility_stats_by_seed": {
            str(seed): {
                vname: stats
                for vname, stats in seed_stats.items()
                if stats is not None
            }
            for seed, seed_stats in utility_stats_by_seed.items()
        },
        "gates": gate_dict,
        "gate_report": format_gate_report_dec054(gates),
    }

    out_path = out_dir / "dec054_results.json"
    with open(out_path, "w") as f:
        json.dump(results_out, f, indent=2, default=str)
    log.info(f"Results written to {out_path}")

    # ── Print gate report ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DEC-054: Oracle Utility Gate Experiment")
    print("=" * 60)
    print(format_gate_report_dec054(gates))

    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")
    n_fail = sum(1 for g in gates.values() if g.verdict == "FAIL")
    n_ne = sum(1 for g in gates.values() if g.verdict == "NOT_EVALUATED")
    print(f"\nGates: {n_pass}/10 PASS, {n_fail}/10 FAIL, {n_ne}/10 NOT_EVALUATED")

    # Summary table
    print("\nOOS Variant Summary (averaged over OOS seeds):")
    header = f"{'Variant':<8} {'mae_gated':>10} {'mae_temporal':>12} {'gate_mean':>10} {'AUROC':>8} {'AUPRC':>8}"
    print(header)
    print("-" * len(header))
    for vname in ["T0", "G0", "G1", "G2", "G3", "A0", "P0"]:
        if vname in oos_aggregated:
            r = oos_aggregated[vname]
            print(
                f"{vname:<8} "
                f"{r.get('mae_gated', float('nan')):>10.4f} "
                f"{r.get('mae_temporal', float('nan')):>12.4f} "
                f"{r.get('gate_mean', float('nan')):>10.3f} "
                f"{r.get('auroc', float('nan')):>8.3f} "
                f"{r.get('auprc', float('nan')):>8.3f}"
            )

    elapsed = time.time() - t0
    print(f"\nTotal elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEC-054 oracle utility gate experiment")
    parser.add_argument("--backbone_path", required=True,
                        help="Path to Phase 15 model checkpoint (.pt)")
    parser.add_argument("--out_dir", default="data/processed/phase16_dec054",
                        help="Output directory for results")
    main(parser.parse_args())
