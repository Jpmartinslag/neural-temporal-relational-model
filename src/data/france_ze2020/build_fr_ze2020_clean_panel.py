"""
HERALD — France ZE2020 clean treated panel.

Builds the canonical observed-data panel for France's Zone d'Emploi (ZE2020)
territorial grain: commune-level INSEE SIDE establishment/enterprise creation
counts, aggregated to ZE2020 x year, restricted to the continental-France
methodological scope (see reports/canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md
section 4 for the 306 -> 280 zone selection).

This pipeline is independent of the legacy data/processed/dynamic_stgnn_feature_panel_v1.csv
lineage. It does not compute growth/lag features and does not produce a
model-ready file — see HERALD_15 section 9 for what is deliberately not done
at this stage.

Inputs (read-only):
  data/interim/tables/side_communal_creations_official_2012_2024_v0.csv
    commune x year INSEE SIDE creation counts, already joined to ZE2020
    (columns: codgeo, year, side_enterprise_creations_official,
    side_establishment_creations_official, ze2020, libze2020, dep, reg).

Output:
  data/processed/france_ze2020/fr_ze2020_clean_panel.csv
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SIDE_COMMUNAL_PATH = ROOT / "data/interim/tables/side_communal_creations_official_2012_2024_v0.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_clean_panel.csv"

# Methodological scope filter (documented in HERALD_15 section 4): the
# canonical FR ZE2020 panel covers continental/metropolitan France excluding
# Corsica and the overseas departments (DOM). INSEE region codes (2-digit,
# zero-padded) excluded:
#   94 = Corse, 01 = Guadeloupe, 02 = Martinique, 03 = Guyane,
#   04 = La Reunion, 06 = Mayotte.
# This drops the raw commune-mapping's 306 ZE2020 zones to 280.
EXCLUDED_REGION_CODES = {"01", "02", "03", "04", "06", "94"}


def load_side_communal() -> pd.DataFrame:
    df = pd.read_csv(
        SIDE_COMMUNAL_PATH,
        dtype={"codgeo": str, "ze2020": str, "reg": str},
        low_memory=False,
    )
    df["codgeo"] = df["codgeo"].str.zfill(5)
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["reg"] = df["reg"].str.zfill(2)
    df["year"] = df["year"].astype(int)
    return df


def build_clean_panel() -> pd.DataFrame:
    side = load_side_communal()
    n_zones_raw = side["ze2020"].nunique()

    scoped = side[~side["reg"].isin(EXCLUDED_REGION_CODES)].copy()
    n_zones_scoped = scoped["ze2020"].nunique()

    panel = (
        scoped.groupby(["ze2020", "year"])
        .agg(
            establishment_creations=("side_establishment_creations_official", "sum"),
            enterprise_creations=("side_enterprise_creations_official", "sum"),
            communes_count=("codgeo", "nunique"),
        )
        .reset_index()
    )

    zone_labels = scoped[["ze2020", "libze2020"]].drop_duplicates("ze2020")
    panel = panel.merge(zone_labels, on="ze2020", how="left")
    panel = panel.rename(columns={"libze2020": "ze2020_label"})

    panel["mask_establishment_creations_available"] = (
        panel["establishment_creations"].notna().astype(int)
    )
    panel["mask_enterprise_creations_available"] = (
        panel["enterprise_creations"].notna().astype(int)
    )

    col_order = [
        "ze2020",
        "ze2020_label",
        "year",
        "establishment_creations",
        "enterprise_creations",
        "communes_count",
        "mask_establishment_creations_available",
        "mask_enterprise_creations_available",
    ]
    panel = panel[col_order].sort_values(["ze2020", "year"]).reset_index(drop=True)

    print(f"Raw ZE2020 zones (commune mapping scope): {n_zones_raw}")
    print(f"ZE2020 zones after continental-France methodological filter: {n_zones_scoped}")
    print(f"Panel shape: {panel.shape}")
    return panel


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_clean_panel()
    panel.to_csv(OUT_PATH, index=False)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
