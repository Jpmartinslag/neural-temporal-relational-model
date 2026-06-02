"""Build Netherlands sector births from CBS 83631NED.

Input:
  data/raw/european_panel/cbs/83631NED_TypedDataSet_2007_2025.csv

Output:
  data/external/netherlands/processed/netherlands_sector_births_cbs_83631NED_corop_a10.csv

The output uses the 9-sector HERALD A10 convention used by the French panel:
BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU. CBS section A and O-Q are both folded
into OQ to match the existing HERALD sector contract.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[3]
RAW = BASE / "data/raw/european_panel/cbs/83631NED_TypedDataSet_2007_2025.csv"
OUT = BASE / "data/external/netherlands/processed/netherlands_sector_births_cbs_83631NED_corop_a10.csv"

VALUE_COL = "OprichtingenVanVestigingen_1"
COROP_ZONES = [f"CR{i:02d}" for i in range(1, 41)]
SBI_TO_A10 = {
    "301000": "OQ",  # A agriculture
    "300002": "BE",  # B-E industry + energy
    "350000": "FZ",  # F construction
    "300006": "GI",  # G-I trade/transport/hospitality
    "391600": "JZ",  # J information/communication
    "396300": "KZ",  # K finance
    "402000": "LZ",  # L real estate
    "300010": "MN",  # M-N business services
    "300012": "OQ",  # O-Q public/education/health
    "300014": "RU",  # R-U culture/other
}
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


def build() -> pd.DataFrame:
    if not RAW.exists():
        raise FileNotFoundError(f"Missing CBS raw file: {RAW}")

    df = pd.read_csv(RAW)
    df["zone_id"] = df["RegioS"].astype(str).str.strip()
    df["target_year"] = df["Perioden"].astype(str).str[:4].astype(int)
    df["sbi_key"] = df["BedrijfstakkenBranchesSBI2008"].astype(str).str.strip()
    df["births"] = pd.to_numeric(df[VALUE_COL], errors="coerce")
    df["a10"] = df["sbi_key"].map(SBI_TO_A10)
    df = df[df["zone_id"].isin(COROP_ZONES) & df["a10"].notna()].copy()
    df = df[df["target_year"].between(2007, 2025)].copy()

    grouped = df.groupby(["zone_id", "target_year", "a10"], as_index=False)["births"].sum(min_count=1)
    wide = (
        grouped.pivot_table(
            index=["zone_id", "target_year"],
            columns="a10",
            values="births",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )
    wide.columns.name = None
    for sector in SECTORS:
        if sector not in wide.columns:
            wide[sector] = 0.0
    wide["total"] = wide[SECTORS].sum(axis=1)
    return wide[["zone_id", "target_year"] + SECTORS + ["total"]].sort_values(
        ["zone_id", "target_year"]
    ).reset_index(drop=True)


def validate(out: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if out["zone_id"].nunique() != 40:
        errors.append(f"expected 40 COROP zones, got {out['zone_id'].nunique()}")
    years = sorted(out["target_year"].unique())
    if years != list(range(2007, 2026)):
        errors.append(f"expected years 2007-2025, got {years[0]}-{years[-1]}")
    if out[SECTORS].isna().any().any():
        errors.append("sector births contain NaN")

    raw = pd.read_csv(RAW)
    raw["zone_id"] = raw["RegioS"].astype(str).str.strip()
    raw["target_year"] = raw["Perioden"].astype(str).str[:4].astype(int)
    raw["sbi_key"] = raw["BedrijfstakkenBranchesSBI2008"].astype(str).str.strip()
    raw["target"] = pd.to_numeric(raw[VALUE_COL], errors="coerce")
    total = raw[
        raw["zone_id"].isin(COROP_ZONES)
        & raw["sbi_key"].eq("T001081")
        & raw["target_year"].between(2015, 2025)
    ][["zone_id", "target_year", "target"]]
    cmp = out.merge(total, on=["zone_id", "target_year"], how="inner")
    cmp["abs_diff"] = (cmp["total"] - cmp["target"]).abs()
    max_diff = float(cmp["abs_diff"].max())
    if max_diff > 25:
        errors.append(f"sector total differs from target by max {max_diff}, expected <=25")
    return errors


def main() -> None:
    out = build()
    errors = validate(out)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        raise SystemExit(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print("=== Netherlands CBS sector births ===")
    print(f"saved={OUT}")
    print(
        f"rows={len(out)} zones={out['zone_id'].nunique()} "
        f"years={out['target_year'].min()}-{out['target_year'].max()}"
    )
    print(f"total_2025={out[out['target_year'].eq(2025)]['total'].sum():.0f}")


if __name__ == "__main__":
    main()
