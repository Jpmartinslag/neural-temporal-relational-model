#!/usr/bin/env python3
"""Build a low-cost graphify context graph for the project.

This uses graphify's deterministic code extraction plus lightweight local file
nodes for reports/metadata. It deliberately avoids semantic LLM extraction and
excludes raw/interim/processed datasets through `.graphifyignore`.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import networkx as nx

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build
from graphify.cluster import cluster, score_all
from graphify.detect import detect
from graphify.export import to_html, to_json
from graphify.extract import extract
from graphify.report import generate


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out"


def make_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def read_title(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return path.name
    for line in lines[:80]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.name
    return path.name


def file_group(path: str) -> str:
    try:
        path_obj = Path(path)
        if path_obj.is_absolute():
            path = str(path_obj.relative_to(ROOT))
    except ValueError:
        pass
    p = Path(path)
    if path.startswith("src/data/"):
        name = p.name
        if name.startswith("build_"):
            return "pipeline_builders"
        if name.startswith("integrate_"):
            return "pipeline_integrations"
        if name.startswith("extract_"):
            return "raw_extractors"
        if name.startswith("search_") or name.startswith("audit_") or name.startswith("organize_"):
            return "audit_and_organization"
        return "pipeline_utilities"
    if path.startswith("reports/"):
        name = p.name.lower()
        if "bpe" in name:
            return "bpe_reports"
        if "graph" in name:
            return "graph_reports"
        if "temporal" in name or "baseline" in name or "target" in name:
            return "model_readiness_reports"
        return "project_reports"
    if path.startswith("metadata/"):
        return "metadata_registry"
    return p.parts[0] if p.parts else "root"


def lightweight_file_extraction(detection: dict) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()

    def add_node(node: dict) -> None:
        if node["id"] in seen:
            return
        seen.add(node["id"])
        nodes.append(node)

    for group in [
        "pipeline_builders",
        "pipeline_integrations",
        "raw_extractors",
        "audit_and_organization",
        "pipeline_utilities",
        "bpe_reports",
        "graph_reports",
        "model_readiness_reports",
        "project_reports",
        "metadata_registry",
    ]:
        add_node(
            {
                "id": f"group_{group}",
                "label": group,
                "file_type": "rationale",
                "source_file": "",
            }
        )

    files_by_kind = detection.get("files", {})
    for kind in ["document", "image"]:
        for path_str in files_by_kind.get(kind, []):
            path = ROOT / path_str
            group = file_group(path_str)
            node_id = f"file_{make_id(path_str)}"
            add_node(
                {
                    "id": node_id,
                    "label": read_title(path) if kind == "document" else path.name,
                    "file_type": kind,
                    "source_file": path_str,
                }
            )
            edges.append(
                {
                    "source": f"group_{group}",
                    "target": node_id,
                    "relation": "contains_file",
                    "confidence": "EXTRACTED",
                    "source_file": path_str,
                    "weight": 1.0,
                }
            )

    return {"nodes": nodes, "edges": edges, "input_tokens": 0, "output_tokens": 0}


def label_communities(G: nx.Graph, communities: dict[int, list[str]]) -> dict[int, str]:
    labels: dict[int, str] = {}
    for cid, node_ids in communities.items():
        group_labels = [
            G.nodes[n].get("label", n)
            for n in node_ids
            if str(n).startswith("group_")
        ]
        if group_labels:
            labels[cid] = group_labels[0]
            continue
        source_dirs = Counter()
        for n in node_ids:
            src = G.nodes[n].get("source_file", "")
            if src:
                source_dirs[file_group(src)] += 1
        if source_dirs:
            labels[cid] = source_dirs.most_common(1)[0][0]
        else:
            labels[cid] = f"Community {cid}"
    return labels


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    detection = detect(ROOT)
    (OUT / ".graphify_detect.json").write_text(json.dumps(detection, indent=2), encoding="utf-8")

    code_files = [Path(path) for path in detection.get("files", {}).get("code", [])]
    ast = extract(code_files) if code_files else {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}
    for node in ast.get("nodes", []):
        src = node.get("source_file")
        if src:
            try:
                node["source_file"] = str(Path(src).relative_to(ROOT))
            except ValueError:
                pass
    for edge in ast.get("edges", []):
        src = edge.get("source_file")
        if src:
            try:
                edge["source_file"] = str(Path(src).relative_to(ROOT))
            except ValueError:
                pass
    (OUT / ".graphify_ast.json").write_text(json.dumps(ast, indent=2), encoding="utf-8")

    file_context = lightweight_file_extraction(detection)
    G = build([ast, file_context], directed=True)
    communities = cluster(G)
    cohesion = score_all(G, communities)
    labels = label_communities(G, communities)
    gods = god_nodes(G, top_n=15)
    surprises = surprising_connections(G, communities, top_n=10)
    questions = suggest_questions(G, communities, labels, top_n=10)

    token_cost = {
        "input": int(ast.get("input_tokens", 0)),
        "output": int(ast.get("output_tokens", 0)),
    }
    report = generate(
        G,
        communities,
        cohesion,
        labels,
        gods,
        surprises,
        detection,
        token_cost,
        ".",
        suggested_questions=questions,
    )
    (OUT / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    to_json(G, communities, str(OUT / "graph.json"))
    to_html(G, communities, str(OUT / "graph.html"), community_labels=labels)

    summary = {
        "output_dir": str(OUT),
        "total_files_detected": detection.get("total_files"),
        "total_words_detected": detection.get("total_words"),
        "code_files": len(detection.get("files", {}).get("code", [])),
        "document_files": len(detection.get("files", {}).get("document", [])),
        "image_files": len(detection.get("files", {}).get("image", [])),
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "communities": len(communities),
        "mode": "deterministic_ast_plus_file_context_no_semantic_llm",
    }
    (OUT / "context_graph_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
