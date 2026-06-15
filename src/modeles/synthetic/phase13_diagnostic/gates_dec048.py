"""
gates_dec048.py — C1-C10 gates for DEC-048 (frozen before execution).

Thresholds FROZEN before execution — do NOT change after seeing results:
  MAE_RATIO_THRESHOLD    = 1.0   (C2: oracle must beat ffill, ratio < 1.0)
  DATA_SCALING_MIN_GAIN  = 0.005 (C3: ≥0.5% MAE improvement per doubling)
  DIVERSITY_MIN_GAIN     = 0.005 (C4: D2 beats D0 by ≥0.5% MAE)
  PRETRAINING_MIN_GAIN   = 0.005 (C5: pretraining beats no-pretraining)
  GRAPH_VS_NOGRAPH_THRESHOLD = 0.01 (C6: graph objective beats temporal-only by ≥1%)
  AUC_THRESHOLD          = 0.60  (C7: edge AUC ≥ 0.60)
  BLOCK_THRESHOLD        = 0.01  (C8: gain in block_30 ≥ 1% of ffill MAE)
  SHIFT_CURVE_MIN_STEPS  = 2     (C9: ≥2 shift levels show progressive degradation)
  BASELINE_RATIO         = 1.0   (C10: model beats ffill, ratio < 1.0)
  SEED_PASS_FRAC         = 2/3   (majority of seeds must agree)
"""

from __future__ import annotations

import numpy as np


# ── Frozen thresholds ──────────────────────────────────────────────────────────

MAE_RATIO_THRESHOLD = 1.0       # C2: oracle_mae / ffill_mae < 1.0
DATA_SCALING_MIN_GAIN = 0.005   # C3: MAE reduction per doubling of datasets
DIVERSITY_MIN_GAIN = 0.005      # C4: D2 MAE < D0 MAE by at least this
PRETRAINING_MIN_GAIN = 0.005    # C5: pretrained MAE < no-pretrain MAE by at least this
GRAPH_VS_NOGRAPH_THRESHOLD = 0.01  # C6: L2/L3 MAE < L0/L1 MAE by at least this
AUC_THRESHOLD = 0.60            # C7: edge AUC >= 0.60
BLOCK_THRESHOLD = 0.01          # C8: block_30 gain >= 1% of ffill MAE
SHIFT_CURVE_MIN_STEPS = 2       # C9: progressive degradation steps
BASELINE_RATIO = 1.0            # C10: any model beats ffill
SEED_PASS_FRAC = 2 / 3          # majority of seeds must agree


def _mean_mae(records: list[dict], filters: dict | None = None) -> float:
    """Mean MAE from records list with optional filter kwargs."""
    filtered = records
    if filters:
        for k, v in filters.items():
            filtered = [r for r in filtered if r.get(k) == v]
    maes = [r["mae"] for r in filtered if "mae" in r and not np.isnan(r["mae"])]
    return float(np.mean(maes)) if maes else float("nan")


def _majority_pass(values: list[bool]) -> bool:
    """True if at least SEED_PASS_FRAC fraction pass."""
    if not values:
        return False
    return sum(values) / len(values) >= SEED_PASS_FRAC


