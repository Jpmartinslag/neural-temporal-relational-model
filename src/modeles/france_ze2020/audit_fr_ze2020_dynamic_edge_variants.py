"""
HERALD -- audit France ZE2020 dynamic edge variants.

Audit-only script for HERALD_26. It summarizes edge distributions and pruning
coverage. It does not train a model and does not create recommendation or causal
claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_edge_variants import (
    PRUNED_STABLE_EDGES_OUT_PATH,
)
from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EXPANDING_EDGES_OUT_PATH,
)

CLAIM_STATUS = "dynamic_edge_variant_audit_exploratory_not_causal"
FORBIDDEN_OUTPUT_COLUMNS = {
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
}


def load_edges(path: Path) -> pd.DataFrame:
    edges = pd.read_csv(path)
    edges["decision_year"] = edges["decision_year"].astype(int)
    if "edge_age" in edges.columns:
        edges["edge_age"] = edges["edge_age"].astype(int)
    return edges


def summarize_edges(edges: pd.DataFrame, label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
    }
    missing = required.difference(edges.columns)
    if missing:
        raise ValueError(f"Edge table {label} missing required columns: {sorted(missing)}")

    out = edges.copy()
    out["abs_edge_weight"] = out["edge_weight"].astype(float).abs()
    out["abs_signal_strength"] = out["signal_strength"].astype(float).abs()
    out["edge_age"] = out["edge_age"].astype(int) if "edge_age" in out.columns else 0
    out["volatile_edge_flag"] = (
        (out["abs_signal_strength"] >= 0.7) & (out["stability_score"].astype(float) < 0.25)
    ).astype(int)

    type_year = (
        out.groupby(["decision_year", "edge_type"], as_index=False)
        .agg(
            edge_count=("edge_type", "size"),
            target_node_count=("target_node_id", "nunique"),
            source_node_count=("source_node_id", "nunique"),
            mean_abs_edge_weight=("abs_edge_weight", "mean"),
            mean_stability=("stability_score", "mean"),
            median_stability=("stability_score", "median"),
            mean_edge_age=("edge_age", "mean"),
            max_edge_age=("edge_age", "max"),
            volatile_edge_share=("volatile_edge_flag", "mean"),
        )
        .sort_values(["decision_year", "edge_type"])
        .reset_index(drop=True)
    )
    degree = (
        out.groupby(["decision_year", "target_node_id"], as_index=False)
        .agg(in_degree=("source_node_id", "count"))
        .groupby("decision_year", as_index=False)
        .agg(
            target_nodes_with_edges=("target_node_id", "count"),
            mean_in_degree=("in_degree", "mean"),
            median_in_degree=("in_degree", "median"),
            max_in_degree=("in_degree", "max"),
        )
        .sort_values("decision_year")
        .reset_index(drop=True)
    )

    for frame in [type_year, degree]:
        frame.insert(0, "edge_table", label)
        frame["claim_status"] = CLAIM_STATUS
    return type_year, degree


def compare_edge_tables(base_edges: pd.DataFrame, variant_edges: pd.DataFrame, variant_label: str) -> dict[str, object]:
    base_count = len(base_edges)
    variant_count = len(variant_edges)
    return {
        "claim_status": CLAIM_STATUS,
        "base_edge_count": int(base_count),
        "variant_edge_count": int(variant_count),
        "variant_label": variant_label,
        "retained_edge_share": float(variant_count / base_count) if base_count else 0.0,
        "base_years": sorted(int(y) for y in base_edges["decision_year"].unique()),
        "variant_years": sorted(int(y) for y in variant_edges["decision_year"].unique()) if variant_count else [],
        "base_edge_types": sorted(str(t) for t in base_edges["edge_type"].unique()),
        "variant_edge_types": sorted(str(t) for t in variant_edges["edge_type"].unique()) if variant_count else [],
    }


def run_audit(
    base_edges_path: Path = EXPANDING_EDGES_OUT_PATH,
    variant_edges_path: Path = PRUNED_STABLE_EDGES_OUT_PATH,
    variant_label: str = "pruned_stable",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    base_edges = load_edges(base_edges_path)
    variant_edges = load_edges(variant_edges_path)
    base_type_year, base_degree = summarize_edges(base_edges, "expanding_memory")
    variant_type_year, variant_degree = summarize_edges(variant_edges, variant_label)
    type_year = pd.concat([base_type_year, variant_type_year], ignore_index=True)
    degree = pd.concat([base_degree, variant_degree], ignore_index=True)
    manifest = compare_edge_tables(base_edges, variant_edges, variant_label)
    return type_year, degree, manifest


def _assert_no_forbidden_columns(frames: list[pd.DataFrame]) -> None:
    for frame in frames:
        lowered = {col.lower() for col in frame.columns}
        forbidden = FORBIDDEN_OUTPUT_COLUMNS.intersection(lowered)
        if forbidden:
            raise ValueError(f"Forbidden output columns: {sorted(forbidden)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit HERALD France ZE2020 dynamic edge variants.")
    parser.add_argument("--base-edges", type=Path, default=EXPANDING_EDGES_OUT_PATH)
    parser.add_argument("--variant-edges", type=Path, default=PRUNED_STABLE_EDGES_OUT_PATH)
    parser.add_argument("--variant-label", default="pruned_stable")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    type_year, degree, manifest = run_audit(
        base_edges_path=args.base_edges,
        variant_edges_path=args.variant_edges,
        variant_label=args.variant_label,
    )
    _assert_no_forbidden_columns([type_year, degree])

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        type_year.to_csv(args.output_dir / "fr_ze2020_dynamic_edge_variant_type_year_audit.csv", index=False)
        degree.to_csv(args.output_dir / "fr_ze2020_dynamic_edge_variant_degree_audit.csv", index=False)
        (args.output_dir / "fr_ze2020_dynamic_edge_variant_audit_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
