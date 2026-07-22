#!/usr/bin/env python3
"""Assign official commuting snapshots to decision years under strict availability."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_commuting_edges import (
    EDGES_OUT_PATH as SOURCE_EDGES_PATH,
)

OUT_DIR = ROOT / "data/processed/france_ze2020"
STRICT_EDGES_OUT_PATH = OUT_DIR / "fr_ze2020_commuting_strict_ex_ante_edges.csv.gz"
STRICT_SUMMARY_OUT_PATH = OUT_DIR / "fr_ze2020_commuting_strict_ex_ante_summary.json"
DECISION_YEARS = tuple(range(2012, 2026))
CLAIM_STATUS = "strict_ex_ante_commuting_relation_not_causal"


def load_source_edges(path: Path = SOURCE_EDGES_PATH) -> pd.DataFrame:
    edges = pd.read_csv(
        path,
        dtype={"source_ze2020": str, "target_ze2020": str},
    )
    edges["source_ze2020"] = edges["source_ze2020"].str.zfill(4)
    edges["target_ze2020"] = edges["target_ze2020"].str.zfill(4)
    return edges


def build_strict_ex_ante_edges(
    source_edges: pd.DataFrame | None = None,
    decision_years: tuple[int, ...] = DECISION_YEARS,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if source_edges is None:
        source_edges = load_source_edges()
    required = {
        "source_ze2020",
        "target_ze2020",
        "observation_year",
        "commuter_count",
        "origin_worker_share",
        "origin_in_scope_share",
        "origin_interze_share",
        "is_self_loop",
        "aggregated_flow_below_200_caution",
        "strict_ex_ante_valid_from_year",
        "strict_ex_ante_valid_through_year",
        "source_release_date",
    }
    missing = required.difference(source_edges.columns)
    if missing:
        raise ValueError(f"Commuting source missing columns: {sorted(missing)}")

    source_edges = source_edges.copy()
    source_edges["source_release_date"] = pd.to_datetime(
        source_edges["source_release_date"], errors="raise"
    )
    frames = []
    assignments = []
    unavailable = []
    for year in decision_years:
        eligible = source_edges[
            (source_edges["strict_ex_ante_valid_from_year"] <= year)
            & (source_edges["strict_ex_ante_valid_through_year"] >= year)
        ]
        snapshots = sorted(eligible["observation_year"].unique())
        if not snapshots:
            unavailable.append(int(year))
            continue
        if len(snapshots) != 1:
            raise ValueError(f"Expected one strict snapshot for {year}, found {snapshots}")
        snapshot_year = int(snapshots[0])
        current = eligible[eligible["is_self_loop"] == 0].copy()
        if current.empty:
            raise ValueError(f"No cross-ZE commuting edges for {year}")
        if not (current["source_release_date"].dt.year < year).all():
            raise ValueError(f"Release-time leakage in strict commuting year {year}")
        current.insert(0, "decision_year", int(year))
        current.insert(
            0,
            "edge_id",
            [
                f"commuting_strict__{year}__{source}__{target}"
                for source, target in zip(
                    current["source_ze2020"], current["target_ze2020"]
                )
            ],
        )
        current["edge_type"] = "ze_commuting_strict_ex_ante"
        current["edge_weight"] = current["origin_interze_share"].astype(float)
        current["snapshot_age_years"] = year - snapshot_year
        current["availability_mode"] = "strict_ex_ante_release_aware"
        current["claim_status"] = CLAIM_STATUS
        frames.append(current)
        assignments.append(
            {
                "decision_year": int(year),
                "snapshot_observation_year": snapshot_year,
                "source_release_date": current["source_release_date"]
                .dt.strftime("%Y-%m-%d")
                .iloc[0],
                "edge_count": int(len(current)),
            }
        )

    if not frames:
        raise ValueError("No strict ex-ante commuting edges could be assigned")
    combined = pd.concat(frames, ignore_index=True)
    combined["source_release_date"] = combined["source_release_date"].dt.strftime("%Y-%m-%d")
    combined = combined.sort_values(
        ["decision_year", "source_ze2020", "target_ze2020"]
    ).reset_index(drop=True)
    if combined["edge_id"].duplicated().any():
        raise ValueError("Duplicate strict commuting edge_id")
    numeric = combined.select_dtypes(include=[np.number]).to_numpy(float)
    if not np.isfinite(numeric).all():
        raise ValueError("Non-finite strict commuting edge value")
    cross_sums = combined.groupby(["decision_year", "source_ze2020"])[
        "edge_weight"
    ].sum()
    if not np.allclose(cross_sums.to_numpy(float), 1.0, atol=1e-9):
        raise ValueError("Strict commuting outgoing weights do not sum to one")

    summary = {
        "artifact": "fr_ze2020_commuting_strict_ex_ante_edges",
        "status": "REGENERABLE_MODEL_INPUT_CANDIDATE",
        "decision_year_min": min(decision_years),
        "decision_year_max": max(decision_years),
        "available_decision_years": sorted(combined["decision_year"].unique().tolist()),
        "unavailable_decision_years": unavailable,
        "edge_count": int(len(combined)),
        "source_zone_count": int(combined["source_ze2020"].nunique()),
        "target_zone_count": int(combined["target_ze2020"].nunique()),
        "snapshot_assignments": assignments,
        "method": (
            "Latest uniquely valid official commuting snapshot under release-aware "
            "strict ex-ante intervals; cross-ZE directed edges only."
        ),
        "forbidden_claim": (
            "Not yet validated as a useful model relation; no causal, neural-gain, "
            "automatic-recommendation, or policy claim."
        ),
    }
    return combined, summary


def write_outputs(edges: pd.DataFrame, summary: dict[str, object]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    edges.to_csv(
        STRICT_EDGES_OUT_PATH,
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    STRICT_SUMMARY_OUT_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n"
    )


def main() -> None:
    edges, summary = build_strict_ex_ante_edges()
    write_outputs(edges, summary)
    print(f"wrote {len(edges):,} strict edges to {STRICT_EDGES_OUT_PATH}")
    print(f"wrote strict summary to {STRICT_SUMMARY_OUT_PATH}")


if __name__ == "__main__":
    main()
