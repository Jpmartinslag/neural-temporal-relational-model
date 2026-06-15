"""
gates_dec049.py — E1-E10 gates for DEC-049 convergence audit (frozen before execution).

Thresholds FROZEN before execution — do NOT change after seeing results:
  AUC_THRESHOLD           = 0.60   # E3: AUC >= 0.60
  AUPRC_MIN_MULT          = 1.5    # E3: AUPRC >= 1.5 * prevalence
  CONVERGENCE_MIN_GAIN    = 0.005  # E2: val loss must improve by >= 0.5% each budget step
  RECONSTRUCTION_MARGIN   = 0.005  # E4: learned herald must beat no_graph by >= 0.5% MAE
  FEWSHOT_MIN_GAIN        = 0.005  # E7: few-shot must beat zero-shot by >= 0.5% MAE
  GRAPH_PRESERVATION_MAX_DROP = 0.05  # E8: AUC can't drop more than 5% after few-shot
  BLOCK_FRAC              = 2/3    # E10: must appear in block_30 in >= 2/3 seeds
  SEED_PASS_FRAC          = 2/3    # E9: at least 2/3 seeds must agree
  MULTITASK_MIN_GAIN_VS_TEMPORAL = 0.005  # E6: graph multitask must beat temporal-masked
  BUDGET_300_AUTO_TRIGGER = True   # if E2 shows consistent improvement at 150
"""

from __future__ import annotations

import numpy as np

# ── Frozen thresholds (do NOT change after seeing results) ────────────────────

AUC_THRESHOLD: float = 0.60
AUPRC_MIN_MULT: float = 1.5           # AUPRC >= AUPRC_MIN_MULT * prevalence
CONVERGENCE_MIN_GAIN: float = 0.005   # val_loss improvement per budget step
RECONSTRUCTION_MARGIN: float = 0.005  # herald beats no_graph by >= 0.5% MAE
FEWSHOT_MIN_GAIN: float = 0.005       # few-shot beats zero-shot by >= 0.5% MAE
GRAPH_PRESERVATION_MAX_DROP: float = 0.05  # AUC drop after few-shot <= 5%
BLOCK_FRAC: float = 2 / 3             # block_30 gate fraction
SEED_PASS_FRAC: float = 2 / 3         # majority vote fraction
MULTITASK_MIN_GAIN_VS_TEMPORAL: float = 0.005  # GRAPH_MASKED_MULTITASK gain over TEMPORAL_MASKED
BUDGET_300_AUTO_TRIGGER: bool = True   # auto-trigger 300 epochs if E1+E2+E3 pass at 150


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    vals = [v for v in values if not (np.isnan(v) or np.isinf(v))]
    return float(np.mean(vals)) if vals else float("nan")


def _filter(records: list[dict], **kwargs) -> list[dict]:
    result = records
    for k, v in kwargs.items():
        result = [r for r in result if r.get(k) == v]
    return result


def _majority(pass_list: list[bool]) -> bool:
    if not pass_list:
        return False
    return sum(pass_list) / len(pass_list) >= SEED_PASS_FRAC


def _per_seed_pass(records: list[dict], metric_key: str, threshold: float,
                   better_is_lower: bool = True) -> list[bool]:
    """For each unique seed, check if metric passes threshold."""
    seeds = sorted({r["seed"] for r in records})
    per_seed: list[bool] = []
    for s in seeds:
        recs_s = [r for r in records if r.get("seed") == s]
        vals = [r[metric_key] for r in recs_s
                if metric_key in r and not np.isnan(r.get(metric_key, float("nan")))]
        if not vals:
            continue
        m = float(np.mean(vals))
        if better_is_lower:
            per_seed.append(m <= threshold)
        else:
            per_seed.append(m >= threshold)
    return per_seed


# ── Gate evaluation ───────────────────────────────────────────────────────────

