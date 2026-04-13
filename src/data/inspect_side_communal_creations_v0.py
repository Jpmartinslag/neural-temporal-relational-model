from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
TARGET_PROXY_PATH = ROOT / "data" / "processed" / "target_proxy_annual_core_v0.csv"

SIDE_ENT_COM_ZIP = ROOT / "data" / "raw" / "business_demography" / "side" / "DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip"
SIDE_ETAB_COM_ZIP = ROOT / "data" / "raw" / "business_demography" / "side" / "DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip"

COMMUNE_OUT = ROOT / "data" / "interim" / "tables" / "side_communal_creations_official_2012_2024_v0.csv"
ZE_OUT = ROOT / "data" / "processed" / "side_communal_creations_ze2020_official_2012_2024_v0.csv"
COMPARE_OUT = ROOT / "data" / "processed" / "target_proxy_vs_side_official_ze2020_2012_2024_v0.csv"
INVENTORY_OUT = ROOT / "metadata" / "side_communal_creations_inventory_v0.csv"
QUALITY_OUT = ROOT / "reports" / "side_communal_creations_inspection_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "SIDE_COMMUNAL_CREATIONS_INSPECTION_V0.md"


def parse_number(value: str) -> float:
    raw = (value or "").strip().replace("\xa0", "").replace(",", ".")
    return float(raw) if raw else 0.0


def fmt(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return ""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_mapping() -> pd.DataFrame:
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str, "DEP": str, "REG": str})
    mapping["codgeo"] = mapping["CODGEO"].str.zfill(5)
    mapping["ze2020"] = mapping["ZE2020"].str.zfill(4)
    mapping["dep"] = mapping["DEP"].str.zfill(2)
    mapping["reg"] = mapping["REG"].str.zfill(2)
    return mapping[["codgeo", "LIBGEO", "ze2020", "LIBZE2020", "dep", "reg"]].rename(
        columns={"LIBGEO": "libgeo", "LIBZE2020": "libze2020"}
    )


