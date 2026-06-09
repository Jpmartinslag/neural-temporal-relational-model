#!/usr/bin/env python3
"""Build the harmonized `enterprise_birth` subpanel (PT + IT only).

This is the partial Path-H subpanel: both countries share the SAME target concept
(`enterprise_birth`, total population, Eurostat-OECD demographic births), so a LOCO
on it controls the concept and isolates the country effect. FR/NL/BE are NOT
included (different concepts). No model is trained here.

Outputs (does not overwrite existing panels):
  data/processed/european_panel/it_panel.csv
  data/processed/european_panel/enterprise_birth_pt_it_panel.csv
  data/processed/european_panel/enterprise_birth_pt_it_summary.json
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.data.european_panel.adapters.it_adapter import ITAdapter
from src.data.european_panel.validation import validate_panel

BASE = Path(__file__).resolve().parents[3]
OUT = BASE / "data/processed/european_panel"
PT_PANEL = OUT / "pt_panel.csv"
WINDOW = (2008, 2020)  # bd_size_r3 ends at 2020; PT covers 2008-2024 -> common = 2008-2020


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> None:
    adapter = ITAdapter()
    it = adapter.build(year_min=WINDOW[0], year_max=WINDOW[1])
    it_report = validate_panel(it, country="IT")
    if it_report["errors"]:
        raise ValueError(f"IT panel failed validation: {it_report['errors']}")
    it_path = OUT / "it_panel.csv"
    it.to_csv(it_path, index=False)

    pt = pd.read_csv(PT_PANEL)
    pt = pt[(pt["year"] >= WINDOW[0]) & (pt["year"] <= WINDOW[1])].copy()
    if not (pt["flag_target_concept"] == "enterprise_birth").all():
        raise ValueError("PT panel rows are not all enterprise_birth")

    common = sorted(set(pt["year"]) & set(it["year"]))
    sub = pd.concat([pt, it[pt.columns]], ignore_index=True)
    sub = sub[sub["year"].isin(common)].reset_index(drop=True)
    sub_path = OUT / "enterprise_birth_pt_it_panel.csv"
    sub.to_csv(sub_path, index=False)

    def country_block(frame: pd.DataFrame, country: str) -> dict:
        c = frame[frame["country"] == country]
        return {
            "regions": int(c["region_id"].nunique()),
            "years": [int(c["year"].min()), int(c["year"].max())],
            "rows": int(len(c)),
            "target_concept": sorted(c["flag_target_concept"].unique()),
            "geometry": sorted(c["meta_region_system"].unique()),
            "source": sorted(c["meta_source_label"].unique()),
            "target_coverage_pct": round(100 * c["mask_target"].mean(), 2),
            "sector_coverage_pct": round(100 * c["mask_sector_a10"].mean(), 2),
            "employment_coverage_pct": round(100 * c["mask_employment"].mean(), 2),
            "forecast_safe_rows": int(c["flag_forecast_safe"].sum()),
            "target_scale_median": float(c["target_births"].median()),
            "target_scale_max": float(c["target_births"].max()),
        }

    summary = {
        "subpanel": "enterprise_birth (PT + IT) — partial Path H",
        "common_window": [common[0], common[-1]],
        "common_years": len(common),
        "countries": {c: country_block(sub, c) for c in ("PT", "IT")},
        "it_dropped_nuts_transition_regions": adapter.dropped_regions,
        "files": {
            "it_panel": {"path": str(it_path.relative_to(BASE)), "md5": md5(it_path),
                         "rows": int(len(it))},
            "subpanel": {"path": str(sub_path.relative_to(BASE)), "md5": md5(sub_path),
                         "rows": int(len(sub))},
        },
        "pooled_wmape_used": False,
        "note": "FR/NL/BE excluded (different concepts). Not a European generalization claim.",
    }
    (OUT / "enterprise_birth_pt_it_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
