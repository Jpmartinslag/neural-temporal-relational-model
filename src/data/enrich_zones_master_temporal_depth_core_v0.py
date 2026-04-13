"""
enrich_zones_master_temporal_depth_core_v0.py

Objetivo:
- Adicionar profundidade temporal ao zones_master_annual_v0.csv
- Novas colunas: SIDE stocks ET/UL 2019-2020 e FLORES ET total 2019-2021
- Motivacao: aumentar amostras de treino efetivas de 3 para 5-6 anos anuais

Fontes:
- SIDE ET: DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip (ZE2020 direto, TIME_PERIOD 2014-2023)
- SIDE UL: DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip (ZE2020 direto, TIME_PERIOD 2014-2023)
- FLORES: TD_FLORES{ano}_NA17_TREF_NBETAB_*.zip (CODGEO + ET_TOT, nivel comunal)

Decisao metodologica:
- SIDE stocks ET e UL sao extraidos diretamente no nivel ZE2020 (nao precisa agregar)
- FLORES historico usa ET_TOT = total de estabelecimentos ativos por comuna
- FLORES historico e uma feature distinta da FLORES 2024 (presential/productive)
  e e adicionada como flores_et_total (feature nova no panel)
- Nenhuma imputacao temporal e feita — cada coluna so existe para seu ano fonte
"""

import json
import pathlib
import zipfile

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]

ZONES_MASTER = ROOT / "data/processed/zones_master_annual_v0.csv"
SIDE_ET_ZIP = ROOT / "data/raw/temporal_depth/side/DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip"
SIDE_UL_ZIP = ROOT / "data/raw/temporal_depth/side/DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip"
FLORES_DIR = ROOT / "data/raw/employment/flores"
MAPPING_CSV = ROOT / "data/interim/mappings/commune_to_ze2020_2026.csv"

OUT_JSON = ROOT / "reports/temporal_depth_enrichment_core_quality_v0.json"
OUT_MD = ROOT / "reports/TEMPORAL_DEPTH_ENRICHMENT_CORE_V0.md"

SIDE_YEARS = [2019, 2020]
FLORES_YEARS = [2019, 2020, 2021]

FLORES_FILES = {
    2019: "TD_FLORES2019_NA17_TREF_NBETAB_CSV.zip",
    2020: "TD_FLORES2020_NA17_TREF_NBETAB_CSV.zip",
    2021: "TD_FLORES2021_NA17_TREF_NBETAB_csv.zip",
}


def load_side_ze2020(zip_path, measure_filter, years):
    """
    Extrai OBS_VALUE agregado por ZE2020 e TIME_PERIOD.
    Retorna dict {year: {ze2020: valor}}.
    """
    with zipfile.ZipFile(zip_path) as z:
        data_file = [f for f in z.namelist() if f.endswith("_data.csv")][0]
        with z.open(data_file) as f:
            df = pd.read_csv(f, sep=";", dtype={"GEO": str}, low_memory=False)

    df["GEO"] = df["GEO"].astype(str).str.zfill(4)
    result = {}
    for yr in years:
        mask = (
            (df["GEO_OBJECT"] == "ZE2020")
            & (df["ACTIVITY"] == "_T")
            & (df["TIME_PERIOD"] == yr)
        )
        if "SIDE_MEASURE" in df.columns:
            mask &= df["SIDE_MEASURE"] == measure_filter
        sub = df[mask]
        if sub["GEO"].duplicated().any():
            duplicated = int(sub["GEO"].duplicated().sum())
            raise ValueError(f"{zip_path.name} {yr} has {duplicated} duplicated ZE2020 rows after filtering.")
        result[yr] = sub.set_index("GEO")["OBS_VALUE"].astype(float).to_dict()
        print(f"  {zip_path.name} [{yr}]: {len(result[yr])} ZE2020 rows")
    return result


def load_flores_ze2020(year, mapping):
    """
    Carrega FLORES NBETAB comunal, agrega ET_TOT para ZE2020.
    """
    fname = FLORES_FILES[year]
    zip_path = FLORES_DIR / fname
    with zipfile.ZipFile(zip_path) as z:
        csv_file = [f for f in z.namelist()
                    if f.endswith(".csv") and not f.startswith("meta")][0]
        with z.open(csv_file) as f:
            df = pd.read_csv(f, sep=";", dtype={"CODGEO": str}, low_memory=False)

    df["CODGEO"] = df["CODGEO"].astype(str).str.zfill(5)
    df["ET_TOT"] = pd.to_numeric(df["ET_TOT"], errors="coerce").fillna(0)

    merged = df.merge(mapping, on="CODGEO", how="left")
    merged = merged.dropna(subset=["ZE2020"])
    merged["ZE2020"] = merged["ZE2020"].astype(str).str.zfill(4)

    ze_agg = merged.groupby("ZE2020")["ET_TOT"].sum().astype(float).to_dict()
    print(f"  FLORES {year}: {len(merged['CODGEO'].unique())} comunas mapadas → {len(ze_agg)} ZE2020")
    return ze_agg


