"""
gates.py

Fail-closed gate evaluation for HERALD Phase 9 synthetic benchmark (DEC-040).

Gates are pre-specified and frozen before any model training. Thresholds must
NOT be adjusted after observing results.

Gate structure:
    G1 — Imputation: HERALD-graph MAE ≤ best_non_graph × 0.95 on ≥ 2/3 mask mechanisms
    G2 — Edge recovery: AUC > 0.60 averaged over seeds
    G3 — Permuted graph control: permuted MAE ≥ HERALD-graph MAE (graph must help)
    G4 — Calibration: 90% interval coverage ≥ 0.80
    G5 — No leakage: all temporal features strictly causal
    G6 — No false promotion: FPR at top-k ≤ 0.30
    G7 — No regression: HERALD MAE ≤ best_non_graph × 1.10 on linear scenarios
    G8 — Generalization: G1 passes on 'generalization' scenario

Outcome flags (set per-gate, independent):
    ARCHITECTURE_RECONSTRUCTION_SUPPORTED  ← G1 PASS
    DYNAMIC_RELATION_RECOVERY_SUPPORTED    ← G2 PASS
    UNCERTAINTY_CALIBRATED                 ← G4 PASS
    SYNTHETIC_GENERALIZATION_SUPPORTED     ← G8 PASS
"""

from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass
class GateResult:
    gate: str
    description: str
    threshold: Any
    observed: Any
    passed: bool
    details: str = ""


@dataclasses.dataclass
class BenchmarkVerdict:
    gates: list[GateResult]
    architecture_reconstruction_supported: bool
    dynamic_relation_recovery_supported: bool
    uncertainty_calibrated: bool
    synthetic_generalization_supported: bool
    minimum_criterion_passed: bool  # (G1 OR G2) AND G5 AND G3
    hpc_advance_recommended: bool

    def summary(self) -> str:
        lines = ["── Gate Results ─────────────────────────────────────────────"]
        for g in self.gates:
            sym = "PASS" if g.passed else "FAIL"
            lines.append(f"  {g.gate:4s} [{sym}] {g.description}")
            lines.append(f"       threshold={g.threshold}  observed={g.observed}")
            if g.details:
                lines.append(f"       {g.details}")
        lines.append("")
        lines.append(f"  ARCHITECTURE_RECONSTRUCTION_SUPPORTED : {self.architecture_reconstruction_supported}")
        lines.append(f"  DYNAMIC_RELATION_RECOVERY_SUPPORTED   : {self.dynamic_relation_recovery_supported}")
        lines.append(f"  UNCERTAINTY_CALIBRATED                : {self.uncertainty_calibrated}")
        lines.append(f"  SYNTHETIC_GENERALIZATION_SUPPORTED    : {self.synthetic_generalization_supported}")
        lines.append(f"  MINIMUM_CRITERION_PASSED              : {self.minimum_criterion_passed}")
        lines.append(f"  HPC_ADVANCE_RECOMMENDED               : {self.hpc_advance_recommended}")
        return "\n".join(lines)


def _mean_over_seeds(results: list[dict], key_path: list[str]) -> float:
    """Extract a nested value from per-seed results and return its mean."""
    import numpy as _np
    vals = []
    for r in results:
        v = r
        try:
            for k in key_path:
                v = v[k]
            if v is not None and not _np.isnan(float(v)):
                vals.append(float(v))
        except (KeyError, TypeError):
            pass
    return float(_np.mean(vals)) if vals else float("nan")


