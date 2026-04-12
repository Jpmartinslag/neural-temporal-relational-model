from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
ZONES_MASTER_PATH = ROOT / "data" / "processed" / "zones_master_annual_v0.csv"

RP_POP_2021_ZIP = ROOT / "data" / "raw" / "temporal_depth" / "rp" / "base-cc-evol-struct-pop-2021_csv.zip"
RP_EMP_2021_ZIP = ROOT / "data" / "raw" / "temporal_depth" / "rp" / "base-cc-emploi-pop-active-2021_csv.zip"
FILOSOFI_2020_ZIP = (
    ROOT / "data" / "raw" / "temporal_depth" / "filosofi" / "indic-struct-distrib-revenu-2020-COMMUNES_csv.zip"
)

RP_POP_2021_INTERIM = ROOT / "data" / "interim" / "tables" / "rp_population_commune_2021.csv"
RP_EMP_2021_INTERIM = ROOT / "data" / "interim" / "tables" / "rp_emploi_lr_commune_2021_v0.csv"
FILOSOFI_2020_INTERIM = ROOT / "data" / "interim" / "tables" / "filosofi_commune_2020.csv"

QUALITY_OUT = ROOT / "reports" / "temporal_depth_integration_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "TEMPORAL_DEPTH_INTEGRATION_V0.md"


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    raw = value.strip().replace("\xa0", "")
    if raw == "" or raw.lower() in {"s", "ns", "nd", "na"}:
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


def extract_rp_population_2021(commune_map: dict[str, dict[str, str]]) -> dict[str, float]:
    by_zone: dict[str, float] = defaultdict(float)
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(RP_POP_2021_ZIP) as zf:
        with zf.open("base-cc-evol-struct-pop-2021.CSV") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                codgeo = row["CODGEO"].zfill(5)
                info = commune_map.get(codgeo)
                if not info:
                    continue
                population = parse_number(row.get("P21_POP"))
                if population is None:
                    continue
                rows.append(
                    {
                        "codgeo": codgeo,
                        "ze2020": info["ze2020"],
                        "libze2020": info["libze2020"],
                        "population_2021_total": fmt(population),
                    }
                )
                by_zone[info["ze2020"]] += population

    RP_POP_2021_INTERIM.parent.mkdir(parents=True, exist_ok=True)
    with RP_POP_2021_INTERIM.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["codgeo", "ze2020", "libze2020", "population_2021_total"])
        writer.writeheader()
        writer.writerows(rows)
    return dict(by_zone)


def extract_rp_employment_2021(commune_map: dict[str, dict[str, str]]) -> dict[str, dict[str, float]]:
    by_zone: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(RP_EMP_2021_ZIP) as zf:
        with zf.open("base-cc-emploi-pop-active-2021.CSV") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                codgeo = row["CODGEO"].zfill(5)
                info = commune_map.get(codgeo)
                if not info:
                    continue
                active = parse_number(row.get("P21_ACT1564"))
                employed = parse_number(row.get("P21_ACTOCC1564"))
                unemployed = parse_number(row.get("P21_CHOM1564"))
                jobs_lt = parse_number(row.get("P21_EMPLT"))
                unemployment_rate = None
                if active is not None and unemployed is not None and active > 0:
                    unemployment_rate = unemployed / active

                rows.append(
                    {
                        "codgeo": codgeo,
                        "ze2020": info["ze2020"],
                        "active_15_64_2021_total": fmt(active),
                        "employed_15_64_2021_total": fmt(employed),
                        "unemployed_15_64_2021_total": fmt(unemployed),
                        "unemployment_rate_est_2021": fmt(unemployment_rate),
                        "jobs_lt_2021_total": fmt(jobs_lt),
                    }
                )

                if active is not None:
                    by_zone[info["ze2020"]]["active_15_64_2021_total"] += active
                if employed is not None:
                    by_zone[info["ze2020"]]["employed_15_64_2021_total"] += employed
                if unemployed is not None:
                    by_zone[info["ze2020"]]["unemployed_15_64_2021_total"] += unemployed
                if jobs_lt is not None:
                    by_zone[info["ze2020"]]["jobs_lt_2021_total"] += jobs_lt

    for ze, metrics in by_zone.items():
        active = metrics.get("active_15_64_2021_total")
        unemployed = metrics.get("unemployed_15_64_2021_total")
        if active is not None and unemployed is not None and active > 0:
            metrics["unemployment_rate_est_2021"] = unemployed / active
        else:
            metrics["unemployment_rate_est_2021"] = None

    with RP_EMP_2021_INTERIM.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "codgeo",
            "ze2020",
            "active_15_64_2021_total",
            "employed_15_64_2021_total",
            "unemployed_15_64_2021_total",
            "unemployment_rate_est_2021",
            "jobs_lt_2021_total",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return {ze: dict(values) for ze, values in by_zone.items()}


