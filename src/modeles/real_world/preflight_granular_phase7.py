"""
DEC-062 Part D: Granular Phase 7 Readiness Preflight.

Evaluates readiness for running Phase 7 sector-precedence analysis at
municipality/gemeente level for FR, PT, and NL (or NL fallback at COROP).

Does NOT run Phase 7. Does NOT train models. Does NOT promote relations.
"""

from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR = REPO_ROOT / "data/processed/granular_phase7_preflight"
OUT_JSON = OUT_DIR / "granular_phase7_readiness.json"

FRANCE_PANEL = REPO_ROOT / "data/processed/european_panel/france_panel.csv"
PT_MUNI_PANEL = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel.csv"
NL_PANEL = REPO_ROOT / "data/processed/european_panel/nl_panel.csv"
PHASE7_CSV = REPO_ROOT / "data/processed/sector_precedence_results/main_with_sensitivity.csv"

PHASE7_MIN_SAMPLES = 60
PHASE7_MIN_WINDOWS = 5   # at least 5 rolling windows
PHASE7_WINDOW_SIZE = 5   # years

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "LZ", "MN", "OQ", "RU"]


def assess_panel(
    path: Path,
    country: str,
    region_system: str,
    has_sector: bool = True,
) -> dict:
    """Assess a panel's Phase 7 readiness."""
    if not path.exists():
        return {
            "country": country,
            "region_system": region_system,
            "readiness_status": "BLOCKED",
            "reason": f"Panel file not found: {path.name}",
            "recommended_next_action": "Build panel first",
        }

    df = pd.read_csv(path)
    n_regions = df["region_id"].nunique() if "region_id" in df.columns else 0
    years = sorted(df["year"].unique()) if "year" in df.columns else []
    n_years = len(years)
    year_range = f"{years[0]}-{years[-1]}" if years else ""

    # Sector columns
    sector_cols = [f"sector_{s}" for s in A10_SECTORS]
    present_sectors = [s for s in sector_cols if s in df.columns]
    missing_sectors = [s for s in sector_cols if s not in df.columns]
    structural_absent = []
    if "sector_KZ" in df.columns and df["sector_KZ"].isna().all():
        structural_absent = ["KZ"]

    # Coverage
    if has_sector and present_sectors:
        mask_col = "mask_sector_a10"
        if mask_col in df.columns:
            valid_frac = float(df[mask_col].mean())
        else:
            valid_frac = float(df[present_sectors].notna().all(axis=1).mean())
    else:
        valid_frac = 0.0

    # Phase 7 compatibility
    n_windows = max(0, n_years - PHASE7_WINDOW_SIZE + 1)
    n_samples = n_regions * PHASE7_WINDOW_SIZE  # rows per window
    n_pairs = len(A10_SECTORS) * (len(A10_SECTORS) - 1)  # directed pairs

    # Missing rate
    if present_sectors:
        missing_rate = float(df[present_sectors].isna().mean().mean())
    else:
        missing_rate = 1.0

    # Readiness decision
    limitations = []
    if n_regions < 10:
        limitations.append(f"Too few regions: {n_regions}")
    if n_windows < PHASE7_MIN_WINDOWS:
        limitations.append(f"Too few windows: {n_windows} < {PHASE7_MIN_WINDOWS}")
    if n_samples < PHASE7_MIN_SAMPLES:
        limitations.append(f"Too few samples: {n_samples} < {PHASE7_MIN_SAMPLES}")
    if not has_sector or not present_sectors:
        limitations.append("No sector columns — cannot run sector-precedence analysis")
    if structural_absent:
        limitations.append(f"Structural absent sectors: {structural_absent}")

    # Classify limitations
    hard_blocks = [lim for lim in limitations if "no sector columns" in lim.lower() or "too few" in lim.lower()]
    soft_limits = [lim for lim in limitations if lim not in hard_blocks]

    if not limitations:
        status = "READY"
        action = "Can run Phase 7 granular at this level"
    elif hard_blocks and any("no sector" in b.lower() for b in hard_blocks):
        status = "BLOCKED"
        action = "Sector data required for Phase 7"
    elif hard_blocks:
        status = "BLOCKED"
        action = "; ".join(hard_blocks)
    elif soft_limits or structural_absent:
        status = "READY_WITH_LIMITATION"
        all_lims = soft_limits + ([f"KZ structural_absent"] if structural_absent else [])
        action = "Ready; " + "; ".join(all_lims) if all_lims else "Ready with minor limitations"
    else:
        status = "READY"
        action = "Can run Phase 7 granular at this level"

    # Flag_target_concept
    target_concept = "unknown"
    if "flag_target_concept" in df.columns:
        target_concept = str(df["flag_target_concept"].iloc[0])

    return {
        "country": country,
        "region_system": region_system,
        "n_regions": int(n_regions),
        "years": [int(y) for y in years],
        "n_years": int(n_years),
        "year_range": year_range,
        "n_windows": int(n_windows),
        "n_samples_per_window": int(n_samples),
        "n_directed_pairs": int(n_pairs),
        "sectors_present": present_sectors,
        "sectors_missing": missing_sectors,
        "structural_absent_sectors": structural_absent,
        "valid_row_frac": round(valid_frac, 4),
        "missing_rate": round(missing_rate, 4),
        "concept": target_concept,
        "readiness_status": status,
        "limitations": limitations,
        "recommended_next_action": action,
    }


