from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
NODES_IN = ROOT / "data" / "processed" / "graph_nodes_ze2020_v0.csv"
EDGES_IN = ROOT / "data" / "processed" / "graph_edges_ze2020_v0.csv"
NODES_OUT = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"
EDGES_OUT = ROOT / "data" / "processed" / "graph_edges_ze2020_core_v0.csv"
EXCLUDED_OUT = ROOT / "data" / "processed" / "graph_excluded_ze2020_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "graph_ze2020_core_quality_v0.json"


def main() -> None:
    nodes = pd.read_csv(NODES_IN, dtype={"ze2020": str})
    edges = pd.read_csv(EDGES_IN, dtype={"source_ze2020": str, "target_ze2020": str})

    adj = defaultdict(set)
    for s, t in edges[["source_ze2020", "target_ze2020"]].itertuples(index=False):
        adj[s].add(t)
        adj[t].add(s)

    seen = set()
    components = []
    for node in nodes["ze2020"]:
        if node in seen:
            continue
        q = deque([node])
        seen.add(node)
        comp = []
        while q:
            x = q.popleft()
            comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        components.append(sorted(comp))

    components = sorted(components, key=len, reverse=True)
    core_nodes = set(components[0])
    excluded_components = components[1:]
    excluded_nodes = set().union(*excluded_components) if excluded_components else set()

    nodes_core = nodes[nodes["ze2020"].isin(core_nodes)].copy()
    edges_core = edges[
        edges["source_ze2020"].isin(core_nodes) & edges["target_ze2020"].isin(core_nodes)
    ].copy()
    excluded = nodes[nodes["ze2020"].isin(excluded_nodes)].copy()
    excluded["exclusion_reason"] = "non_hexagonal_or_insular_component_for_core_v0"

    nodes_core.to_csv(NODES_OUT, index=False)
    edges_core.to_csv(EDGES_OUT, index=False)
    excluded.to_csv(EXCLUDED_OUT, index=False)

    quality = {
        "rule": "Keep only the largest connected component of the ZE2020 geographic graph for core_v0.",
        "core_node_count": int(len(nodes_core)),
        "core_directed_edge_count": int(len(edges_core)),
        "excluded_node_count": int(len(excluded)),
        "excluded_components_count": int(len(excluded_components)),
        "excluded_components_sizes": [len(c) for c in excluded_components],
        "excluded_nodes_sample": excluded[["ze2020", "libze2020"]].head(20).to_dict("records"),
        "notes": [
            "core_v0 is restricted to continental France as the largest connected component.",
            "Corsica and overseas components are excluded from the MVP graph to reduce territorial anomalies in early-stage modeling.",
        ],
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