def main():
    print("Carregando zones_master...")
    zm = pd.read_csv(ZONES_MASTER, dtype={"ze2020": str})
    zm["ze2020"] = zm["ze2020"].str.zfill(4)
    n_zones = len(zm)
    print(f"  {n_zones} zonas no zones_master")

    mapping = pd.read_csv(MAPPING_CSV, dtype={"CODGEO": str, "ZE2020": str})
    mapping["CODGEO"] = mapping["CODGEO"].str.zfill(5)
    mapping["ZE2020"] = mapping["ZE2020"].str.zfill(4)
    print(f"  Mapeamento: {len(mapping)} comunas")

    # --- SIDE ET 2019, 2020 ---
    print("\nExtraindo SIDE stocks ET (ZE2020 direto)...")
    side_et = load_side_ze2020(SIDE_ET_ZIP, "UNIT_LOC", SIDE_YEARS)

    # --- SIDE UL 2019, 2020 ---
    print("\nExtraindo SIDE stocks UL (ZE2020 direto)...")
    side_ul = load_side_ze2020(SIDE_UL_ZIP, "LEGAL_UNIT", SIDE_YEARS)

    # --- FLORES ET 2019, 2020, 2021 ---
    print("\nAgregando FLORES historico (comunal → ZE2020)...")
    flores = {}
    for yr in FLORES_YEARS:
        flores[yr] = load_flores_ze2020(yr, mapping)

    # --- adicionar colunas ---
    quality_cols = {}

    for yr in SIDE_YEARS:
        col_et = f"side_stocks_et_{yr}_total"
        col_ul = f"side_stocks_ul_{yr}_total"
        zm[col_et] = zm["ze2020"].map(side_et[yr])
        zm[col_ul] = zm["ze2020"].map(side_ul[yr])
        quality_cols[col_et] = int(zm[col_et].notna().sum())
        quality_cols[col_ul] = int(zm[col_ul].notna().sum())
        print(f"  {col_et}: {quality_cols[col_et]}/{n_zones} nao nulos")
        print(f"  {col_ul}: {quality_cols[col_ul]}/{n_zones} nao nulos")

    for yr in FLORES_YEARS:
        col = f"flores_et_total_{yr}"
        zm[col] = zm["ze2020"].map(flores[yr])
        quality_cols[col] = int(zm[col].notna().sum())
        print(f"  {col}: {quality_cols[col]}/{n_zones} nao nulos")

    zm.to_csv(ZONES_MASTER, index=False)
    print(f"\nZones master atualizado: {ZONES_MASTER.name}")
    print(f"Colunas adicionadas: {len(quality_cols)}")

    # --- relatorio ---
    quality = {
        "zones_count": n_zones,
        "new_columns": quality_cols,
        "side_years_added": SIDE_YEARS,
        "flores_years_added": FLORES_YEARS,
        "notes": (
            "SIDE stocks extraidos diretamente no nivel ZE2020 do arquivo multi-anual. "
            "FLORES ET_TOT agregado de nivel comunal via mapeamento commune_to_ze2020_2026. "
            "Nenhuma imputacao temporal aplicada."
        ),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2, ensure_ascii=False)

    lines = [
        "# Temporal Depth Enrichment Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- Adicionar profundidade temporal ao zones_master para expandir amostras de treino",
        "- Melhorar a cobertura observada das features nos anos ja alinhados do tensor",
        "- Nao aumenta, por si so, o numero de anos supervisionados de treino",
        "",
        "## Fontes",
        "",
        "- **SIDE stocks ET/UL**: `DS_SIDE_STOCKS_ET/UL_COM_2023_CSV_FR.zip`",
        "  - nivel ZE2020 direto, TIME_PERIOD 2019-2020",
        "  - medida: UNIT_LOC (ET) e LEGAL_UNIT (UL), atividade total (_T)",
        "",
        "- **FLORES historico**: `TD_FLORES{ano}_NA17_TREF_NBETAB_CSV.zip`",
        "  - nivel comunal, campo ET_TOT = total de estabelecimentos ativos",
        "  - agregado para ZE2020 via mapeamento commune_to_ze2020_2026",
        "  - anos: 2019, 2020, 2021",
        "",
        "## Colunas Adicionadas",
        "",
        f"| coluna | cobertura (de {n_zones}) |",
        "|---|---|",
    ]
    for col, n in quality_cols.items():
        lines.append(f"| `{col}` | `{n}` |")

    lines += [
        "",
        "## Decisao",
        "",
        "- `flores_et_total` e uma feature nova (distinta de `flores_presential_unit_loc_total`)",
        "  e captura o estoque total de estabelecimentos FLORES por ano",
        "- `side_stocks_et_total` e `side_stocks_ul_total` ganham cobertura observada em 2019 e 2020",
        "  dentro da janela anual ja usada pelo tensor",
        "- o proximo passo e atualizar build_panel_zones_v0.py e reconstruir o tensor STGNN",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "=" * 60)
    print("TEMPORAL DEPTH ENRICHMENT — CORE v0")
    print("=" * 60)
    for col, n in quality_cols.items():
        print(f"  {col}: {n}/{n_zones}")


if __name__ == "__main__":
    main()
