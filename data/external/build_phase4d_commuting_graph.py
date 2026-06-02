#!/usr/bin/env python3
"""Phase 4D — Build commuting adjacency matrices for NL and BE.

NL: CBS StatLine 85481NED (COROP×COROP, December 2022 snapshot)
    Raw: data/external/netherlands/raw/commuting/85481NED_corop_commuting_2022.json
    API: https://opendata.cbs.nl/ODataApi/OData/85481NED/

BE: StatBel Census 2011 municipality OD matrix, aggregated to arrondissement
    Raw: data/external/belgium/raw/commuting/TU_CENSUS_2011_COMMUTERS_MUNTY.txt
    Source: https://statbel.fgov.be/sites/default/files/files/opendata/
            census%202011%20Matrix%20woon-%20werkverkeer%20per%20geslacht/
            TU_CENSUS_2011_COMMUTERS_MUNTY.zip

PT: BLOCKED — see HERALD_PHASE4D_DATA_AND_GRAPH_AUDIT.md

Output format (same as adj_geo.csv):
    source_idx | 0 | 1 | ... | N-1
    Row i = outgoing commuting weights from zone i to all zones.
    Row-normalised; self-loop (diagonal) retained.

Usage:
    python3 data/external/build_phase4d_commuting_graph.py
    python3 data/external/build_phase4d_commuting_graph.py --country nl
    python3 data/external/build_phase4d_commuting_graph.py --country be
"""
from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# NL — CBS 85481NED
# ---------------------------------------------------------------------------
NL_RAW = BASE / "data/external/netherlands/raw/commuting/85481NED_corop_commuting_2022.json"
NL_CBS_URL = "https://opendata.cbs.nl/ODataApi/OData/85481NED/UntypedDataSet?$format=json"

# CR99 = international / unknown, excluded
NL_EXCLUDED = {"CR99  "}


def _nl_download() -> None:
    print("  Downloading CBS 85481NED...")
    records = []
    url: str | None = NL_CBS_URL
    while url:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        data = r.json()
        records.extend(data.get("value", []))
        url = data.get("odata.nextLink")
    NL_RAW.parent.mkdir(parents=True, exist_ok=True)
    NL_RAW.write_text(json.dumps({"value": records}, ensure_ascii=False))
    print(f"  Saved {len(records)} records → {NL_RAW}")


def build_nl(zone_mapping: pd.DataFrame) -> np.ndarray:
    if not NL_RAW.exists():
        _nl_download()

    raw = json.loads(NL_RAW.read_text())
    records = raw["value"]

    # zone_mapping: zone_id (CRxx) → ZE2020 (0-based idx = ZE2020 - 1)
    zm = zone_mapping.copy()
    zm["idx"] = zm["ZE2020"] - 1
    cr_to_idx = dict(zip(zm["zone_id"].str.strip(), zm["idx"]))
    N = len(zm)

    flow = np.zeros((N, N), dtype=np.float64)
    skipped = 0
    for rec in records:
        src = rec.get("WoonregioS", "").strip()
        dst = rec.get("WerkregioS", "").strip()
        val = float(rec.get("BanenVanWerknemers_1") or 0)
        if src in NL_EXCLUDED or dst in NL_EXCLUDED:
            skipped += 1
            continue
        i = cr_to_idx.get(src)
        j = cr_to_idx.get(dst)
        if i is None or j is None:
            skipped += 1
            continue
        flow[i, j] += val

    print(f"  NL: processed {len(records)} records, skipped {skipped} (CR99/unmatched)")
    print(f"  NL: total flow = {flow.sum():,.0f} jobs")
    return flow


# ---------------------------------------------------------------------------
# BE — StatBel Census 2011
# ---------------------------------------------------------------------------
BE_RAW = BASE / "data/external/belgium/raw/commuting/TU_CENSUS_2011_COMMUTERS_MUNTY.txt"
BE_ZIP_URL = (
    "https://statbel.fgov.be/sites/default/files/files/opendata/"
    "census%202011%20Matrix%20woon-%20werkverkeer%20per%20geslacht/"
    "TU_CENSUS_2011_COMMUTERS_MUNTY.zip"
)

