from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
V1_PATH = ROOT / "data" / "processed" / "zones_master_annual_v1.csv"
EMP_ZIP_PATH = ROOT / "DS_RP_EMPLOI_LR_COMP_2022_CSV_FR.zip"
EMP_INTERIM_V2_PATH = ROOT / "data" / "interim" / "tables" / "rp_emploi_lr_comp_commune_2022_v2.csv"
V2_PATH = ROOT / "data" / "processed" / "zones_master_annual_v2.csv"
QUALITY_V1_PATH = ROOT / "reports" / "data_quality_report_v1.json"


def parse_number(value: str) -> float | None:
    if value is None:
        return None
    raw = value.strip().replace("\xa0", "")
    if raw == "":
        return None
    return float(raw.replace(",", "."))


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value - round(value)) < 1e-9:
        return f"{value:.1f}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_mapping() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    commune_map: dict[str, dict[str, str]] = {}
    zone_map: dict[str, dict[str, str]] = {}
    with MAPPING_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codgeo = row["CODGEO"].zfill(5)
            ze = row["ZE2020"].zfill(4)
            commune_map[codgeo] = {
                "ze2020": ze,
                "libze2020": row["LIBZE2020"],
                "reg": row["REG"].zfill(2) if row["REG"] else "",
            }
            zone_map.setdefault(
                ze,
                {
                    "ze2020": ze,
                    "libze2020": row["LIBZE2020"],
                    "reg": row["REG"].zfill(2) if row["REG"] else "",
                },
            )
    return commune_map, zone_map


