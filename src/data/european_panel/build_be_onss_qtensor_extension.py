"""Extend Belgium ONSS employment q-tensor through 2024.

The legacy Phase 4 tensor covers 2008-2020. This script parses the local ONSS
Q4 work-location spreadsheets downloaded under data/raw/european_panel/onss/
and appends 2021-2024 with the same 42-arrondissement harmonisation used by
src/data/ingest_belgium_panel.py.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

BASE = Path(__file__).resolve().parents[3]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.data.ingest_belgium_panel import COL_A10, ONSS_NAME_MAP

RAW_DIR = BASE / "data/raw/european_panel/onss"
OUT = BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv"
YEARS = range(2021, 2025)
EXPECTED_ZONES = 42
EXPECTED_A10 = ["A", "BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OPQ", "RSU"]


def parse_year(year: int) -> pd.DataFrame:
    path = RAW_DIR / f"localunit-val-fr-{year}-4.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Missing ONSS Q4 spreadsheet: {path}")

    xl = pd.read_excel(path, sheet_name="tableau 8-17", header=None)
    if xl.shape[1] < 41:
        raise ValueError(f"{path.name}: expected >=41 columns, got {xl.shape[1]}")

    arr_mask = (
        xl.iloc[:, 0].isna()
        & xl.iloc[:, 1].notna()
        & xl.iloc[:, 1].apply(lambda x: isinstance(x, str) and len(str(x)) > 2)
    )
    arr_rows = xl[arr_mask].copy()

    records = []
    unknown: set[str] = set()
    for _, row in arr_rows.iterrows():
        arr_name = str(row.iloc[1]).strip()
        zone_id = ONSS_NAME_MAP.get(arr_name, "UNKNOWN")
        if zone_id is None:
            continue
        if zone_id == "UNKNOWN":
            unknown.add(arr_name)
            continue

        for col_idx, a10 in COL_A10.items():
            jobs = pd.to_numeric(pd.Series([row.iloc[col_idx]]), errors="coerce").iloc[0]
            records.append(
                {
                    "zone_id": zone_id,
                    "target_year": year,
                    "a10": a10,
                    "jobs": float(jobs) if pd.notna(jobs) else 0.0,
                }
            )

    if unknown:
        raise ValueError(f"{path.name}: unknown arrondissement names: {sorted(unknown)}")

    df = pd.DataFrame(records)
    df = df.groupby(["zone_id", "target_year", "a10"], as_index=False)["jobs"].sum()
    return df.sort_values(["zone_id", "target_year", "a10"]).reset_index(drop=True)


def build() -> pd.DataFrame:
    legacy = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
    if not legacy.empty:
        legacy = legacy[legacy["target_year"] <= 2020].copy()
    ext = pd.concat([parse_year(y) for y in YEARS], ignore_index=True)
    out = pd.concat([legacy, ext], ignore_index=True)
    return (
        out.drop_duplicates(["zone_id", "target_year", "a10"], keep="last")
        .sort_values(["zone_id", "target_year", "a10"])
        .reset_index(drop=True)
    )


def validate(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    years = sorted(df["target_year"].unique())
    if years != list(range(2008, 2025)):
        errors.append(f"expected years 2008-2024, got {years[0]}-{years[-1]}")
    for year in range(2021, 2025):
        sub = df[df["target_year"].eq(year)]
        if sub["zone_id"].nunique() != EXPECTED_ZONES:
            errors.append(f"{year}: expected {EXPECTED_ZONES} zones, got {sub['zone_id'].nunique()}")
        if sorted(sub["a10"].unique()) != sorted(EXPECTED_A10):
            errors.append(f"{year}: A10 mismatch {sorted(sub['a10'].unique())}")
        if sub["jobs"].isna().any():
            errors.append(f"{year}: jobs contains NaN")
        if (sub.groupby("zone_id")["jobs"].sum() <= 0).any():
            errors.append(f"{year}: some zones have non-positive total jobs")
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
    print("=== Belgium ONSS q-tensor ===")
    print(f"saved={OUT}")
    print(
        f"rows={len(out)} zones={out['zone_id'].nunique()} "
        f"years={out['target_year'].min()}-{out['target_year'].max()}"
    )
    for year in range(2021, 2025):
        total = out[out["target_year"].eq(year)]["jobs"].sum()
        print(f"jobs_{year}={total:.0f}")


if __name__ == "__main__":
    main()
