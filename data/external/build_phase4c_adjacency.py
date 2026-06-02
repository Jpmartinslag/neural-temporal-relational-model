#!/usr/bin/env python3
"""Phase 4C — Build real geographic contiguity adjacency matrices.

Downloads Eurostat NUTS3 shapefiles and computes queen contiguity
(shared border or point) for NL (COROP→NUTS3), BE (arrondissements→NUTS3),
PT (NUTS3).

Outputs adj_geo.csv in data/processed/phase4/{country}/ — same format
as the identity matrices used in Phase 4A, replacing them.

Usage:
    python3 data/external/build_phase4c_adjacency.py
    python3 data/external/build_phase4c_adjacency.py --country nl
"""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent.parent

# Eurostat GISCO — NUTS 2021, 1:3M resolution
NUTS_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/nuts/download/"
    "ref-nuts-2021-03m.geojson.zip"
)
NUTS_CACHE = BASE / "data/external/nuts3_2021_eurostat.geojson"

# COROP → NUTS3 2021: CBS COROP CR01-CR40 in canonical CBS order → Eurostat NUTS3 2021
COROP_TO_NUTS3 = {
    "CR01": "NL111", "CR02": "NL112", "CR03": "NL113",  # Groningen
    "CR04": "NL124", "CR05": "NL125", "CR06": "NL126",  # Friesland
    "CR07": "NL131", "CR08": "NL132", "CR09": "NL133",  # Drenthe
    "CR10": "NL211", "CR11": "NL212", "CR12": "NL213",  # Overijssel
    "CR13": "NL221", "CR14": "NL225", "CR15": "NL226",  # Gelderland (Veluwe/Achterhoek/Arnhem)
    "CR16": "NL224",                                     # Zuidwest-Gelderland
    "CR17": "NL230",                                     # Flevoland
    "CR18": "NL310",                                     # Utrecht
    "CR19": "NL321", "CR20": "NL328", "CR21": "NL323",  # Noord-Holland (Kop/Alkmaar/IJmond)
    "CR22": "NL324", "CR23": "NL329", "CR24": "NL327",  # NH (Haarlem/Groot-Amsterdam/Gooi)
    "CR25": "NL325",                                     # Zaanstreek
    "CR26": "NL337", "CR27": "NL332", "CR28": "NL333",  # Zuid-Holland (Leiden/Den Haag/Delft)
    "CR29": "NL33B", "CR30": "NL33C", "CR31": "NL33A",  # ZH (Oost/Groot-Rijnmond/Zuidoost)
    "CR32": "NL341", "CR33": "NL342",                   # Zeeland
    "CR34": "NL411", "CR35": "NL412",                   # Noord-Brabant (West/Midden)
    "CR36": "NL413", "CR37": "NL414",                   # Noord-Brabant (NO/ZO)
    "CR38": "NL421", "CR39": "NL422", "CR40": "NL423",  # Limburg
}

# Belgium arrondissements → NUTS3 2021 (zone IDs match zone_mapping.csv French names)
BE_TO_NUTS3 = {
    "BE_alost":              "BE231",  # Arr. Aalst
    "BE_anvers":             "BE211",  # Arr. Antwerpen
    "BE_arlon":              "BE341",
    "BE_ath":                "BE32A",  # was BE325 pre-2021
    "BE_audenarde":          "BE235",  # Arr. Oudenaarde
    "BE_bastogne":           "BE342",
    "BE_bruges":             "BE251",  # Arr. Brugge
    "BE_bruxelles_capitale": "BE100",
    "BE_charleroi":          "BE32B",  # was BE322 pre-2021
    "BE_courtrai":           "BE254",  # Arr. Kortrijk
    "BE_dinant":             "BE351",
    "BE_dixmude":            "BE252",  # Arr. Diksmuide
    "BE_eeklo":              "BE233",
    "BE_furnes":             "BE258",  # Arr. Veurne
    "BE_gand":               "BE234",  # Arr. Gent
    "BE_hal_vilvorde":       "BE241",
    "BE_hasselt":            "BE224",  # was BE221 pre-2021
    "BE_huy":                "BE331",
    "BE_liege":              "BE332",
    "BE_louvain":            "BE242",  # Arr. Leuven
    "BE_maaseik":            "BE225",  # was BE222 pre-2021
    "BE_malines":            "BE212",  # Arr. Mechelen
    "BE_marche_en_famenne":  "BE343",
    "BE_mons":               "BE323",
    "BE_namur":              "BE352",
    "BE_neufchateau":        "BE344",
    "BE_nivelles":           "BE310",
    "BE_ostende":            "BE255",  # Arr. Oostende
    "BE_philippeville":      "BE353",
    "BE_roulers":            "BE256",  # Arr. Roeselare
    "BE_saint_nicolas":      "BE236",  # Arr. Sint-Niklaas
    "BE_soignies":           "BE32C",  # was BE326 pre-2021
    "BE_termonde":           "BE232",  # Arr. Dendermonde
    "BE_thuin":              "BE32D",  # was BE327 pre-2021
    "BE_tielt":              "BE257",
    "BE_tongres":            "BE223",  # Arr. Tongeren
    "BE_tournai_mouscron":   "BE328",  # merged in 2021
    "BE_turnhout":           "BE213",
    "BE_verviers":           "BE335",  # francophone part
    "BE_virton":             "BE345",
    "BE_waremme":            "BE334",
    "BE_ypres":              "BE253",  # Arr. Ieper
}