# NIS arrondissement code → zone_id (French names, matching zone_mapping.csv)
# Tournai (57000) and Mouscron (54000) merged as in the zone_mapping
BE_NIS_TO_ZONE: dict[int, str] = {
    11000: "BE_anvers",
    12000: "BE_malines",
    13000: "BE_turnhout",
    21000: "BE_bruxelles_capitale",
    23000: "BE_hal_vilvorde",
    24000: "BE_louvain",
    25000: "BE_nivelles",
    31000: "BE_bruges",
    32000: "BE_dixmude",
    33000: "BE_ypres",
    34000: "BE_courtrai",
    35000: "BE_ostende",
    36000: "BE_roulers",
    37000: "BE_tielt",
    38000: "BE_furnes",
    41000: "BE_alost",
    42000: "BE_termonde",
    43000: "BE_eeklo",
    44000: "BE_gand",
    45000: "BE_audenarde",
    46000: "BE_saint_nicolas",
    51000: "BE_ath",
    52000: "BE_charleroi",
    53000: "BE_mons",
    54000: "BE_tournai_mouscron",   # Mouscron merged with Tournai
    55000: "BE_soignies",
    56000: "BE_thuin",
    57000: "BE_tournai_mouscron",   # Tournai merged with Mouscron
    61000: "BE_huy",
    62000: "BE_liege",
    63000: "BE_verviers",
    64000: "BE_waremme",
    71000: "BE_hasselt",
    72000: "BE_maaseik",
    73000: "BE_tongres",
    81000: "BE_arlon",
    82000: "BE_bastogne",
    83000: "BE_marche_en_famenne",
    84000: "BE_neufchateau",
    85000: "BE_virton",
    91000: "BE_dinant",
    92000: "BE_namur",
    93000: "BE_philippeville",
}


def _be_download() -> None:
    print("  Downloading StatBel Census 2011 commuting matrix...")
    r = requests.get(BE_ZIP_URL, timeout=120)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    BE_RAW.parent.mkdir(parents=True, exist_ok=True)
    zf.extractall(BE_RAW.parent)
    print(f"  Extracted to {BE_RAW.parent}")


def build_be(zone_mapping: pd.DataFrame) -> np.ndarray:
    if not BE_RAW.exists():
        _be_download()

    # Read only relevant columns — file is large (~4MB, ~2M rows M+F)
    df = pd.read_csv(
        BE_RAW, sep="|",
        usecols=["CD_DSTR_REFNIS_RESIDENCE", "CD_DSTR_REFNIS_WORK", "OBS_VALUE"],
        na_values=[" ", ""],
    )
    df["CD_DSTR_REFNIS_RESIDENCE"] = pd.to_numeric(df["CD_DSTR_REFNIS_RESIDENCE"], errors="coerce")
    df["CD_DSTR_REFNIS_WORK"] = pd.to_numeric(df["CD_DSTR_REFNIS_WORK"], errors="coerce")
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce").fillna(0)
    # Sum M+F
    df = df.groupby(["CD_DSTR_REFNIS_RESIDENCE", "CD_DSTR_REFNIS_WORK"],
                    as_index=False)["OBS_VALUE"].sum()

    zm = zone_mapping.copy()
    zm["idx"] = zm["ZE2020"] - 1
    zone_to_idx = dict(zip(zm["zone_id"], zm["idx"]))
    N = len(zm)

    flow = np.zeros((N, N), dtype=np.float64)
    skipped = 0
    for _, row in df.iterrows():
        src_nis = int(row["CD_DSTR_REFNIS_RESIDENCE"]) if pd.notna(row["CD_DSTR_REFNIS_RESIDENCE"]) else None
        dst_nis = int(row["CD_DSTR_REFNIS_WORK"]) if pd.notna(row["CD_DSTR_REFNIS_WORK"]) else None
        if src_nis is None or dst_nis is None:
            skipped += 1
            continue
        src_zone = BE_NIS_TO_ZONE.get(src_nis)
        dst_zone = BE_NIS_TO_ZONE.get(dst_nis)
        if src_zone is None or dst_zone is None:
            skipped += 1
            continue
        i = zone_to_idx.get(src_zone)
        j = zone_to_idx.get(dst_zone)
        if i is None or j is None:
            skipped += 1
            continue
        flow[i, j] += row["OBS_VALUE"]

    print(f"  BE: processed {len(df)} OD pairs, skipped {skipped} (unmatched NIS codes)")
    print(f"  BE: total flow = {flow.sum():,.0f} commuters (M+F)")
    return flow


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def row_normalize(flow: np.ndarray) -> np.ndarray:
    adj = flow.astype(np.float32)
    row_sums = adj.sum(axis=1, keepdims=True)
    # Isolated zones get self-loop
    isolated = (row_sums.squeeze() == 0)
    if isolated.any():
        for i in np.where(isolated)[0]:
            adj[i, i] = 1.0
        row_sums = adj.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return adj / row_sums


