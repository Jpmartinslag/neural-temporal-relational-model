"""
HERALD -- France ZE2020 sector composition panel (MVP2 Category C, step 1).

Audit summary (full table in
reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md, "MVP2
Categoria C" section): data/processed/side_creations_a10_ze2020_v1.csv has
no generator script in the current tree (same gap pattern documented for
the legacy ZE adjacency matrices, HERALD_16 section 4.1) -- it is a
CANDIDATE_NEEDS_PROVENANCE source. It is used here ONLY because its values
independently reconcile EXACTLY with the canonical
fr_ze2020_clean_panel.csv: 280 zones, 13 years (2012-2024), 9 A10 sectors,
no duplicates, no missing values, no negative values, and `total` equals
the sum of the 9 sector columns for every row (max abs diff 0.0). This
builder RE-VERIFIES the reconciliation against the canonical panel at every
run (see build_sector_panel below) and refuses to write an output if it
ever stops matching -- the caveat is enforced, not just documented once.

This panel is OBSERVED/SECTORAL, not yet model-ready: no lag, no growth, no
history-based masking. It is a prototype layer feeding a future relational/
graph input (Category C of the relational plan), not a validated or final
data source.

Input (read-only):
  data/processed/side_creations_a10_ze2020_v1.csv      (candidate, no
    generator in tree -- content-verified only, see above)
  data/processed/france_ze2020/fr_ze2020_clean_panel.csv  (canonical anchor
    for ze2020_label and total_establishment_creations)

Output:
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
A10_SOURCE_PATH = ROOT / "data/processed/side_creations_a10_ze2020_v1.csv"
CLEAN_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_sector_panel.csv"

# Matches the canonical A10 sector label mapping already used elsewhere in
# the repo (src/data/european_panel/build_observatory_v05_narrative_exports.py
# SECTOR_LABELS) -- duplicated here (not imported) because that module
# belongs to the unrelated European-panel/Observatory track and this is a
# small, fixed, stable vocabulary.
SECTOR_LABELS = {
    "BE": "Industry and energy",
    "FZ": "Construction",
    "GI": "Trade, transport and hospitality",
    "JZ": "Information and communication",
    "KZ": "Financial and insurance activities",
    "LZ": "Real estate activities",
    "MN": "Professional and administrative services",
    "OQ": "Public administration, education and health",
    "RU": "Arts and other services",
}
SECTOR_CODES = list(SECTOR_LABELS.keys())

RECONCILIATION_TOLERANCE = 1e-6


def load_a10_source(path: Path = A10_SOURCE_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ZE2020": str})
    df["ZE2020"] = df["ZE2020"].str.zfill(4)
    df = df.rename(columns={"ZE2020": "ze2020", "target_year": "year", "total": "a10_total"})
    df["year"] = df["year"].astype(int)
    return df


def load_clean_panel(path: Path = CLEAN_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    return df[["ze2020", "ze2020_label", "year", "establishment_creations"]]


def build_sector_panel(
    a10: pd.DataFrame | None = None, clean: pd.DataFrame | None = None
) -> pd.DataFrame:
    if a10 is None:
        a10 = load_a10_source()
    if clean is None:
        clean = load_clean_panel()

    merged = a10.merge(clean, on=["ze2020", "year"], how="inner")
    if len(merged) != len(a10):
        raise ValueError(
            f"A10 source has {len(a10)} rows but only {len(merged)} matched the "
            "canonical clean panel on (ze2020, year) -- provenance check failed."
        )

    reconciliation_diff = (merged["a10_total"] - merged["establishment_creations"]).abs()
    if (reconciliation_diff > RECONCILIATION_TOLERANCE).any():
        raise ValueError(
            "A10 source 'total' column does not reconcile with the canonical "
            "establishment_creations column -- refusing to build the sector "
            f"panel (max abs diff = {reconciliation_diff.max()})."
        )

    long_rows = []
    for sector in SECTOR_CODES:
        sub = merged[["ze2020", "ze2020_label", "year", "establishment_creations", sector]].copy()
        sub = sub.rename(
            columns={
                "establishment_creations": "total_establishment_creations",
                sector: "sector_establishment_creations",
            }
        )
        sub["sector_code"] = sector
        sub["sector_label"] = SECTOR_LABELS[sector]
        long_rows.append(sub)

    panel = pd.concat(long_rows, ignore_index=True)
    panel["sector_establishment_creations"] = panel["sector_establishment_creations"].astype(float)
    panel["mask_sector_available"] = panel["sector_establishment_creations"].notna().astype(int)
    panel["sector_share"] = (
        panel["sector_establishment_creations"] / panel["total_establishment_creations"]
    )
    panel["sector_rank_in_ze_year"] = (
        panel.groupby(["ze2020", "year"])["sector_share"].rank(ascending=False, method="min").astype(int)
    )

    col_order = [
        "ze2020",
        "ze2020_label",
        "year",
        "sector_code",
        "sector_label",
        "sector_establishment_creations",
        "total_establishment_creations",
        "sector_share",
        "sector_rank_in_ze_year",
        "mask_sector_available",
    ]
    panel = panel[col_order].sort_values(["ze2020", "year", "sector_code"]).reset_index(drop=True)
    return panel


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_sector_panel()
    panel.to_csv(OUT_PATH, index=False)

    print(f"Zones: {panel['ze2020'].nunique()}, sectors: {panel['sector_code'].nunique()}")
    print(f"Rows: {len(panel)} (expected {280 * 13 * 9})")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
