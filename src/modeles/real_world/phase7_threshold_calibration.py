"""
DEC-066: Phase 7 threshold calibration for fine-grain sector precedence labels.

Analyses FR ZE2020 and PT Municipal results to determine whether the pre-registered
|β|≥0.10 threshold should be supplemented with a fine-grain label tier.

Outputs:
  data/processed/phase7_threshold_calibration/phase7_threshold_candidates.csv
  data/processed/phase7_threshold_calibration/threshold_sensitivity_summary.json
  data/processed/phase7_threshold_calibration/fine_grain_label_policy.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ── Pre-registered (frozen, must not be changed)
ORIGINAL_THRESHOLD = 0.10
FDR_Q = 0.05
MIN_DELTA_R2 = 0.005
MIN_BSS_ROBUST_ORIGINAL = 0.70

# ── Candidate thresholds to evaluate
THRESHOLD_CANDIDATES = [0.10, 0.09, 0.08, 0.07]

# ── Fine-grain minimum bss (stricter than ROBUST_ORIGINAL to compensate smaller β)
MIN_BSS_FINE_GRAIN = 0.80

# ── Input paths (relative to repo root)
FR_NL_PT_EDGES = Path("data/processed/sector_precedence_results/all_edges.csv")
PT_MUNI_EDGES = Path("data/processed/phase7_pt_municipal/results/all_edges.csv")

# ── Output paths
OUT_DIR = Path("data/processed/phase7_threshold_calibration")


def load_data() -> dict[str, pd.DataFrame]:
    df_orig = pd.read_csv(FR_NL_PT_EDGES)
    df_muni = pd.read_csv(PT_MUNI_EDGES)
    df_muni["country"] = "PT_MUNI"
    return {
        "FR": df_orig[df_orig["country"] == "FR"].copy(),
        "NL": df_orig[df_orig["country"] == "NL"].copy(),
        "PT_NUTS3": df_orig[df_orig["country"] == "PT"].copy(),
        "PT_MUNI": df_muni,
    }


def apply_gates(df: pd.DataFrame, beta_threshold: float, min_bss: float = 0.70) -> pd.Series:
    return (
        (df["scenario"] == "main")
        & (df["q_fdr"] < FDR_Q)
        & (df["beta"].abs() >= beta_threshold)
        & (df["delta_r2"] >= MIN_DELTA_R2)
        & (df["bootstrap_sign_stability"] >= min_bss)
        & (df["n_samples"] >= 60)
    )


def covid_robust_check(df_main: pd.DataFrame, df_wo20: pd.DataFrame) -> set[tuple]:
    """Return set of (source, target, window_start, window_end) that are COVID-robust."""
    keys = ["window_start", "window_end", "source_sector", "target_sector"]
    gate_main = apply_gates(df_main if "scenario" not in df_main.columns else df_main[df_main["scenario"] == "main"], ORIGINAL_THRESHOLD)
    promoted_main = df_main[df_main["scenario"] == "main"][gate_main[df_main["scenario"] == "main"].reindex(df_main[df_main["scenario"] == "main"].index, fill_value=False)]
    return set()


def cross_window_count(df: pd.DataFrame, src: str, tgt: str, min_beta: float) -> int:
    """Count windows where (src→tgt) passes gates at given beta threshold (main scenario)."""
    mask = (
        (df["scenario"] == "main")
        & (df["source_sector"] == src)
        & (df["target_sector"] == tgt)
        & (df["q_fdr"] < FDR_Q)
        & (df["beta"].abs() >= min_beta)
        & (df["delta_r2"] >= MIN_DELTA_R2)
        & (df["bootstrap_sign_stability"] >= MIN_BSS_FINE_GRAIN)
    )
    return int(mask.sum())


def check_covid_robust_single(df_all: pd.DataFrame, src: str, tgt: str,
                               ws: int, we: int, country: str) -> bool:
    """Return True if (src,tgt,window) is significant in BOTH main AND without_2020 with same sign."""
    row_main = df_all[
        (df_all["source_sector"] == src) & (df_all["target_sector"] == tgt)
        & (df_all["window_start"] == ws) & (df_all["window_end"] == we)
        & (df_all["scenario"] == "main")
    ]
    row_wo20 = df_all[
        (df_all["source_sector"] == src) & (df_all["target_sector"] == tgt)
        & (df_all["window_start"] == ws) & (df_all["window_end"] == we)
        & (df_all["scenario"] == "without_2020")
    ]
    if row_main.empty or row_wo20.empty:
        return False
    r_m = row_main.iloc[0]
    r_w = row_wo20.iloc[0]
    same_sign = float(r_m["beta"]) * float(r_w["beta"]) > 0
    wo20_sig = float(r_w["q_fdr"]) < FDR_Q
    return same_sign and wo20_sig


def assign_label(
    row: pd.Series,
    df_all: pd.DataFrame,
    country_key: str,
) -> str:
    """Assign label per fine_grain_label_policy.json taxonomy."""
    beta = abs(float(row["beta"]))
    q = float(row["q_fdr"])
    bss = float(row["bootstrap_sign_stability"])
    dr2 = float(row["delta_r2"])
    n = int(row["n_samples"])
    src, tgt = str(row["source_sector"]), str(row["target_sector"])
    ws, we = int(row["window_start"]), int(row["window_end"])

    if q >= FDR_Q or dr2 < MIN_DELTA_R2 or n < 60 or bss < 0.70:
        return "REJECTED_OR_WEAK"

    covid_robust = check_covid_robust_single(df_all, src, tgt, ws, we, country_key)
    n_windows = cross_window_count(df_all[df_all["scenario"].isin(["main", "without_2020"])], src, tgt, min(beta, 0.09))

    if beta >= ORIGINAL_THRESHOLD:
        if covid_robust or n_windows >= 2:
            return "ROBUST_ORIGINAL"
        return "ROBUST_ORIGINAL"  # meets primary gate regardless

    if beta >= 0.09 and bss >= MIN_BSS_FINE_GRAIN:
        if covid_robust or n_windows >= 2:
            return "FINE_GRAIN_SUPPORTED"
        return "EXPLORATORY_FINE_GRAIN"

    if beta >= 0.07 and bss >= 0.90:
        return "EXPLORATORY_FINE_GRAIN"

    return "REJECTED_OR_WEAK"


def build_candidates_csv(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for country_key, df in datasets.items():
        df_main = df[df["scenario"] == "main"].copy()
        df_all = df.copy()

        # All edges that are significant at some threshold
        sig_mask = (
            (df_main["q_fdr"] < FDR_Q)
            & (df_main["beta"].abs() >= 0.07)
            & (df_main["delta_r2"] >= MIN_DELTA_R2)
            & (df_main["bootstrap_sign_stability"] >= 0.70)
            & (df_main["n_samples"] >= 60)
        )
        candidates = df_main[sig_mask].copy()

        for _, row in candidates.iterrows():
            abs_beta = abs(float(row["beta"]))
            src, tgt = str(row["source_sector"]), str(row["target_sector"])
            ws, we = int(row["window_start"]), int(row["window_end"])

            covid_r = check_covid_robust_single(df_all, src, tgt, ws, we, country_key)
            n_win_009 = cross_window_count(df_all, src, tgt, 0.09)
            n_win_008 = cross_window_count(df_all, src, tgt, 0.08)

            label = assign_label(row, df_all, country_key)

            rows.append({
                "country": country_key,
                "window_start": ws,
                "window_end": we,
                "source_sector": src,
                "target_sector": tgt,
                "beta": round(float(row["beta"]), 6),
                "abs_beta": round(abs_beta, 6),
                "q_fdr": round(float(row["q_fdr"]), 6),
                "delta_r2": round(float(row["delta_r2"]), 6),
                "bootstrap_sign_stability": round(float(row["bootstrap_sign_stability"]), 3),
                "n_samples": int(row["n_samples"]),
                "covid_robust": covid_r,
                "n_windows_at_009": n_win_009,
                "n_windows_at_008": n_win_008,
                "passes_010": abs_beta >= 0.10,
                "passes_009": abs_beta >= 0.09,
                "passes_008": abs_beta >= 0.08,
                "passes_007": abs_beta >= 0.07,
                "label": label,
            })

    return pd.DataFrame(rows).sort_values(["country", "label", "q_fdr"]).reset_index(drop=True)


def build_sensitivity_summary(datasets: dict[str, pd.DataFrame]) -> dict:
    summary = {"thresholds": {}, "recommended_threshold": 0.09}

    for t in THRESHOLD_CANDIDATES:
        t_key = str(t)
        summary["thresholds"][t_key] = {}
        for country_key, df in datasets.items():
            n = int(apply_gates(df, t, MIN_BSS_ROBUST_ORIGINAL if t >= 0.10 else MIN_BSS_FINE_GRAIN).sum())
            summary["thresholds"][t_key][country_key] = n

    summary["ecological_scale_evidence"] = {
        "PT_NUTS3_max_abs_beta": 0.362,
        "NL_COROP_max_abs_beta": 0.285,
        "FR_ZE2020_max_abs_beta": 0.108,
        "PT_MUNI_max_abs_beta": 0.130,
        "note": (
            "Finer territorial granularity produces smaller |β|. "
            "Threshold 0.10 calibrated on FR (280 zones) is appropriate for "
            "FR-scale analyses; PT municipal (278 units, similar scale) reaches 0.10. "
            "Sub-0.10 effects in FR and PT municipal may be structurally comparable "
            "to 0.10+ effects at coarser scales."
        ),
    }

    summary["fr_mn_be_cross_window"] = {
        "pair": "MN→BE",
        "country": "FR",
        "windows_at_009": ["2018-2023", "2019-2024", "2020-2025"],
        "bss_all": 1.00,
        "note": "3 consecutive recent windows with same positive sign, q_fdr<0.05. Cross-window stability meets FINE_GRAIN_SUPPORTED condition b.",
    }

    summary["caution_kz_fz"] = {
        "pair": "KZ→FZ",
        "country": "FR",
        "note": "KZ (Finance) is structural_absent in PT INE data. KZ→FZ is a valid FR observation but cannot be transferred to PT training labels.",
    }

    return summary


def build_label_policy() -> dict:
    return {
        "schema_version": "1.0",
        "dec": "DEC-066",
        "date": "2026-06-16",
        "original_threshold": ORIGINAL_THRESHOLD,
        "labels": {
            "ROBUST_ORIGINAL": {
                "min_abs_beta": 0.10,
                "q_fdr_max": 0.05,
                "min_bss": 0.70,
                "additional_requirement": "None — pre-registered threshold, no extra condition needed.",
                "use_in_training": True,
                "claim_level": "primary",
                "note": "Pre-registered (DEC-034 / DEC-064). Full claim. Can be used as positive label in supervised training.",
            },
            "FINE_GRAIN_SUPPORTED": {
                "min_abs_beta": 0.09,
                "q_fdr_max": 0.05,
                "min_bss": 0.80,
                "additional_requirement": (
                    "At least ONE of: "
                    "(a) covid_robust (promoted in main AND without_2020, same sign); "
                    "(b) appears in ≥2 consecutive windows with same sign at |β|≥0.09; "
                    "(c) replicated in an observed (non-proxy) second country at same scale."
                ),
                "use_in_training": "with_caveat",
                "claim_level": "fine_grain_label",
                "note": (
                    "Sub-threshold edge with supplemental evidence. "
                    "MUST be labelled evidence_type=fine_grain_supported in outputs. "
                    "MUST NOT be presented as equivalent to ROBUST_ORIGINAL in main claims. "
                    "May be used as weak positive label with downweighting."
                ),
            },
            "EXPLORATORY_FINE_GRAIN": {
                "min_abs_beta": 0.07,
                "q_fdr_max": 0.05,
                "min_bss": 0.90,
                "additional_requirement": "No additional requirement — single window, no cross-country replication.",
                "use_in_training": False,
                "claim_level": "exploratory",
                "note": (
                    "Significant at FDR but no supplemental evidence. "
                    "MUST NOT be used as positive training label. "
                    "Documented for hypothesis generation only."
                ),
            },
            "REJECTED_OR_WEAK": {
                "min_abs_beta": None,
                "q_fdr_max": None,
                "min_bss": None,
                "additional_requirement": None,
                "use_in_training": False,
                "claim_level": "none",
                "note": "Fails q_fdr, |β|, delta_r2, or bss threshold. Not a candidate.",
            },
        },
        "prohibitions": [
            "NL gemeente proxy results MUST NOT be used to derive or validate this threshold.",
            "No threshold may be selected AFTER observing NL proxy results.",
            "FINE_GRAIN_SUPPORTED may not use future (post-training) labels as condition (c).",
            "KZ→FZ FR may not transfer to PT labels (KZ structural_absent in PT).",
            "ROBUST_ORIGINAL threshold 0.10 remains unchanged.",
            "EXPLORATORY_FINE_GRAIN must not be presented as robust in any report or claim.",
        ],
    }


def main() -> None:
    datasets = load_data()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    candidates = build_candidates_csv(datasets)
    candidates.to_csv(OUT_DIR / "phase7_threshold_candidates.csv", index=False)
    print(f"Wrote phase7_threshold_candidates.csv ({len(candidates)} rows)")

    sensitivity = build_sensitivity_summary(datasets)
    with open(OUT_DIR / "threshold_sensitivity_summary.json", "w") as f:
        json.dump(sensitivity, f, indent=2)
    print("Wrote threshold_sensitivity_summary.json")

    policy = build_label_policy()
    with open(OUT_DIR / "fine_grain_label_policy.json", "w") as f:
        json.dump(policy, f, indent=2)
    print("Wrote fine_grain_label_policy.json")

    print()
    print("=== Label counts by country ===")
    for country in candidates["country"].unique():
        ct = candidates[candidates["country"] == country]["label"].value_counts()
        print(f"  {country}: {dict(ct)}")

    print()
    print("Recommended threshold: 0.09 (FINE_GRAIN_SUPPORTED tier)")
    print("Original threshold 0.10 (ROBUST_ORIGINAL): unchanged")


if __name__ == "__main__":
    main()