def aggregate_zip(path: Path, kind: str) -> tuple[dict[tuple[str, int], float], dict[str, object]]:
    totals: dict[tuple[str, int], float] = defaultdict(float)
    rows_seen = 0
    rows_selected = 0
    geo_objects: set[str] = set()
    years: set[int] = set()

    with zipfile.ZipFile(path) as zf:
        data_name = next(name for name in zf.namelist() if name.endswith("_data.csv"))
        with zf.open(data_name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                rows_seen += 1
                geo_objects.add(row.get("GEO_OBJECT", ""))
                if kind == "enterprise":
                    selected = (
                        row.get("GEO_OBJECT") == "COM"
                        and row.get("SIDE_MEASURE") == "BURE"
                        and row.get("ACTIVITY") == "_T"
                        and row.get("LEGAL_FORM") == "_T"
                        and row.get("FREQ") == "A"
                    )
                    codgeo = row.get("GEO", "").zfill(5)
                    year = int(row.get("TIME_PERIOD"))
                    value = parse_number(row.get("OBS_VALUE", ""))
                elif kind == "establishment":
                    selected = (
                        row.get("GEO_OBJECT") == "COM"
                        and row.get("SIDE_MEASURE") == "UNIT_LOC_BURE"
                        and row.get("ACTIVITY") == "_T"
                        and row.get("LEGAL_FORM") == "_T"
                        and row.get("FREQ") == "A"
                    )
                    codgeo = row.get("GEO", "").zfill(5)
                    year = int(row.get("TIME_PERIOD"))
                    value = parse_number(row.get("OBS_VALUE", ""))
                else:
                    raise ValueError(f"Unsupported kind: {kind}")

                if not selected:
                    continue
                rows_selected += 1
                years.add(year)
                totals[(codgeo, year)] += value

    quality = {
        "source_file": str(path.relative_to(ROOT)),
        "kind": kind,
        "rows_seen": rows_seen,
        "rows_selected_commune_total": rows_selected,
        "commune_year_pairs": len(totals),
        "years": sorted(years),
        "geo_objects_seen": sorted(geo_objects),
    }
    return totals, quality


def build_commune_frame(mapping: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    enterprise, enterprise_quality = aggregate_zip(SIDE_ENT_COM_ZIP, "enterprise")
    establishment, establishment_quality = aggregate_zip(SIDE_ETAB_COM_ZIP, "establishment")

    keys = sorted(set(enterprise) | set(establishment))
    rows = []
    mapped = set(mapping["codgeo"])
    for codgeo, year in keys:
        rows.append(
            {
                "codgeo": codgeo,
                "year": year,
                "side_enterprise_creations_official": enterprise.get((codgeo, year), 0.0),
                "side_establishment_creations_official": establishment.get((codgeo, year), 0.0),
                "is_mapped_to_ze2020": int(codgeo in mapped),
            }
        )

    commune = pd.DataFrame(rows)
    commune = commune.merge(mapping, on="codgeo", how="left")
    return commune, [enterprise_quality, establishment_quality]


def aggregate_to_ze(commune: pd.DataFrame) -> pd.DataFrame:
    mapped = commune[commune["is_mapped_to_ze2020"] == 1].copy()
    ze = (
        mapped.groupby(["year", "ze2020", "libze2020"], as_index=False)
        .agg(
            side_enterprise_creations_official=("side_enterprise_creations_official", "sum"),
            side_establishment_creations_official=("side_establishment_creations_official", "sum"),
            communes_count=("codgeo", "nunique"),
        )
        .sort_values(["year", "ze2020"])
    )
    return ze


def compare_with_target(ze: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    target = pd.read_csv(TARGET_PROXY_PATH, dtype={"ze2020": str})
    target["ze2020"] = target["ze2020"].str.zfill(4)
    target = target.rename(columns={"target_year": "year"})
    compare = ze.merge(target, on=["year", "ze2020"], how="left")
    compare["proxy_minus_side_enterprise"] = (
        compare["target_proxy_establishment_creations_year"] - compare["side_enterprise_creations_official"]
    )
    compare["proxy_minus_side_establishment"] = (
        compare["target_proxy_establishment_creations_year"] - compare["side_establishment_creations_official"]
    )
    compare["proxy_to_side_enterprise_ratio"] = (
        compare["target_proxy_establishment_creations_year"] / compare["side_enterprise_creations_official"].replace(0, np.nan)
    )
    compare["proxy_to_side_establishment_ratio"] = (
        compare["target_proxy_establishment_creations_year"] / compare["side_establishment_creations_official"].replace(0, np.nan)
    )

    overlap = compare.dropna(subset=["target_proxy_establishment_creations_year"]).copy()
    by_year = (
        overlap.groupby("year", as_index=False)
        .agg(
            target_proxy_total=("target_proxy_establishment_creations_year", "sum"),
            side_enterprise_total=("side_enterprise_creations_official", "sum"),
            side_establishment_total=("side_establishment_creations_official", "sum"),
            ze_count=("ze2020", "nunique"),
        )
    )
    by_year["proxy_to_side_enterprise_ratio"] = by_year["target_proxy_total"] / by_year["side_enterprise_total"]
    by_year["proxy_to_side_establishment_ratio"] = by_year["target_proxy_total"] / by_year["side_establishment_total"]

    quality = {
        "overlap_years": sorted(int(y) for y in overlap["year"].unique()),
        "overlap_rows": int(len(overlap)),
        "annual_totals": by_year.to_dict(orient="records"),
        "correlation_proxy_side_enterprise": float(
            overlap["target_proxy_establishment_creations_year"].corr(overlap["side_enterprise_creations_official"])
        ),
        "correlation_proxy_side_establishment": float(
            overlap["target_proxy_establishment_creations_year"].corr(overlap["side_establishment_creations_official"])
        ),
        "median_proxy_to_side_enterprise_ratio": float(overlap["proxy_to_side_enterprise_ratio"].median()),
        "median_proxy_to_side_establishment_ratio": float(overlap["proxy_to_side_establishment_ratio"].median()),
    }
    return compare, quality


def write_outputs(commune: pd.DataFrame, ze: pd.DataFrame, compare: pd.DataFrame, source_quality: list[dict[str, object]], comparison_quality: dict[str, object]) -> None:
    COMMUNE_OUT.parent.mkdir(parents=True, exist_ok=True)
    ZE_OUT.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_OUT.parent.mkdir(parents=True, exist_ok=True)

    commune.to_csv(COMMUNE_OUT, index=False)
    ze.to_csv(ZE_OUT, index=False)
    compare.to_csv(COMPARE_OUT, index=False)

    inventory_rows = []
    for q in source_quality:
        inventory_rows.append(
            {
                "source_file": q["source_file"],
                "kind": q["kind"],
                "rows_seen": q["rows_seen"],
                "rows_selected_commune_total": q["rows_selected_commune_total"],
                "commune_year_pairs": q["commune_year_pairs"],
                "years": ";".join(str(y) for y in q["years"]),
                "status": "usable_for_official_commune_creation_audit",
            }
        )
    pd.DataFrame(inventory_rows).to_csv(INVENTORY_OUT, index=False)

    quality = {
        "source_quality": source_quality,
        "commune_output_rows": int(len(commune)),
        "commune_mapped_rows": int(commune["is_mapped_to_ze2020"].sum()),
        "ze_output_rows": int(len(ze)),
        "comparison_quality": comparison_quality,
        "decision": (
            "SIDE communal creations are suitable for auditing the current target proxy. "
            "They should not be used as ordinary predictors of the same creation target without leakage controls."
        ),
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)


def write_report(quality: dict[str, object]) -> None:
    comparison = quality["comparison_quality"]
    annual = comparison["annual_totals"]
    lines = [
        "# SIDE Communal Creations Inspection v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- verificar se os arquivos oficiais `SIDE` comunais de criacoes servem para auditar o target proxy atual",
        "- agregar criacoes oficiais de comuna para `ZE2020`",
        "- comparar os totais oficiais `SIDE` com o target proxy derivado atualmente",
        "",
        "## Artefatos",
        "",
        f"- comunal oficial: `{COMMUNE_OUT.relative_to(ROOT)}`",
        f"- agregado `ZE2020`: `{ZE_OUT.relative_to(ROOT)}`",
        f"- comparacao target proxy vs SIDE: `{COMPARE_OUT.relative_to(ROOT)}`",
        f"- inventario: `{INVENTORY_OUT.relative_to(ROOT)}`",
        f"- qualidade: `{QUALITY_OUT.relative_to(ROOT)}`",
        "",
        "## Fontes Inspecionadas",
        "",
    ]
    for q in quality["source_quality"]:
        lines.extend(
            [
                f"### {q['kind']}",
                "",
                f"- arquivo: `{q['source_file']}`",
                f"- linhas vistas: `{q['rows_seen']}`",
                f"- linhas selecionadas comuna-total: `{q['rows_selected_commune_total']}`",
                f"- pares comuna-ano: `{q['commune_year_pairs']}`",
                f"- anos: `{q['years']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Comparacao Com Target Proxy Atual",
            "",
            f"- anos sobrepostos: `{comparison['overlap_years']}`",
            f"- linhas sobrepostas: `{comparison['overlap_rows']}`",
            f"- correlacao proxy vs SIDE empresas: `{comparison['correlation_proxy_side_enterprise']:.4f}`",
            f"- correlacao proxy vs SIDE estabelecimentos: `{comparison['correlation_proxy_side_establishment']:.4f}`",
            f"- mediana ratio proxy/SIDE empresas: `{comparison['median_proxy_to_side_enterprise_ratio']:.4f}`",
            f"- mediana ratio proxy/SIDE estabelecimentos: `{comparison['median_proxy_to_side_establishment_ratio']:.4f}`",
            "",
            "## Totais Anuais",
            "",
            "| Ano | Target proxy | SIDE empresas | SIDE estabelecimentos | Proxy/Empresas | Proxy/Estab. |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in annual:
        lines.append(
            "| "
            f"{int(row['year'])} | "
            f"{int(row['target_proxy_total'])} | "
            f"{int(row['side_enterprise_total'])} | "
            f"{int(row['side_establishment_total'])} | "
            f"{row['proxy_to_side_enterprise_ratio']:.3f} | "
            f"{row['proxy_to_side_establishment_ratio']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Leitura",
            "",
            "- os arquivos `SIDE` comunais sao utilizaveis para auditoria oficial do target",
            "- eles cobrem `2012-2024` em nivel comunal e agregam para `ZE2020`",
            "- o target proxy atual e sistematicamente maior que os totais oficiais `SIDE`",
            "- a correlacao alta indicara se o proxy preserva ranking/dinamica espacial, mesmo com diferenca de nivel",
            "",
            "## Decisao",
            "",
            "- usar `SIDE` comunal oficial como auditoria prioritaria do target",
            "- nao usar `SIDE` comunal como feature comum para prever o mesmo target sem controles de vazamento",
            "- decidir depois se o target deve ser substituido pelo `SIDE` oficial ou se o proxy atual sera mantido apenas como serie auxiliar",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    mapping = load_mapping()
    commune, source_quality = build_commune_frame(mapping)
    ze = aggregate_to_ze(commune)
    compare, comparison_quality = compare_with_target(ze)
    write_outputs(commune, ze, compare, source_quality, comparison_quality)
    print(json.dumps({"source_quality": source_quality, "comparison_quality": comparison_quality}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