# Portugal NUTS3 codes (direct — already NUTS3)
# PT_111 → PT111, etc. (strip underscore)
def pt_to_nuts3(zone_id: str) -> str:
    return zone_id.replace("PT_", "PT")


def download_nuts3(cache: Path = NUTS_CACHE) -> gpd.GeoDataFrame:
    if cache.exists():
        print(f"  Using cached: {cache}")
        return gpd.read_file(cache)

    print(f"  Downloading Eurostat NUTS3 2021 (3M)...")
    r = requests.get(NUTS_URL, timeout=120)
    r.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = [n for n in zf.namelist() if "NUTS_RG_03M_2021_4326_LEVL_3" in n and n.endswith(".geojson")]
    if not names:
        names = [n for n in zf.namelist() if n.endswith(".geojson") and "LEVL_3" in n]
    if not names:
        raise FileNotFoundError(f"NUTS3 geojson not found in zip. Files: {zf.namelist()[:10]}")

    with zf.open(names[0]) as f:
        gdf = gpd.read_file(f)

    cache.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(cache, driver="GeoJSON")
    print(f"  Saved to {cache}")
    return gdf


def compute_contiguity(gdf: gpd.GeoDataFrame, zone_ids: list[str],
                       nuts3_ids: list[str]) -> np.ndarray:
    """Queen contiguity matrix (shared border/point) for given zones."""
    sub = gdf[gdf["NUTS_ID"].isin(nuts3_ids)].copy()
    sub = sub.set_index("NUTS_ID").reindex(nuts3_ids)

    missing = sub[sub.geometry.isna()]["NUTS_ID"].tolist() if "NUTS_ID" in sub.columns else []
    if sub.geometry.isna().any():
        missing_ids = [n for n, g in zip(nuts3_ids, sub.geometry) if g is None or (hasattr(g, '__class__') and g is None)]
        print(f"  WARNING: {sub.geometry.isna().sum()} zones not found in Eurostat data")

    N = len(zone_ids)
    adj = np.zeros((N, N), dtype=np.float32)

    geoms = sub.geometry.values
    for i in range(N):
        if geoms[i] is None or (hasattr(geoms[i], 'is_empty') and geoms[i].is_empty):
            adj[i, i] = 1.0
            continue
        for j in range(N):
            if i == j:
                continue
            if geoms[j] is None or (hasattr(geoms[j], 'is_empty') and geoms[j].is_empty):
                continue
            try:
                if geoms[i].touches(geoms[j]) or geoms[i].intersects(geoms[j]):
                    adj[i, j] = 1.0
            except Exception:
                pass
        if adj[i].sum() == 0:
            adj[i, i] = 1.0  # isolated zone → self-loop

    # Row-normalize
    row_sums = adj.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    adj = adj / row_sums
    return adj


def adj_to_df(adj: np.ndarray) -> pd.DataFrame:
    N = adj.shape[0]
    df = pd.DataFrame(adj, columns=list(range(N)))
    df.insert(0, "source_idx", list(range(N)))
    return df


def build_adjacency(country: str, gdf: gpd.GeoDataFrame) -> None:
    mapping = pd.read_csv(BASE / f"data/processed/phase4/{country}/zone_mapping.csv")
    zone_ids = mapping["zone_id"].tolist()
    out_dir = BASE / f"data/processed/phase4/{country}"

    if country == "nl":
        nuts3_ids = [COROP_TO_NUTS3[z] for z in zone_ids]
    elif country == "be":
        nuts3_ids = [BE_TO_NUTS3.get(z, z) for z in zone_ids]
    elif country == "pt":
        nuts3_ids = [pt_to_nuts3(z) for z in zone_ids]
    else:
        raise ValueError(country)

    print(f"[{country.upper()}] Computing contiguity for {len(zone_ids)} zones...")
    adj = compute_contiguity(gdf, zone_ids, nuts3_ids)

    nonzero_neighbors = (adj > 0).sum(axis=1) - (np.diag(adj) > 0).astype(int)
    print(f"[{country.upper()}] Avg neighbors: {nonzero_neighbors.mean():.1f} "
          f"(min {nonzero_neighbors.min()}, max {nonzero_neighbors.max()})")

    df = adj_to_df(adj)
    out_path = out_dir / "adj_geo.csv"
    df.to_csv(out_path, index=False)
    print(f"[{country.upper()}] Wrote {out_path}")

    # Keep identity for mobility (no commuting data for international)
    mob_path = out_dir / "adj_mob.csv"
    if not mob_path.exists():
        df.to_csv(mob_path, index=False)
        print(f"[{country.upper()}] adj_mob.csv kept as identity (no commuting data)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", choices=["nl", "be", "pt", "all"], default="all")
    args = parser.parse_args()
    targets = ["nl", "be", "pt"] if args.country == "all" else [args.country]

    print("Downloading Eurostat NUTS3 geometries...")
    gdf = download_nuts3()
    print(f"  Loaded {len(gdf)} NUTS3 regions")

    for c in targets:
        build_adjacency(c, gdf)

    print("\nDone. adj_geo.csv files written for:", targets)
    print("Next: sync to cluster and run Phase 4C battery.")


if __name__ == "__main__":
    main()
