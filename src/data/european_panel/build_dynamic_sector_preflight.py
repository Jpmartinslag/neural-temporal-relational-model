"""Build the clean European sector panel used by the G1 graph preflight.

This builder deliberately reads unlagged national sector tables. The canonical
European panel stores sector_* as t-1 predictive features, which is correct for
forecasting but would create an off-by-one label in an analytical graph.

The graph vocabulary contains nine business sectors and excludes agriculture.
Existing predictive datasets are not modified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[3]
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

FR_SOURCE = BASE / "data/processed/side_creations_a10_ze2020_through_2025_v1.csv"
NL_SOURCE = BASE / "data/external/netherlands/raw/cbs/83631NED_corop.csv"
PT_SOURCE = BASE / "data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv"
BE_EMP_SOURCE = BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv"

CANONICAL = {
    "FR": BASE / "data/processed/european_panel/france_panel.csv",
    "NL": BASE / "data/processed/european_panel/nl_panel.csv",
    "PT": BASE / "data/processed/european_panel/pt_panel.csv",
    "BE": BASE / "data/processed/european_panel/be_panel.csv",
}

NL_SBI_TO_SECTOR = {
    "300002": "BE",
    "350000": "FZ",
    "300006": "GI",
    "391600": "JZ",
    "396300": "KZ",
    "402000": "LZ",
    "300010": "MN",
    "300012": "OQ",
    "300014": "RU",
}

EMPLOYMENT_A10_MAP = {"OPQ": "OQ", "RSU": "RU"}


def _metadata(country: str) -> pd.DataFrame:
    panel = pd.read_csv(CANONICAL[country])
    cols = [
        "region_id",
        "region_name",
        "region_level",
        "flag_target_concept",
        "meta_region_system",
        "meta_source_label",
    ]
    metadata = panel[cols].drop_duplicates("region_id").copy()
    metadata["region_id"] = metadata["region_id"].astype(str)
    return metadata


def _wide_to_long(
    frame: pd.DataFrame,
    country: str,
    region_col: str,
    year_col: str,
    source_label: str,
) -> pd.DataFrame:
    out = frame.melt(
        id_vars=[region_col, year_col],
        value_vars=SECTORS,
        var_name="sector_a10",
        value_name="sector_births",
    ).rename(columns={region_col: "region_id", year_col: "observation_year"})
    out["country"] = country
    out["region_id"] = out["region_id"].astype(str)
    out["source_label"] = source_label
    return out


def load_france() -> pd.DataFrame:
    source = pd.read_csv(FR_SOURCE)
    out = _wide_to_long(source, "FR", "ZE2020", "target_year", "SIDE/SIRENE")
    return out.merge(_metadata("FR"), on="region_id", how="left", validate="many_to_one")


def load_netherlands() -> pd.DataFrame:
    raw = pd.read_csv(NL_SOURCE)
    raw["region_id"] = raw["RegioS"].astype(str).str.strip()
    raw["observation_year"] = raw["Perioden"].astype(str).str[:4].astype(int)
    raw["sbi_key"] = raw["BedrijfstakkenBranchesSBI2008"].astype(str).str.strip()
    raw["sector_a10"] = raw["sbi_key"].map(NL_SBI_TO_SECTOR)
    raw["sector_births"] = pd.to_numeric(raw["OprichtingenVanVestigingen_1"], errors="coerce")
    valid_regions = {f"CR{i:02d}" for i in range(1, 41)}
    out = raw[
        raw["region_id"].isin(valid_regions) & raw["sector_a10"].notna()
    ][["region_id", "observation_year", "sector_a10", "sector_births"]]
    out = (
        out.groupby(["region_id", "observation_year", "sector_a10"], as_index=False)
        ["sector_births"]
        .sum(min_count=1)
    )
    out["country"] = "NL"
    out["source_label"] = "CBS 83631NED"
    return out.merge(_metadata("NL"), on="region_id", how="left", validate="many_to_one")


def load_portugal() -> pd.DataFrame:
    raw = pd.read_csv(PT_SOURCE)
    raw = raw[raw["a10"].ne("A")].copy()
    raw["sector_a10"] = raw["a10"].replace({"OPQ": "OQ", "RSU": "RU"})
    out = raw.rename(
        columns={
            "zone_id": "region_id",
            "target_year": "observation_year",
            "births": "sector_births",
        }
    )[["region_id", "observation_year", "sector_a10", "sector_births"]]
    out = (
        out.groupby(["region_id", "observation_year", "sector_a10"], as_index=False)
        ["sector_births"]
        .sum(min_count=1)
    )
    out["country"] = "PT"
    out["source_label"] = "INE CAE"
    return out.merge(_metadata("PT"), on="region_id", how="left", validate="many_to_one")


def load_belgium_employment() -> pd.DataFrame:
    raw = pd.read_csv(BE_EMP_SOURCE)
    raw = raw[raw["a10"].ne("A")].copy()
    raw["sector_a10"] = raw["a10"].replace(EMPLOYMENT_A10_MAP)
    out = raw.rename(
        columns={
            "zone_id": "region_id",
            "target_year": "observation_year",
            "jobs": "sector_employment",
        }
    )[["region_id", "observation_year", "sector_a10", "sector_employment"]]
    out["country"] = "BE"
    out["source_label"] = "ONSS Q4"
    return out.merge(_metadata("BE"), on="region_id", how="left", validate="many_to_one")


def enrich_birth_panel(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    panel["sector_births"] = pd.to_numeric(panel["sector_births"], errors="coerce")
    panel["mask_sector_births"] = panel["sector_births"].notna().astype(int)
    sector_mass = panel.groupby(
        ["country", "observation_year", "sector_a10"]
    )["sector_births"].transform(lambda values: values.sum(min_count=1))
    panel["mask_sector_supported"] = sector_mass.fillna(0).gt(0).astype(int)
    keys = ["country", "region_id", "observation_year"]
    panel["mask_complete_sector_vector"] = (
        (panel["mask_sector_births"] * panel["mask_sector_supported"])
        .groupby([panel[column] for column in keys])
        .transform("sum")
        .eq(len(SECTORS))
        .astype(int)
    )
    panel["business_sector_total"] = panel.groupby(keys)["sector_births"].transform(
        lambda x: x.sum(min_count=1)
    )
    panel["sector_share"] = panel["sector_births"] / panel["business_sector_total"].replace(0, np.nan)
    panel = panel.sort_values(keys + ["sector_a10"]).reset_index(drop=True)
    panel["sector_growth_1y"] = panel.groupby(
        ["country", "region_id", "sector_a10"]
    )["sector_births"].pct_change(fill_method=None)
    panel["available_for_forecast_year"] = panel["observation_year"] + 1
    return panel


def validate_birth_panel(panel: pd.DataFrame) -> tuple[list[str], dict]:
    errors: list[str] = []
    key = ["country", "region_id", "observation_year", "sector_a10"]
    duplicates = int(panel.duplicated(key).sum())
    if duplicates:
        errors.append(f"{duplicates} duplicate country-region-year-sector keys")
    invalid_sectors = sorted(set(panel["sector_a10"]) - set(SECTORS))
    if invalid_sectors:
        errors.append(f"invalid sectors: {invalid_sectors}")
    if (panel["sector_births"].dropna() < 0).any():
        errors.append("negative observed sector births")
    if panel["region_name"].isna().any():
        errors.append("missing canonical region metadata")

    observed_coverage = panel.groupby(
        ["country", "region_id", "observation_year"]
    )["mask_sector_births"].sum()
    incomplete = int((observed_coverage != len(SECTORS)).sum())

    share_sums = panel.groupby(["country", "region_id", "observation_year"])["sector_share"].sum()
    bad_shares = int(((share_sums - 1.0).abs() > 1e-9).sum())
    if bad_shares:
        errors.append(f"{bad_shares} region-years have sector shares not summing to one")

    summary: dict[str, object] = {
        "rows": int(len(panel)),
        "duplicates": duplicates,
        "invalid_sectors": invalid_sectors,
        "incomplete_region_years": incomplete,
        "countries": {},
    }
    for country, sub in panel.groupby("country"):
        unsupported = (
            sub.loc[sub["mask_sector_supported"].eq(0), "sector_a10"]
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        summary["countries"][country] = {
            "regions": int(sub["region_id"].nunique()),
            "years": [int(sub["observation_year"].min()), int(sub["observation_year"].max())],
            "year_count": int(sub["observation_year"].nunique()),
            "sectors": int(sub["sector_a10"].nunique()),
            "observed_pct": round(100 * float(sub["mask_sector_births"].mean()), 3),
            "complete_region_year_pct": round(
                100
                * float(
                    sub.drop_duplicates(["region_id", "observation_year"])[
                        "mask_complete_sector_vector"
                    ].mean()
                ),
                3,
            ),
            "complete_years_all_regions": [
                int(year)
                for year, year_sub in sub.groupby("observation_year")
                if year_sub["mask_complete_sector_vector"].eq(1).all()
            ],
            "unsupported_sectors": unsupported,
            "target_concept": sorted(sub["flag_target_concept"].dropna().unique().tolist()),
            "region_system": sorted(sub["meta_region_system"].dropna().unique().tolist()),
        }
    return errors, summary


def validate_employment_panel(panel: pd.DataFrame) -> tuple[list[str], dict]:
    errors: list[str] = []
    key = ["country", "region_id", "observation_year", "sector_a10"]
    if panel.duplicated(key).any():
        errors.append("duplicate Belgium employment keys")
    if (panel["sector_employment"].dropna() < 0).any():
        errors.append("negative Belgium employment")
    if set(panel["sector_a10"]) != set(SECTORS):
        errors.append("Belgium employment sector vocabulary mismatch")
    summary = {
        "rows": int(len(panel)),
        "regions": int(panel["region_id"].nunique()),
        "years": [int(panel["observation_year"].min()), int(panel["observation_year"].max())],
        "sectors": int(panel["sector_a10"].nunique()),
        "observed_pct": round(100 * float(panel["sector_employment"].notna().mean()), 3),
    }
    return errors, summary


def render_report(summary: dict, output_paths: dict[str, str]) -> str:
    lines = [
        "# HERALD G1 Sector Data Preflight",
        "",
        "**Status:** " + ("PASS" if summary["status"] == "PASS" else "FAIL"),
        "",
        "The panel is analytical and unlagged. `available_for_forecast_year` makes",
        "the temporal contract explicit. Agriculture is excluded rather than folded",
        "into `OQ`.",
        "",
        "## Birth-sector nucleus",
        "",
        "| Country | Regions | Years | Complete graph years | Unsupported | Observed | Concept | Region system |",
        "|---|---:|---|---|---|---:|---|---|",
    ]
    for country, item in summary["birth_panel"]["countries"].items():
        complete = item["complete_years_all_regions"]
        complete_label = f"{min(complete)}-{max(complete)}" if complete else "none"
        lines.append(
            f"| {country} | {item['regions']} | {item['years'][0]}-{item['years'][1]} "
            f"| {complete_label} "
            f"| {', '.join(item['unsupported_sectors']) or 'none'} "
            f"| {item['observed_pct']:.1f}% "
            f"| {', '.join(item['target_concept'])} | {', '.join(item['region_system'])} |"
        )
    be = summary["belgium_employment"]
    lines += [
        "",
        "## Belgium employment complement",
        "",
        f"BE contains {be['regions']} territories, {be['sectors']} sectors and years "
        f"{be['years'][0]}-{be['years'][1]} ({be['observed_pct']:.1f}% observed).",
        "",
        "## Important limitations",
        "",
        "- FR, NL and PT use different target concepts and territorial systems.",
        "- Raw birth counts must not be pooled across countries.",
        "- France has aggregate quarterly URSSAF employment in the current repository,",
        "  not a verified territory-by-A10 employment table.",
        "- Belgium is an employment complement, not a birth-sector member of the core.",
        "- A country-year sector with zero total mass is marked unsupported rather",
        "  than interpreted as a verified economic absence.",
        "- PT has no complete nine-sector graph year because `KZ` has zero mass in",
        "  every territory and year; PT is retained in the file but excluded from",
        "  L1/L3 validation until the source definition is resolved.",
        "- `bd_hgnace_r` is a complementary NUTS3 bridge and requires a separate",
        "  crosswalk for ZE2020 and COROP comparisons.",
        "",
        "## Outputs",
        "",
    ]
    lines.extend(f"- `{name}`: `{path}`" for name, path in output_paths.items())
    if summary["errors"]:
        lines += ["", "## Errors", ""] + [f"- {err}" for err in summary["errors"]]
    return "\n".join(lines) + "\n"


def build(out_dir: Path, report_path: Path) -> dict:
    births = enrich_birth_panel(
        pd.concat([load_france(), load_netherlands(), load_portugal()], ignore_index=True)
    )
    employment = load_belgium_employment().sort_values(
        ["region_id", "observation_year", "sector_a10"]
    )
    birth_errors, birth_summary = validate_birth_panel(births)
    emp_errors, emp_summary = validate_employment_panel(employment)
    errors = birth_errors + emp_errors

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    birth_path = out_dir / "sector_panel_fr_nl_pt.csv"
    emp_path = out_dir / "employment_panel_be.csv"
    json_path = out_dir / "g1_sector_preflight.json"
    births.to_csv(birth_path, index=False)
    employment.to_csv(emp_path, index=False)

    summary = {
        "status": "PASS" if not errors else "FAIL",
        "contract": "reports/HERALD_G0_FORMAL_CONTRACT.md",
        "sector_vocabulary": SECTORS,
        "agriculture_policy": "excluded_not_folded",
        "birth_panel": birth_summary,
        "belgium_employment": emp_summary,
        "errors": errors,
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    outputs = {
        "birth sector panel": str(birth_path.relative_to(BASE)),
        "Belgium employment complement": str(emp_path.relative_to(BASE)),
        "machine-readable audit": str(json_path.relative_to(BASE)),
    }
    report_path.write_text(render_report(summary, outputs), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=BASE / "data/processed/economic_graph",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=BASE / "reports/HERALD_G1_SECTOR_DATA_PREFLIGHT.md",
    )
    args = parser.parse_args()
    summary = build(args.out_dir, args.report)
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
