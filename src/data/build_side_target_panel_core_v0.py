from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

SIDE_ZE_PATH = ROOT / "data" / "processed" / "side_communal_creations_ze2020_official_2012_2024_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"

TARGET_OUT = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "target_side_establishments_annual_core_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "TARGET_SIDE_ESTABLISHMENTS_ANNUAL_CORE_V0.md"

TARGET_COL = "side_establishment_creations_official"


def main() -> None:
    side = pd.read_csv(SIDE_ZE_PATH, dtype={"ze2020": str})
    nodes = pd.read_csv(NODE_INDEX_PATH, dtype={"ze2020": str})

    frame = side.merge(nodes[["node_idx", "ze2020"]], on="ze2020", how="inner")
    frame = frame.rename(columns={"year": "target_year"})
    frame = frame[
        [
            "target_year",
            "ze2020",
            "node_idx",
            "libze2020",
            "side_enterprise_creations_official",
            "side_establishment_creations_official",
            "communes_count",
        ]
    ].sort_values(["target_year", "node_idx"])

    expected_rows = frame["target_year"].nunique() * nodes["node_idx"].nunique()
    if len(frame) != expected_rows:
        raise ValueError(f"SIDE target panel is incomplete: {len(frame)} rows, expected {expected_rows}.")
    if frame[TARGET_COL].isna().any():
        raise ValueError(f"SIDE target column has missing values: {TARGET_COL}.")

    quality = {
        "source": str(SIDE_ZE_PATH.relative_to(ROOT)),
        "target_file": str(TARGET_OUT.relative_to(ROOT)),
        "target_column": TARGET_COL,
        "sensitivity_column": "side_enterprise_creations_official",
        "node_count": int(frame["node_idx"].nunique()),
        "year_min": int(frame["target_year"].min()),
        "year_max": int(frame["target_year"].max()),
        "year_count": int(frame["target_year"].nunique()),
        "row_count": int(len(frame)),
        "expected_rows": int(expected_rows),
        "annual_totals": [
            {
                "year": int(year),
                "side_establishment_creations_official": float(group[TARGET_COL].sum()),
                "side_enterprise_creations_official": float(group["side_enterprise_creations_official"].sum()),
            }
            for year, group in frame.groupby("target_year", sort=True)
        ],
        "decision": (
            "Use official SIDE establishment creations as the formal target candidate. "
            "Keep official SIDE enterprise creations as a sensitivity target and the old proxy as audit only."
        ),
    }

    frame.to_csv(TARGET_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


def write_report(quality: dict) -> None:
    lines = [
        "# Target SIDE Establishments Annual Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- criar um target anual oficial baseado em `SIDE` estabelecimentos",
        "- preservar `SIDE` empresas como alvo alternativo de sensibilidade",
        "- manter o target proxy antigo apenas como auditoria/comparacao",
        "",
        "## Artefatos",
        "",
        f"- fonte agregada: `{quality['source']}`",
        f"- target: `{quality['target_file']}`",
        f"- qualidade: `{QUALITY_OUT.relative_to(ROOT)}`",
        "",
        "## Estrutura",
        "",
        f"- nos `ZE2020`: `{quality['node_count']}`",
        f"- anos: `{quality['year_min']}-{quality['year_max']}`",
        f"- linhas: `{quality['row_count']}`",
        f"- coluna principal: `{quality['target_column']}`",
        f"- coluna de sensibilidade: `{quality['sensitivity_column']}`",
        "",
        "## Decisao",
        "",
        "- o alvo principal formal passa a ser `side_establishment_creations_official`",
        "- `side_enterprise_creations_official` deve ser usado para teste de sensibilidade",
        "- o proxy anterior nao deve ser interpretado como ground truth final",
        "",
        "## Totais Anuais",
        "",
        "| Ano | SIDE estabelecimentos | SIDE empresas |",
        "|---:|---:|---:|",
    ]
    for row in quality["annual_totals"]:
        lines.append(
            f"| {row['year']} | {row['side_establishment_creations_official']:.0f} | {row['side_enterprise_creations_official']:.0f} |"
        )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