def extract_filosofi_2020(commune_map: dict[str, dict[str, str]]) -> dict[str, dict[str, float]]:
    by_zone_sum: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_zone_weight: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(FILOSOFI_2020_ZIP) as zf:
        with zf.open("FILO2020_DISP_COM.csv") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                codgeo = row["CODGEO"].zfill(5)
                info = commune_map.get(codgeo)
                if not info:
                    continue
                nbmen = parse_number(row.get("NBMEN20"))
                s_hh_tax = parse_number(row.get("PACT20"))
                s_dir_tax_di = parse_number(row.get("PIMPOT20"))
                # Keep the same proxy family names already used in the project.
                if s_hh_tax is not None:
                    rows.append(
                        {
                            "codgeo": codgeo,
                            "ze2020": info["ze2020"],
                            "filosofi_measure": "S_HH_TAX",
                            "weight_households_2020": fmt(nbmen),
                            "obs_value": fmt(s_hh_tax),
                        }
                    )
                if s_dir_tax_di is not None:
                    rows.append(
                        {
                            "codgeo": codgeo,
                            "ze2020": info["ze2020"],
                            "filosofi_measure": "S_DIR_TAX_DI",
                            "weight_households_2020": fmt(nbmen),
                            "obs_value": fmt(s_dir_tax_di),
                        }
                    )
                if nbmen is None or nbmen <= 0:
                    continue
                if s_hh_tax is not None:
                    by_zone_sum[info["ze2020"]]["filosofi_s_hh_tax_weighted_proxy_2020"] += s_hh_tax * nbmen
                    by_zone_weight[info["ze2020"]]["filosofi_s_hh_tax_weighted_proxy_2020"] += nbmen
                if s_dir_tax_di is not None:
                    by_zone_sum[info["ze2020"]]["filosofi_s_dir_tax_di_weighted_proxy_2020"] += s_dir_tax_di * nbmen
                    by_zone_weight[info["ze2020"]]["filosofi_s_dir_tax_di_weighted_proxy_2020"] += nbmen

    by_zone: dict[str, dict[str, float]] = defaultdict(dict)
    for ze, sums in by_zone_sum.items():
        for key, total in sums.items():
            weight = by_zone_weight[ze].get(key)
            by_zone[ze][key] = total / weight if weight else None

    with FILOSOFI_2020_INTERIM.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["codgeo", "ze2020", "filosofi_measure", "weight_households_2020", "obs_value"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return {ze: dict(values) for ze, values in by_zone.items()}


def integrate_into_zones_master(
    zone_population_2021: dict[str, float],
    zone_employment_2021: dict[str, dict[str, float]],
    zone_filosofi_2020: dict[str, dict[str, float]],
) -> dict[str, object]:
    with ZONES_MASTER_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys())
    new_fields = [
        "filosofi_s_hh_tax_weighted_proxy_2020",
        "filosofi_s_dir_tax_di_weighted_proxy_2020",
        "population_2021_total",
        "active_15_64_2021_total",
        "employed_15_64_2021_total",
        "unemployed_15_64_2021_total",
        "unemployment_rate_est_2021",
        "jobs_lt_2021_total",
        "jobs_lt_per_1000_pop_2021",
    ]
    for field in new_fields:
        if field not in fieldnames:
            insert_at = fieldnames.index("population_2022_total") if field.startswith("population_2021") else None
            if insert_at is not None:
                fieldnames.insert(insert_at, field)
            else:
                fieldnames.append(field)

    zones_with_population_2021 = 0
    zones_with_rp_2021 = 0
    zones_with_filosofi_2020 = 0

    for row in rows:
        ze = row["ze2020"].zfill(4)
        pop_2021 = zone_population_2021.get(ze)
        emp_2021 = zone_employment_2021.get(ze, {})
        filo_2020 = zone_filosofi_2020.get(ze, {})

        row["population_2021_total"] = fmt(pop_2021)
        row["active_15_64_2021_total"] = fmt(emp_2021.get("active_15_64_2021_total"))
        row["employed_15_64_2021_total"] = fmt(emp_2021.get("employed_15_64_2021_total"))
        row["unemployed_15_64_2021_total"] = fmt(emp_2021.get("unemployed_15_64_2021_total"))
        row["unemployment_rate_est_2021"] = fmt(emp_2021.get("unemployment_rate_est_2021"))
        row["jobs_lt_2021_total"] = fmt(emp_2021.get("jobs_lt_2021_total"))
        if pop_2021 is not None and pop_2021 > 0 and emp_2021.get("jobs_lt_2021_total") is not None:
            row["jobs_lt_per_1000_pop_2021"] = fmt(emp_2021["jobs_lt_2021_total"] / pop_2021 * 1000.0)
        else:
            row["jobs_lt_per_1000_pop_2021"] = ""
        row["filosofi_s_hh_tax_weighted_proxy_2020"] = fmt(
            filo_2020.get("filosofi_s_hh_tax_weighted_proxy_2020")
        )
        row["filosofi_s_dir_tax_di_weighted_proxy_2020"] = fmt(
            filo_2020.get("filosofi_s_dir_tax_di_weighted_proxy_2020")
        )

        if row["population_2021_total"] != "":
            zones_with_population_2021 += 1
        if row["active_15_64_2021_total"] != "":
            zones_with_rp_2021 += 1
        if row["filosofi_s_hh_tax_weighted_proxy_2020"] != "" or row["filosofi_s_dir_tax_di_weighted_proxy_2020"] != "":
            zones_with_filosofi_2020 += 1

        if ze == "0601":
            row["population_2021_total"] = ""
            row["active_15_64_2021_total"] = ""
            row["employed_15_64_2021_total"] = ""
            row["unemployed_15_64_2021_total"] = ""
            row["unemployment_rate_est_2021"] = ""
            row["jobs_lt_2021_total"] = ""
            row["jobs_lt_per_1000_pop_2021"] = ""
            row["filosofi_s_hh_tax_weighted_proxy_2020"] = ""
            row["filosofi_s_dir_tax_di_weighted_proxy_2020"] = ""

    with ZONES_MASTER_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    quality = {
        "zones_master_rows": len(rows),
        "zones_with_population_2021": zones_with_population_2021,
        "zones_with_rp_2021": zones_with_rp_2021,
        "zones_with_filosofi_2020": zones_with_filosofi_2020,
    }
    return quality


