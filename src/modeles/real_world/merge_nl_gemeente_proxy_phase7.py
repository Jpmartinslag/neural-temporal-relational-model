"""
DEC-065: Merge NL gemeente proxy Phase 7 results, apply BH/FDR,
assign DEC-066 labels, compare with NL COROP, output audit artefacts.

Run after HPC job 7475756 completes (252/252 tasks):
    python src/modeles/real_world/merge_nl_gemeente_proxy_phase7.py

Outputs:
    data/processed/phase7_nl_gemeente_proxy/results/all_edges.csv
    data/processed/phase7_nl_gemeente_proxy/results/latest.csv
    data/processed/phase7_nl_gemeente_proxy/results/covid_robust_edges.csv
    data/processed/phase7_nl_gemeente_proxy/results/decision.json
    data/processed/phase7_nl_gemeente_proxy/nl_corop_vs_gemeente_proxy_comparison.csv
    data/processed/phase7_nl_gemeente_proxy/nl_gemeente_proxy_label_summary.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths
RAW_DIR = Path("hpc_results/phase7_nl_gemeente_proxy/raw")
MANIFEST_PATH = Path("data/processed/phase7_nl_gemeente_proxy/hpc_task_manifest.json")
PANEL_MANIFEST_PATH = Path("data/processed/phase7_nl_gemeente_proxy/nl_gemeente_phase7_panel_manifest.json")
OUT_DIR = Path("data/processed/phase7_nl_gemeente_proxy/results")
POLICY_PATH = Path("data/processed/phase7_threshold_calibration/fine_grain_label_policy.json")
COROP_EDGES_PATH = Path("data/processed/sector_precedence_results/all_edges.csv")
OUT_COMPARISON = Path("data/processed/phase7_nl_gemeente_proxy/nl_corop_vs_gemeente_proxy_comparison.csv")
OUT_LABEL_SUMMARY = Path("data/processed/phase7_nl_gemeente_proxy/nl_gemeente_proxy_label_summary.json")

# ── Pre-registered gate constants (DEC-034 / DEC-065)
FDR_Q = 0.05
MIN_ABS_BETA = 0.10
MIN_DELTA_R2 = 0.005
MIN_SIGN_STABILITY = 0.70
MIN_SAMPLES = 60

# ── DEC-066 fine-grain thresholds
FINE_GRAIN_BETA = 0.09
FINE_GRAIN_BSS = 0.80
EXPLORATORY_BETA = 0.07
EXPLORATORY_BSS = 0.90
N_WINDOWS_MIN = 2

# ── Pre-registered NL COROP promoted main-scenario pairs
COROP_PROMOTED = [
    ("BE", "MN", 2009, 2014, -1),
    ("BE", "RU", 2009, 2014, -1),
    ("FZ", "GI", 2014, 2019, +1),
    ("FZ", "RU", 2014, 2019, +1),
    ("JZ", "FZ", 2014, 2019, -1),
    ("JZ", "RU", 2014, 2019, -1),
    ("LZ", "RU", 2014, 2019, +1),
    ("OQ", "JZ", 2014, 2019, -1),
]
COROP_ROBUST = {("FZ", "GI"), ("FZ", "RU"), ("JZ", "FZ")}

EVIDENCE_TYPE = "proxy_disaggregated_by_stock_share"


def bh_fdr(pvalues: pd.Series) -> pd.Series:
    values = pvalues.to_numpy(dtype=float)
    result = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        return pd.Series(result, index=pvalues.index)
    order = valid[np.argsort(values[valid])]
    ranked = values[order] * len(order) / np.arange(1, len(order) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    result[order] = np.minimum(ranked, 1.0)
    return pd.Series(result, index=pvalues.index)


def load_raw_results(raw_dir: Path, manifest: list[dict]) -> pd.DataFrame:
    rows = []
    missing = []
    for task in manifest:
        path = raw_dir / task["expected_output"]
        if not path.exists():
            missing.append(task["task_id"])
            continue
        result = json.loads(path.read_text())
        if result.get("status") != "complete":
            sys.exit(f"ERROR: task {task['task_id']} status={result.get('status')!r}")
        for edge in result.get("edges", []):
            rows.append({
                "task_id": result["task_id"],
                "country": result["country"],
                "scenario": result["scenario"],
                "window_start": result["window_start"],
                "window_end": result["window_end"],
                "source_sector": result["source_sector"],
                "target_sector": edge["target_sector"],
                "n_samples": edge["n_samples"],
                "beta": float(edge["beta"]),
                "delta_r2": float(edge["delta_r2"]),
                "p_perm": float(edge["p_perm"]),
                "bootstrap_sign_stability": float(edge["bootstrap_sign_stability"]),
                "panel_checksum": result.get("panel_checksum", ""),
                "commit_sha": result.get("commit_sha", ""),
                "hostname": result.get("hostname", ""),
                "runtime_seconds": result.get("runtime_seconds", None),
            })
    if missing:
        sys.exit(f"ERROR: {len(missing)} tasks missing: {sorted(missing)[:20]}")
    return pd.DataFrame(rows)


def apply_fdr(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["q_fdr"] = np.nan
    for (country, scenario, ws, we), group in df.groupby(
        ["country", "scenario", "window_start", "window_end"]
    ):
        q = bh_fdr(group["p_perm"])
        df.loc[group.index, "q_fdr"] = q.values
    return df


def apply_promotion(df: pd.DataFrame) -> pd.Series:
    return (
        df["q_fdr"].le(FDR_Q)
        & df["beta"].abs().ge(MIN_ABS_BETA)
        & df["delta_r2"].ge(MIN_DELTA_R2)
        & df["bootstrap_sign_stability"].ge(MIN_SIGN_STABILITY)
        & df["n_samples"].ge(MIN_SAMPLES)
    )


def get_covid_robust(df: pd.DataFrame) -> pd.DataFrame:
    main_p = df[(df["scenario"] == "main") & df["promoted"]][
        ["country", "window_start", "window_end", "source_sector", "target_sector", "beta"]
    ].rename(columns={"beta": "beta_main"})
    wo20_p = df[(df["scenario"] == "without_2020") & df["promoted"]][
        ["country", "window_start", "window_end", "source_sector", "target_sector", "beta"]
    ].rename(columns={"beta": "beta_wo20"})
    merged = main_p.merge(wo20_p, on=["country", "window_start", "window_end",
                                       "source_sector", "target_sector"], how="inner")
    return merged[np.sign(merged["beta_main"]) == np.sign(merged["beta_wo20"])].copy()


def count_windows_at_threshold(df: pd.DataFrame, src: str, tgt: str, min_beta: float,
                                scenario: str = "main") -> int:
    sub = df[
        (df["scenario"] == scenario) &
        (df["source_sector"] == src) &
        (df["target_sector"] == tgt) &
        (df["beta"].abs() >= min_beta) &
        (df["q_fdr"] < FDR_Q)
    ]
    return len(sub)


def assign_dec066_label(row: pd.Series, df_main: pd.DataFrame,
                        covid_robust_set: set) -> str:
    src, tgt = row["source_sector"], row["target_sector"]
    beta = abs(float(row["beta"]))
    bss = float(row["bootstrap_sign_stability"])
    ws, we = int(row["window_start"]), int(row["window_end"])

    if beta >= MIN_ABS_BETA:
        return "ROBUST_ORIGINAL"

    if beta >= FINE_GRAIN_BETA and bss >= FINE_GRAIN_BSS:
        is_covid_robust = (src, tgt, ws, we) in covid_robust_set
        n_windows = count_windows_at_threshold(df_main, src, tgt, FINE_GRAIN_BETA)
        if is_covid_robust or n_windows >= N_WINDOWS_MIN:
            return "FINE_GRAIN_SUPPORTED"
        return "EXPLORATORY_FINE_GRAIN"

    if beta >= EXPLORATORY_BETA and bss >= EXPLORATORY_BSS:
        return "EXPLORATORY_FINE_GRAIN"

    return "REJECTED_OR_WEAK"


def build_corop_comparison(gemeente_main: pd.DataFrame) -> pd.DataFrame:
    """Compare NL COROP promoted pairs against gemeente proxy signal."""
    rows = []
    for src, tgt, corop_ws, corop_we, expected_sign in COROP_PROMOTED:
        is_robust = (src, tgt) in COROP_ROBUST
        proxy_rows = gemeente_main[
            (gemeente_main["source_sector"] == src) &
            (gemeente_main["target_sector"] == tgt)
        ].copy()

        best_row = None
        if len(proxy_rows) > 0:
            sig = proxy_rows[proxy_rows["p_perm"] < 0.20]
            if len(sig) > 0:
                best_row = sig.loc[sig["beta"].abs().idxmax()]

        rows.append({
            "source_sector": src,
            "target_sector": tgt,
            "corop_window": f"{corop_ws}-{corop_we}",
            "corop_expected_sign": "+" if expected_sign > 0 else "-",
            "corop_covid_robust": is_robust,
            "region_system": "COROP",
            "source": "NL_COROP_observed",
            "proxy_n_windows_p020": len(proxy_rows[proxy_rows["p_perm"] < 0.20]),
            "proxy_best_window": (
                f"{int(best_row['window_start'])}-{int(best_row['window_end'])}"
                if best_row is not None else "none"
            ),
            "proxy_best_beta": (
                float(best_row["beta"]) if best_row is not None else None
            ),
            "proxy_sign_consistent": (
                (np.sign(float(best_row["beta"])) == expected_sign)
                if best_row is not None else None
            ),
            "proxy_best_q_fdr": (
                float(best_row["q_fdr"]) if best_row is not None else None
            ),
            "proxy_best_bss": (
                float(best_row["bootstrap_sign_stability"])
                if best_row is not None else None
            ),
            "evidence_type": EVIDENCE_TYPE,
            "proxy_source": "NL_GEMEENTE_PROXY",
        })
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text())
    panel_manifest = json.loads(PANEL_MANIFEST_PATH.read_text())
    print(f"Manifest: {len(manifest)} tasks")

    df = load_raw_results(RAW_DIR, manifest)
    print(f"Loaded {len(df)} edges")

    df = apply_fdr(df)
    df["promoted"] = apply_promotion(df)

    df.to_csv(OUT_DIR / "all_edges.csv", index=False)
    print(f"Wrote all_edges.csv ({len(df)} rows)")

    robust_df = get_covid_robust(df)
    robust_df.to_csv(OUT_DIR / "covid_robust_edges.csv", index=False)

    promoted_main = df[(df["scenario"] == "main") & df["promoted"]].copy()
    promoted_main.to_csv(OUT_DIR / "latest.csv", index=False)
    print(f"Promoted (main): {len(promoted_main)}")
    print(f"COVID-robust: {len(robust_df)}")

    # ── DEC-066 labelling (main scenario, promoted + near-misses ≥0.07)
    main_df = df[df["scenario"] == "main"].copy()
    candidates = main_df[
        (main_df["q_fdr"] < FDR_Q) &
        (main_df["beta"].abs() >= EXPLORATORY_BETA) &
        (main_df["delta_r2"] >= MIN_DELTA_R2) &
        (main_df["n_samples"] >= MIN_SAMPLES)
    ].copy()

    covid_robust_set = set(
        (r.source_sector, r.target_sector, r.window_start, r.window_end)
        for _, r in robust_df.iterrows()
    )

    if len(candidates) > 0:
        candidates["label"] = candidates.apply(
            lambda r: assign_dec066_label(r, main_df, covid_robust_set), axis=1
        )
        candidates.to_csv(OUT_DIR / "dec066_labelled_candidates.csv", index=False)
        label_counts = candidates["label"].value_counts().to_dict()
    else:
        label_counts = {}

    # ── COROP comparison
    gemeente_main = df[df["scenario"] == "main"].copy()
    comparison = build_corop_comparison(gemeente_main)
    comparison.to_csv(OUT_COMPARISON, index=False)
    print(f"Wrote COROP comparison ({len(comparison)} rows)")

    # ── N4 gate check
    n_preserved = comparison["proxy_sign_consistent"].sum() if "proxy_sign_consistent" in comparison else 0
    n4_pass = int(n_preserved) >= 4

    # ── Verdict
    n_robust_gemeente = len(robust_df)
    n_promoted_gemeente = len(promoted_main)
    if n_robust_gemeente >= 2 and n4_pass:
        verdict = "NL_GEMEENTE_PROXY_PHASE7_SUPPORTED"
    elif n4_pass:
        verdict = "NL_GEMEENTE_PROXY_PHASE7_EXPLORATORY_ONLY"
    elif n_promoted_gemeente > 0:
        verdict = "NL_GEMEENTE_PROXY_PHASE7_EXPLORATORY_ONLY"
    else:
        verdict = "NL_GEMEENTE_PROXY_PHASE7_BLOCKED"

    decision = {
        "dec": "DEC-065",
        "verdict": verdict,
        "country": "NL",
        "region_system": "GEMEENTE_PROXY",
        "evidence_type": EVIDENCE_TYPE,
        "total_tasks": len(manifest),
        "total_edges_raw": len(df),
        "promoted_main_count": n_promoted_gemeente,
        "covid_robust_count": n_robust_gemeente,
        "n4_corop_pairs_preserved": int(n_preserved),
        "n4_pass": n4_pass,
        "gate_thresholds": {
            "q_fdr": FDR_Q,
            "min_abs_beta": MIN_ABS_BETA,
            "min_delta_r2": MIN_DELTA_R2,
            "min_sign_stability": MIN_SIGN_STABILITY,
            "min_samples": MIN_SAMPLES,
        },
        "label_policy": "DEC-066",
        "label_counts": label_counts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "All results carry evidence_type=proxy_disaggregated_by_stock_share. "
            "This is NOT observed births. Results must not be pooled with observed "
            "data without sensitivity analysis excluding proxy."
        ),
    }
    (OUT_DIR / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")

    label_summary = {
        "dec": "DEC-065",
        "evidence_type": EVIDENCE_TYPE,
        "proxy_method": "corop_births_allocated_by_gemeente_stock_share",
        "panel_checksum": panel_manifest.get("panel_checksum_sha256", ""),
        "label_counts": label_counts,
        "n_promoted_robust_original": n_promoted_gemeente,
        "n_covid_robust": n_robust_gemeente,
        "corop_comparison": {
            "n_corop_promoted_pairs": len(COROP_PROMOTED),
            "n_preserved_in_proxy": int(n_preserved),
            "n4_pass": n4_pass,
        },
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": "proxy_disaggregated_by_stock_share — not observed births",
    }
    OUT_LABEL_SUMMARY.write_text(json.dumps(label_summary, indent=2) + "\n")

    print(f"\nVERDICT: {verdict}")
    print(f"N4 COROP preservation: {n_preserved}/8 pairs")
    print(f"N4 PASS: {n4_pass}")
    print(f"Wrote: {OUT_DIR / 'decision.json'}")
    print(f"Wrote: {OUT_LABEL_SUMMARY}")


if __name__ == "__main__":
    main()
