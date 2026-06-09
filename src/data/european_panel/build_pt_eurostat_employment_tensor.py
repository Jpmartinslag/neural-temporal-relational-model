#!/usr/bin/env python3
"""Build Portugal employment q-tensor from Eurostat/ARDECO.

Input is the Eurostat linear CSV with code columns preserved. Output keeps the
existing HERALD Portugal 25-zone geography, while using Eurostat regional
employment by NACE aggregate as a Q7-like employment tensor.

If ARDECO SNETZ 2024 parquet files are available under the standardized
download directory data/raw/european_panel/ardeco/snetz/PT_2024, they are
appended as a 2024 sector tensor.  The legacy local directory
data/raw/european_panel/ardeco/snetz_pt_2024 is still accepted for
reproducibility.  This is explicitly a JRC/DG REGIO ARDECO continuation of the
Eurostat regional accounts signal, not a pure Eurostat observation.

Important geography note:
The Portugal births panel uses the older 25 NUTS3 layout from the INE raw
series. Eurostat currently exposes some regions in the newer NUTS layout. This
builder maps newer Eurostat codes back to the old HERALD zones. The only real
aggregation is old PT_170, which combines current Grande Lisboa and Peninsula de
Setubal.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = BASE / "data/raw/european_panel/eurostat/nama_10r_3empers_pt_codes.csv"
DEFAULT_OUTPUT = BASE / "data/external/portugal/processed/portugal_qtensor_employment_eurostat_nuts3.csv"
ARDECO_2024_DIRS = [
    BASE / "data/raw/european_panel/ardeco/snetz/PT_2024",
    BASE / "data/raw/european_panel/ardeco/snetz_pt_2024",
]

# Existing HERALD Portugal zone_id -> Eurostat NUTS3 code(s).
ZONE_TO_EUROSTAT = {
    "PT_111": ["PT111"],  # Alto Minho
    "PT_112": ["PT112"],  # Cavado
    "PT_119": ["PT119"],  # Ave
    "PT_11A": ["PT11A"],  # Area Metropolitana do Porto
    "PT_11B": ["PT11B"],  # Alto Tamega e Barroso
    "PT_11C": ["PT11C"],  # Tamega e Sousa
    "PT_11D": ["PT11D"],  # Douro
    "PT_11E": ["PT11E"],  # Terras de Tras-os-Montes
    "PT_150": ["PT150"],  # Algarve
    "PT_16B": ["PT1D1"],  # Oeste
    "PT_16D": ["PT191"],  # Regiao de Aveiro
    "PT_16E": ["PT192"],  # Regiao de Coimbra
    "PT_16F": ["PT193"],  # Regiao de Leiria
    "PT_16G": ["PT194"],  # Viseu Dao Lafoes
    "PT_16H": ["PT195"],  # Beira Baixa
    "PT_16I": ["PT1D2"],  # Medio Tejo
    "PT_16J": ["PT196"],  # Beiras e Serra da Estrela
    "PT_170": ["PT1A0", "PT1B0"],  # old AML = Grande Lisboa + Peninsula de Setubal
    "PT_181": ["PT1C1"],  # Alentejo Litoral
    "PT_184": ["PT1C2"],  # Baixo Alentejo
    "PT_185": ["PT1D3"],  # Leziria do Tejo
    "PT_186": ["PT1C3"],  # Alto Alentejo
    "PT_187": ["PT1C4"],  # Alentejo Central
    "PT_200": ["PT200"],  # Acores
    "PT_300": ["PT300"],  # Madeira
}

NACE_TO_A10 = {
    "A": "A",
    "B-E": "BE",
    "F": "FZ",
    "G-I": "GI",
    "J": "JZ",
    "K": "KZ",
    "L": "LZ",
    "M_N": "MN",
    "O-Q": "OPQ",
    "R-U": "RSU",
}

ALL_A10 = ["A", "BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OPQ", "RSU"]

ARDECO_SECTOR_TO_A10 = NACE_TO_A10
ARDECO_FILES = {
    "A": "SNETZ_PT_2024_A.parquet",
    "B-E": "SNETZ_PT_2024_B-E.parquet",
    "F": "SNETZ_PT_2024_F.parquet",
    "G-I": "SNETZ_PT_2024_G-I.parquet",
    "J": "SNETZ_PT_2024_J.parquet",
    "K": "SNETZ_PT_2024_K.parquet",
    "L": "SNETZ_PT_2024_L.parquet",
    "M_N": "SNETZ_PT_2024_M_N.parquet",
    "O-Q": "SNETZ_PT_2024_O-Q.parquet",
    "R-U": "SNETZ_PT_2024_R-U.parquet",
}

# ARDECO SNETZ 2024 is exposed on NUTS 2021 codes.  These match the HERALD PT
# zone_id after removing the underscore; unlike the Eurostat linear file, no
# old PT1A0/PT1B0 back-aggregation is needed.
ARDECO_2024_TO_ZONE = {z.replace("_", ""): z for z in ZONE_TO_EUROSTAT}


def _find_ardeco_2024_dir() -> Path | None:
    for raw_dir in ARDECO_2024_DIRS:
        if raw_dir.exists():
            return raw_dir
    return None


def build_tensor(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    df = pd.read_csv(
        input_path,
        usecols=["geo", "TIME_PERIOD", "wstatus", "nace_r2", "OBS_VALUE"],
        low_memory=False,
    )
    df = df[(df["wstatus"] == "EMP") & (df["nace_r2"].isin(NACE_TO_A10))].copy()
    df["a10"] = df["nace_r2"].map(NACE_TO_A10)
    df["jobs"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce") * 1000.0

    reverse = {
        eurostat_geo: zone_id
        for zone_id, eurostat_geos in ZONE_TO_EUROSTAT.items()
        for eurostat_geo in eurostat_geos
    }
    df["zone_id"] = df["geo"].map(reverse)
    df = df[df["zone_id"].notna()].copy()

    out = (
        df.groupby(["zone_id", "TIME_PERIOD", "a10"], as_index=False)["jobs"]
        .sum()
        .rename(columns={"TIME_PERIOD": "target_year"})
    )
    out["target_year"] = out["target_year"].astype(int)

    years = range(int(out["target_year"].min()), int(out["target_year"].max()) + 1)
    idx = pd.MultiIndex.from_product(
        [sorted(ZONE_TO_EUROSTAT), years, ALL_A10],
        names=["zone_id", "target_year", "a10"],
    )
    out = (
        out.set_index(["zone_id", "target_year", "a10"])
        .reindex(idx)
        .reset_index()
        .sort_values(["zone_id", "target_year", "a10"])
        .reset_index(drop=True)
    )
    out["source"] = "Eurostat nama_10r_3empers"

    ardeco = build_ardeco_2024_tensor()
    if ardeco is not None:
        out = pd.concat([out, ardeco], ignore_index=True)
        out = (
            out.drop_duplicates(["zone_id", "target_year", "a10"], keep="last")
            .sort_values(["zone_id", "target_year", "a10"])
            .reset_index(drop=True)
        )
    return out


def build_ardeco_2024_tensor(raw_dir: Path | None = None) -> pd.DataFrame | None:
    raw_dir = raw_dir or _find_ardeco_2024_dir()
    if raw_dir is None:
        return None
    if not raw_dir.exists():
        return None
    missing = [name for name in ARDECO_FILES.values() if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"ARDECO 2024 files missing: {missing}")

    frames = []
    for sector, filename in ARDECO_FILES.items():
        df = pd.read_parquet(raw_dir / filename)
        df = df[df["TERRITORY_ID"].isin(ARDECO_2024_TO_ZONE)].copy()
        df["zone_id"] = df["TERRITORY_ID"].map(ARDECO_2024_TO_ZONE)
        df["target_year"] = df["YEAR"].astype(int)
        df["a10"] = sector
        df["a10"] = df["a10"].map(ARDECO_SECTOR_TO_A10)
        df["jobs"] = pd.to_numeric(df["VALUE"], errors="coerce") * 1000.0
        frames.append(df[["zone_id", "target_year", "a10", "jobs"]])

    out = pd.concat(frames, ignore_index=True)
    out = (
        out.groupby(["zone_id", "target_year", "a10"], as_index=False)["jobs"]
        .sum()
        .sort_values(["zone_id", "target_year", "a10"])
        .reset_index(drop=True)
    )
    out["source"] = "ARDECO SNETZ 2024"
    return out


def preflight(df: pd.DataFrame) -> None:
    failures: list[str] = []
    zones = sorted(df["zone_id"].unique())
    years = sorted(df["target_year"].unique())
    a10 = sorted(df["a10"].unique())

    if zones != sorted(ZONE_TO_EUROSTAT):
        failures.append(f"zones mismatch: got {len(zones)}, expected {len(ZONE_TO_EUROSTAT)}")
    expected_last = 2024 if _find_ardeco_2024_dir() is not None else 2023
    if years[0] != 2000 or years[-1] != expected_last:
        failures.append(f"year window mismatch: {years[0]}-{years[-1]}, expected 2000-{expected_last}")
    if a10 != sorted(ALL_A10):
        failures.append(f"A10 mismatch: {a10}")
    nan_jobs = int(df["jobs"].isna().sum())
    if nan_jobs:
        failures.append(f"jobs has {nan_jobs} NaN cells")
    non_positive_totals = (
        df.groupby(["zone_id", "target_year"])["jobs"].sum().le(0).sum()
    )
    if non_positive_totals:
        failures.append(f"{int(non_positive_totals)} zone-year totals are <= 0")

    print("=== Portugal Eurostat employment tensor ===")
    print(f"rows={len(df)} zones={len(zones)} years={years[0]}-{years[-1]} a10={len(a10)}")
    print(f"jobs_sum={df['jobs'].sum():.0f}")
    if "source" in df.columns:
        print("sources:")
        print(df.groupby("source")["target_year"].agg(["min", "max", "count"]).to_string())
    if failures:
        print("PREFLIGHT: FAIL")
        for msg in failures:
            print(f"  FAIL: {msg}")
        raise SystemExit(1)
    print("PREFLIGHT: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    out = build_tensor(args.input)
    preflight(out)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"saved: {args.output}")


if __name__ == "__main__":
    main()
