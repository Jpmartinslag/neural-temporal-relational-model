"""Build and validate communities on the causal G1-L2 co-growth layer.

Each country-year territory graph is rebuilt from the underlying sector-growth
series. Positive cross-territory correlations are averaged across eligible
sectors, then sparsified with a fixed symmetric top-k rule before Louvain.

Null graphs are also rebuilt from temporally or territorially permuted growth
series. A node relabeling is deliberately not used because graph modularity is
invariant to labels and therefore cannot serve as a territory null.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_mutual_info_score

BASE = Path(__file__).resolve().parents[3]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.data.european_panel.build_g1_l2_cogrowth import (
    COVID_YEAR,
    WINDOW,
    bh_fdr,
    build_growth_matrix,
    eligible_sectors,
    empirical_p,
    eval_years_for_country,
    pairwise_corr,
    permute_growth_temporal,
    permute_growth_territory,
    window_matrix,
)


DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
DEFAULT_OUT = BASE / "data/processed/economic_graph/g1_communities"
DEFAULT_REPORT = BASE / "reports/HERALD_G1_COMMUNITIES_AUDIT.md"

SEED = 42
TOP_K = 5
N_LOUVAIN_RESTARTS = 1
N_PERMUTATIONS = 99


def louvain_best(
    graph: nx.Graph,
    seed: int = SEED,
    restarts: int = N_LOUVAIN_RESTARTS,
) -> tuple[list[set[str]] | None, float]:
    """Return the highest-modularity Louvain partition over equal restarts."""
    if graph.number_of_nodes() < 2 or graph.number_of_edges() == 0:
        return None, float("nan")
    best_partition = None
    best_modularity = float("-inf")
    for restart in range(restarts):
        partition = nx.algorithms.community.louvain_communities(
            graph,
            weight="weight",
            seed=seed + restart,
        )
        modularity = nx.algorithms.community.quality.modularity(
            graph,
            partition,
            weight="weight",
        )
        if modularity > best_modularity:
            best_partition = partition
            best_modularity = float(modularity)
    return best_partition, best_modularity


def symmetric_top_k(
    weights: np.ndarray,
    region_ids: list[str],
    top_k: int = TOP_K,
) -> nx.Graph:
    """Create a sparse undirected union-of-top-k graph from positive weights."""
    graph = nx.Graph()
    graph.add_nodes_from(region_ids)
    n_regions = len(region_ids)
    selected: set[tuple[int, int]] = set()
    for source in range(n_regions):
        candidates = [
            target
            for target in range(n_regions)
            if target != source
            and np.isfinite(weights[source, target])
            and weights[source, target] > 0
        ]
        candidates.sort(key=lambda target: (-weights[source, target], target))
        for target in candidates[: min(top_k, len(candidates))]:
            selected.add(tuple(sorted((source, target))))
    for source, target in sorted(selected):
        graph.add_edge(
            region_ids[source],
            region_ids[target],
            weight=float(weights[source, target]),
        )
    return graph


def aggregate_cogrowth_graph(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sectors: list[str],
    eval_year: int,
    exclude_years: frozenset[int] = frozenset(),
    top_k: int = TOP_K,
) -> nx.Graph:
    """Aggregate positive L2 correlations across sectors and sparsify."""
    reference_regions = sector_data[sectors[0]][0]
    n_regions = len(reference_regions)
    weight_sum = np.zeros((n_regions, n_regions), dtype=float)
    weight_count = np.zeros((n_regions, n_regions), dtype=int)

    for sector in sectors:
        region_ids, growth_years, matrix = sector_data[sector]
        if region_ids != reference_regions:
            raise ValueError(f"{sector}: inconsistent territory ordering")
        window = window_matrix(
            growth_years,
            matrix,
            eval_year,
            WINDOW,
            exclude_years,
        )
        correlations = pairwise_corr(window)
        valid = np.isfinite(correlations) & (correlations > 0)
        np.fill_diagonal(valid, False)
        weight_sum[valid] += correlations[valid]
        weight_count[valid] += 1

    mean_weights = np.divide(
        weight_sum,
        weight_count,
        out=np.full_like(weight_sum, np.nan),
        where=weight_count > 0,
    )
    return symmetric_top_k(mean_weights, reference_regions, top_k)


def partition_labels(
    partition: list[set[str]],
    nodes: list[str],
) -> np.ndarray:
    labels = np.full(len(nodes), -1, dtype=int)
    node_index = {node: index for index, node in enumerate(nodes)}
    for community_id, members in enumerate(partition):
        for node in members:
            if node in node_index:
                labels[node_index[node]] = community_id
    return labels


def partition_ami(
    previous: list[set[str]],
    current: list[set[str]],
    nodes: list[str],
) -> float:
    previous_labels = partition_labels(previous, nodes)
    current_labels = partition_labels(current, nodes)
    valid = (previous_labels >= 0) & (current_labels >= 0)
    if valid.sum() < 2:
        return float("nan")
    return float(
        adjusted_mutual_info_score(
            previous_labels[valid],
            current_labels[valid],
        )
    )


def analyse_sequence(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sectors: list[str],
    eval_years: list[int],
    exclude_years: frozenset[int],
    seed: int,
) -> tuple[list[dict], list[dict]]:
    """Build yearly sparse graphs, partitions and consecutive dynamics."""
    yearly: list[dict] = []
    for year_index, eval_year in enumerate(eval_years):
        graph = aggregate_cogrowth_graph(
            sector_data,
            sectors,
            eval_year,
            exclude_years,
        )
        partition, modularity = louvain_best(
            graph,
            seed=seed + 1000 * year_index,
        )
        if partition is None:
            continue
        yearly.append(
            {
                "eval_year": int(eval_year),
                "graph": graph,
                "partition": partition,
                "modularity": modularity,
                "n_nodes": graph.number_of_nodes(),
                "n_edges": graph.number_of_edges(),
                "n_communities": len(partition),
                "community_sizes": sorted(
                    [len(community) for community in partition],
                    reverse=True,
                ),
            }
        )

    dynamics: list[dict] = []
    for previous, current in zip(yearly, yearly[1:]):
        if current["eval_year"] != previous["eval_year"] + 1:
            continue
        previous_edges = {
            tuple(sorted(edge)) for edge in previous["graph"].edges()
        }
        current_edges = {
            tuple(sorted(edge)) for edge in current["graph"].edges()
        }
        nodes = sorted(
            set(previous["graph"].nodes()) | set(current["graph"].nodes())
        )
        dynamics.append(
            {
                "eval_year_from": previous["eval_year"],
                "eval_year_to": current["eval_year"],
                "n_appeared": len(current_edges - previous_edges),
                "n_disappeared": len(previous_edges - current_edges),
                "n_stable_edges": len(previous_edges & current_edges),
                "community_ami": partition_ami(
                    previous["partition"],
                    current["partition"],
                    nodes,
                ),
                "modularity_from": previous["modularity"],
                "modularity_to": current["modularity"],
                "modularity_delta": (
                    current["modularity"] - previous["modularity"]
                ),
            }
        )
    return yearly, dynamics


def sequence_statistics(
    yearly: list[dict],
    dynamics: list[dict],
) -> tuple[float, float]:
    modularities = [
        row["modularity"] for row in yearly if np.isfinite(row["modularity"])
    ]
    amis = [
        row["community_ami"]
        for row in dynamics
        if np.isfinite(row["community_ami"])
    ]
    return (
        float(np.mean(modularities)) if modularities else float("nan"),
        float(np.mean(amis)) if amis else float("nan"),
    )


def validate_country(
    panel: pd.DataFrame,
    country: str,
    rng: np.random.Generator,
    exclude_years: frozenset[int] = frozenset(),
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    sectors = eligible_sectors(panel, country)
    sector_data = {
        sector: build_growth_matrix(panel, country, sector)
        for sector in sectors
    }
    eval_years = eval_years_for_country(sector_data, sectors, WINDOW)
    yearly, dynamics = analyse_sequence(
        sector_data,
        sectors,
        eval_years,
        exclude_years,
        seed=SEED,
    )
    observed_modularity, observed_ami = sequence_statistics(yearly, dynamics)

    temporal_modularity: list[float] = []
    temporal_ami: list[float] = []
    territory_modularity: list[float] = []
    territory_ami: list[float] = []
    for permutation_index in range(N_PERMUTATIONS):
        temporal_data = permute_growth_temporal(sector_data, rng)
        territory_data = permute_growth_territory(sector_data, rng)
        for permuted_data, modularity_store, ami_store, offset in (
            (temporal_data, temporal_modularity, temporal_ami, 100000),
            (territory_data, territory_modularity, territory_ami, 200000),
        ):
            null_yearly, null_dynamics = analyse_sequence(
                permuted_data,
                sectors,
                eval_years,
                exclude_years,
                seed=SEED + offset + 10000 * permutation_index,
            )
            null_modularity, null_ami = sequence_statistics(
                null_yearly,
                null_dynamics,
            )
            modularity_store.append(null_modularity)
            ami_store.append(null_ami)

    membership_rows: list[dict] = []
    for row in yearly:
        for community_id, community in enumerate(row["partition"]):
            for region_id in sorted(community):
                membership_rows.append(
                    {
                        "country": country,
                        "eval_year": row["eval_year"],
                        "exclude_covid": bool(exclude_years),
                        "community_id": community_id,
                        "region_id": region_id,
                        "community_size": len(community),
                        "n_graph_edges": row["n_edges"],
                        "modularity": row["modularity"],
                    }
                )
    dynamics_rows = [
        {
            "country": country,
            "exclude_covid": bool(exclude_years),
            **row,
        }
        for row in dynamics
    ]
    summary = {
        "country": country,
        "exclude_covid": bool(exclude_years),
        "excluded_window_years": sorted(exclude_years),
        "sectors": sectors,
        "eval_years": [row["eval_year"] for row in yearly],
        "n_eval_years": len(yearly),
        "mean_nodes": float(np.mean([row["n_nodes"] for row in yearly])),
        "mean_edges": float(np.mean([row["n_edges"] for row in yearly])),
        "mean_communities": float(
            np.mean([row["n_communities"] for row in yearly])
        ),
        "mean_modularity": observed_modularity,
        "mean_ami_consecutive": observed_ami,
        "temporal_null_median_modularity": float(
            np.nanmedian(temporal_modularity)
        ),
        "territory_null_median_modularity": float(
            np.nanmedian(territory_modularity)
        ),
        "temporal_null_median_ami": float(np.nanmedian(temporal_ami)),
        "territory_null_median_ami": float(np.nanmedian(territory_ami)),
        "modularity_temporal_p": empirical_p(
            observed_modularity,
            temporal_modularity,
        ),
        "modularity_territory_p": empirical_p(
            observed_modularity,
            territory_modularity,
        ),
        "ami_temporal_p": empirical_p(observed_ami, temporal_ami),
        "ami_territory_p": empirical_p(observed_ami, territory_ami),
        "n_dynamics_pairs": len(dynamics),
    }
    return (
        pd.DataFrame(membership_rows),
        pd.DataFrame(dynamics_rows),
        summary,
    )


def add_fdr_and_gate(rows: list[dict], pass_column: str) -> list[dict]:
    """Apply BH/FDR across countries, metrics and null families."""
    p_columns = [
        "modularity_temporal_p",
        "modularity_territory_p",
        "ami_temporal_p",
        "ami_territory_p",
    ]
    p_values = [
        row[column]
        for row in rows
        for column in p_columns
    ]
    q_values = iter(bh_fdr(p_values))
    for row in rows:
        for column in p_columns:
            row[column.replace("_p", "_q")] = next(q_values)
        required_q = [
            row[column.replace("_p", "_q")] for column in p_columns
        ]
        row[pass_column] = bool(
            np.isfinite(row["mean_modularity"])
            and row["mean_modularity"] > 0
            and np.isfinite(row["mean_ami_consecutive"])
            and row["mean_ami_consecutive"] > 0
            and all(value <= 0.05 for value in required_q)
        )
    return rows


def build(panel: pd.DataFrame, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    main_rows: list[dict] = []
    covid_rows: list[dict] = []
    memberships: list[pd.DataFrame] = []
    dynamics: list[pd.DataFrame] = []

    for country_index, country in enumerate(sorted(panel["country"].unique())):
        main_rng = np.random.default_rng(SEED + 1000 * country_index)
        covid_rng = np.random.default_rng(SEED + 50000 + 1000 * country_index)
        membership, country_dynamics, summary = validate_country(
            panel,
            country,
            main_rng,
        )
        covid_membership, covid_dynamics, covid_summary = validate_country(
            panel,
            country,
            covid_rng,
            exclude_years=frozenset({COVID_YEAR}),
        )
        memberships.extend([membership, covid_membership])
        dynamics.extend([country_dynamics, covid_dynamics])
        main_rows.append(summary)
        covid_rows.append(covid_summary)

    add_fdr_and_gate(main_rows, "country_pass")
    add_fdr_and_gate(covid_rows, "country_pass_covid")

    membership_output = pd.concat(memberships, ignore_index=True)
    dynamics_output = pd.concat(dynamics, ignore_index=True)
    membership_output.to_csv(
        out_dir / "g1_communities_membership.csv",
        index=False,
    )
    dynamics_output.to_csv(
        out_dir / "g1_communities_dynamics.csv",
        index=False,
    )

    countries_passing = sum(row["country_pass"] for row in main_rows)
    covid_passing = sum(row["country_pass_covid"] for row in covid_rows)
    required = 2
    result = {
        "layer": "G1_L2_sparse_community_baseline",
        "method": "Louvain on symmetric top-k positive L2 co-growth graph",
        "top_k": TOP_K,
        "seed": SEED,
        "n_louvain_restarts_observed_and_null": N_LOUVAIN_RESTARTS,
        "n_permutations": N_PERMUTATIONS,
        "countries": main_rows,
        "countries_covid_sensitivity": covid_rows,
        "countries_passing": int(countries_passing),
        "countries_passing_covid": int(covid_passing),
        "required_countries": required,
        "community_status": (
            "PASS" if countries_passing >= required else "FAIL"
        ),
        "covid_status": (
            "COVID_ROBUST" if covid_passing >= required else "COVID_SENSITIVE"
        ),
        "scope": (
            "Statistical co-growth communities only. No causal, productive-"
            "district, forecasting or recommendation interpretation."
        ),
    }
    (out_dir / "g1_communities_decision.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def year_list(values: list[int]) -> str:
    return ",".join(str(value) for value in values)


def render_report(summary: dict) -> str:
    lines = [
        "# HERALD G1 Community Detection Audit",
        "",
        f"**Decision:** `{summary['community_status']}`",
        f"**COVID sensitivity:** `{summary['covid_status']}`",
        "",
        "Communities are calculated on a symmetric top-k=5 L2 graph rebuilt",
        "from causal sector-growth windows. Observed and null graphs use the",
        "same Louvain restart budget. Nulls are reconstructed from permuted",
        "growth series; node relabeling is not used.",
        "",
        "## Main validation",
        "",
        "| Country | Years | Nodes | Edges | Communities | Modularity | AMI | Mod temp q | Mod terr q | AMI temp q | AMI terr q | Pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary["countries"]:
        lines.append(
            f"| {row['country']} | {year_list(row['eval_years'])} "
            f"| {row['mean_nodes']:.1f} | {row['mean_edges']:.1f} "
            f"| {row['mean_communities']:.2f} "
            f"| {row['mean_modularity']:.4f} "
            f"| {row['mean_ami_consecutive']:.4f} "
            f"| {row['modularity_temporal_q']:.4f} "
            f"| {row['modularity_territory_q']:.4f} "
            f"| {row['ami_temporal_q']:.4f} "
            f"| {row['ami_territory_q']:.4f} "
            f"| {row['country_pass']} |"
        )
    lines += [
        "",
        "## COVID sensitivity",
        "",
        "The observation year 2020 is removed from every rolling window, while",
        "evaluation year 2020 remains because its window uses only pre-COVID data.",
        "",
        "| Country | Years | Modularity | AMI | Pass |",
        "|---|---|---:|---:|---|",
    ]
    for row in summary["countries_covid_sensitivity"]:
        lines.append(
            f"| {row['country']} | {year_list(row['eval_years'])} "
            f"| {row['mean_modularity']:.4f} "
            f"| {row['mean_ami_consecutive']:.4f} "
            f"| {row['country_pass_covid']} |"
        )
    lines += [
        "",
        "## Scope",
        "",
        "- PASS requires modularity and consecutive-year AMI to exceed both null families after BH/FDR.",
        "- Communities are statistical co-growth clusters, not production districts.",
        "- Positive top-k sparsification is fixed before evaluation and applied identically to nulls.",
        "- No GNN, forecast improvement, causal relation or recommendation is validated here.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    panel = pd.read_csv(args.panel, dtype={"region_id": str}, low_memory=False)
    summary = build(panel, args.out_dir)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["community_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
