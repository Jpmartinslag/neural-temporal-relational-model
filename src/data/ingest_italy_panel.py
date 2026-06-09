#!/usr/bin/env python3
"""Ingest Italy enterprise-birth panel (NUTS3) from Eurostat business demography.

Reproducible source: Eurostat SDMX/JSON dissemination API, dataset `bd_size_r3`
("Business demography by size class and NUTS 3 region", 2008-2020).

Indicators (indic_sb), size class TOTAL (whole enterprise population, incl.
enterprises without employees):
  - V11920  Births of enterprises in t      -> target_births
  - V11910  Population of active enterprises -> enterprise stock (stock_lag1 source)

Concept: enterprise births, demographic (economic, not administrative), built on
the ASIA statistical register, Eurostat-OECD aligned, 2-year reactivation rule,
births "from scratch" (exclude mergers/splits). Same concept as Portugal INE.

This script ONLY downloads and reshapes official data. Suppressed/absent cells are
kept as NaN (never zero). No interpolation. A NUTS-version note is recorded: IT
NUTS3 codes change at 2019 (NUTS 2021, e.g. Sardinia); codes are treated as-is and
documented, not silently merged.

Outputs (raw + processed + manifest with checksums):
  data/external/italy/raw/bd_size_r3_IT_<indic>.json
  data/external/italy/processed/italy_births_panel_nuts3.csv
  data/external/italy/processed/italy_ingest_manifest.json
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / "data/external/italy/raw"
PROC = BASE / "data/external/italy/processed"
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/bd_size_r3"
INDICATORS = {"V11920": "births", "V11910": "stock"}
LICENSE = "Eurostat — © European Union, CC BY 4.0 (reuse with attribution)"


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def fetch(indic: str) -> dict:
    url = f"{API}?format=JSON&lang=EN&indic_sb={indic}&sizeclas=TOTAL"
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = response.read()
    out = RAW / f"bd_size_r3_IT_{indic}.json"
    out.write_bytes(payload)
    return {"indic": indic, "url": url, "file": str(out.relative_to(BASE)),
            "bytes": len(payload), "md5": md5(out)}


def to_long(indic: str) -> pd.DataFrame:
    data = json.loads((RAW / f"bd_size_r3_IT_{indic}.json").read_text())
    dim = data["dimension"]
    geo_index = dim["geo"]["category"]["index"]
    geo_label = dim["geo"]["category"]["label"]
    time_index = dim["time"]["category"]["index"]
    n_time = len(time_index)
    values = data["value"]
    years = sorted(time_index, key=lambda t: time_index[t])
    # IT NUTS3 = 'IT' + 3 chars, length 5, excluding extra-regio ITZ*.
    geos = sorted(
        g for g in geo_index
        if g.startswith("IT") and len(g) == 5 and not g.startswith("ITZ")
    )
    rows = []
    for g in geos:
        for t in years:
            idx = geo_index[g] * n_time + time_index[t]
            v = values.get(str(idx))
            rows.append(
                {
                    "region_id": g,
                    "region_name": geo_label.get(g, g),
                    "year": int(t),
                    INDICATORS[indic]: np.nan if v is None else float(v),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    manifest_sources = [fetch(indic) for indic in INDICATORS]

    births = to_long("V11920")
    stock = to_long("V11910")
    panel = births.merge(
        stock[["region_id", "year", "stock"]],
        on=["region_id", "year"],
        how="outer",
    ).sort_values(["region_id", "year"]).reset_index(drop=True)

    # Causal lags and growth — only from the past, never future. Suppressed cells
    # stay NaN and propagate to flag_forecast_safe; no imputation.
    panel["lag1_births"] = panel.groupby("region_id")["births"].shift(1)
    panel["lag2_births"] = panel.groupby("region_id")["births"].shift(2)
    panel["lag3_births"] = panel.groupby("region_id")["births"].shift(3)
    panel["stock_lag1"] = panel.groupby("region_id")["stock"].shift(1)
    panel["growth_1y"] = (panel["lag1_births"] - panel["lag2_births"]) / panel["lag2_births"]
    panel["growth_2y"] = (panel["lag1_births"] - panel["lag3_births"]) / panel["lag3_births"]
    panel["mask_target"] = panel["births"].notna().astype(float)
    panel["flag_forecast_safe"] = (
        panel["births"].notna() & panel["lag1_births"].notna()
    ).astype(float)

    out_csv = PROC / "italy_births_panel_nuts3.csv"
    panel.to_csv(out_csv, index=False)

    nuts_versions = {
        "2008-2018": "NUTS 2013/2016 IT NUTS3 codes",
        "2019-2020": "NUTS 2021 IT NUTS3 codes (Sardinia reorganization; province count 110->107)",
    }
    manifest = {
        "dataset": "Eurostat bd_size_r3 (Business demography by size class and NUTS 3 region, 2008-2020)",
        "indicators": INDICATORS,
        "size_class": "TOTAL (whole enterprise population, incl. without employees)",
        "concept": "enterprise_birth (demographic, Eurostat-OECD; ASIA register)",
        "downloaded": date.today().isoformat(),
        "license": LICENSE,
        "sources": manifest_sources,
        "processed_file": str(out_csv.relative_to(BASE)),
        "processed_md5": md5(out_csv),
        "rows": int(len(panel)),
        "regions": int(panel["region_id"].nunique()),
        "years": [int(panel["year"].min()), int(panel["year"].max())],
        "target_coverage_pct": round(100 * panel["births"].notna().mean(), 2),
        "suppressed_or_absent_cells": int(panel["births"].isna().sum()),
        "nuts_version_note": nuts_versions,
        "no_imputation": True,
    }
    (PROC / "italy_ingest_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    print(f"\nSaved {out_csv} ({len(panel)} rows, {panel['region_id'].nunique()} regions)")


if __name__ == "__main__":
    main()
