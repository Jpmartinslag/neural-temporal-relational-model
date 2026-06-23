"""
HERALD — France ZE2020 model-ready causal panel (step 3 of the FR data pipeline).

Builds a simple, causal, explainable model-input panel on top of the clean
treated panel (data/processed/france_ze2020/fr_ze2020_clean_panel.csv). Adds
only lag-1/2/3 and lag-only growth features, plus their availability masks
and a deterministic integer node_id. Does not train anything, does not touch
the clean panel in place, and does not read the legacy
dynamic_stgnn_feature_panel_v1.csv lineage.

See reports/canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md section
10 ("Step 3 — Model-ready causal panel") for the full description.

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_clean_panel.csv

Output:
  data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CLEAN_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_model_ready_panel.csv"

TARGET_VARIABLE_NAME = "establishment_creations"


def load_clean_panel() -> pd.DataFrame:
    df = pd.read_csv(CLEAN_PANEL_PATH, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    return df


def build_model_ready_panel() -> pd.DataFrame:
    clean = load_clean_panel()

    panel = clean[["ze2020", "ze2020_label", "year"]].copy()
    panel["observed_value"] = clean[TARGET_VARIABLE_NAME].astype(float)
    panel["target_variable"] = TARGET_VARIABLE_NAME
    panel = panel.sort_values(["ze2020", "year"]).reset_index(drop=True)

    grouped = panel.groupby("ze2020")["observed_value"]
    panel["lag_1"] = grouped.shift(1)
    panel["lag_2"] = grouped.shift(2)
    panel["lag_3"] = grouped.shift(3)

    # Causal by construction: both formulas use only lag_1/2/3 (strictly
    # t-1 and earlier), never observed_value of the current row.
    panel["growth_1y_safe"] = (panel["lag_1"] - panel["lag_2"]) / panel["lag_2"]
    panel["growth_2y_safe"] = (panel["lag_1"] - panel["lag_3"]) / panel["lag_3"]

    panel["mask_observed_available"] = panel["observed_value"].notna().astype(int)
    panel["mask_lag_1_available"] = panel["lag_1"].notna().astype(int)
    panel["mask_lag_2_available"] = panel["lag_2"].notna().astype(int)
    panel["mask_lag_3_available"] = panel["lag_3"].notna().astype(int)

    zone_ids = pd.DataFrame({"ze2020": sorted(panel["ze2020"].unique())})
    zone_ids["node_id"] = range(len(zone_ids))
    panel = panel.merge(zone_ids, on="ze2020", how="left")

    col_order = [
        "ze2020",
        "ze2020_label",
        "year",
        "observed_value",
        "target_variable",
        "lag_1",
        "lag_2",
        "lag_3",
        "growth_1y_safe",
        "growth_2y_safe",
        "mask_observed_available",
        "mask_lag_1_available",
        "mask_lag_2_available",
        "mask_lag_3_available",
        "node_id",
    ]
    panel = panel[col_order].sort_values(["ze2020", "year"]).reset_index(drop=True)

    print(f"Zones: {panel['ze2020'].nunique()}")
    print(f"node_id range: {panel['node_id'].min()}-{panel['node_id'].max()}")
    print(f"Panel shape: {panel.shape}")
    return panel


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_model_ready_panel()
    panel.to_csv(OUT_PATH, index=False)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
