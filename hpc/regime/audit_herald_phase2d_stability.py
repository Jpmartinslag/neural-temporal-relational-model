#!/usr/bin/env python3
"""Audit script for HERALD Phase 2D stability battery.

Checks:
  - 120/120 expected runs present (12 configs × 10 seeds)
  - JSON, CSV total, CSV sector, NPZ, metadata artefacts exist
  - No manual flags in non-ctrl configs
  - No source flags in no_source configs
  - PELT breakpoints are causal (all bkp_year <= train_max)
  - WMAPE mean (from per-run JSON total_wmape_mean — correct per seed)
  - WMAPE per fold (2021-2025)
  - CV WMAPE 2021 across seeds
  - A10 WMAPE
  - Alpha by year
  - Latent step 2020→2021 per seed (from NPZ)
  - Error concentration in large zones 2021 (from CSV)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_LABELS = [
    "ctrl_manual",
    "ctrl_noregime",
    "cand_2c",
    "D1a_col01",
    "D1b_col05",
    "D2a_pelt3",
    "D2b_pelt5",
    "D3_aba",
    "D4_dro15",
    "D5_swa",
    "D6_roll9",
    "D7_roll7",
]
SEEDS = [0, 1, 7, 13, 17, 42, 77, 99, 123, 2025]
N_EXPECTED = len(EXPECTED_LABELS) * len(SEEDS)   # 120
PELT_LABELS = {"D2a_pelt3", "D2b_pelt5"}
CTRL_LABEL = "ctrl_manual"

# Rejection thresholds (Phase 2D plan)
WMAPE_MEAN_REF = 0.02883
WMAPE_2021_REF = 0.04876
WMAPE_2025_REF = 0.01854
A10_REF        = 0.16241


# ---------------------------------------------------------------------------
# Artefact path helpers
# ---------------------------------------------------------------------------

def _run_tag_for_label(label: str) -> str:
    """Reconstruct the run tag used in file naming for a given experiment label."""
    # Mirrors the tag logic in run_herald_regime_seed.sh:
    #   tag = "regime_{mode}" [+ "_{variant}"] [+ "_no_source_flags"] [+ "_{label}"]
    # For phase2d_stability all non-ctrl are no_source_flags + secenh variant.
    if label == "ctrl_manual":
        return f"regime_manual_flags_no_source_flags_{label}"
    if label == "ctrl_noregime":
        return f"regime_no_regime_no_source_flags_{label}"
    if label in {"D2a_pelt3", "D6_pelt3"}:
        return f"regime_pelt_regime_pen3_learned_regime_gate_sector_enhanced_no_source_flags_{label}"
    if label in {"D2b_pelt5", "D7_pelt5"}:
        return f"regime_pelt_regime_pen5_learned_regime_gate_sector_enhanced_no_source_flags_{label}"
    # All other Phase 2D: no_regime + secenh variant
    return f"regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_{label}"


def find_per_run_json(root: Path, label: str, seed: int) -> Path | None:
    """Find the per-run metrics JSON by globbing for the label+seed pattern."""
    pattern = f"*{label}_seed_{seed}.json"
    matches = sorted((root / "reports" / "per_run").glob(pattern))
    if not matches:
        return None
    return matches[0]


def find_artefacts(root: Path, label: str, seed: int) -> dict:
    tag = _run_tag_for_label(label)
    # semiv2 suffix: "{mode}{_runtag}_seed_{seed}" = "full_{tag}_seed_{seed}"
    suffix = f"full_{tag}_seed_{seed}"
    dp = root / "data_processed"
    return {
        "json":       root / "reports" / "per_run" / f"{tag}_seed_{seed}.json",
        "csv_total":  dp / f"herald_semi_v2_predictions_total_{suffix}_v1.csv",
        "csv_sector": dp / f"herald_semi_v2_predictions_sector_{suffix}_v1.csv",
        "npz":        dp / f"herald_semi_v2_internals_{suffix}_v1.npz",
        "metadata":   root / "metadata" / f"{tag}_seed_{seed}.json",
    }


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def load_metadata(arts: dict) -> dict:
    p = arts["metadata"]
    return json.loads(p.read_text()) if p.exists() else {}


def load_per_run_metrics(root: Path, label: str, seed: int) -> dict:
    """Load the per-run metrics from the JSON file (total_wmape_mean is pre-computed)."""
    jf = find_per_run_json(root, label, seed)
    if jf is None or not jf.exists():
        return {}
    payload = json.loads(jf.read_text())
    # payload is {run_key: result_dict}; take the first (only) value
    for v in payload.values():
        return v
    return {}


def load_predictions(arts: dict) -> pd.DataFrame | None:
    p = arts["csv_total"]
    return pd.read_csv(p) if p.exists() else None


def load_sector_predictions(arts: dict) -> pd.DataFrame | None:
    p = arts["csv_sector"]
    return pd.read_csv(p) if p.exists() else None


def load_npz(arts: dict) -> dict | None:
    p = arts["npz"]
    return dict(np.load(p, allow_pickle=True)) if p.exists() else None


def wmape(y_true, y_pred) -> float:
    denom = float(np.abs(y_true).sum())
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 1e-8 else float("nan")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_completeness(root: Path):
    ok, missing = [], []
    for label in EXPECTED_LABELS:
        for seed in SEEDS:
            arts = find_artefacts(root, label, seed)
            absent = [k for k, p in arts.items() if not p.exists()]
            if absent:
                missing.append(f"{label}/seed={seed}: missing {absent}")
            else:
                ok.append((label, seed, arts))
    return ok, missing


def check_flags(label: str, metadata: dict) -> list[str]:
    errs = []
    if label != CTRL_LABEL:
        if metadata.get("manual_flags_in_annual_features", True):
            errs.append("manual_flags_in_annual_features=True")
        if metadata.get("manual_flags_in_regime_vector", True):
            errs.append("manual_flags_in_regime_vector=True")
    if metadata.get("source_flags_in_annual_features", True):
        errs.append("source_flags_in_annual_features=True")
    return errs


def check_pelt_causality(label: str, metadata: dict) -> list[str]:
    if label not in PELT_LABELS:
        return []
    bkps_by_tm = metadata.get("pelt_breakpoints_by_train_max")
    if bkps_by_tm is None:
        return ["pelt_breakpoints_by_train_max missing from metadata"]
    errs = []
    for tm_str, bkp_years in bkps_by_tm.items():
        tm = int(tm_str)
        bad = [y for y in bkp_years if y > tm]
        if bad:
            errs.append(f"LEAKAGE train_max={tm}: breakpoints {bad} > {tm}")
    return errs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Audit HERALD Phase 2D stability battery")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    root = args.root
    print(f"Auditing: {root}\n")

    errors: list[str] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # 1. Completeness
    # ------------------------------------------------------------------
    print("[1] Completeness check...")
    ok_runs, missing = check_completeness(root)
    print(f"    Found {len(ok_runs)}/{N_EXPECTED} complete runs")
    for m in missing:
        errors.append(f"MISSING: {m}")
        if args.verbose:
            print(f"  ERROR: {m}")

    if not ok_runs:
        print("No complete runs found — aborting.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Flag + PELT causality audit
    # ------------------------------------------------------------------
    print("\n[2] Flag and PELT causality audit...")
    flag_err_count = pelt_err_count = 0
    for label, seed, arts in ok_runs:
        meta = load_metadata(arts)
        for e in check_flags(label, meta):
            errors.append(f"FLAG {label}/seed={seed}: {e}")
            flag_err_count += 1
        for e in check_pelt_causality(label, meta):
            errors.append(f"PELT {label}/seed={seed}: {e}")
            pelt_err_count += 1
    print(f"    Flag errors: {flag_err_count}  |  PELT causality errors: {pelt_err_count}")

    # ------------------------------------------------------------------
    # 3. Metrics per config — read from per-run JSON (correct per seed)
    # ------------------------------------------------------------------
    print("\n[3] Metrics per config (from per-run JSON — correct per-seed mean)...")
    metrics_rows = []
    for label in EXPECTED_LABELS:
        wmape_mean_seeds = []
        wmape_by_year: dict[int, list[float]] = {yr: [] for yr in range(2021, 2026)}
        a10_seeds = []
        alpha_2021_seeds = []

        for seed in SEEDS:
            result = load_per_run_metrics(root, label, seed)
            if not result:
                continue
            # total_wmape_mean is the mean across all folds for this seed — correct
            mw = result.get("total_wmape_mean")
            if mw is not None:
                wmape_mean_seeds.append(float(mw))
            # per-year WMAPE
            per_yr = result.get("per_year_total", {})
            for yr in range(2021, 2026):
                v = per_yr.get(str(yr)) or per_yr.get(yr)
                if v is not None:
                    wmape_by_year[yr].append(float(v))
            # A10
            swm = result.get("sector_wmape_mean")
            if swm is not None:
                a10_seeds.append(float(swm))
            # Alpha 2021
            apy = result.get("alpha_by_year", {})
            a21 = apy.get("2021") or apy.get(2021)
            if a21 is not None:
                alpha_2021_seeds.append(float(a21))

        def _m(vals): return round(float(np.nanmean(vals)), 6) if vals else float("nan")
        def _cv(vals):
            if len(vals) < 2 or np.nanmean(vals) < 1e-8:
                return float("nan")
            return round(float(np.nanstd(vals) / np.nanmean(vals) * 100), 2)

        metrics_rows.append({
            "label":           label,
            "mean_wmape":      _m(wmape_mean_seeds),
            "wmape_2021":      _m(wmape_by_year[2021]),
            "wmape_2021_cv%":  _cv(wmape_by_year[2021]),
            "wmape_2022":      _m(wmape_by_year[2022]),
            "wmape_2023":      _m(wmape_by_year[2023]),
            "wmape_2024":      _m(wmape_by_year[2024]),
            "wmape_2025":      _m(wmape_by_year[2025]),
            "a10_wmape":       _m(a10_seeds),
            "alpha_2021_mean": round(float(np.nanmean(alpha_2021_seeds)), 4) if alpha_2021_seeds else float("nan"),
            "n_seeds":         len(wmape_mean_seeds),
        })

    mdf = pd.DataFrame(metrics_rows).set_index("label")
    print(mdf.to_string())

    # ------------------------------------------------------------------
    # 4. Latent step 2020→2021 per config (NPZ)
    # ------------------------------------------------------------------
    print("\n[4] Latent regime step 2020→2021...")
    lat_rows = []
    for label in EXPECTED_LABELS:
        steps = []
        frozen = overreact = 0
        for seed in SEEDS:
            arts = find_artefacts(root, label, seed)
            npz = load_npz(arts)
            if not npz:
                continue
            years = list(npz.get("years", []))
            lat = npz.get("latent_regime_values")
            if lat is None or 2020 not in years or 2021 not in years:
                continue
            t20, t21 = years.index(2020), years.index(2021)
            step = float(np.linalg.norm(lat[t21] - lat[t20]))
            steps.append(step)
            frozen    += int(step < 0.1)
            overreact += int(step > 0.8)

        def _cv(v): return round(float(np.std(v) / np.mean(v) * 100), 1) if len(v) > 1 and np.mean(v) > 0 else float("nan")
        lat_rows.append({
            "label":              label,
            "step_mean":          round(float(np.mean(steps)), 4) if steps else float("nan"),
            "step_cv%":           _cv(steps),
            "frozen<0.1":         frozen,
            "overreact>0.8":      overreact,
            "n_seeds":            len(steps),
        })
    ldf = pd.DataFrame(lat_rows).set_index("label")
    print(ldf.to_string())

    # ------------------------------------------------------------------
    # 5. Error concentration Q5 zones — fold 2021
    # ------------------------------------------------------------------
    print("\n[5] Q5 zone error concentration — fold 2021...")
    ctrl_q5 = None
    zone_rows = []
    for label in EXPECTED_LABELS:
        q5_vals = []
        for seed in SEEDS:
            arts = find_artefacts(root, label, seed)
            df = load_predictions(arts)
            if df is None:
                continue
            df21 = df[df["target_year"] == 2021].copy()
            if df21.empty:
                continue
            q5t = np.nanpercentile(df21["y_true"].values, 80)
            q5df = df21[df21["y_true"] >= q5t]
            if not q5df.empty:
                q5_vals.append(float(q5df["abs_error"].mean()))
        mean_q5 = round(float(np.nanmean(q5_vals)), 2) if q5_vals else float("nan")
        zone_rows.append({"label": label, "q5_ae_2021": mean_q5})
        if label == CTRL_LABEL:
            ctrl_q5 = mean_q5

    zdf = pd.DataFrame(zone_rows).set_index("label")
    if ctrl_q5 and not np.isnan(ctrl_q5):
        zdf["delta_vs_ctrl"] = (zdf["q5_ae_2021"] - ctrl_q5).round(2)
    print(zdf.to_string())

    # ------------------------------------------------------------------
    # 6. Rejection criteria
    # ------------------------------------------------------------------
    print("\n[6] Rejection criteria check...")
    for row in metrics_rows:
        lbl = row["label"]
        if lbl in {CTRL_LABEL, "ctrl_noregime"}:
            continue
        mw = row["mean_wmape"]
        if np.isnan(mw):
            continue
        if mw > WMAPE_MEAN_REF + 0.002:
            warnings.append(f"WARN {lbl}: mean_wmape={mw:.5f} > cand_2c+0.002={WMAPE_MEAN_REF+0.002:.5f}")
        a10 = row["a10_wmape"]
        if not np.isnan(a10) and a10 > A10_REF + 0.005:
            errors.append(f"REJECT {lbl}: A10={a10:.5f} > cand_2c+0.005={A10_REF+0.005:.5f}")
        w21 = row["wmape_2021"]
        if not np.isnan(w21) and w21 > WMAPE_2021_REF + 0.005:
            warnings.append(f"WARN {lbl}: wmape_2021={w21:.5f} (> cand_2c+0.005)")

    if errors:
        print("  REJECTIONS/ERRORS:")
        for e in errors[:20]:
            print(f"    {e}")
    if warnings:
        print("  WARNINGS:")
        for w in warnings[:15]:
            print(f"    {w}")

    # ------------------------------------------------------------------
    # 7. Summary + save CSVs
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    n_found = len(ok_runs)
    if errors:
        print(f"AUDIT FAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
        for e in errors[:20]:
            print(f"  ERROR: {e}")
        sys.exit(1)
    else:
        print(f"AUDIT PASSED — {n_found}/{N_EXPECTED} runs, {len(warnings)} warning(s)")
        for w in warnings[:10]:
            print(f"  WARN: {w}")

    out_dir = root / "reports"
    out_dir.mkdir(exist_ok=True)
    mdf.to_csv(out_dir / "phase2d_audit_metrics.csv")
    ldf.to_csv(out_dir / "phase2d_audit_latent.csv")
    zdf.to_csv(out_dir / "phase2d_audit_zones.csv")
    print(f"\nSaved audit CSVs → {out_dir}/phase2d_audit_*.csv")


if __name__ == "__main__":
    main()
