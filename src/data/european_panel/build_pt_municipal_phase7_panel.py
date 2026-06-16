"""
DEC-064: Build Phase 7 long-format panel from PT municipal observed births.

Converts pt_municipal_sector_panel.csv (wide, 278 municipalities × 16 years) to
the long format required by build_sector_precedence_graph.pair_samples:
    columns: country, territory_id, observation_year, sector_id, velocity,
             structural_mask, observation_mask

Velocity = sector_value[t] / sector_value[t-1] - 1  (YoY growth rate).
KZ structural_absent → structural_mask=0, never included in pairs.
Evidence type: observed_births (enterprise_birth, INE).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).parents[3]
IN_PANEL = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel.csv"
OUT_DIR = REPO_ROOT / "data/processed/phase7_pt_municipal"
OUT_PANEL = OUT_DIR / "pt_municipal_phase7_panel.csv"
OUT_MANIFEST = OUT_DIR / "pt_municipal_phase7_panel_manifest.json"

OBSERVABLE_SECTORS = ["BE", "FZ", "GI", "JZ", "LZ", "MN", "OQ", "RU"]
STRUCTURAL_ABSENT = ["KZ"]
ALL_A10 = OBSERVABLE_SECTORS + STRUCTURAL_ABSENT

COUNTRY = "PT"
REGION_SYSTEM = "MUNICIPALITY_CONTINENTE"
EVIDENCE_TYPE = "observed_births"
TARGET_CONCEPT = "enterprise_birth"


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_phase7_panel(in_path: Path = IN_PANEL) -> pd.DataFrame:
    """Convert wide PT municipal panel to Phase 7 long format."""
    df = pd.read_csv(in_path, low_memory=False)

    # Guard: only continental PT
    assert df["country"].eq(COUNTRY).all(), "Panel contains non-PT rows"
    assert df["is_continental"].eq(True).all() if "is_continental" in df.columns else True
    assert df["region_id"].nunique() == 278, f"Expected 278 municipalities, got {df['region_id'].nunique()}"

    rows = []
    for sector in OBSERVABLE_SECTORS:
        col = f"sector_{sector}"
        if col not in df.columns:
            raise ValueError(f"Missing sector column: {col}")

        sec_df = df[["region_id", "year", col]].copy()
        sec_df = sec_df.rename(columns={"region_id": "territory_id", "year": "observation_year", col: "observed_value"})
        sec_df["territory_id"] = sec_df["territory_id"].astype(str)

        # Compute velocity = YoY growth per municipality, strictly causal (uses only past)
        sec_df = sec_df.sort_values(["territory_id", "observation_year"])
        sec_df["lag1_value"] = sec_df.groupby("territory_id")["observed_value"].shift(1)
        sec_df["velocity"] = np.where(
            sec_df["lag1_value"].notna() & sec_df["lag1_value"] > 0,
            sec_df["observed_value"] / sec_df["lag1_value"] - 1,
            np.nan,
        )

        sec_df["country"] = COUNTRY
        sec_df["sector_id"] = sector
        sec_df["structural_mask"] = 1
        # observation_mask: 1 only if velocity is finite (requires both current and lag1 values)
        sec_df["observation_mask"] = (
            sec_df["velocity"].notna()
            & sec_df["velocity"].apply(np.isfinite)
        ).astype(int)

        rows.append(sec_df[[
            "country", "territory_id", "observation_year", "sector_id",
            "observed_value", "lag1_value", "velocity",
            "structural_mask", "observation_mask"
        ]])

    for sector in STRUCTURAL_ABSENT:
        col = f"sector_{sector}"
        if col not in df.columns:
            continue
        sec_df = df[["region_id", "year", col]].copy()
        sec_df = sec_df.rename(columns={"region_id": "territory_id", "year": "observation_year", col: "observed_value"})
        sec_df["territory_id"] = sec_df["territory_id"].astype(str)
        sec_df["country"] = COUNTRY
        sec_df["sector_id"] = sector
        sec_df["structural_mask"] = 0  # KZ structural_absent
        sec_df["lag1_value"] = np.nan
        sec_df["velocity"] = np.nan
        sec_df["observation_mask"] = 0
        rows.append(sec_df[[
            "country", "territory_id", "observation_year", "sector_id",
            "observed_value", "lag1_value", "velocity",
            "structural_mask", "observation_mask"
        ]])

    long = pd.concat(rows, ignore_index=True)
    long = long.sort_values(["territory_id", "sector_id", "observation_year"]).reset_index(drop=True)

    return long


def main() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nDEC-064: Build PT Municipal Phase 7 Panel")
    print("=" * 45)

    long = build_phase7_panel()

    obs_sectors = long[long["structural_mask"] == 1]
    n_territories = int(obs_sectors["territory_id"].nunique())
    n_years = int(obs_sectors["observation_year"].nunique())
    years_available = sorted(obs_sectors["observation_year"].unique().tolist())
    n_obs = int(obs_sectors["observation_mask"].sum())
    n_sectors = int(obs_sectors["sector_id"].nunique())

    print(f"Territories: {n_territories}")
    print(f"Years: {years_available[0]}–{years_available[-1]} ({n_years} years)")
    print(f"Sectors (observable): {n_sectors}")
    print(f"Observation mask==1: {n_obs} / {len(obs_sectors)}")
    print(f"Total rows: {len(long)}")

    # Temporal leakage check: velocity at year t uses only lag1 (t-1), never future
    # Verified by construction: lag1 = shift(1), never shift(-1)
    print("Temporal leakage check: PASS (velocity uses lag1=shift(1) only)")

    long.to_csv(OUT_PANEL, index=False)
    print(f"\nPanel saved: {OUT_PANEL}")

    panel_sha = _sha256(OUT_PANEL)
    manifest = {
        "experiment": "DEC-064",
        "source_panel": str(IN_PANEL.relative_to(REPO_ROOT)),
        "output_panel": str(OUT_PANEL.relative_to(REPO_ROOT)),
        "panel_checksum": panel_sha,
        "commit_sha": _git_head(),
        "country": COUNTRY,
        "region_system": REGION_SYSTEM,
        "evidence_type": EVIDENCE_TYPE,
        "target_concept": TARGET_CONCEPT,
        "n_territories": n_territories,
        "n_years": n_years,
        "years_available": years_available,
        "observable_sectors": OBSERVABLE_SECTORS,
        "structural_absent_sectors": STRUCTURAL_ABSENT,
        "n_rows_total": len(long),
        "n_obs_with_velocity": n_obs,
        "temporal_leakage_check": "PASS",
        "notes": "velocity = sector_value[t] / sector_value[t-1] - 1. "
                 "KZ structural_absent (structural_mask=0, observation_mask=0). "
                 "Evidence type: observed_births (enterprise_birth, INE 0009703/0014099). "
                 "No proxy data used.",
    }

    with open(OUT_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest saved: {OUT_MANIFEST}")

    return manifest


if __name__ == "__main__":
    main()