def main() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nDEC-062 Part D: Granular Phase 7 Readiness Preflight")
    print("=" * 55)

    entries = []

    # France ZE2020 (already running Phase 7)
    if FRANCE_PANEL.exists():
        fr = assess_panel(FRANCE_PANEL, "FR", "ZE2020", has_sector=True)
        print(f"\nFR ZE2020: {fr['readiness_status']} — {fr['n_regions']} regions, {fr['n_years']} years")
        if fr.get("limitations"):
            for lim in fr["limitations"]:
                print(f"  WARNING: {lim}")
        entries.append(fr)

    # PT Municipal (continental)
    if PT_MUNI_PANEL.exists():
        pt = assess_panel(PT_MUNI_PANEL, "PT", "MUNICIPALITY_CONTINENTE", has_sector=True)
        print(f"\nPT MUNICIPALITY: {pt['readiness_status']} — {pt['n_regions']} regions, {pt['n_years']} years")
        if pt.get("limitations"):
            for lim in pt["limitations"]:
                print(f"  WARNING: {lim}")
        entries.append(pt)
    else:
        entries.append({
            "country": "PT",
            "region_system": "MUNICIPALITY_CONTINENTE",
            "readiness_status": "BLOCKED",
            "reason": "PT municipal panel not built yet",
            "recommended_next_action": "Run build_pt_municipal_sector_panel.py",
        })

    # NL at COROP (current level — fallback)
    if NL_PANEL.exists():
        nl_corop = assess_panel(NL_PANEL, "NL", "COROP", has_sector=True)
        print(f"\nNL COROP (fallback): {nl_corop['readiness_status']} — {nl_corop['n_regions']} regions")
        entries.append(nl_corop)

    # NL at gemeente — explicitly blocked
    entries.append({
        "country": "NL",
        "region_system": "GEMEENTE",
        "n_regions": 342,
        "readiness_status": "BLOCKED",
        "reason": "CBS Open Data has no table with gemeente × oprichtingen × SBI × jaar (DEC-061, confirmed DEC-062)",
        "recommended_next_action": "Apply for CBS Microdata (ABR) access via Research Data Center",
        "years": [],
        "n_years": 0,
        "concept": "local_unit_opening",
        "limitations": ["No open-data source found for gemeente × births × SBI"],
    })

    # Granularity comparison
    granularity_matrix = []
    for e in entries:
        if e.get("n_regions", 0) > 0:
            granularity_matrix.append({
                "country": e["country"],
                "system": e.get("region_system", ""),
                "n_regions": e.get("n_regions", 0),
                "n_years": e.get("n_years", 0),
                "n_windows": e.get("n_windows", 0),
                "readiness": e.get("readiness_status", "UNKNOWN"),
            })

    print("\nGranularity comparison:")
    for g in granularity_matrix:
        bar = "█" * (g["n_regions"] // 10)
        print(f"  {g['country']} {g['system']}: {bar} {g['n_regions']} units [{g['readiness']}]")

    # Overall result
    result = {
        "experiment": "DEC-062",
        "purpose": "Granular Phase 7 readiness assessment",
        "entries": entries,
        "granularity_matrix": granularity_matrix,
        "phase7_thresholds": {
            "min_samples": PHASE7_MIN_SAMPLES,
            "min_windows": PHASE7_MIN_WINDOWS,
            "window_size_years": PHASE7_WINDOW_SIZE,
        },
        "note_fr": "FR ZE2020 already running Phase 7 — used as reference",
        "note_pt": "PT municipal ≈ FR ZE2020 in granularity (278 vs 280 units)",
        "note_nl": "NL gemeente blocked via CBS Open Data; COROP (40) is current fallback",
        "note_concept": "FR=establishment_creation, PT=enterprise_birth, NL=local_unit_opening — cross-country pooling requires harmonisation DEC",
    }

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved: {OUT_JSON}")

    return result


if __name__ == "__main__":
    main()
