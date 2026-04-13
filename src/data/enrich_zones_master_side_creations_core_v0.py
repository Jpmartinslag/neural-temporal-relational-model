"""
enrich_zones_master_side_creations_core_v0.py

Objetivo:
- adicionar historico de criações de estabelecimentos SIDE como feature temporal
- anos cobertos: 2019-2023 (cobre todos os feature_years do tensor STGNN)
- fonte: DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip, nivel ZE2020 direto

Motivacao:
- o target e criacao de estabelecimentos em t+1
- a melhor predicao naive e criacao em t (persistencia, WMAPE=3.566)
- adicionar side_creations_et_total como feature explicita permite que modelos
  aprendam a dinamica temporal do proprio target (lags 1 e 2)
- o dado e ao nivel ZE2020 direto: sem agregacao, sem risco de alinhamento
- cobre 280/280 zonas core para todos os anos de feature do tensor

Regra:
- ACTIVITY='_T' (total), LEGAL_FORM='_T' (todas as formas legais)
- SIDE_MEASURE='UNIT_LOC_BURE' (criação de unidades locais = estabelecimentos)
- sem imputacao temporal: cada coluna existe apenas para seu ano
"""

import json
import pathlib
import zipfile

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]

SIDE_CREA_ZIP = ROOT / "data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip"
ZONES_MASTER = ROOT / "data/processed/zones_master_annual_v0.csv"

OUT_JSON = ROOT / "reports/side_creations_enrichment_core_quality_v0.json"

FEATURE_YEARS = [2019, 2020, 2021, 2022, 2023]


def main():
    print("Carregando SIDE criações de estabelecimentos...")
    with zipfile.ZipFile(SIDE_CREA_ZIP) as z:
        data_file = [f for f in z.namelist() if "_data" in f][0]
        with z.open(data_file) as f:
            df = pd.read_csv(f, sep=";", dtype={"GEO": str}, low_memory=False)

    df["GEO"] = df["GEO"].astype(str).str.zfill(4)
    total = df[
        (df["GEO_OBJECT"] == "ZE2020")
        & (df["ACTIVITY"] == "_T")
        & (df["LEGAL_FORM"] == "_T")
    ].copy()
    if "SIDE_MEASURE" in total.columns:
        total = total[total["SIDE_MEASURE"] == "UNIT_LOC_BURE"].copy()
    duplicated = int(total.duplicated(["GEO", "TIME_PERIOD"]).sum())
    if duplicated:
        raise ValueError(f"SIDE creations has {duplicated} duplicated GEO/TIME_PERIOD rows after filtering.")

    pivot = total.pivot(index="GEO", columns="TIME_PERIOD", values="OBS_VALUE")
    pivot.index.name = "ze2020"
    print(f"  ZE2020 disponíveis: {len(pivot)} | Anos: {list(pivot.columns)}")

    zm = pd.read_csv(ZONES_MASTER, dtype={"ze2020": str})
    zm["ze2020"] = zm["ze2020"].str.zfill(4)

    quality_cols = {}
    for yr in FEATURE_YEARS:
        col = f"side_creations_et_total_{yr}"
        zm[col] = zm["ze2020"].map(pivot[yr].to_dict())
        quality_cols[col] = int(zm[col].notna().sum())
        print(f"  {col}: {quality_cols[col]}/{len(zm)} não nulos")

    zm.to_csv(ZONES_MASTER, index=False)
    print(f"\nZones master atualizado com {len(quality_cols)} colunas de criações.")

    quality = {
        "source": "DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip",
        "measure": "UNIT_LOC_BURE (ACTIVITY=_T, LEGAL_FORM=_T)",
        "years_added": FEATURE_YEARS,
        "coverage": quality_cols,
        "note": (
            "Dado ao nível ZE2020 direto. "
            "Feature side_creations_et_total captura o fluxo anual de criações, "
            "distinto do estoque (side_stocks_et_total). "
            "Permite que modelos aprendam a dinâmica temporal do próprio target."
        ),
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("SIDE CREATIONS ENRICHMENT — CORE v0")
    print("=" * 60)
    for col, n in quality_cols.items():
        print(f"  {col}: {n}/{len(zm)}")


if __name__ == "__main__":
    main()
