"""Construct and validate the first observable HERALD economic graph.

Outputs:
- bipartite territory-sector edges for each complete country-year;
- top-k territory similarity projection based on nine-sector shares;
- null-model stability tests and long-run bootstrap edge frequencies.

This is an analytical graph. It does not train a GNN or modify forecasting.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
DEFAULT_OUT = BASE / "data/processed/economic_graph/g1_observable"
DEFAULT_REPORT = BASE / "reports/HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md"
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
TOP_K = 5
N_PERMUTATIONS = 199
N_BOOTSTRAPS = 199
SEED = 42


def cosine_similarity(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    normalized = np.divide(
        matrix,
        norms,
        out=np.zeros_like(matrix, dtype=float),
        where=norms > 0,
    )
    return normalized @ normalized.T


def upper_triangle(matrix: np.ndarray) -> np.ndarray:
    return matrix[np.triu_indices(matrix.shape[0], k=1)]


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) <= 1e-12 or np.std(b) <= 1e-12:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def top_k_edges(similarity: np.ndarray, region_ids: list[str], k: int = TOP_K) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    n = len(region_ids)
    for index, source in enumerate(region_ids):
        order = np.argsort(-similarity[index])
        neighbors = [candidate for candidate in order if candidate != index][: min(k, n - 1)]
        for candidate in neighbors:
            target = region_ids[candidate]
            edges.add(tuple(sorted((source, target))))
    return edges


def country_tensor(panel: pd.DataFrame, country: str) -> tuple[list[int], list[str], np.ndarray]:
    sub = panel[
        panel["country"].eq(country) & panel["mask_complete_sector_vector"].eq(1)
    ].copy()
    complete_years = [
        int(year)
        for year, year_sub in sub.groupby("observation_year")
        if year_sub["region_id"].nunique() == sub["region_id"].nunique()
    ]
    sub = sub[sub["observation_year"].isin(complete_years)]
    regions = sorted(sub["region_id"].astype(str).unique())
    tensor = np.empty((len(complete_years), len(regions), len(SECTORS)), dtype=float)
    for year_index, year in enumerate(complete_years):
        wide = (
            sub[sub["observation_year"].eq(year)]
            .pivot(index="region_id", columns="sector_a10", values="sector_share")
            .reindex(index=regions, columns=SECTORS)
        )
        if wide.isna().any().any():
            raise ValueError(f"{country} {year}: incomplete vector after eligibility filter")
        tensor[year_index] = wide.to_numpy(dtype=float)
    return complete_years, regions, tensor


def consecutive_stability(tensor: np.ndarray) -> tuple[float, list[float]]:
    graphs = [upper_triangle(cosine_similarity(snapshot)) for snapshot in tensor]
    values = [correlation(graphs[i - 1], graphs[i]) for i in range(1, len(graphs))]
    finite = [value for value in values if np.isfinite(value)]
    return (float(np.mean(finite)) if finite else np.nan), values


def leave_one_year_mean(pair_values: list[float], omitted_year_index: int) -> float:
    """Mean consecutive stability without bridging across an omitted year."""
    kept = [
        value
        for pair_index, value in enumerate(pair_values)
        if pair_index not in {omitted_year_index - 1, omitted_year_index}
        and np.isfinite(value)
    ]
    return float(np.mean(kept)) if kept else np.nan


def temporal_permutation(tensor: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    permuted = np.empty_like(tensor)
    for region in range(tensor.shape[1]):
        for sector in range(tensor.shape[2]):
            permuted[:, region, sector] = rng.permutation(tensor[:, region, sector])
    row_sums = permuted.sum(axis=2, keepdims=True)
    return np.divide(permuted, row_sums, out=np.zeros_like(permuted), where=row_sums > 0)


def territory_permutation(tensor: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    permuted = np.empty_like(tensor)
    for year in range(tensor.shape[0]):
        permuted[year] = tensor[year, rng.permutation(tensor.shape[1])]
    return permuted


def empirical_p(observed: float, null_values: list[float]) -> float:
    values = np.asarray([value for value in null_values if np.isfinite(value)])
    return float((1 + np.sum(values >= observed)) / (1 + len(values)))


def bh_fdr(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running = 1.0
    for reverse_rank in range(len(p) - 1, -1, -1):
        index = order[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, p[index] * len(p) / rank)
        adjusted[index] = running
    return adjusted.tolist()


def leave_one_year_direction(
    tensor: np.ndarray,
    temporal_nulls: list[np.ndarray],
    territory_nulls: list[np.ndarray],
) -> bool:
    _, observed_pairs = consecutive_stability(tensor)
    temporal_pairs = [consecutive_stability(null)[1] for null in temporal_nulls]
    territory_pairs = [consecutive_stability(null)[1] for null in territory_nulls]
    for omitted in range(tensor.shape[0]):
        observed = leave_one_year_mean(observed_pairs, omitted)
        if not np.isfinite(observed):
            continue
        temporal = [leave_one_year_mean(values, omitted) for values in temporal_pairs]
        territory = [leave_one_year_mean(values, omitted) for values in territory_pairs]
        if observed <= np.nanmedian(temporal) or observed <= np.nanmedian(territory):
            return False
    return True


def graph_integrity(edges: pd.DataFrame, regions: list[str]) -> dict[str, float | int]:
    adjacency = {region: set() for region in regions}
    for row in edges.itertuples(index=False):
        adjacency[str(row.source_region)].add(str(row.target_region))
        adjacency[str(row.target_region)].add(str(row.source_region))
    unseen = set(regions)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            node = stack.pop()
            neighbors = adjacency[node] & unseen
            unseen.difference_update(neighbors)
            stack.extend(neighbors)
    degrees = [len(adjacency[region]) for region in regions]
    possible = len(regions) * (len(regions) - 1) / 2
    return {
        "components": components,
        "isolated_nodes": int(sum(degree == 0 for degree in degrees)),
        "min_degree": int(min(degrees)),
        "max_degree": int(max(degrees)),
        "density": float(len(edges) / possible),
    }


def bootstrap_edge_frequency(
    tensor: np.ndarray,
    region_ids: list[str],
    rng: np.random.Generator,
) -> pd.DataFrame:
    counts: dict[tuple[str, str], int] = {}
    for _ in range(N_BOOTSTRAPS):
        sampled_years = rng.integers(0, tensor.shape[0], size=tensor.shape[0])
        mean_structure = tensor[sampled_years].mean(axis=0)
        similarity = cosine_similarity(mean_structure)
        for edge in top_k_edges(similarity, region_ids):
            counts[edge] = counts.get(edge, 0) + 1
    records = [
        {
            "source_region": edge[0],
            "target_region": edge[1],
            "bootstrap_frequency": count / N_BOOTSTRAPS,
            "promoted_stable_edge": int(count / N_BOOTSTRAPS >= 0.70),
        }
        for edge, count in counts.items()
    ]
    return pd.DataFrame(records).sort_values(
        ["promoted_stable_edge", "bootstrap_frequency", "source_region", "target_region"],
        ascending=[False, False, True, True],
    )


def build_graph_outputs(panel: pd.DataFrame, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    eligible = panel[panel["mask_complete_sector_vector"].eq(1)].copy()

    bipartite = eligible[
        [
            "country",
            "observation_year",
            "region_id",
            "region_name",
            "sector_a10",
            "sector_births",
            "sector_share",
            "source_label",
            "flag_target_concept",
            "meta_region_system",
        ]
    ].rename(columns={"sector_share": "edge_weight"})
    bipartite["territory_node"] = (
        bipartite["country"].astype(str) + ":" + bipartite["region_id"].astype(str)
    )
    bipartite["sector_node"] = "A10:" + bipartite["sector_a10"].astype(str)
    bipartite.to_csv(out_dir / "g1_bipartite_edges.csv", index=False)

    projected_records: list[dict] = []
    integrity_records: list[dict] = []
    validation_rows: list[dict] = []
    bootstrap_frames: list[pd.DataFrame] = []
    rng = np.random.default_rng(SEED)
    null_cache: dict[str, tuple[list[np.ndarray], list[np.ndarray]]] = {}

    for country in sorted(eligible["country"].unique()):
        years, regions, tensor = country_tensor(panel, country)
        for year_index, year in enumerate(years):
            similarity = cosine_similarity(tensor[year_index])
            for source, target in top_k_edges(similarity, regions):
                source_index = regions.index(source)
                target_index = regions.index(target)
                projected_records.append(
                    {
                        "country": country,
                        "observation_year": year,
                        "source_region": source,
                        "target_region": target,
                        "weight_cosine": float(similarity[source_index, target_index]),
                        "top_k": TOP_K,
                    }
                )
            year_edges = pd.DataFrame(
                [
                    row
                    for row in projected_records
                    if row["country"] == country and row["observation_year"] == year
                ]
            )
            integrity_records.append(
                {
                    "country": country,
                    "observation_year": year,
                    **graph_integrity(year_edges, regions),
                }
            )

        observed, yearly = consecutive_stability(tensor)
        temporal_tensors = [
            temporal_permutation(tensor, rng) for _ in range(N_PERMUTATIONS)
        ]
        territory_tensors = [
            territory_permutation(tensor, rng) for _ in range(N_PERMUTATIONS)
        ]
        null_cache[country] = (temporal_tensors, territory_tensors)
        temporal_values = [consecutive_stability(null)[0] for null in temporal_tensors]
        territory_values = [consecutive_stability(null)[0] for null in territory_tensors]
        validation_rows.append(
            {
                "country": country,
                "years": f"{years[0]}-{years[-1]}",
                "year_count": len(years),
                "regions": len(regions),
                "observed_stability": observed,
                "temporal_null_median": float(np.nanmedian(temporal_values)),
                "temporal_p": empirical_p(observed, temporal_values),
                "territory_null_median": float(np.nanmedian(territory_values)),
                "territory_p": empirical_p(observed, territory_values),
                "leave_one_year_direction_pass": leave_one_year_direction(
                    tensor, temporal_tensors, territory_tensors
                ),
                "min_yearly_stability": float(np.nanmin(yearly)),
                "max_yearly_stability": float(np.nanmax(yearly)),
            }
        )
        boot = bootstrap_edge_frequency(tensor, regions, rng)
        boot.insert(0, "country", country)
        bootstrap_frames.append(boot)

    projected = pd.DataFrame(projected_records).drop_duplicates(
        ["country", "observation_year", "source_region", "target_region"]
    )
    projected.to_csv(out_dir / "g1_territory_similarity_top5.csv", index=False)
    integrity = pd.DataFrame(integrity_records)
    integrity.to_csv(out_dir / "g1_graph_integrity.csv", index=False)
    bootstrap = pd.concat(bootstrap_frames, ignore_index=True)
    bootstrap.to_csv(out_dir / "g1_bootstrap_edge_stability.csv", index=False)

    validation = pd.DataFrame(validation_rows)
    p_values = validation[["temporal_p", "territory_p"]].to_numpy().ravel().tolist()
    q_values = bh_fdr(p_values)
    validation[["temporal_q", "territory_q"]] = np.asarray(q_values).reshape(
        len(validation), 2
    )
    stable_counts = (
        bootstrap.groupby("country")["promoted_stable_edge"].sum().to_dict()
    )
    validation["stable_edge_count"] = validation["country"].map(stable_counts).fillna(0).astype(int)
    max_components = integrity.groupby("country")["components"].max().to_dict()
    max_isolated = integrity.groupby("country")["isolated_nodes"].max().to_dict()
    validation["max_components"] = validation["country"].map(max_components).astype(int)
    validation["max_isolated_nodes"] = validation["country"].map(max_isolated).astype(int)
    validation["country_pass"] = (
        validation["temporal_q"].le(0.05)
        & validation["territory_q"].le(0.05)
        & validation["leave_one_year_direction_pass"]
        & validation["stable_edge_count"].gt(0)
        & validation["max_isolated_nodes"].eq(0)
    )
    validation.to_csv(out_dir / "g1_validation_by_country.csv", index=False)
    return {
        "validated_layer": "L3_territory_economic_structure_similarity",
        "bipartite_rows": int(len(bipartite)),
        "projected_rows": int(len(projected)),
        "validation": validation.to_dict(orient="records"),
        "countries_passing": int(validation["country_pass"].sum()),
        "required_countries": 2,
        "g1_status": "PASS" if validation["country_pass"].sum() >= 2 else "FAIL",
    }


def render_report(summary: dict) -> str:
    lines = [
        "# HERALD G1 Observable Economic Graph Audit",
        "",
        f"**Decision:** `{summary['g1_status']}`",
        f"**Validated layer:** `{summary['validated_layer']}`",
        "",
        "Graph construction uses only complete nine-sector vectors. Agriculture",
        "is excluded. Similarity is calculated independently inside each country.",
        "",
        "## Validation",
        "",
        "| Country | Years | Regions | Stability | Temporal q | Territory q | LOYO | Stable edges | Max components | Pass |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for row in summary["validation"]:
        lines.append(
            f"| {row['country']} | {row['years']} | {row['regions']} "
            f"| {row['observed_stability']:.4f} | {row['temporal_q']:.4f} "
            f"| {row['territory_q']:.4f} | {row['leave_one_year_direction_pass']} "
            f"| {row['stable_edge_count']} | {row['max_components']} "
            f"| {row['country_pass']} |"
        )
    lines += [
        "",
        f"Countries passing: {summary['countries_passing']}/{summary['required_countries']} required.",
        "",
        "## Scope",
        "",
        "- PASS validates this observable similarity construction as an analytical graph.",
        "- L1 sector-sector was tested separately and failed its common promotion gate.",
        "- L2 co-growth, L4 mobility and L5 geography remain unvalidated.",
        "- It does not validate causality, recommendation, GNN training or forecast gain.",
        "- Dashboard work remains deferred until L1, L2 and L3 pass their respective audits.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    panel = pd.read_csv(args.panel, dtype={"region_id": str})
    summary = build_graph_outputs(panel, args.out_dir)
    args.report.write_text(render_report(summary), encoding="utf-8")
    (args.out_dir / "g1_decision.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["g1_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
