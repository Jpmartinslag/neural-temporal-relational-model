"""
Download and cache all EU common signals for FR/NL/BE/PT.

Usage
-----
    python3 -m src.data.european_panel.eu_signals.fetch_all
    python3 -m src.data.european_panel.eu_signals.fetch_all --refresh

Effects
-------
  * caches raw JSON-stat under data/raw/european_panel/eurostat/
  * writes a tidy long provenance CSV:
        data/raw/european_panel/eu_signals_annual.csv
    columns: country, ref_year, signal, value, source_dataset
The tidy CSV stores values by *reference year* (not lagged).  Lagging to the
panel's target year is done by assemble.attach_eu_signals.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve()
_BASE = _HERE.parents[4]
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from src.data.european_panel.eu_signals.assemble import EU_SIGNAL_SPECS
from src.data.european_panel.eu_signals.eurostat_client import RAW_DIR

COUNTRIES = ["FR", "NL", "BE", "PT"]

_SOURCE_DATASET = {
    "eu_gdp_growth_lag1": "nama_10_gdp",
    "eu_employment_rate_lag1": "lfsi_emp_a",
    "eu_unemployment_rate_lag1": "une_rt_a",
    "eu_esi_lag1": "ei_bssi_m_r2",
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch EU common signals (Eurostat).")
    ap.add_argument("--refresh", action="store_true", help="Bypass disk cache and re-download.")
    args = ap.parse_args()

    rows = []
    for field, (concept, getter) in EU_SIGNAL_SPECS.items():
        series = getter(COUNTRIES, refresh=args.refresh)
        for (country, ref_year), value in series.items():
            rows.append({
                "country": country,
                "ref_year": int(ref_year),
                "signal": field,
                "value": float(value),
                "source_dataset": _SOURCE_DATASET.get(field, ""),
            })
        print(f"  {field:<28} {concept}")
        for c in COUNTRIES:
            yrs = sorted(y for (cc, y) in series if cc == c)
            span = f"{yrs[0]}-{yrs[-1]} ({len(yrs)})" if yrs else "none"
            print(f"      {c}: {span}")

    out = pd.DataFrame(rows).sort_values(["signal", "country", "ref_year"])
    tidy_path = RAW_DIR.parent / "eu_signals_annual.csv"
    tidy_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(tidy_path, index=False)
    print(f"\n  Raw JSON cache : {RAW_DIR}")
    print(f"  Tidy CSV       : {tidy_path}  ({len(out)} rows)")


if __name__ == "__main__":
    main()