def evaluate_gates(
    functional_result: dict,
    axis_d_records: list[dict],
    axis_m_records: list[dict],
    axis_l_records: list[dict],
    axis_s_records: list[dict],
    pretraining_records: list[dict],
) -> dict:
    """
    Evaluate C1-C10 gates and return gate report.

    Returns:
      {
        "C1": {"result": "PASS"|"FAIL"|"NA", "note": str, "evidence": ...},
        ...
        "C10": {...},
        "decision": str,
        "principal_cause": str,
        "next_step": str,
      }
    """
    gates: dict[str, dict] = {}

    # ── C1: No NaN/Inf in any record ─────────────────────────────────────────
    all_records = axis_d_records + axis_m_records + axis_l_records + axis_s_records + pretraining_records
    nan_count = sum(
        1 for r in all_records
        if any(
            (isinstance(r.get(k), float) and (np.isnan(r[k]) or np.isinf(r[k])))
            for k in ["mae", "edge_auc"]
            if k in r and r[k] is not None
        )
    )
    # Allow NaN in edge_auc when AUC is genuinely not computable (no true edges)
    real_nan = sum(
        1 for r in all_records
        if "mae" in r and isinstance(r["mae"], float) and (np.isnan(r["mae"]) or np.isinf(r["mae"]))
    )
    gates["C1"] = {
        "result": "PASS" if real_nan == 0 else "FAIL",
        "note": f"{real_nan} records with NaN/Inf MAE out of {len(all_records)}",
        "evidence": {"nan_mae_count": real_nan, "total_records": len(all_records)},
    }

    # ── C2: Oracle beats ffill in functional scenario ─────────────────────────
    oracle_mae = functional_result.get("oracle_mae", float("nan"))
    ffill_mae_func = functional_result.get("ffill_mae", float("nan"))
    oracle_ratio = functional_result.get("oracle_ratio", float("nan"))
    c2_pass = functional_result.get("gate_c2_pass", False)

    gates["C2"] = {
        "result": "PASS" if c2_pass else "FAIL",
        "note": (
            f"oracle_mae={oracle_mae:.4f} vs ffill_mae={ffill_mae_func:.4f}, "
            f"ratio={oracle_ratio:.3f}"
        ),
        "evidence": {
            "oracle_mae": oracle_mae,
            "ffill_mae": ffill_mae_func,
            "oracle_ratio": oracle_ratio,
            "threshold": MAE_RATIO_THRESHOLD,
        },
        "stop_if_fail": True,
    }

    # ── C3: Data scaling benefit ──────────────────────────────────────────────
    # Compare best diversity at n=10 vs n=25, same diversity
    c3_pass_per_diversity = []
    c3_evidence = {}
    if axis_d_records:
        for diversity in ["D0", "D1", "D2"]:
            mae_10 = _mean_mae(axis_d_records, {"n_datasets": 10, "diversity": diversity})
            mae_25 = _mean_mae(axis_d_records, {"n_datasets": 25, "diversity": diversity})
            if not np.isnan(mae_10) and not np.isnan(mae_25) and mae_10 > 0:
                gain = (mae_10 - mae_25) / mae_10
                c3_pass_per_diversity.append(gain >= DATA_SCALING_MIN_GAIN)
                c3_evidence[diversity] = {"mae_10": mae_10, "mae_25": mae_25, "gain": gain}
    c3_pass = _majority_pass(c3_pass_per_diversity) if c3_pass_per_diversity else False
    gates["C3"] = {
        "result": "PASS" if c3_pass else "FAIL",
        "note": f"Data scaling gain (10→25 datasets): {len([x for x in c3_pass_per_diversity if x])}/{len(c3_pass_per_diversity)} diversity levels pass",
        "evidence": c3_evidence,
    }

    # ── C4: Diversity benefit (D2 vs D0) ─────────────────────────────────────
    c4_pass_per_n = []
    c4_evidence = {}
    if axis_d_records:
        for n_ds in [10, 25]:
            mae_d0 = _mean_mae(axis_d_records, {"n_datasets": n_ds, "diversity": "D0"})
            mae_d2 = _mean_mae(axis_d_records, {"n_datasets": n_ds, "diversity": "D2"})
            if not np.isnan(mae_d0) and not np.isnan(mae_d2) and mae_d0 > 0:
                gain = (mae_d0 - mae_d2) / mae_d0
                c4_pass_per_n.append(gain >= DIVERSITY_MIN_GAIN)
                c4_evidence[f"n={n_ds}"] = {"mae_d0": mae_d0, "mae_d2": mae_d2, "gain": gain}
    c4_pass = _majority_pass(c4_pass_per_n) if c4_pass_per_n else False
    gates["C4"] = {
        "result": "PASS" if c4_pass else "FAIL",
        "note": f"Diversity gain (D0→D2): {len([x for x in c4_pass_per_n if x])}/{len(c4_pass_per_n)} dataset sizes pass",
        "evidence": c4_evidence,
    }

    # ── C5: Pretraining benefit ───────────────────────────────────────────────
    c5_evidence = {}
    if pretraining_records:
        mae_no_pretrain = _mean_mae(pretraining_records, {"variant": "NO_PRETRAINING"})
        mae_temporal = _mean_mae(pretraining_records, {"variant": "TEMPORAL_MASKED"})
        mae_graph = _mean_mae(pretraining_records, {"variant": "GRAPH_MASKED_MULTITASK"})
        best_pretrain = min(
            (m for m in [mae_temporal, mae_graph] if not np.isnan(m)),
            default=float("nan")
        )
        if not np.isnan(mae_no_pretrain) and not np.isnan(best_pretrain) and mae_no_pretrain > 0:
            gain = (mae_no_pretrain - best_pretrain) / mae_no_pretrain
            c5_pass = gain >= PRETRAINING_MIN_GAIN
            c5_evidence = {
                "mae_no_pretrain": mae_no_pretrain,
                "mae_temporal": mae_temporal,
                "mae_graph": mae_graph,
                "best_pretrain": best_pretrain,
                "gain": gain,
            }
        else:
            c5_pass = False
            c5_evidence = {"note": "insufficient data for comparison"}
    else:
        c5_pass = False
        c5_evidence = {"note": "no pretraining records"}
    gates["C5"] = {
        "result": "PASS" if c5_pass else "FAIL",
        "note": f"Pretraining gain over NO_PRETRAINING: {c5_evidence.get('gain', float('nan')):.3f}",
        "evidence": c5_evidence,
    }

    # ── C6: Graph objective beats temporal-only ───────────────────────────────
    c6_evidence = {}
    if axis_l_records:
        mae_l0 = _mean_mae(axis_l_records, {"objective": "L0"})
        mae_l1 = _mean_mae(axis_l_records, {"objective": "L1"})
        mae_l2 = _mean_mae(axis_l_records, {"objective": "L2"})
        mae_l3 = _mean_mae(axis_l_records, {"objective": "L3"})
        temporal_baseline = min(m for m in [mae_l0, mae_l1] if not np.isnan(m)) if not (np.isnan(mae_l0) and np.isnan(mae_l1)) else float("nan")
        graph_best = min(m for m in [mae_l2, mae_l3] if not np.isnan(m)) if not (np.isnan(mae_l2) and np.isnan(mae_l3)) else float("nan")
        if not np.isnan(temporal_baseline) and not np.isnan(graph_best) and temporal_baseline > 0:
            gain = (temporal_baseline - graph_best) / temporal_baseline
            c6_pass = gain >= GRAPH_VS_NOGRAPH_THRESHOLD
            c6_evidence = {
                "mae_l0": mae_l0, "mae_l1": mae_l1,
                "mae_l2": mae_l2, "mae_l3": mae_l3,
                "temporal_baseline": temporal_baseline,
                "graph_best": graph_best, "gain": gain,
            }
        else:
            c6_pass = False
            c6_evidence = {"note": "insufficient objective data"}
    else:
        c6_pass = False
        c6_evidence = {"note": "no axis_l records"}
    gates["C6"] = {
        "result": "PASS" if c6_pass else "FAIL",
        "note": f"Graph objective vs temporal-only: gain={c6_evidence.get('gain', float('nan')):.3f}",
        "evidence": c6_evidence,
    }

    # ── C7: Edge AUC ≥ 0.60 in at least 2/3 seeds ────────────────────────────
    c7_aucs = []
    if axis_l_records:
        l2_recs = [r for r in axis_l_records if r.get("objective") == "L2"]
        c7_aucs = [r["edge_auc"] for r in l2_recs if "edge_auc" in r and not np.isnan(r.get("edge_auc", float("nan")))]
    elif axis_d_records:
        c7_aucs = [r["edge_auc"] for r in axis_d_records if "edge_auc" in r and not np.isnan(r.get("edge_auc", float("nan")))]
    pass_list = [a >= AUC_THRESHOLD for a in c7_aucs]
    c7_pass = _majority_pass(pass_list) if pass_list else False
    gates["C7"] = {
        "result": "PASS" if c7_pass else "FAIL",
        "note": f"Edge AUC ≥ {AUC_THRESHOLD}: {sum(pass_list)}/{len(pass_list)} records pass",
        "evidence": {"aucs": c7_aucs[:10], "threshold": AUC_THRESHOLD},
    }

    # ── C8: Block masking consistent gain ─────────────────────────────────────
    # Check that best model on block_30 shows similar gain direction as mcar_30
    c8_pass = False
    c8_evidence = {}
    if axis_d_records:
        mcar_recs = [r for r in axis_d_records if r.get("mask_key") == "mcar_30"]
        block_recs = [r for r in axis_d_records if r.get("mask_key") == "block_30"]
        if mcar_recs and block_recs:
            # Check best D2/25 vs D0/25
            mae_d2_25_mcar = _mean_mae(axis_d_records, {"n_datasets": 25, "diversity": "D2", "mask_key": "mcar_30"})
            mae_d0_25_mcar = _mean_mae(axis_d_records, {"n_datasets": 25, "diversity": "D0", "mask_key": "mcar_30"})
            mae_d2_25_block = _mean_mae(axis_d_records, {"n_datasets": 25, "diversity": "D2", "mask_key": "block_30"})
            mae_d0_25_block = _mean_mae(axis_d_records, {"n_datasets": 25, "diversity": "D0", "mask_key": "block_30"})
            mcar_gain = mae_d0_25_mcar - mae_d2_25_mcar
            block_gain = mae_d0_25_block - mae_d2_25_block
            # Both should show positive gain if D2 is better
            c8_pass = (
                not np.isnan(mcar_gain) and not np.isnan(block_gain)
                and min(mcar_gain, block_gain) >= -BLOCK_THRESHOLD
            )
            c8_evidence = {
                "mcar_gain": mcar_gain, "block_gain": block_gain,
                "mae_d2_25_mcar": mae_d2_25_mcar, "mae_d0_25_mcar": mae_d0_25_mcar,
                "mae_d2_25_block": mae_d2_25_block, "mae_d0_25_block": mae_d0_25_block,
            }
    gates["C8"] = {
        "result": "PASS" if c8_pass else "FAIL",
        "note": "Block masking consistent with MCAR direction",
        "evidence": c8_evidence,
    }

    # ── C9: Progressive shift degradation ─────────────────────────────────────
    # S0 < S1 < S2 < S3 in model MAE (at least 2 steps should be progressive)
    c9_pass = False
    c9_evidence = {}
    if axis_s_records:
        shift_order = ["S0_indist", "S1_moderate", "S2_novel_lag2", "S3_novel_highvar"]
        shift_maes = {}
        for sl in shift_order:
            maes = [r["mae"] for r in axis_s_records if r.get("shift_level") == sl]
            if maes:
                shift_maes[sl] = float(np.mean(maes))
        levels_available = [s for s in shift_order if s in shift_maes]
        progressive_steps = 0
        for i in range(len(levels_available) - 1):
            if shift_maes[levels_available[i]] < shift_maes[levels_available[i + 1]]:
                progressive_steps += 1
        c9_pass = progressive_steps >= SHIFT_CURVE_MIN_STEPS
        c9_evidence = {
            "shift_maes": shift_maes,
            "progressive_steps": progressive_steps,
            "min_required": SHIFT_CURVE_MIN_STEPS,
        }
    gates["C9"] = {
        "result": "PASS" if c9_pass else "FAIL",
        "note": f"Progressive degradation: {c9_evidence.get('progressive_steps', 0)}/{SHIFT_CURVE_MIN_STEPS} required steps",
        "evidence": c9_evidence,
    }

    # ── C10: Any model beats ffill ────────────────────────────────────────────
    c10_pass = False
    c10_evidence = {}
    if axis_m_records or axis_l_records:
        all_model_recs = axis_m_records + axis_l_records + axis_d_records
        neural_recs = [r for r in all_model_recs if r.get("model_type", "neural") not in ("M0_ffill",)]
        ffill_recs = [r for r in axis_m_records if r.get("model_type") == "M0_ffill"]
        if neural_recs and ffill_recs:
            best_neural_mae = min(r["mae"] for r in neural_recs if "mae" in r and not np.isnan(r["mae"]))
            mean_ffill_mae = float(np.mean([r["mae"] for r in ffill_recs if "mae" in r]))
            ratio = best_neural_mae / max(mean_ffill_mae, 1e-8)
            c10_pass = ratio < BASELINE_RATIO
            c10_evidence = {
                "best_neural_mae": best_neural_mae,
                "ffill_mae": mean_ffill_mae,
                "ratio": ratio,
                "threshold": BASELINE_RATIO,
            }
    gates["C10"] = {
        "result": "PASS" if c10_pass else "FAIL",
        "note": f"Best neural vs ffill ratio: {c10_evidence.get('ratio', float('nan')):.3f}",
        "evidence": c10_evidence,
    }

    # ── Principal cause identification ────────────────────────────────────────
    pass_count = sum(1 for g in gates.values() if g["result"] == "PASS")
    fail_count = sum(1 for g in gates.values() if g["result"] == "FAIL")

    if gates["C2"]["result"] == "FAIL":
        principal_cause = "ARCHITECTURE_INADEQUATE"
        next_step = "Stop DEC-048 OFAT — architecture cannot use graph signal even in ideal conditions. Redesign architecture."
    elif gates["C10"]["result"] == "FAIL":
        principal_cause = "MODEL_CANNOT_BEAT_FFILL"
        if gates["C5"]["result"] == "PASS":
            next_step = "Pretraining helps but insufficient. Increase pretraining dataset size or epochs."
        elif gates["C4"]["result"] == "PASS":
            next_step = "Diversity helps. Scale up D2 pretraining with more epochs."
        else:
            next_step = "No axis shows improvement over ffill. Consider architectural redesign."
    elif gates["C4"]["result"] == "FAIL" and gates["C3"]["result"] == "FAIL":
        principal_cause = "DATA_QUANTITY_AND_DIVERSITY_INSUFFICIENT"
        next_step = "Scale up training datasets to n=100+ with D2 diversity."
    elif gates["C4"]["result"] == "PASS" and gates["C5"]["result"] == "FAIL":
        principal_cause = "PRETRAINING_VARIANT_SUBOPTIMAL"
        next_step = "D2 diversity helps but current pretraining variants insufficient. Try longer training or different architecture."
    elif gates["C6"]["result"] == "PASS":
        principal_cause = "GRAPH_OBJECTIVE_HELPS"
        next_step = "Edge BCE supervision helps. Run DEC-047 strategies with L2-pretrained model."
    elif gates["C9"]["result"] == "FAIL":
        principal_cause = "NON_PROGRESSIVE_SHIFT_DEGRADATION"
        next_step = "Degradation is abrupt — suggests architecture problem. Redesign."
    else:
        principal_cause = "MIXED_SIGNAL"
        next_step = "No single dominant cause. Review per-gate evidence and proceed with best pretraining variant."

    decision = "PASS" if pass_count > fail_count else "FAIL"

    return {
        **gates,
        "summary": {
            "n_pass": pass_count,
            "n_fail": fail_count,
            "total_gates": len(gates),
            "decision": decision,
            "principal_cause": principal_cause,
            "next_step": next_step,
        },
        "decision": decision,
        "principal_cause": principal_cause,
        "next_step": next_step,
    }