def write_report(quality: dict[str, object]) -> None:
    lines = [
        "# Temporal Depth Integration v0",
        "",
        "Data: 2026-04-10",
        "",
        "Objetivo:",
        "",
        "- integrar `RP 2021` e `Filosofi 2020` no pipeline vivo",
        "",
        "## Artefatos interim produzidos",
        "",
        f"- [rp_population_commune_2021.csv]({RP_POP_2021_INTERIM})",
        f"- [rp_emploi_lr_commune_2021_v0.csv]({RP_EMP_2021_INTERIM})",
        f"- [filosofi_commune_2020.csv]({FILOSOFI_2020_INTERIM})",
        "",
        "## Efeito sobre o dataset principal",
        "",
        "- `zones_master_annual_v0.csv` recebeu colunas `2021` para populacao e emprego",
        "- `zones_master_annual_v0.csv` recebeu colunas `2020` para proxies Filosofi",
        "",
        "## Cobertura observada",
        "",
        f"- zonas com populacao 2021: `{quality['zones_with_population_2021']}`",
        f"- zonas com emprego 2021: `{quality['zones_with_rp_2021']}`",
        f"- zonas com Filosofi 2020: `{quality['zones_with_filosofi_2020']}`",
        "",
        "## Nota metodologica",
        "",
        "- os proxies `Filosofi 2020` foram agregados por media ponderada pelo numero de menages (`NBMEN20`)",
        "- `Mayotte` permanece vazia nessas colunas, coerente com a cobertura oficial",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    commune_map, _zone_map = load_mapping()
    zone_population_2021 = extract_rp_population_2021(commune_map)
    zone_employment_2021 = extract_rp_employment_2021(commune_map)
    zone_filosofi_2020 = extract_filosofi_2020(commune_map)
    quality = integrate_into_zones_master(zone_population_2021, zone_employment_2021, zone_filosofi_2020)
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
