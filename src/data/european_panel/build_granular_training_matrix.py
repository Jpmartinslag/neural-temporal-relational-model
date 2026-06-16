"""
DEC-063: Build granular FR/PT/NL training eligibility matrix.

Reads existing panels and produces a per-country eligibility matrix with:
- data dimensions
- evidence type
- allowed and forbidden claims
"""

from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[3]
OUT_CSV = REPO_ROOT / "data/processed/european_panel/granular_fr_pt_nl_training_matrix.csv"

FR_PANEL = REPO_ROOT / "data/processed/european_panel/france_panel.csv"
PT_PANEL = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel.csv"
NL_PANEL = REPO_ROOT / "data/processed/european_panel/nl_panel.csv"
NL_PROXY = REPO_ROOT / "data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv"

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


def _sector_info(df: pd.DataFrame) -> dict:
    sector_cols = [f"sector_{s}" for s in A10_SECTORS]
    present = [s for s in A10_SECTORS if f"sector_{s}" in df.columns]
    absent_structural = [
        s for s in present
        if df[f"sector_{s}"].isna().all()
    ]
    observable = [s for s in present if s not in absent_structural]
    return {
        "sectors_available": ",".join(present),
        "observable_sectors": ",".join(observable),
        "structural_missing_sectors": ",".join(absent_structural),
    }


def _row(country, region_system, n_regions, years, obs_births, proxy_births,
         stock, sectors_info, target, allowed_claims, forbidden_claims, notes=""):
    return {
        "country": country,
        "region_system": region_system,
        "n_regions": n_regions,
        "years": years,
        "observed_births_available": obs_births,
        "proxy_births_available": proxy_births,
        "stock_available": stock,
        "sectors_available": sectors_info["sectors_available"],
        "observable_sectors": sectors_info["observable_sectors"],
        "structural_missing_sectors": sectors_info["structural_missing_sectors"],
        "recommended_training_target": target,
        "allowed_claims": allowed_claims,
        "forbidden_claims": forbidden_claims,
        "notes": notes,
    }


