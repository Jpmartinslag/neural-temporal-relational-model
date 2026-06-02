#!/usr/bin/env python3
"""Phase 4D — Build sector-similarity adjacency matrices.

Uses existing A10 sector distributions (a10_ze2020.csv) to compute
cosine similarity between zone pairs. No new data required.

Outputs adj_sector_similarity.csv in data/processed/phase4d/{country}/
Same format as adj_geo.csv: source_idx column + zone columns (0-indexed).

Usage:
    python3 data/external/build_phase4d_sector_similarity.py
    python3 data/external/build_phase4d_sector_similarity.py --country nl
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent.parent

SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


def cosine_similarity_matrix(X: np.ndarray) -> np.ndarray:
    """Row-wise cosine similarity. X shape: (N, S)."""
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms
    return X_norm @ X_norm.T


def build_sector_adj(country: str, threshold: float = 0.0, top_k: int = 0) -> dict:
    """Build sector-similarity adjacency for one country.

    threshold: minimum cosine similarity to retain an edge (0 = keep all).
    top_k: if > 0, keep only top-k neighbours per zone (plus self-loop).
           top_k overrides threshold when both are set.
    Returns dict with matrix, stats, zone_ids.
    """
    a10_path = BASE / f"data/processed/phase4/{country}/a10_ze2020.csv"
    df = pd.read_csv(a10_path)

    # Use last 5 years of data to average sector shares (more stable than single year)
    years = sorted(df["target_year"].unique())
    recent = years[-5:] if len(years) >= 5 else years
    sub = df[df["target_year"].isin(recent)].copy()

    # Pivot: zone × sector, average over recent years
    pivot = sub.groupby("ZE2020")[SECTORS].mean()
    zone_ids = pivot.index.tolist()
    N = len(zone_ids)

    X = pivot.values.astype(np.float32)

    # Replace NaN with 0 (suppressed sectors)
    X = np.nan_to_num(X, nan=0.0)

    # Cosine similarity
    sim = cosine_similarity_matrix(X)

    # Sparsify: top-k per zone or threshold
    if top_k > 0:
        # For each row: keep top_k off-diagonal, zero the rest
        for i in range(N):
            row = sim[i].copy()
            row[i] = -1  # temporarily exclude diagonal
            cutoff_idx = np.argsort(row)[:-(top_k)]  # indices to zero
            sim[i, cutoff_idx] = 0.0
    elif threshold > 0:
        sim[sim < threshold] = 0.0

    # Ensure diagonal is 1 (self-similarity, retained)
    np.fill_diagonal(sim, 1.0)

    # Row-normalize
    row_sums = sim.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    adj = (sim / row_sums).astype(np.float32)

    # Stats (excluding diagonal)
    mask = ~np.eye(N, dtype=bool)
    nonzero_off_diag = (adj[mask] > 0).sum()
    effective_neighbors = nonzero_off_diag / N
    raw_sim_offdiag = sim[mask]

    stats = {
        "country": country,
        "n_zones": N,
        "sectors_used": SECTORS,
        "years_averaged": recent,
        "threshold": threshold,
        "top_k": top_k,
        "effective_neighbors_mean": float(effective_neighbors),
        "density": float(nonzero_off_diag / (N * (N - 1))),
        "cosine_sim_mean": float(raw_sim_offdiag.mean()),
        "cosine_sim_min": float(raw_sim_offdiag.min()),
        "cosine_sim_max": float(raw_sim_offdiag.max()),
        "row_sum_min": float(adj.sum(axis=1).min()),
        "row_sum_max": float(adj.sum(axis=1).max()),
    }

    return {"adj": adj, "zone_ids": zone_ids, "stats": stats}


def adj_to_df(adj: np.ndarray) -> pd.DataFrame:
    N = adj.shape[0]
    df = pd.DataFrame(adj, columns=list(range(N)))
    df.insert(0, "source_idx", list(range(N)))
    return df


def validate(df: pd.DataFrame, country: str) -> None:
    mat = df.drop("source_idx", axis=1).values.astype(float)
    row_sums = mat.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-4), f"[{country}] Row sums not ~1: {row_sums.min():.4f}..{row_sums.max():.4f}"
    assert not np.isnan(mat).any(), f"[{country}] NaN in matrix"
    assert mat.min() >= 0, f"[{country}] Negative values"
    print(f"  [{country}] Validation OK — row sums {row_sums.min():.6f}..{row_sums.max():.6f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", choices=["nl", "be", "pt", "all"], default="all")
    parser.add_argument("--threshold", type=float, default=0.0,
                        help="Min cosine similarity to keep edge (0=keep all)")
    parser.add_argument("--top-k", type=int, default=0,
                        help="Keep only top-k neighbours per zone (0=keep all). Overrides --threshold.")
    args = parser.parse_args()
    targets = ["nl", "be", "pt"] if args.country == "all" else [args.country]

    label = f"top{args.top_k}" if args.top_k > 0 else (f"thr{args.threshold}" if args.threshold > 0 else "dense")
    print(f"Building sector-similarity adjacency ({label})")
    print(f"Sectors: {SECTORS}\n")

    for c in targets:
        result = build_sector_adj(c, threshold=args.threshold, top_k=args.top_k)
        adj = result["adj"]
        stats = result["stats"]

        out_dir = BASE / f"data/processed/phase4d/{c}"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"_top{args.top_k}" if args.top_k > 0 else ""
        out_path = out_dir / f"adj_sector_similarity{suffix}.csv"

        df = adj_to_df(adj)
        validate(df, c)
        df.to_csv(out_path, index=False)

        print(f"[{c.upper()}]")
        print(f"  Zones: {stats['n_zones']}")
        print(f"  Years averaged: {stats['years_averaged']}")
        print(f"  Effective neighbors (off-diag > 0): {stats['effective_neighbors_mean']:.1f}")
        print(f"  Density: {stats['density']:.3f}")
        print(f"  Cosine sim range (off-diag): {stats['cosine_sim_min']:.3f} .. {stats['cosine_sim_max']:.3f} (mean {stats['cosine_sim_mean']:.3f})")
        print(f"  Wrote: {out_path}")
        print()

        # Also find top-5 most similar pairs
        N = adj.shape[0]
        zone_ids = result["zone_ids"]
        sim_raw = cosine_similarity_matrix(
            np.nan_to_num(
                pd.read_csv(BASE / f"data/processed/phase4/{c}/a10_ze2020.csv")
                .groupby("ZE2020")[SECTORS].mean().values.astype(np.float32),
                nan=0.0
            )
        )
        pairs = []
        for i in range(N):
            for j in range(i + 1, N):
                pairs.append((sim_raw[i, j], zone_ids[i], zone_ids[j]))
        pairs.sort(reverse=True)
        print(f"  Top-5 most similar pairs:")
        for sim_val, zi, zj in pairs[:5]:
            print(f"    zone {zi} ↔ zone {zj}: cosine={sim_val:.4f}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