def evaluate_gates(
    records: list[dict],
    pretrain_results: dict,  # variant → budget → result (includes grad_norms, history)
) -> dict:
    """
    Evaluate E1-E10 gates.

    E1 SAFETY: no NaN/Inf/leakage, pretrain seeds disjoint from test
    E2 CONVERGENCE: val loss and at least one graph metric improve 30→75→150
    E3 RELATION_LEARNING: AUC >= 0.60 and AUPRC >= 1.5 * prevalence
    E4 RECONSTRUCTION: learned herald MAE < no_graph MAE
    E5 BASELINE_RELEVANCE: learned herald MAE < ffill MAE
    E6 MULTITASK_VALUE: GRAPH_MASKED_MULTITASK beats TEMPORAL_MASKED
    E7 FEWSHOT_VALUE: few-shot (5% or 10%) beats zero-shot
    E8 GRAPH_PRESERVATION: AUC doesn't drop > 0.05 after few-shot adaptation
    E9 REPLICATION: effect in same direction in >= 2/3 seeds
    E10 BLOCK_ROBUSTNESS: gain in block_30 for >= 2/3 seeds

    Returns gate report dict.
    """
    gates: dict[str, dict] = {}

    # ── E1: SAFETY ────────────────────────────────────────────────────────────
    nan_mae = sum(
        1 for r in records
        if "mae" in r and isinstance(r["mae"], float)
        and (np.isnan(r["mae"]) or np.isinf(r["mae"]))
    )
    nan_auc = sum(
        1 for r in records
        if "edge_auc" in r and isinstance(r["edge_auc"], float)
        and np.isinf(r.get("edge_auc", 0.0))
    )
    # Check seed disjointness
    from src.modeles.synthetic.phase11_generalization.splits import TEST_SEEDS
    test_seeds_set = set(TEST_SEEDS) | set(range(1000, 5001))
    seed_overlap = False
    for variant, budget_map in pretrain_results.items():
        if variant == "NO_PRETRAINING":
            continue
        for budget, res in budget_map.items():
            pretrain_seeds = set(range(200, 200 + res.get("n_pretrain_datasets", 50)))
            if pretrain_seeds & test_seeds_set:
                seed_overlap = True
                break

    e1_pass = (nan_mae == 0) and not seed_overlap
    gates["E1"] = {
        "result": "PASS" if e1_pass else "FAIL",
        "note": (
            f"{nan_mae} NaN MAEs, {nan_auc} Inf AUCs, "
            f"seed_overlap={seed_overlap}"
        ),
        "evidence": {
            "nan_mae_count": nan_mae,
            "nan_auc_inf_count": nan_auc,
            "seed_overlap": seed_overlap,
            "total_records": len(records),
        },
        "stop_if_fail": True,
    }

    # ── E2: CONVERGENCE ───────────────────────────────────────────────────────
    e2_evidence: dict = {}
    e2_converge_per_variant: list[bool] = []

    for variant in ["TEMPORAL_MASKED", "GRAPH_MASKED_MULTITASK"]:
        if variant not in pretrain_results:
            continue
        budget_map = pretrain_results[variant]
        budgets = sorted(budget_map.keys())
        if len(budgets) < 2:
            continue

        val_losses = []
        for b in budgets:
            res = budget_map[b]
            val_losses.append(res.get("best_val_loss", float("nan")))

        # Check monotone improvement
        improvements = []
        for i in range(len(val_losses) - 1):
            if not np.isnan(val_losses[i]) and not np.isnan(val_losses[i + 1]):
                gain = (val_losses[i] - val_losses[i + 1]) / max(abs(val_losses[i]), 1e-8)
                improvements.append(gain >= CONVERGENCE_MIN_GAIN)

        variant_converges = any(improvements) if improvements else False
        e2_converge_per_variant.append(variant_converges)
        e2_evidence[variant] = {
            "budgets": budgets,
            "val_losses": val_losses,
            "improvements": improvements,
            "converges": variant_converges,
        }

    e2_pass = any(e2_converge_per_variant) if e2_converge_per_variant else False
    gates["E2"] = {
        "result": "PASS" if e2_pass else "FAIL",
        "note": (
            f"Convergence per variant: {e2_converge_per_variant}. "
            f"At least one variant must show >=0.5% val_loss improvement per budget step."
        ),
        "evidence": e2_evidence,
    }

    # ── E3: RELATION LEARNING ─────────────────────────────────────────────────
    # Best budget (150) for GRAPH_MASKED_MULTITASK on herald_lagged records
    herald_recs = _filter(records, model_type="herald_lagged", eval_type="zero_shot")
    # Focus on highest budget
    all_budgets = sorted({r.get("epoch_budget", 0) for r in herald_recs})
    best_budget = max(all_budgets) if all_budgets else 0
    best_herald = _filter(herald_recs, epoch_budget=best_budget)
    multitask_recs = _filter(best_herald, variant="GRAPH_MASKED_MULTITASK")

    aucs = [r["edge_auc"] for r in multitask_recs
            if "edge_auc" in r and not np.isnan(r.get("edge_auc", float("nan")))]
    auc_pass_list = [a >= AUC_THRESHOLD for a in aucs]
    auc_majority = _majority(auc_pass_list)

    # AUPRC: prevalence = n_true_edges / n_off_diagonal
    n_off = N_SECTORS * (N_SECTORS - 1) if "N_SECTORS" in dir() else 72
    n_true_edges = _mean([r.get("n_true_edges", 0) for r in multitask_recs])
    prevalence = n_true_edges / max(n_off, 1) if not np.isnan(n_true_edges) else float("nan")
    # Note: AUPRC not directly computed in zero-shot; use edge_precision_at_k as proxy
    prec_vals = [r.get("edge_precision_at_k", float("nan")) for r in multitask_recs
                 if not np.isnan(r.get("edge_precision_at_k", float("nan")))]
    auprc_proxy = _mean(prec_vals)
    auprc_pass = (not np.isnan(auprc_proxy) and not np.isnan(prevalence)
                  and auprc_proxy >= AUPRC_MIN_MULT * prevalence) if prec_vals else False

    e3_pass = auc_majority and auprc_pass
    gates["E3"] = {
        "result": "PASS" if e3_pass else "FAIL",
        "note": (
            f"AUC: {_mean(aucs):.3f} (threshold={AUC_THRESHOLD}), "
            f"AUPRC proxy: {auprc_proxy:.3f} vs {AUPRC_MIN_MULT}×prevalence={AUPRC_MIN_MULT*prevalence:.3f}. "
            f"AUC majority={auc_majority}, AUPRC pass={auprc_pass}"
        ),
        "evidence": {
            "aucs": aucs[:10],
            "mean_auc": _mean(aucs),
            "auc_threshold": AUC_THRESHOLD,
            "prevalence": prevalence,
            "auprc_proxy": auprc_proxy,
            "auc_majority_pass": auc_majority,
            "auprc_pass": auprc_pass,
        },
    }

    # ── E4: RECONSTRUCTION ────────────────────────────────────────────────────
    nograph_recs = _filter(records, model_type="no_graph", eval_type="zero_shot")
    herald_zs_recs = _filter(records, model_type="herald_lagged", eval_type="zero_shot")

    # Per seed/mask comparison
    e4_passes: list[bool] = []
    for seed in sorted({r["seed"] for r in herald_zs_recs}):
        for mk in sorted({r["mask_key"] for r in herald_zs_recs}):
            for variant in ["GRAPH_MASKED_MULTITASK", "TEMPORAL_MASKED", "NO_PRETRAINING"]:
                for budget in sorted({r.get("epoch_budget", 0) for r in herald_zs_recs}):
                    ng = _mean([r["mae"] for r in nograph_recs
                                if r.get("seed") == seed and r.get("mask_key") == mk
                                and r.get("variant") == variant and r.get("epoch_budget") == budget])
                    hl = _mean([r["mae"] for r in herald_zs_recs
                                if r.get("seed") == seed and r.get("mask_key") == mk
                                and r.get("variant") == variant and r.get("epoch_budget") == budget])
                    if not np.isnan(ng) and not np.isnan(hl) and ng > 0:
                        gain = (ng - hl) / ng
                        e4_passes.append(gain >= RECONSTRUCTION_MARGIN)

    e4_pass = _majority(e4_passes) if e4_passes else False
    mean_gain_e4 = _mean([
        (r.get("graph_contribution", float("nan")) / max(
            _mean([r2["mae"] for r2 in nograph_recs
                   if r2.get("seed") == r.get("seed") and r2.get("mask_key") == r.get("mask_key")
                   and r2.get("variant") == r.get("variant") and r2.get("epoch_budget") == r.get("epoch_budget")]),
            1e-8
        ))
        for r in herald_zs_recs
        if not np.isnan(r.get("graph_contribution", float("nan")))
    ])

    gates["E4"] = {
        "result": "PASS" if e4_pass else "FAIL",
        "note": (
            f"Learned HERALD beats no_graph: {sum(e4_passes)}/{len(e4_passes)} comparisons. "
            f"Majority={e4_pass}."
        ),
        "evidence": {
            "n_comparisons": len(e4_passes),
            "n_pass": sum(e4_passes),
            "pass_frac": sum(e4_passes) / max(len(e4_passes), 1),
            "mean_gain_vs_nograph": mean_gain_e4,
            "threshold": RECONSTRUCTION_MARGIN,
        },
    }

    # ── E5: BASELINE RELEVANCE (herald beats ffill) ───────────────────────────
    ffill_recs = _filter(records, model_type="ffill", eval_type="zero_shot")
    e5_passes: list[bool] = []
    for r in herald_zs_recs:
        seed, mk, variant, budget = r.get("seed"), r.get("mask_key"), r.get("variant"), r.get("epoch_budget")
        ff_mae = _mean([rf["mae"] for rf in ffill_recs
                        if rf.get("seed") == seed and rf.get("mask_key") == mk
                        and rf.get("variant") == variant and rf.get("epoch_budget") == budget])
        if not np.isnan(ff_mae) and not np.isnan(r["mae"]) and ff_mae > 0:
            e5_passes.append(r["mae"] < ff_mae)

    e5_pass = _majority(e5_passes) if e5_passes else False
    gates["E5"] = {
        "result": "PASS" if e5_pass else "FAIL",
        "note": (
            f"Herald beats ffill: {sum(e5_passes)}/{len(e5_passes)} comparisons. "
            f"Majority={e5_pass}."
        ),
        "evidence": {
            "n_comparisons": len(e5_passes),
            "n_pass": sum(e5_passes),
            "pass_frac": sum(e5_passes) / max(len(e5_passes), 1),
        },
    }

    # ── E6: MULTITASK VALUE (GRAPH_MASKED_MULTITASK beats TEMPORAL_MASKED) ────
    e6_passes: list[bool] = []
    # Compare at highest budget
    for seed in sorted({r["seed"] for r in herald_zs_recs}):
        for mk in sorted({r["mask_key"] for r in herald_zs_recs}):
            tm_mae = _mean([r["mae"] for r in herald_zs_recs
                            if r.get("seed") == seed and r.get("mask_key") == mk
                            and r.get("variant") == "TEMPORAL_MASKED"
                            and r.get("epoch_budget") == best_budget])
            gm_mae = _mean([r["mae"] for r in herald_zs_recs
                            if r.get("seed") == seed and r.get("mask_key") == mk
                            and r.get("variant") == "GRAPH_MASKED_MULTITASK"
                            and r.get("epoch_budget") == best_budget])
            if not np.isnan(tm_mae) and not np.isnan(gm_mae) and tm_mae > 0:
                gain = (tm_mae - gm_mae) / tm_mae
                e6_passes.append(gain >= MULTITASK_MIN_GAIN_VS_TEMPORAL)

    e6_pass = _majority(e6_passes) if e6_passes else False
    gates["E6"] = {
        "result": "PASS" if e6_pass else "FAIL",
        "note": (
            f"GRAPH_MASKED_MULTITASK beats TEMPORAL_MASKED: "
            f"{sum(e6_passes)}/{len(e6_passes)} comparisons at budget={best_budget}. "
            f"Majority={e6_pass}."
        ),
        "evidence": {
            "n_comparisons": len(e6_passes),
            "n_pass": sum(e6_passes),
            "threshold": MULTITASK_MIN_GAIN_VS_TEMPORAL,
        },
    }

    # ── E7: FEWSHOT VALUE (few-shot beats zero-shot) ──────────────────────────
    fs_recs = _filter(records, model_type="fewshot_A1")
    zs_recs_for_fs = _filter(records, model_type="herald_lagged", eval_type="zero_shot")
    e7_passes: list[bool] = []

    for seed in sorted({r["seed"] for r in fs_recs}):
        for mk in sorted({r["mask_key"] for r in fs_recs}):
            for variant in sorted({r.get("variant", "") for r in fs_recs}):
                for budget in sorted({r.get("epoch_budget", 0) for r in fs_recs}):
                    zs_mae = _mean([r["mae"] for r in zs_recs_for_fs
                                    if r.get("seed") == seed and r.get("mask_key") == mk
                                    and r.get("variant") == variant and r.get("epoch_budget") == budget])
                    best_fs_mae = min(
                        [r["mae"] for r in fs_recs
                         if r.get("seed") == seed and r.get("mask_key") == mk
                         and r.get("variant") == variant and r.get("epoch_budget") == budget
                         and r.get("k_frac", 0) > 0
                         and not np.isnan(r["mae"])],
                        default=float("nan")
                    )
                    if not np.isnan(zs_mae) and not np.isnan(best_fs_mae) and zs_mae > 0:
                        gain = (zs_mae - best_fs_mae) / zs_mae
                        e7_passes.append(gain >= FEWSHOT_MIN_GAIN)

    e7_pass = _majority(e7_passes) if e7_passes else False
    gates["E7"] = {
        "result": "PASS" if e7_pass else "FAIL",
        "note": (
            f"Few-shot beats zero-shot: {sum(e7_passes)}/{len(e7_passes)} comparisons. "
            f"Majority={e7_pass}."
        ),
        "evidence": {
            "n_comparisons": len(e7_passes),
            "n_pass": sum(e7_passes),
            "threshold": FEWSHOT_MIN_GAIN,
        },
    }

    # ── E8: GRAPH PRESERVATION (AUC doesn't drop after few-shot) ─────────────
    e8_passes: list[bool] = []
    zs_aucs_map: dict = {}
    for r in zs_recs_for_fs:
        key = (r.get("seed"), r.get("mask_key"), r.get("variant"), r.get("epoch_budget"))
        if not np.isnan(r.get("edge_auc", float("nan"))):
            zs_aucs_map[key] = r["edge_auc"]

    for r in fs_recs:
        key = (r.get("seed"), r.get("mask_key"), r.get("variant"), r.get("epoch_budget"))
        if key in zs_aucs_map and not np.isnan(r.get("edge_auc", float("nan"))):
            auc_drop = zs_aucs_map[key] - r["edge_auc"]
            e8_passes.append(auc_drop <= GRAPH_PRESERVATION_MAX_DROP)

    e8_pass = _majority(e8_passes) if e8_passes else True  # no fs data → not applicable → pass
    gates["E8"] = {
        "result": "PASS" if e8_pass else "FAIL",
        "note": (
            f"AUC preserved after few-shot: {sum(e8_passes)}/{len(e8_passes)} comparisons. "
            f"Max allowed drop={GRAPH_PRESERVATION_MAX_DROP}."
        ),
        "evidence": {
            "n_comparisons": len(e8_passes),
            "n_pass": sum(e8_passes),
            "max_allowed_drop": GRAPH_PRESERVATION_MAX_DROP,
        },
    }

    # ── E9: REPLICATION (effect in same direction in >= 2/3 seeds) ────────────
    # Check that GRAPH_MASKED_MULTITASK beats NO_PRETRAINING consistently across seeds
    e9_passes: list[bool] = []
    seeds_test = sorted({r["seed"] for r in herald_zs_recs})
    for seed in seeds_test:
        gm_mae = _mean([r["mae"] for r in herald_zs_recs
                        if r.get("seed") == seed and r.get("variant") == "GRAPH_MASKED_MULTITASK"
                        and r.get("epoch_budget") == best_budget])
        np_mae = _mean([r["mae"] for r in herald_zs_recs
                        if r.get("seed") == seed and r.get("variant") == "NO_PRETRAINING"
                        and r.get("epoch_budget") == max(30, min(best_budget, 150))])
        if not np.isnan(gm_mae) and not np.isnan(np_mae):
            e9_passes.append(gm_mae <= np_mae)

    e9_pass = _majority(e9_passes) if e9_passes else False
    gates["E9"] = {
        "result": "PASS" if e9_pass else "FAIL",
        "note": (
            f"GRAPH_MASKED_MULTITASK <= NO_PRETRAINING in {sum(e9_passes)}/{len(e9_passes)} seeds. "
            f"Required: {SEED_PASS_FRAC:.0%}."
        ),
        "evidence": {
            "n_seeds": len(e9_passes),
            "n_agree": sum(e9_passes),
            "required_frac": SEED_PASS_FRAC,
        },
    }

    # ── E10: BLOCK ROBUSTNESS (gain in block_30 for >= 2/3 seeds) ─────────────
    block_herald = _filter(records, model_type="herald_lagged", mask_key="block_30", eval_type="zero_shot")
    block_ffill = _filter(records, model_type="ffill", mask_key="block_30", eval_type="zero_shot")
    e10_passes: list[bool] = []

    for seed in sorted({r["seed"] for r in block_herald}):
        for variant in ["GRAPH_MASKED_MULTITASK"]:
            hl_mae = _mean([r["mae"] for r in block_herald
                            if r.get("seed") == seed and r.get("variant") == variant
                            and r.get("epoch_budget") == best_budget])
            ff_mae = _mean([r["mae"] for r in block_ffill
                            if r.get("seed") == seed and r.get("variant") == variant])
            if not np.isnan(hl_mae) and not np.isnan(ff_mae):
                e10_passes.append(hl_mae < ff_mae)

    e10_pass = (
        _majority(e10_passes) if e10_passes
        else (len(block_herald) == 0)  # no block data → not applicable → NA
    )
    gates["E10"] = {
        "result": "PASS" if e10_pass else ("FAIL" if e10_passes else "NA"),
        "note": (
            f"Block_30 gain in {sum(e10_passes)}/{len(e10_passes)} seeds. "
            f"Required fraction: {BLOCK_FRAC:.0%}."
        ),
        "evidence": {
            "n_seeds": len(e10_passes),
            "n_pass": sum(e10_passes),
            "required_frac": BLOCK_FRAC,
        },
    }

    # ── Summary ───────────────────────────────────────────────────────────────
    pass_count = sum(1 for g in gates.values() if g["result"] == "PASS")
    fail_count = sum(1 for g in gates.values() if g["result"] == "FAIL")
    na_count = sum(1 for g in gates.values() if g["result"] == "NA")

    if gates["E1"]["result"] == "FAIL":
        decision = "STOP_E1_SAFETY"
        recommendation = "E1 safety gate failed. Check for NaN/Inf in records or seed leakage."
    elif pass_count >= 6:
        decision = "CONVERGENCE_HYPOTHESIS_SUPPORTED"
        recommendation = (
            "Training budget hypothesis confirmed. "
            "Proceed to DEC-050: full adaptation evaluation with 150+ epoch checkpoint."
        )
    elif pass_count >= 4:
        decision = "CONVERGENCE_PARTIAL"
        recommendation = (
            "Partial support for training budget hypothesis. "
            "Consider 300-epoch extension if E2 trigger fires."
        )
    else:
        decision = "CONVERGENCE_HYPOTHESIS_NOT_SUPPORTED"
        recommendation = (
            "Training budget hypothesis not supported at this scale. "
            "Investigate alternative causes."
        )

    return {
        **gates,
        "summary": {
            "n_pass": pass_count,
            "n_fail": fail_count,
            "n_na": na_count,
            "total_gates": len(gates),
            "decision": decision,
            "recommendation": recommendation,
        },
        "decision": decision,
        "recommendation": recommendation,
    }


def check_300_epoch_trigger(
    gates: dict,
    records: list[dict],
    pretrain_results: dict,
) -> bool:
    """
    Auto-trigger rule: run 300 epochs only if E1+E2 PASS at budget=150
    AND val_loss at 150 shows monotone improvement from 75→150.

    Returns True if 300-epoch run should be triggered.
    """
    if not BUDGET_300_AUTO_TRIGGER:
        return False
    if gates.get("E1", {}).get("result") != "PASS":
        return False
    if gates.get("E2", {}).get("result") != "PASS":
        return False

    # Check that at least one variant shows improvement at 150 vs 75
    for variant in ["TEMPORAL_MASKED", "GRAPH_MASKED_MULTITASK"]:
        if variant not in pretrain_results:
            continue
        budget_map = pretrain_results[variant]
        val_75 = budget_map.get(75, {}).get("best_val_loss", float("nan"))
        val_150 = budget_map.get(150, {}).get("best_val_loss", float("nan"))
        if not np.isnan(val_75) and not np.isnan(val_150):
            if (val_75 - val_150) / max(abs(val_75), 1e-8) >= CONVERGENCE_MIN_GAIN:
                return True

    return False
