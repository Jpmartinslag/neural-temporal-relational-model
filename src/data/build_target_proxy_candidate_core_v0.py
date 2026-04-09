from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds


ROOT = Path(__file__).resolve().parents[2]
SIRENE_STOCK_PARQUET = ROOT / "data" / "raw" / "business_registry" / "sirene" / "StockEtablissement_utf8.parquet"
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
CORE_NODES_PATH = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"

OUT_CSV = ROOT / "data" / "processed" / "target_proxy_candidate_core_v0.csv"
OUT_QUALITY = ROOT / "reports" / "target_proxy_candidate_core_quality_v0.json"
OUT_REPORT = ROOT / "reports" / "TARGET_PROXY_CANDIDATE_CORE_V0.md"

MIN_YEAR = 2000
MAX_YEAR = 2026


def load_core_mapping() -> dict[str, str]:
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str})
    core_nodes = pd.read_csv(CORE_NODES_PATH, dtype={"ze2020": str})
    mapping = mapping[mapping["ZE2020"].isin(core_nodes["ze2020"])][["CODGEO", "ZE2020"]].drop_duplicates()
    return dict(zip(mapping["CODGEO"], mapping["ZE2020"]))


def build_target_proxy(core_map: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    dataset = ds.dataset(SIRENE_STOCK_PARQUET, format="parquet")
    scanner = dataset.scanner(
        columns=["dateCreationEtablissement", "codeCommuneEtablissement"],
        batch_size=250_000,
    )

    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    stats = {
        "rows_scanned": 0,
        "rows_with_valid_date_and_commune": 0,
        "rows_in_core_mapping": 0,
        "distinct_core_communes_observed": set(),
    }

    for batch in scanner.to_batches():
        frame = batch.to_pandas(types_mapper=None)
        stats["rows_scanned"] += len(frame)

        frame = frame.dropna(subset=["dateCreationEtablissement", "codeCommuneEtablissement"])
        frame["codeCommuneEtablissement"] = frame["codeCommuneEtablissement"].astype(str)
        frame = frame[frame["codeCommuneEtablissement"].str.fullmatch(r"\d{5}")]
        frame["year_month"] = frame["dateCreationEtablissement"].astype(str).str.slice(0, 7)
        frame = frame[frame["year_month"].str.fullmatch(r"\d{4}-\d{2}")]
        stats["rows_with_valid_date_and_commune"] += len(frame)

        frame["ze2020"] = frame["codeCommuneEtablissement"].map(core_map)
        frame = frame.dropna(subset=["ze2020"])
        if frame.empty:
            continue

        stats["rows_in_core_mapping"] += len(frame)
        stats["distinct_core_communes_observed"].update(frame["codeCommuneEtablissement"].unique().tolist())

        grouped = frame.groupby(["year_month", "ze2020"]).size()
        for (year_month, ze2020), value in grouped.items():
            counts[(year_month, ze2020)] += int(value)

    result = pd.DataFrame(
        [
            {"year_month": ym, "ze2020": ze, "target_proxy_establishment_creations_count": cnt}
            for (ym, ze), cnt in counts.items()
        ]
    ).sort_values(["year_month", "ze2020"]).reset_index(drop=True)

    quality = {
        "rows_scanned": int(stats["rows_scanned"]),
        "rows_with_valid_date_and_commune": int(stats["rows_with_valid_date_and_commune"]),
        "rows_in_core_mapping": int(stats["rows_in_core_mapping"]),
        "distinct_core_communes_observed": int(len(stats["distinct_core_communes_observed"])),
        "raw_distinct_core_ze2020_observed": int(result["ze2020"].nunique()) if not result.empty else 0,
        "raw_distinct_year_month": int(result["year_month"].nunique()) if not result.empty else 0,
        "raw_min_year_month": None if result.empty else str(result["year_month"].min()),
        "raw_max_year_month": None if result.empty else str(result["year_month"].max()),
        "target_definition": "proxy_establishment_creations_from_current_sirene_stock",
        "territorial_caveat": (
            "Commune is observed from current stock establishment address, not necessarily the exact commune at historical creation time."
        ),
    }
    return result, quality


def write_report(result: pd.DataFrame, quality: dict) -> None:
    totals = result.groupby("year_month")["target_proxy_establishment_creations_count"].sum().reset_index()
    top_months = totals.sort_values("target_proxy_establishment_creations_count", ascending=False).head(10)

    lines = [
        "# Target Proxy Candidate Core v0",
        "",
        "Data: 2026-04-09",
        "",
        "Objetivo:",
        "",
        "- construir um primeiro target proxy mensal por `zone d'emploi` a partir do `SIRENE StockEtablissement`",
        "",
        "## Definicao",
        "",
        "- cada linha conta uma criacao de estabelecimento",
        "- a data usada e `dateCreationEtablissement`",
        "- a localizacao usada e `codeCommuneEtablissement` observado no estoque atual",
        "- a agregacao final e `commune -> ZE2020 core_v0`",
        "",
        "## Caveat metodologico",
        "",
        "- este target e um **proxy**",
        "- a comuna observada e a do estoque atual, nao necessariamente a comuna exata do momento da criacao historica",
        "",
        "## Cobertura",
        "",
        f"- linhas escaneadas no `SIRENE`: `{quality['rows_scanned']}`",
        f"- linhas com data e comuna validas: `{quality['rows_with_valid_date_and_commune']}`",
        f"- linhas dentro do mapeamento `core_v0`: `{quality['rows_in_core_mapping']}`",
        f"- comunas core observadas: `{quality['distinct_core_communes_observed']}`",
        f"- zonas core observadas apos limpeza: `{quality['distinct_core_ze2020_observed']}`",
        f"- meses observados apos limpeza: `{quality['distinct_year_month']}`",
        f"- janela observada apos limpeza: `{quality['min_year_month']} -> {quality['max_year_month']}`",
        "",
        "## Regra de limpeza temporal",
        "",
        f"- anos mantidos: `{MIN_YEAR} -> {MAX_YEAR}`",
        f"- meses brutos antes da limpeza: `{quality['raw_distinct_year_month']}`",
        f"- meses apos limpeza: `{quality['distinct_year_month']}`",
        f"- linhas agregadas excluidas por ano fora da janela: `{quality['excluded_aggregated_rows_out_of_range']}`",
        f"- contagem excluida por ano fora da janela: `{quality['excluded_creation_count_out_of_range']}`",
        "",
        "## Meses com maior contagem observada",
        "",
    ]
    for row in top_months.itertuples(index=False):
        lines.append(f"- `{row.year_month}`: `{int(row.target_proxy_establishment_creations_count)}` criacoes")

    OUT_REPORT.write_text("\n".join(lines) + "\n")


def main() -> None:
    core_map = load_core_mapping()
    result, quality = build_target_proxy(core_map)
    result["year"] = result["year_month"].str.slice(0, 4).astype(int)
    excluded = result[(result["year"] < MIN_YEAR) | (result["year"] > MAX_YEAR)].copy()
    result = result[(result["year"] >= MIN_YEAR) & (result["year"] <= MAX_YEAR)].copy()
    result = result.drop(columns=["year"]).reset_index(drop=True)

    quality["excluded_aggregated_rows_out_of_range"] = int(len(excluded))
    quality["excluded_creation_count_out_of_range"] = int(
        excluded["target_proxy_establishment_creations_count"].sum()
    )
    quality["distinct_core_ze2020_observed"] = int(result["ze2020"].nunique()) if not result.empty else 0
    quality["distinct_year_month"] = int(result["year_month"].nunique()) if not result.empty else 0
    quality["min_year_month"] = None if result.empty else str(result["year_month"].min())
    quality["max_year_month"] = None if result.empty else str(result["year_month"].max())

    result.to_csv(OUT_CSV, index=False)
    pd.Series(quality).to_json(OUT_QUALITY, indent=2)
    write_report(result, quality)
    print(quality)


if __name__ == "__main__":
    main()