def build_employment_v2(commune_map: dict[str, dict[str, str]]) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
    by_commune: dict[str, dict[str, float]] = defaultdict(dict)
    counters: dict[str, int] = defaultdict(int)

    with zipfile.ZipFile(EMP_ZIP_PATH) as zf:
        data_name = next(name for name in zf.namelist() if name.endswith("_data.csv"))
        with zf.open(data_name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                if row["GEO_OBJECT"] != "COM":
                    continue
                if row["TIME_PERIOD"] != "2022":
                    continue
                if row["AGE"] != "Y15T64":
                    continue
                if row["PCS"] != "_T":
                    continue
                if row["RP_MEASURE"] != "POP":
                    continue
                empsta = row["EMPSTA_ENQ"]
                if empsta not in {"1", "1T2"}:
                    continue
                codgeo = row["GEO"].zfill(5)
                if codgeo not in commune_map:
                    continue
                value = parse_number(row["OBS_VALUE"])
                if value is None:
                    continue
                counters["rp_lr_rows_selected"] += 1
                if empsta == "1T2":
                    by_commune[codgeo]["active_15_64_2022_total"] = value
                elif empsta == "1":
                    by_commune[codgeo]["employed_15_64_2022_total"] = value

    rows: list[dict[str, str]] = []
    by_zone: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    communes_with_both = 0
    mayotte_communes_with_rp = 0

    for codgeo, measures in sorted(by_commune.items()):
        info = commune_map[codgeo]
        active = measures.get("active_15_64_2022_total")
        employed = measures.get("employed_15_64_2022_total")
        unemployed = None
        rate = None
        if active is not None and employed is not None:
            communes_with_both += 1
            unemployed = max(active - employed, 0.0)
            if active > 0:
                rate = unemployed / active
        if info["ze2020"] == "0601":
            mayotte_communes_with_rp += 1
        rows.append(
            {
                "codgeo": codgeo,
                "ze2020": info["ze2020"],
                "active_15_64_2022_total": fmt(active),
                "employed_15_64_2022_total": fmt(employed),
                "unemployed_15_64_2022_est": fmt(unemployed),
                "unemployment_rate_est_2022": fmt(rate),
            }
        )
        if active is not None:
            by_zone[info["ze2020"]]["active_15_64_2022_total"] += active
        if employed is not None:
            by_zone[info["ze2020"]]["employed_15_64_2022_total"] += employed

    for ze, metrics in by_zone.items():
        active = metrics.get("active_15_64_2022_total")
        employed = metrics.get("employed_15_64_2022_total")
        unemployed = None
        rate = None
        if active is not None and employed is not None:
            unemployed = max(active - employed, 0.0)
            if active > 0:
                rate = unemployed / active
        metrics["unemployed_15_64_2022_est"] = unemployed
        metrics["unemployment_rate_est_2022"] = rate

    EMP_INTERIM_V2_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EMP_INTERIM_V2_PATH.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "codgeo",
            "ze2020",
            "active_15_64_2022_total",
            "employed_15_64_2022_total",
            "unemployed_15_64_2022_est",
            "unemployment_rate_est_2022",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counters["communes_with_active_or_employed"] = len(by_commune)
    counters["communes_with_both_active_and_employed"] = communes_with_both
    counters["mayotte_communes_with_rp_coverage"] = mayotte_communes_with_rp
    counters["zones_with_lr_coverage"] = len(by_zone)
    return by_zone, counters


def build_zones_master_v2(zone_employment: dict[str, dict[str, float]]) -> dict[str, object]:
    with V1_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    output_rows = []
    missing_population_zones = []
    missing_jobs_lt_zones = []
    missing_active_zones = []
    mayotte_row = None

    for row in rows:
        ze = row["ze2020"].zfill(4)
        metrics = zone_employment.get(ze, {})

        if not metrics:
            row["active_15_64_2022_total"] = ""
            row["jobs_lt_2022_total"] = "" if ze == "0601" else row["jobs_lt_2022_total"]
            row["jobs_lt_per_1000_pop_2022"] = "" if ze == "0601" else row["jobs_lt_per_1000_pop_2022"]
        else:
            row["active_15_64_2022_total"] = fmt(metrics.get("active_15_64_2022_total"))

        employed = metrics.get("employed_15_64_2022_total")
        unemployed = metrics.get("unemployed_15_64_2022_est")
        rate = metrics.get("unemployment_rate_est_2022")

        row["employed_15_64_2022_total"] = fmt(employed)
        row["unemployed_15_64_2022_total"] = fmt(unemployed)
        row["unemployment_rate_est_2022"] = fmt(rate)

        if ze == "0601":
            row["population_2022_total"] = ""
            row["jobs_lt_2022_total"] = ""
            row["jobs_lt_per_1000_pop_2022"] = ""
            mayotte_row = dict(row)
            mayotte_row.pop("unemployment_rate_proxy_2022", None)

        if row.get("population_2022_total", "") == "":
            missing_population_zones.append(ze)
        if row.get("jobs_lt_2022_total", "") == "":
            missing_jobs_lt_zones.append(ze)
        if row.get("active_15_64_2022_total", "") == "":
            missing_active_zones.append(ze)

        output_rows.append(row)

    fieldnames = [
        "ze2020",
        "libze2020",
        "reg",
        "population_2022_total",
        "active_15_64_2022_total",
        "employed_15_64_2022_total",
        "unemployed_15_64_2022_total",
        "unemployment_rate_est_2022",
        "jobs_lt_2022_total",
        "jobs_lt_per_1000_pop_2022",
        "side_stocks_et_2023_total",
        "side_stocks_ul_2023_total",
        "side_stocks_et_per_1000_pop_2023",
        "bpe_facilities_2024_total",
        "bpe_facilities_per_1000_pop_2024",
        "flores_presential_unit_loc_2024_total",
        "flores_productive_unit_loc_2024_total",
        "filosofi_s_hh_tax_weighted_proxy_2021",
        "filosofi_s_dir_tax_di_weighted_proxy_2021",
    ]

    V2_PATH.parent.mkdir(parents=True, exist_ok=True)
    with V2_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            row = dict(row)
            row.pop("unemployment_rate_proxy_2022", None)
            writer.writerow(row)

    quality = {
        "zones_master_rows": len(output_rows),
        "zones_with_population": len(output_rows) - len(missing_population_zones),
        "zones_with_jobs_lt": len(output_rows) - len(missing_jobs_lt_zones),
        "zones_with_active": len(output_rows) - len(missing_active_zones),
        "missing_population_zones": missing_population_zones,
        "missing_jobs_lt_zones": missing_jobs_lt_zones,
        "missing_active_zones": missing_active_zones,
        "mayotte_row_v2": mayotte_row,
    }

    with QUALITY_V1_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    return quality


def main() -> None:
    commune_map, _ = load_mapping()
    zone_employment, counters = build_employment_v2(commune_map)
    quality = build_zones_master_v2(zone_employment)
    print(
        json.dumps(
            {
                "employment_counters": counters,
                "quality": quality,
                "outputs": {
                    "employment_interim_v2": str(EMP_INTERIM_V2_PATH),
                    "zones_master_annual_v2": str(V2_PATH),
                    "data_quality_report_v1": str(QUALITY_V1_PATH),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
