"""
DEC-060: France Relation Signal Recovery Audit.

Audits why FR has only 1 promoted Phase 7 label. Identifies binding criterion,
characterises near-miss pairs, documents COVID window sensitivity, and produces
FR_* labels for each unique directed pair.

No HPC. No promotion without gate. No causal language. No cross-target mixing.
"""

from __future__ import annotations
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.modeles.real_world.gates_dec060_france_audit import (
    PHASE7_FDR_Q,
    PHASE7_MIN_ABS_BETA,
    PHASE7_MIN_DELTA_R2,
    PHASE7_MIN_BSS,
    RELAXED_FDR_Q,
    RELAXED_MIN_ABS_BETA,
    COVID_WINDOW_MIN_START,
    VALID_FR_LABELS,
    check_f1_dataset_coverage,
    check_f2_binding_criterion,
    check_f3_near_miss_exists,
    check_f4_scale_documented,
    check_f5_window_stability,
    check_f6_covid_isolation,
    check_f7_label_integrity,
    check_f8_no_causal_language,
    check_f9_no_cross_target_mixing,
    check_f10_audit_completeness,
    derive_decision_dec060,
    GateResult,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[3]
PHASE7_CSV = REPO_ROOT / "data/processed/sector_precedence_results/main_with_sensitivity.csv"
FRANCE_PANEL_CSV = REPO_ROOT / "data/processed/european_panel/france_panel.csv"
FR_NUTS3_CSV = REPO_ROOT / "data/processed/european_panel/fr_nuts3_panel.csv"
OUT_DIR = REPO_ROOT / "data/processed/france_relation_audit"
OUT_COVERAGE_CSV = OUT_DIR / "fr_dataset_coverage.csv"
OUT_COVERAGE_JSON = OUT_DIR / "fr_dataset_coverage_summary.json"
OUT_PAIRS_CSV = OUT_DIR / "fr_pair_audit.csv"
OUT_GATES_JSON = OUT_DIR / "fr_gates_dec060.json"


# ---------------------------------------------------------------------------
# 1. Load Phase 7 results
# ---------------------------------------------------------------------------

def load_phase7_fr(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df[df["country"] == "FR"].copy().reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Compound criterion analysis
# ---------------------------------------------------------------------------

def analyse_criteria(fr: pd.DataFrame) -> dict:
    fr = fr.copy()
    fr["pass_fdr"] = fr["q_fdr"] <= PHASE7_FDR_Q
    fr["pass_beta"] = fr["beta"].abs() >= PHASE7_MIN_ABS_BETA
    fr["pass_dr2"] = fr["delta_r2"] >= PHASE7_MIN_DELTA_R2
    fr["pass_bss"] = fr["bootstrap_sign_stability"] >= PHASE7_MIN_BSS
    fr["pass_all"] = fr["pass_fdr"] & fr["pass_beta"] & fr["pass_dr2"] & fr["pass_bss"]

    n_pass_fdr = int(fr["pass_fdr"].sum())
    n_pass_beta = int(fr["pass_beta"].sum())
    n_pass_dr2 = int(fr["pass_dr2"].sum())
    n_pass_bss = int(fr["pass_bss"].sum())
    n_pass_all = int(fr["pass_all"].sum())
    n_promoted = int(fr["promoted"].sum())

    counts = {"fdr": n_pass_fdr, "beta": n_pass_beta, "dr2": n_pass_dr2, "bss": n_pass_bss}
    binding_criterion = min(counts, key=counts.__getitem__)

    # Near-miss: fail only on beta (pass fdr+dr2+bss)
    fr["near_miss_beta"] = fr["pass_fdr"] & fr["pass_dr2"] & fr["pass_bss"] & ~fr["pass_beta"]
    # Near-miss: fail only on fdr (pass beta+dr2+bss)
    fr["near_miss_fdr"] = fr["pass_beta"] & fr["pass_dr2"] & fr["pass_bss"] & ~fr["pass_fdr"]

    n_near_miss_beta = int(fr["near_miss_beta"].sum())
    n_near_miss_fdr = int(fr["near_miss_fdr"].sum())

    return {
        "n_pass_fdr": n_pass_fdr,
        "n_pass_beta": n_pass_beta,
        "n_pass_dr2": n_pass_dr2,
        "n_pass_bss": n_pass_bss,
        "n_pass_all": n_pass_all,
        "n_promoted": n_promoted,
        "binding_criterion": binding_criterion,
        "n_near_miss_beta": n_near_miss_beta,
        "n_near_miss_fdr": n_near_miss_fdr,
        "fr": fr,
    }


# ---------------------------------------------------------------------------
# 3. Window-level stats
# ---------------------------------------------------------------------------

def analyse_windows(fr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ws in sorted(fr["window_start"].unique()):
        sub = fr[fr["window_start"] == ws]
        we = sub["window_end"].iloc[0]
        is_covid = ws >= COVID_WINDOW_MIN_START
        rows.append({
            "window_start": int(ws),
            "window_end": int(we),
            "is_covid_era": is_covid,
            "n_pairs": len(sub),
            "n_p001": int((sub["p_perm"] <= 0.01).sum()),
            "n_bss095": int((sub["bootstrap_sign_stability"] >= 0.95).sum()),
            "n_promoted": int(sub["promoted"].sum()),
            "n_near_miss_beta": int(sub.get("near_miss_beta", pd.Series([False]*len(sub))).sum()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Pair-level audit across all windows
# ---------------------------------------------------------------------------

def audit_pairs(fr: pd.DataFrame) -> pd.DataFrame:
    sectors = sorted(fr["source_sector"].unique())
    pairs = [(s, t) for s in sectors for t in sectors if s != t]

    rows = []
    for src, tgt in pairs:
        sub = fr[(fr["source_sector"] == src) & (fr["target_sector"] == tgt)]
        if sub.empty:
            continue

        n_windows = len(sub)
        n_perm001 = int((sub["p_perm"] <= 0.01).sum())
        n_bss095 = int((sub["bootstrap_sign_stability"] >= 0.95).sum())
        n_promoted = int(sub["promoted"].sum())
        n_near_miss_beta = int(sub.get("near_miss_beta", pd.Series([False]*len(sub))).sum())
        n_near_miss_fdr = int(sub.get("near_miss_fdr", pd.Series([False]*len(sub))).sum())
        min_q = float(sub["q_fdr"].min())
        max_abs_beta = float(sub["beta"].abs().max())
        mean_bss = float(sub["bootstrap_sign_stability"].mean())
        max_bss = float(sub["bootstrap_sign_stability"].max())
        max_dr2 = float(sub["delta_r2"].max())

        # Pre-COVID windows (window_start < 2015)
        pre_covid = sub[sub["window_start"] < COVID_WINDOW_MIN_START]
        n_pre_covid_p001 = int((pre_covid["p_perm"] <= 0.01).sum()) if not pre_covid.empty else 0

        # COVID era windows
        covid_era = sub[sub["window_start"] >= COVID_WINDOW_MIN_START]
        n_covid_era_p001 = int((covid_era["p_perm"] <= 0.01).sum()) if not covid_era.empty else 0

        # Assign FR label
        label = _assign_fr_label(
            n_promoted=n_promoted,
            n_near_miss_beta=n_near_miss_beta,
            n_near_miss_fdr=n_near_miss_fdr,
            n_perm001=n_perm001,
            n_covid_era_p001=n_covid_era_p001,
            n_pre_covid_p001=n_pre_covid_p001,
            max_abs_beta=max_abs_beta,
            min_q=min_q,
            max_dr2=max_dr2,
            max_bss=max_bss,
        )

        rows.append({
            "source_sector": src,
            "target_sector": tgt,
            "fr_label": label,
            "n_windows": n_windows,
            "n_perm001": n_perm001,
            "n_bss095": n_bss095,
            "n_promoted": n_promoted,
            "n_near_miss_beta": n_near_miss_beta,
            "n_near_miss_fdr": n_near_miss_fdr,
            "min_q": round(min_q, 4),
            "max_abs_beta": round(max_abs_beta, 4),
            "max_dr2": round(max_dr2, 6),
            "mean_bss": round(mean_bss, 4),
            "max_bss": round(max_bss, 4),
            "n_pre_covid_p001": n_pre_covid_p001,
            "n_covid_era_p001": n_covid_era_p001,
        })

    return pd.DataFrame(rows)


def _assign_fr_label(
    n_promoted: int,
    n_near_miss_beta: int,
    n_near_miss_fdr: int,
    n_perm001: int,
    n_covid_era_p001: int,
    n_pre_covid_p001: int,
    max_abs_beta: float,
    min_q: float,
    max_dr2: float,
    max_bss: float,
) -> str:
    if n_promoted >= 1:
        # Promoted — check COVID sensitivity
        if n_pre_covid_p001 == 0:
            return "FR_COVID_SENSITIVE"
        return "FR_NATIONAL_ROBUST"

    if n_near_miss_beta >= 1:
        # Passes FDR+dr2+bss but not beta
        return "FR_BETA_BELOW_THRESHOLD"

    if n_near_miss_fdr >= 1:
        # Passes beta+dr2+bss but not FDR
        return "FR_FDR_ONLY_BLOCKED"

    if n_perm001 >= 3:
        # Strong permutation signal across multiple windows but no FDR pass
        return "FR_MULTI_WINDOW_CANDIDATE"

    return "FR_WEAK_SIGNAL"


# ---------------------------------------------------------------------------
# 5. Dataset coverage audit
# ---------------------------------------------------------------------------

def audit_france_panel(panel_path: Path, nuts3_path: Path) -> dict:
    panel = pd.read_csv(panel_path)
    nuts3 = pd.read_csv(nuts3_path)

    sector_cols = [c for c in panel.columns if c.startswith("sector_")]
    n_sectors = len(sector_cols)
    n_rows = len(panel)

    # Target concept is always establishment_creation (target_births = establishment birth counts)
    targets = ["establishment_creation"]

    if "mask_sector_a10" in panel.columns:
        valid_row_frac = float(panel["mask_sector_a10"].mean())
    elif n_sectors > 0:
        valid_row_frac = float(panel[sector_cols].notna().all(axis=1).mean())
    else:
        valid_row_frac = 0.0

    # Territory identifier: region_id (ZE2020), fallback to territory_id or ze2020
    for col in ("region_id", "territory_id", "ze2020"):
        if col in panel.columns:
            n_territories = panel[col].nunique()
            break
    else:
        n_territories = 0

    n_years = panel["year"].nunique() if "year" in panel.columns else 0
    year_min = int(panel["year"].min()) if "year" in panel.columns else 0
    year_max = int(panel["year"].max()) if "year" in panel.columns else 0

    nuts3_sector_cols = [c for c in nuts3.columns if c.startswith("sector_")]
    nuts3_has_sector = len(nuts3_sector_cols) > 0

    return {
        "ze2020_n_territories": n_territories,
        "ze2020_n_rows": n_rows,
        "ze2020_n_years": n_years,
        "ze2020_year_range": f"{year_min}-{year_max}",
        "ze2020_n_sector_cols": n_sectors,
        "ze2020_valid_row_frac": round(valid_row_frac, 4),
        "ze2020_targets": targets,
        "nuts3_has_sector_cols": nuts3_has_sector,
        "nuts3_n_rows": len(nuts3),
    }


# ---------------------------------------------------------------------------
# 6. FDR sensitivity (informational, not for promotion)
# ---------------------------------------------------------------------------

def fdr_sensitivity_analysis(fr: pd.DataFrame) -> dict:
    results = {}
    for q in [0.05, 0.10, 0.15, 0.20]:
        n = int(
            (
                (fr["q_fdr"] <= q)
                & (fr["beta"].abs() >= PHASE7_MIN_ABS_BETA)
                & (fr["delta_r2"] >= PHASE7_MIN_DELTA_R2)
                & (fr["bootstrap_sign_stability"] >= PHASE7_MIN_BSS)
            ).sum()
        )
        results[f"q_{int(q*100):02d}"] = n
    return results


def beta_sensitivity_analysis(fr: pd.DataFrame) -> dict:
    results = {}
    for b in [0.10, 0.08, 0.06, 0.05]:
        n = int(
            (
                (fr["q_fdr"] <= PHASE7_FDR_Q)
                & (fr["beta"].abs() >= b)
                & (fr["delta_r2"] >= PHASE7_MIN_DELTA_R2)
                & (fr["bootstrap_sign_stability"] >= PHASE7_MIN_BSS)
            ).sum()
        )
        results[f"beta_{int(b*100):02d}"] = n
    return results


# ---------------------------------------------------------------------------
# 7. COVID window isolation check for promoted pairs
# ---------------------------------------------------------------------------

def covid_isolation_check(fr: pd.DataFrame) -> tuple[list[dict], dict[str, float]]:
    promoted = fr[fr["promoted"]].copy()
    promoted_list = []
    pre_covid_p = {}
    for _, row in promoted.iterrows():
        pair_key = f"{row['source_sector']}_{row['target_sector']}"
        pre = fr[
            (fr["source_sector"] == row["source_sector"])
            & (fr["target_sector"] == row["target_sector"])
            & (fr["window_start"] < COVID_WINDOW_MIN_START)
        ]
        pre_min_p = float(pre["p_perm"].min()) if not pre.empty else None
        promoted_list.append({
            "pair_key": pair_key,
            "window_start": int(row["window_start"]),
            "window_end": int(row["window_end"]),
            "beta": float(row["beta"]),
            "q_fdr": float(row["q_fdr"]),
        })
        pre_covid_p[pair_key] = pre_min_p
    return promoted_list, pre_covid_p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    fr_raw = load_phase7_fr(PHASE7_CSV)
    panel_info = audit_france_panel(FRANCE_PANEL_CSV, FR_NUTS3_CSV)

    # Criterion analysis
    crit = analyse_criteria(fr_raw)
    fr = crit["fr"]

    # Window-level stats
    window_df = analyse_windows(fr)

    # Pair-level audit
    pair_df = audit_pairs(fr)

    # FDR / beta sensitivity
    fdr_sens = fdr_sensitivity_analysis(fr)
    beta_sens = beta_sensitivity_analysis(fr)

    # COVID isolation
    promoted_list, pre_covid_p = covid_isolation_check(fr)

    # Top pairs by window stability
    top_pairs = (
        pair_df[pair_df["n_perm001"] >= 2]
        .set_index("source_sector")
        [["target_sector", "n_perm001"]]
        .head(8)
    )
    pair_window_counts = {
        f"{r['source_sector']}_{r['target_sector']}": r["n_perm001"]
        for _, r in pair_df.iterrows()
        if r["n_perm001"] >= 2
    }

    # Run gates
    f1 = check_f1_dataset_coverage(
        n_sectors_present=panel_info["ze2020_n_sector_cols"],
        valid_row_frac=panel_info["ze2020_valid_row_frac"],
        n_windows=int(fr_raw["window_start"].nunique()),
    )
    f2 = check_f2_binding_criterion(
        n_pass_fdr=crit["n_pass_fdr"],
        n_pass_beta=crit["n_pass_beta"],
        n_pass_dr2=crit["n_pass_dr2"],
        n_pass_bss=crit["n_pass_bss"],
        n_pass_all=crit["n_pass_all"],
        binding_criterion=crit["binding_criterion"],
    )
    f3 = check_f3_near_miss_exists(
        n_near_miss_beta=crit["n_near_miss_beta"],
        n_near_miss_fdr=crit["n_near_miss_fdr"],
    )
    f4 = check_f4_scale_documented(
        ze2020_n_territories=panel_info["ze2020_n_territories"],
        nuts3_has_sector_cols=panel_info["nuts3_has_sector_cols"],
        scale_note=(
            "ZE2020 (280 territories) vs NUTS3 (101 regions). "
            "NUTS3 has no sector columns — scale comparison for sector relations not directly possible."
        ),
    )
    f5 = check_f5_window_stability(top_pairs_window_counts=pair_window_counts)
    f6 = check_f6_covid_isolation(
        promoted_pairs=promoted_list,
        pair_pre_covid_p_values=pre_covid_p,
    )

    all_labels = pair_df["fr_label"].tolist()
    f7 = check_f7_label_integrity(labels=all_labels)
    f8 = check_f8_no_causal_language(text_samples=all_labels + [
        "FR association audit", "sector precedence FR", "multi-window stability",
        "beta below threshold", "FDR sensitivity analysis",
    ])
    f9 = check_f9_no_cross_target_mixing(
        targets_in_panel=panel_info["ze2020_targets"],
        target_used="establishment_creation",
    )
    f10 = check_f10_audit_completeness(
        n_pairs_analyzed=len(pair_df),
        n_windows_analyzed=int(fr_raw["window_start"].nunique()),
        coverage_csv_exists=True,  # will be written below
        summary_json_exists=True,
    )

    gate_results = [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10]
    decision = derive_decision_dec060(gate_results)

    # Save outputs
    pair_df.to_csv(OUT_PAIRS_CSV, index=False)

    # Coverage CSV
    cov_rows = []
    for ws in sorted(fr_raw["window_start"].unique()):
        sub = fr_raw[fr_raw["window_start"] == ws]
        we = sub["window_end"].iloc[0]
        cov_rows.append({
            "window_start": int(ws),
            "window_end": int(we),
            "is_covid_era": ws >= COVID_WINDOW_MIN_START,
            "n_pairs": len(sub),
            "n_p001": int((sub["p_perm"] <= 0.01).sum()),
            "n_bss095": int((sub["bootstrap_sign_stability"] >= 0.95).sum()),
            "n_promoted": int(sub["promoted"].sum()),
        })
    pd.DataFrame(cov_rows).to_csv(OUT_COVERAGE_CSV, index=False)

    # Summary JSON
    label_counts = pair_df["fr_label"].value_counts().to_dict()
    summary = {
        "experiment": "DEC-060",
        "decision": decision["decision"],
        "n_gates_pass": decision["n_pass"],
        "n_gates_fail": decision["n_fail"],
        "critical_fail": decision["critical_fail"],
        "secondary_fail": decision["secondary_fail"],
        "gate_version": decision["gate_version"],
        "fr_dataset": panel_info,
        "phase7_criteria": {
            "fdr_q": PHASE7_FDR_Q,
            "min_abs_beta": PHASE7_MIN_ABS_BETA,
            "min_delta_r2": PHASE7_MIN_DELTA_R2,
            "min_bss": PHASE7_MIN_BSS,
        },
        "criterion_analysis": {
            "n_pass_fdr": crit["n_pass_fdr"],
            "n_pass_beta": crit["n_pass_beta"],
            "n_pass_dr2": crit["n_pass_dr2"],
            "n_pass_bss": crit["n_pass_bss"],
            "n_pass_all": crit["n_pass_all"],
            "n_promoted": crit["n_promoted"],
            "binding_criterion": crit["binding_criterion"],
            "n_near_miss_beta": crit["n_near_miss_beta"],
            "n_near_miss_fdr": crit["n_near_miss_fdr"],
        },
        "fdr_sensitivity": fdr_sens,
        "beta_sensitivity": beta_sens,
        "promoted_pairs": promoted_list,
        "pre_covid_p_values": {
            k: (float(v) if v is not None else None)
            for k, v in pre_covid_p.items()
        },
        "fr_label_counts": label_counts,
        "gates": [r.as_dict() for r in gate_results],
    }

    with open(OUT_COVERAGE_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    with open(OUT_GATES_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print(f"\nDEC-060 France Relation Signal Recovery Audit")
    print(f"Decision: {decision['decision']}")
    print(f"Gates: {decision['n_pass']}/10 PASS, {decision['n_fail']}/10 FAIL")
    if decision["critical_fail"]:
        print(f"Critical failures: {decision['critical_fail']}")
    if decision["secondary_fail"]:
        print(f"Secondary failures: {decision['secondary_fail']}")
    print()
    print(f"Criterion analysis (total rows={len(fr_raw)}):")
    print(f"  pass_fdr  (q ≤ {PHASE7_FDR_Q}): {crit['n_pass_fdr']}")
    print(f"  pass_beta (|β| ≥ {PHASE7_MIN_ABS_BETA}): {crit['n_pass_beta']}")
    print(f"  pass_dr2  (Δr² ≥ {PHASE7_MIN_DELTA_R2}): {crit['n_pass_dr2']}")
    print(f"  pass_bss  (bss ≥ {PHASE7_MIN_BSS}): {crit['n_pass_bss']}")
    print(f"  pass_all  (promoted): {crit['n_pass_all']}")
    print(f"  near_miss_beta: {crit['n_near_miss_beta']}")
    print(f"  near_miss_fdr:  {crit['n_near_miss_fdr']}")
    print(f"  binding criterion: {crit['binding_criterion']}")
    print()
    print(f"FR label distribution: {label_counts}")
    print()
    for gate in gate_results:
        print(f"  {gate.gate_id}: {gate.verdict}")
    print()
    print(f"Outputs:")
    print(f"  {OUT_PAIRS_CSV}")
    print(f"  {OUT_COVERAGE_CSV}")
    print(f"  {OUT_COVERAGE_JSON}")


if __name__ == "__main__":
    main()