def build_matrix() -> pd.DataFrame:
    rows = []

    # France ZE2020
    if FR_PANEL.exists():
        fr = pd.read_csv(FR_PANEL)
        n_fr = int(fr["region_id"].nunique()) if "region_id" in fr.columns else 280
        yr_fr = f"{int(fr['year'].min())}-{int(fr['year'].max())}" if "year" in fr.columns else "2009-2021"
        si_fr = _sector_info(fr)
        rows.append(_row(
            country="FR",
            region_system="ZE2020",
            n_regions=n_fr,
            years=yr_fr,
            obs_births=True,
            proxy_births=False,
            stock=False,
            sectors_info=si_fr,
            target="observed_births (establishment_creation, SIDRE)",
            allowed_claims=(
                "temporal precedence between sectors at ZE2020 level; "
                "predictive association between sector activity; "
                "COVID-sensitive vs robust classification"
            ),
            forbidden_claims=(
                "causal claims; universal generalization; "
                "claims without COVID-sensitivity check"
            ),
            notes="FR reference layer. Phase 7 already run at ZE2020. 1 robust label (RU→MN COVID-sensitive).",
        ))

    # Portugal municipal
    if PT_PANEL.exists():
        pt = pd.read_csv(PT_PANEL)
        n_pt = int(pt["region_id"].nunique()) if "region_id" in pt.columns else 278
        yr_pt = f"{int(pt['year'].min())}-{int(pt['year'].max())}" if "year" in pt.columns else "2008-2023"
        si_pt = _sector_info(pt)
        rows.append(_row(
            country="PT",
            region_system="MUNICIPALITY_CONTINENTE",
            n_regions=n_pt,
            years=yr_pt,
            obs_births=True,
            proxy_births=False,
            stock=False,
            sectors_info=si_pt,
            target="observed_births (enterprise_birth, INE 0009703/0014099)",
            allowed_claims=(
                "temporal precedence between sectors at municipal level; "
                "predictive association; "
                "replication of FR patterns or contrast"
            ),
            forbidden_claims=(
                "causal claims; KZ-dependent claims (structurally absent); "
                "claims mixing PT with proxy data"
            ),
            notes="KZ structural_absent (Finance excluded from INE enterprise births). "
                  "Comparable granularity to FR (278 vs 280 units).",
        ))

    # NL COROP (observed)
    if NL_PANEL.exists():
        nl = pd.read_csv(NL_PANEL)
        nl_corop = nl[nl["region_level"] == "COROP"] if "region_level" in nl.columns else nl
        n_nl_corop = int(nl_corop["region_id"].nunique()) if "region_id" in nl_corop.columns else 40
        yr_nl = f"{int(nl_corop['year'].min())}-{int(nl_corop['year'].max())}" if "year" in nl_corop.columns else "2015-2022"
        si_nl = _sector_info(nl_corop)
        rows.append(_row(
            country="NL",
            region_system="COROP",
            n_regions=n_nl_corop,
            years=yr_nl,
            obs_births=True,
            proxy_births=False,
            stock=False,
            sectors_info=si_nl,
            target="observed_births (local_unit_opening, CBS 83631NED)",
            allowed_claims=(
                "temporal precedence between sectors at COROP level; "
                "predictive association; "
                "lower-granularity reference for NL gemeente proxy validation"
            ),
            forbidden_claims=(
                "causal claims; gemeente-level claims from COROP data alone"
            ),
            notes="40 CORPs. Observed births. Lower granularity than FR/PT but fully observed.",
        ))

    # NL gemeente proxy
    if NL_PROXY.exists():
        proxy = pd.read_csv(NL_PROXY)
        n_nl_gm = int(proxy[proxy["evidence_status"] == "proxy_computed"]["gm_code"].nunique())
        yr_proxy = f"{int(proxy['year'].min())}-{int(proxy['year'].max())}"
        n_proxy_computed = int((proxy["evidence_status"] == "proxy_computed").sum())
        n_total = len(proxy)
        pct = round(100 * n_proxy_computed / n_total, 1)
        rows.append(_row(
            country="NL",
            region_system="GEMEENTE_PROXY",
            n_regions=n_nl_gm,
            years=yr_proxy,
            obs_births=False,
            proxy_births=True,
            stock=True,
            sectors_info={
                "sectors_available": ",".join(A10_SECTORS),
                "observable_sectors": ",".join(A10_SECTORS),
                "structural_missing_sectors": "",
            },
            target=(
                "estimated_births_gemeente (PROXY — corop_births_allocated_by_gemeente_stock_share). "
                "Source: 83631NED births + 81575NED stock"
            ),
            allowed_claims=(
                "descriptive associations at gemeente level; "
                "proxy-labelled predictive associations; "
                "spatial distribution patterns consistent with COROP observations"
            ),
            forbidden_claims=(
                "causal claims; "
                "treating proxy as observed births without evidence_type flag; "
                "omitting proxy-excluded sensitivity analysis in evaluation; "
                "claims that do not separately report observed-only vs proxy-included results"
            ),
            notes=(
                f"{n_nl_gm} GMs with COROP mapping ({pct}% of proxy rows computed). "
                "128 historical GMs without current COROP crosswalk (pre-merger municipalities). "
                "Reaggregation to COROP is exact (0.0 absolute error). "
                "evidence_type=proxy_disaggregated_by_stock_share must be present in all outputs."
            ),
        ))

    return pd.DataFrame(rows)


def main():
    REPO_ROOT.joinpath("data/processed/european_panel").mkdir(parents=True, exist_ok=True)
    matrix = build_matrix()
    matrix.to_csv(OUT_CSV, index=False)
    print(f"Training matrix saved: {OUT_CSV}")
    print(f"  {len(matrix)} entries")
    for _, row in matrix.iterrows():
        print(f"  {row['country']} {row['region_system']}: {row['n_regions']} regions, "
              f"obs_births={row['observed_births_available']}, proxy={row['proxy_births_available']}")
    return matrix


if __name__ == "__main__":
    main()