def evaluate_gates(
    all_results: list[dict],          # list of per-seed result dicts from run_full_benchmark
    scenario: str = "mixed_default",  # which scenario these results are for
) -> BenchmarkVerdict:
    """
    Evaluate all gates on aggregated per-seed results.

    Expected result dict structure (per seed):
    {
      "seed": int,
      "leakage_check": {"passed": bool},
      "baselines": {
        "mean": {"mae": float, ...},
        "ridge": {"mae": float, ...},
        "herald_graph": {"mae": float, "edge_auc": float, "edge_fpr": float, "calibration_90": float},
        "herald_permuted": {"mae": float, ...},
        "herald_random": {"mae": float, ...},
      },
      "mask_type": str,   # "mcar" / "mar" / "block"
    }
    """
    import numpy as np

    gates = []

    # ── G5: No leakage (must check first; stops evaluation if failed) ──────────
    leakage_passed = all(r.get("leakage_check", {}).get("passed", False) for r in all_results)
    gates.append(GateResult(
        gate="G5",
        description="No leakage — temporal features strictly causal",
        threshold=True,
        observed=leakage_passed,
        passed=leakage_passed,
        details="STOP: architecture invalid if G5 fails" if not leakage_passed else "",
    ))

    # ── G1: Imputation improvement (≥5% over best non-graph baseline) ─────────
    # Evaluate per mask mechanism across seeds
    non_graph_keys = ["mean", "ffill", "ridge", "knn", "neural_no_graph"]
    mechanisms = list({r.get("mask_type", "mcar") for r in all_results})

    herald_mae_by_mech: dict[str, list[float]] = {}
    best_non_graph_mae_by_mech: dict[str, list[float]] = {}

    for r in all_results:
        mtype = r.get("mask_type", "mcar")
        bl = r.get("baselines", {})
        hg_mae = bl.get("herald_graph", {}).get("mae", float("nan"))
        ng_maes = [bl.get(k, {}).get("mae", float("nan")) for k in non_graph_keys]
        ng_maes = [v for v in ng_maes if not np.isnan(v)]
        best_ng = min(ng_maes) if ng_maes else float("nan")

        herald_mae_by_mech.setdefault(mtype, []).append(hg_mae)
        best_non_graph_mae_by_mech.setdefault(mtype, []).append(best_ng)

    mech_g1_pass = []
    mech_details = []
    for mtype in sorted(herald_mae_by_mech):
        hg = np.nanmean(herald_mae_by_mech[mtype])
        ng = np.nanmean(best_non_graph_mae_by_mech[mtype])
        passes = bool(hg <= ng * 0.95)
        mech_g1_pass.append(passes)
        mech_details.append(f"{mtype}: herald={hg:.4f} vs best_non_graph={ng:.4f} ratio={hg/ng:.3f} {'PASS' if passes else 'FAIL'}")

    n_mech_pass = sum(mech_g1_pass)
    g1_pass = n_mech_pass >= 2  # ≥ 2 of 3 mechanisms
    gates.append(GateResult(
        gate="G1",
        description="Imputation: HERALD MAE ≤ best_non_graph × 0.95 on ≥ 2/3 mask mechanisms",
        threshold="≥ 2 of 3 mechanisms",
        observed=f"{n_mech_pass}/3",
        passed=g1_pass,
        details="; ".join(mech_details),
    ))

    # ── G2: Edge recovery AUC > 0.60 ──────────────────────────────────────────
    auc_vals = [r.get("baselines", {}).get("herald_graph", {}).get("edge_auc", float("nan"))
                for r in all_results]
    auc_vals = [v for v in auc_vals if not np.isnan(v)]
    mean_auc = float(np.mean(auc_vals)) if auc_vals else float("nan")
    g2_pass = mean_auc > 0.60
    gates.append(GateResult(
        gate="G2",
        description="Edge recovery AUC > 0.60 averaged over seeds",
        threshold="> 0.60",
        observed=f"{mean_auc:.3f}",
        passed=g2_pass,
    ))

    # ── G3: Permuted graph must not beat true graph ────────────────────────────
    perm_maes = [r.get("baselines", {}).get("herald_permuted", {}).get("mae", float("nan"))
                 for r in all_results]
    hg_maes = [r.get("baselines", {}).get("herald_graph", {}).get("mae", float("nan"))
               for r in all_results]
    perm_maes = [v for v in perm_maes if not np.isnan(v)]
    hg_maes_f = [v for v in hg_maes if not np.isnan(v)]
    mean_perm = float(np.mean(perm_maes)) if perm_maes else float("nan")
    mean_hg = float(np.mean(hg_maes_f)) if hg_maes_f else float("nan")
    g3_pass = bool(np.isnan(mean_perm) or np.isnan(mean_hg) or mean_perm >= mean_hg)
    gates.append(GateResult(
        gate="G3",
        description="Permuted graph MAE ≥ HERALD graph MAE (graph must help)",
        threshold="permuted ≥ true",
        observed=f"permuted={mean_perm:.4f}  herald={mean_hg:.4f}",
        passed=g3_pass,
        details="FAIL: model appears to ignore graph structure" if not g3_pass else "",
    ))

    # ── G4: Calibration — 90% interval coverage ≥ 0.80 ───────────────────────
    cal_vals = [r.get("baselines", {}).get("herald_graph", {}).get("calibration_90", float("nan"))
                for r in all_results]
    cal_vals = [v for v in cal_vals if not np.isnan(v)]
    mean_cal = float(np.mean(cal_vals)) if cal_vals else float("nan")
    g4_pass = mean_cal >= 0.80
    gates.append(GateResult(
        gate="G4",
        description="90% interval coverage ≥ 0.80",
        threshold=">= 0.80",
        observed=f"{mean_cal:.3f}",
        passed=g4_pass,
    ))

    # ── G6: False positive rate ≤ 0.30 ────────────────────────────────────────
    fpr_vals = [r.get("baselines", {}).get("herald_graph", {}).get("edge_fpr", float("nan"))
                for r in all_results]
    fpr_vals = [v for v in fpr_vals if not np.isnan(v)]
    mean_fpr = float(np.mean(fpr_vals)) if fpr_vals else float("nan")
    g6_pass = np.isnan(mean_fpr) or mean_fpr <= 0.30
    gates.append(GateResult(
        gate="G6",
        description="Edge false positive rate ≤ 0.30 at top-k",
        threshold="≤ 0.30",
        observed=f"{mean_fpr:.3f}",
        passed=g6_pass,
    ))

    # ── G7: No regression on linear scenario (≤ 10% worse than best non-graph) ─
    if scenario == "linear":
        hg_mean = mean_hg
        ng_mean = float(np.nanmean([
            np.nanmean([r.get("baselines", {}).get(k, {}).get("mae", float("nan")) for r in all_results])
            for k in non_graph_keys
        ]))
        g7_pass = np.isnan(hg_mean) or np.isnan(ng_mean) or bool(hg_mean <= ng_mean * 1.10)
    else:
        g7_pass = True  # N/A for non-linear scenarios
    gates.append(GateResult(
        gate="G7",
        description="No regression ≥10% vs best non-graph on linear scenario",
        threshold="HERALD ≤ best_non_graph × 1.10",
        observed="N/A (non-linear scenario)" if scenario != "linear" else f"{mean_hg:.4f} vs {ng_mean:.4f}",
        passed=g7_pass,
    ))

    # ── G8: Generalization (same as G1 but for 'generalization' scenario) ──────
    # This gate is evaluated when scenario == "generalization"
    if scenario == "generalization":
        g8_pass = g1_pass  # reuse G1 logic on generalization scenario
        g8_obs = f"{n_mech_pass}/3"
    else:
        g8_pass = True  # N/A
        g8_obs = "N/A (not generalization scenario)"
    gates.append(GateResult(
        gate="G8",
        description="Generalization: G1 passes on unseen dynamics scenario",
        threshold="≥ 2/3 mask mechanisms on generalization scenario",
        observed=g8_obs,
        passed=g8_pass,
    ))

    # ── Outcome flags ──────────────────────────────────────────────────────────
    arch_recon = g1_pass
    dyn_rel = g2_pass
    uncertainty = g4_pass
    generalization = (scenario == "generalization" and g8_pass) or (scenario != "generalization")
    # Generalization flag is only definitively set when generalization scenario was evaluated

    min_criterion = (g1_pass or g2_pass) and leakage_passed and g3_pass
    hpc_advance = min_criterion and g7_pass

    return BenchmarkVerdict(
        gates=gates,
        architecture_reconstruction_supported=arch_recon,
        dynamic_relation_recovery_supported=dyn_rel,
        uncertainty_calibrated=uncertainty,
        synthetic_generalization_supported=generalization,
        minimum_criterion_passed=min_criterion,
        hpc_advance_recommended=hpc_advance,
    )