def adj_to_df(adj: np.ndarray) -> pd.DataFrame:
    N = adj.shape[0]
    df = pd.DataFrame(adj, columns=list(range(N)))
    df.insert(0, "source_idx", list(range(N)))
    return df


def validate(adj: np.ndarray, country: str) -> None:
    row_sums = adj.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-4), \
        f"[{country}] Row sums not ~1: {row_sums.min():.4f}..{row_sums.max():.4f}"
    assert not np.isnan(adj).any(), f"[{country}] NaN in matrix"
    assert adj.min() >= 0, f"[{country}] Negative values"
    diag = np.diag(adj)
    off = (adj > 0).sum(axis=1) - (diag > 0).astype(int)
    print(f"  [{country}] Validation OK")
    print(f"    row sums: {row_sums.min():.6f}..{row_sums.max():.6f}")
    print(f"    diagonal: mean={diag.mean():.3f} min={diag.min():.3f} max={diag.max():.3f}")
    print(f"    avg off-diag neighbours: {off.mean():.1f}")


def apply_top_k(adj: np.ndarray, k: int) -> np.ndarray:
    """Keep only top-k off-diagonal entries per row; zero the rest; re-normalise."""
    N = adj.shape[0]
    sparse = adj.copy()
    for i in range(N):
        row = sparse[i].copy()
        diag_val = row[i]
        row[i] = -1.0  # temporarily exclude diagonal
        cutoff_indices = np.argsort(row)[:-(k)]  # indices to zero
        sparse[i, cutoff_indices] = 0.0
        sparse[i, i] = diag_val  # restore diagonal
    # Re-normalise
    row_sums = sparse.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return (sparse / row_sums).astype(np.float32)


def build_country(country: str, top_k_variants: "list[int] | None" = None) -> None:
    zm = pd.read_csv(BASE / f"data/processed/phase4/{country}/zone_mapping.csv")
    out_dir = BASE / f"data/processed/phase4d/{country}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{country.upper()}] Building commuting adjacency...")
    if country == "nl":
        flow = build_nl(zm)
    elif country == "be":
        flow = build_be(zm)
    else:
        raise ValueError(f"Commuting graph for {country} is BLOCKED — see audit report.")

    adj = row_normalize(flow)
    validate(adj, country)

    # Dense version
    df = adj_to_df(adj)
    out_path = out_dir / "adj_commuting.csv"
    df.to_csv(out_path, index=False)
    print(f"  Wrote: {out_path}")

    # Sparse top-k variants
    for k in (top_k_variants or []):
        adj_k = apply_top_k(adj, k)
        off = (adj_k > 0).sum(axis=1) - (np.diag(adj_k) > 0).astype(int)
        assert np.allclose(adj_k.sum(axis=1), 1.0, atol=1e-4), f"top{k} row sums"
        df_k = adj_to_df(adj_k)
        out_k = out_dir / f"adj_commuting_top{k}.csv"
        df_k.to_csv(out_k, index=False)
        print(f"  Wrote: {out_k}  (k={k}, density={float((adj_k>0).sum()-(adj_k.shape[0]))/(adj_k.shape[0]*(adj_k.shape[0]-1)):.3f}, avg_off_neighbors={off.mean():.1f})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", choices=["nl", "be", "all"], default="all",
                        help="PT is blocked (NUTS2021/2024 mismatch + inter-zone-only data)")
    parser.add_argument("--top-k", type=int, nargs="*", default=[5, 8],
                        metavar="K", help="Generate sparse top-K variants (default: 5 8)")
    args = parser.parse_args()
    targets = ["nl", "be"] if args.country == "all" else [args.country]
    for c in targets:
        build_country(c, top_k_variants=args.top_k)
    print("\nDone.")


if __name__ == "__main__":
    main()
