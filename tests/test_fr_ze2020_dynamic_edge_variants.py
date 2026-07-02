from pathlib import Path

import numpy as np
import pandas as pd

from src.data.france_ze2020.build_fr_ze2020_dynamic_edge_variants import (
    CLAIM_STATUS,
    DEFAULT_MAX_EDGE_AGE,
    DEFAULT_MIN_ABS_SIGNAL,
    DEFAULT_MIN_STABILITY,
    DEFAULT_TOP_K_PER_NODE,
    EDGE_VARIANT,
    PRUNED_STABLE_EDGES_OUT_PATH,
    STATEFUL_EDGE_MEMORY_MODE,
    STATEFUL_EDGE_VARIANT,
    STATEFUL_EDGES_OUT_PATH,
    STATEFUL_SECTOR_ONLY_EDGE_VARIANT,
    STATEFUL_SECTOR_ONLY_EDGES_OUT_PATH,
    STATEFUL_SECTOR_TOPK_EDGE_VARIANT,
    STATEFUL_SECTOR_TOPK_EDGES_OUT_PATH,
    STATEFUL_TOPK_EDGE_VARIANT,
    STATEFUL_TOPK_EDGES_OUT_PATH,
    STATE_MULTIPLIERS,
    FEATURE_COMPATIBLE_EDGE_MEMORY_MODE,
    FEATURE_COMPATIBLE_EDGE_VARIANT,
    FEATURE_COMPATIBLE_EDGES_OUT_PATH,
    FEATURE_COMPATIBLE_TOPK_EDGE_VARIANT,
    FEATURE_COMPATIBLE_TOPK_EDGES_OUT_PATH,
    LEARNED_EDGE_MEMORY_MODE,
    LEARNED_SECTOR_ONLY_EDGE_VARIANT,
    LEARNED_SECTOR_ONLY_EDGES_OUT_PATH,
    LEARNED_SECTOR_TOPK_EDGE_VARIANT,
    LEARNED_SECTOR_TOPK_EDGES_OUT_PATH,
    LEARNED_STATEFUL_EDGE_VARIANT,
    LEARNED_STATEFUL_EDGES_OUT_PATH,
    LEARNED_STATEFUL_TOPK_EDGE_VARIANT,
    LEARNED_STATEFUL_TOPK_EDGES_OUT_PATH,
    SECTOR_EDGE_TYPES,
    build_pruned_stable_edges,
    build_feature_compatible_edges,
    build_learned_edge_gate_edges,
    build_sector_only_edges,
    build_stateful_edges,
    build_topk_edges,
    load_expanding_edges,
    load_nodes,
)
from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EXPANDING_EDGES_OUT_PATH,
)
from src.modeles.france_ze2020.audit_fr_ze2020_dynamic_edge_variants import (
    CLAIM_STATUS as AUDIT_CLAIM_STATUS,
    compare_edge_tables,
    run_audit,
    summarize_edges,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "src/data/france_ze2020/build_fr_ze2020_dynamic_edge_variants.py"
AUDIT_PATH = REPO_ROOT / "src/modeles/france_ze2020/audit_fr_ze2020_dynamic_edge_variants.py"

FORBIDDEN_TERMS = [
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
]

FORBIDDEN_COLUMNS = {
    "recommendation",
    "recommended_action",
    "policy_action",
    "causal_effect",
    "causal_impact",
}


def test_pruned_stable_edges_exist_and_schema():
    edges = pd.read_csv(PRUNED_STABLE_EDGES_OUT_PATH)
    expected = {
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
        "edge_variant",
        "edge_priority",
        "rank_within_target_year",
        "prune_top_k_per_node",
        "prune_min_stability",
        "prune_min_abs_signal",
        "prune_max_edge_age",
        "claim_status",
    }
    assert expected.issubset(edges.columns)
    assert not edges.empty
    assert edges["edge_id"].is_unique
    assert set(edges["edge_variant"]) == {EDGE_VARIANT}
    assert set(edges["claim_status"]) == {CLAIM_STATUS}
    assert set(edges["edge_type"]) == {
        "cross_ze_same_sector",
        "intra_ze_sector",
        "ze_similarity",
    }


def test_stateful_edges_exist_and_schema():
    edges = pd.read_csv(STATEFUL_EDGES_OUT_PATH)
    expected = {
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
        "edge_variant",
        "edge_state",
        "state_multiplier",
        "recent_observation_count",
        "total_observation_count",
        "first_observed_year",
        "latest_observed_year",
        "claim_status",
    }
    assert expected.issubset(edges.columns)
    assert not edges.empty
    assert edges["edge_id"].is_unique
    assert set(edges["edge_variant"]) == {STATEFUL_EDGE_VARIANT}
    assert set(edges["edge_memory_mode"]) == {STATEFUL_EDGE_MEMORY_MODE}
    assert set(edges["claim_status"]) == {CLAIM_STATUS}
    assert set(edges["edge_state"]).issubset(STATE_MULTIPLIERS)


def test_all_edge_variant_files_exist_and_have_expected_variant_names():
    paths = {
        STATEFUL_SECTOR_ONLY_EDGES_OUT_PATH: STATEFUL_SECTOR_ONLY_EDGE_VARIANT,
        STATEFUL_TOPK_EDGES_OUT_PATH: STATEFUL_TOPK_EDGE_VARIANT,
        STATEFUL_SECTOR_TOPK_EDGES_OUT_PATH: STATEFUL_SECTOR_TOPK_EDGE_VARIANT,
        FEATURE_COMPATIBLE_EDGES_OUT_PATH: FEATURE_COMPATIBLE_EDGE_VARIANT,
        FEATURE_COMPATIBLE_TOPK_EDGES_OUT_PATH: FEATURE_COMPATIBLE_TOPK_EDGE_VARIANT,
        LEARNED_STATEFUL_EDGES_OUT_PATH: LEARNED_STATEFUL_EDGE_VARIANT,
        LEARNED_STATEFUL_TOPK_EDGES_OUT_PATH: LEARNED_STATEFUL_TOPK_EDGE_VARIANT,
        LEARNED_SECTOR_ONLY_EDGES_OUT_PATH: LEARNED_SECTOR_ONLY_EDGE_VARIANT,
        LEARNED_SECTOR_TOPK_EDGES_OUT_PATH: LEARNED_SECTOR_TOPK_EDGE_VARIANT,
    }
    for path, variant in paths.items():
        edges = pd.read_csv(path)
        assert not edges.empty
        assert set(edges["edge_variant"]) == {variant}
        assert set(edges["claim_status"]) == {CLAIM_STATUS}


def test_pruned_stable_edges_apply_thresholds_and_top_k():
    edges = pd.read_csv(PRUNED_STABLE_EDGES_OUT_PATH)
    assert (edges["stability_score"] >= DEFAULT_MIN_STABILITY).all()
    assert (edges["signal_strength"].abs() >= DEFAULT_MIN_ABS_SIGNAL).all()
    assert (edges["edge_age"] <= DEFAULT_MAX_EDGE_AGE).all()
    assert edges["rank_within_target_year"].between(1, DEFAULT_TOP_K_PER_NODE).all()
    assert (
        edges.groupby(["decision_year", "target_node_id"]).size().max()
        <= DEFAULT_TOP_K_PER_NODE
    )
    assert (edges["source_relation_year_end"] <= edges["decision_year"]).all()
    assert (
        edges["edge_age"] == edges["decision_year"] - edges["source_relation_year_end"]
    ).all()


def test_pruned_stable_edges_are_smaller_than_expanding_edges():
    expanding = pd.read_csv(EXPANDING_EDGES_OUT_PATH)
    pruned = pd.read_csv(PRUNED_STABLE_EDGES_OUT_PATH)
    assert 0 < len(pruned) < len(expanding)
    assert len(pruned) / len(expanding) < 0.5


def test_stateful_edges_reweight_expanding_edges_without_changing_grain():
    expanding = pd.read_csv(EXPANDING_EDGES_OUT_PATH)
    stateful = pd.read_csv(STATEFUL_EDGES_OUT_PATH)
    key = ["source_node_id", "target_node_id", "edge_type", "decision_year"]
    assert len(stateful) == len(expanding)
    assert stateful.duplicated(key).sum() == 0
    assert expanding.duplicated(key).sum() == 0
    assert (stateful["source_relation_year_end"] <= stateful["decision_year"]).all()
    assert (
        stateful["edge_age"] == stateful["decision_year"] - stateful["source_relation_year_end"]
    ).all()
    expected_weight = (
        stateful["signal_strength"]
        * stateful["stability_score"]
        * stateful["state_multiplier"]
        / (1.0 + stateful["edge_age"])
    )
    assert np.allclose(stateful["edge_weight"], expected_weight)


def test_sector_only_variants_remove_ze_similarity():
    stateful = pd.read_csv(STATEFUL_EDGES_OUT_PATH)
    sector_only = pd.read_csv(STATEFUL_SECTOR_ONLY_EDGES_OUT_PATH)
    sector_topk = pd.read_csv(STATEFUL_SECTOR_TOPK_EDGES_OUT_PATH)
    assert set(sector_only["edge_type"]).issubset(SECTOR_EDGE_TYPES)
    assert set(sector_topk["edge_type"]).issubset(SECTOR_EDGE_TYPES)
    assert 0 < len(sector_only) < len(stateful)
    assert len(sector_topk) <= len(sector_only)


def test_topk_variants_limit_incoming_degree():
    for path in [STATEFUL_TOPK_EDGES_OUT_PATH, FEATURE_COMPATIBLE_TOPK_EDGES_OUT_PATH]:
        edges = pd.read_csv(path)
        assert edges["rank_within_target_year"].between(1, DEFAULT_TOP_K_PER_NODE).all()
        assert (
            edges.groupby(["decision_year", "target_node_id"]).size().max()
            <= DEFAULT_TOP_K_PER_NODE
        )
        assert set(edges["variant_top_k_per_node"]) == {DEFAULT_TOP_K_PER_NODE}


def test_pruned_stable_edges_are_finite_and_non_causal():
    edges = pd.read_csv(PRUNED_STABLE_EDGES_OUT_PATH)
    for col in ["edge_weight", "signal_strength", "stability_score", "edge_priority"]:
        assert np.isfinite(edges[col].to_numpy(dtype=float)).all()
    assert edges["signal_strength"].between(-1, 1).all()
    assert edges["stability_score"].between(0, 1).all()
    lowered = {col.lower() for col in edges.columns}
    assert not FORBIDDEN_COLUMNS.intersection(lowered)


def test_stateful_edges_are_finite_and_non_causal():
    edges = pd.read_csv(STATEFUL_EDGES_OUT_PATH)
    for col in [
        "edge_weight",
        "signal_strength",
        "stability_score",
        "state_multiplier",
        "recent_observation_count",
        "total_observation_count",
    ]:
        assert np.isfinite(edges[col].to_numpy(dtype=float)).all()
    assert edges["signal_strength"].between(-1, 1).all()
    assert edges["stability_score"].between(0, 1).all()
    assert edges["state_multiplier"].between(0, 1).all()
    lowered = {col.lower() for col in edges.columns}
    assert not FORBIDDEN_COLUMNS.intersection(lowered)


def test_feature_compatible_edges_are_finite_and_bounded():
    edges = pd.read_csv(FEATURE_COMPATIBLE_EDGES_OUT_PATH)
    assert set(edges["edge_memory_mode"]) == {FEATURE_COMPATIBLE_EDGE_MEMORY_MODE}
    compatibility_cols = [c for c in edges.columns if c.endswith("_compatibility")]
    assert compatibility_cols
    for col in [*compatibility_cols, "feature_compatibility_score", "edge_weight"]:
        assert np.isfinite(edges[col].to_numpy(dtype=float)).all()
    for col in [*compatibility_cols, "feature_compatibility_score"]:
        assert edges[col].between(0, 1).all()
    lowered = {col.lower() for col in edges.columns}
    assert not FORBIDDEN_COLUMNS.intersection(lowered)


def test_learned_edge_gate_variants_are_rolling_and_bounded():
    for path in [
        LEARNED_STATEFUL_EDGES_OUT_PATH,
        LEARNED_STATEFUL_TOPK_EDGES_OUT_PATH,
        LEARNED_SECTOR_ONLY_EDGES_OUT_PATH,
        LEARNED_SECTOR_TOPK_EDGES_OUT_PATH,
    ]:
        edges = pd.read_csv(path)
        assert set(edges["edge_memory_mode"]) == {LEARNED_EDGE_MEMORY_MODE}
        assert edges["learned_edge_gate"].between(0, 1).all()
        assert np.isfinite(edges["learned_edge_gate"].to_numpy(dtype=float)).all()
        assert (edges["source_relation_year_end"] <= edges["decision_year"]).all()
        assert (edges["learned_edge_gate_training_rows"] >= 0).all()
        assert edges.groupby("decision_year")["learned_edge_gate_training_rows"].first().is_monotonic_increasing
        assert edges["learned_edge_gate"].std() > 0
        lowered = {col.lower() for col in edges.columns}
        assert not FORBIDDEN_COLUMNS.intersection(lowered)


def test_pruned_stable_builder_is_deterministic():
    disk = pd.read_csv(PRUNED_STABLE_EDGES_OUT_PATH).sort_index(axis=1)
    rebuilt = build_pruned_stable_edges().sort_index(axis=1)
    pd.testing.assert_frame_equal(disk, rebuilt, check_dtype=False)


def test_stateful_builder_is_deterministic():
    disk = pd.read_csv(STATEFUL_EDGES_OUT_PATH).sort_index(axis=1)
    rebuilt = build_stateful_edges().sort_index(axis=1)
    pd.testing.assert_frame_equal(disk, rebuilt, check_dtype=False)


def test_derived_builders_are_deterministic():
    stateful = build_stateful_edges()
    nodes = load_nodes()
    expected = {
        STATEFUL_SECTOR_ONLY_EDGES_OUT_PATH: build_sector_only_edges(stateful),
        STATEFUL_TOPK_EDGES_OUT_PATH: build_topk_edges(
            stateful,
            edge_variant=STATEFUL_TOPK_EDGE_VARIANT,
        ),
        STATEFUL_SECTOR_TOPK_EDGES_OUT_PATH: build_topk_edges(
            build_sector_only_edges(stateful),
            edge_variant=STATEFUL_SECTOR_TOPK_EDGE_VARIANT,
        ),
        FEATURE_COMPATIBLE_EDGES_OUT_PATH: build_feature_compatible_edges(stateful, nodes),
    }
    expected[FEATURE_COMPATIBLE_TOPK_EDGES_OUT_PATH] = build_topk_edges(
        expected[FEATURE_COMPATIBLE_EDGES_OUT_PATH],
        edge_variant=FEATURE_COMPATIBLE_TOPK_EDGE_VARIANT,
    )
    expected[LEARNED_STATEFUL_EDGES_OUT_PATH] = build_learned_edge_gate_edges(stateful, nodes)
    expected[LEARNED_STATEFUL_TOPK_EDGES_OUT_PATH] = build_topk_edges(
        expected[LEARNED_STATEFUL_EDGES_OUT_PATH],
        edge_variant=LEARNED_STATEFUL_TOPK_EDGE_VARIANT,
    )
    expected[LEARNED_SECTOR_ONLY_EDGES_OUT_PATH] = build_learned_edge_gate_edges(
        build_sector_only_edges(stateful),
        nodes,
        edge_variant=LEARNED_SECTOR_ONLY_EDGE_VARIANT,
    )
    expected[LEARNED_SECTOR_TOPK_EDGES_OUT_PATH] = build_topk_edges(
        expected[LEARNED_SECTOR_ONLY_EDGES_OUT_PATH],
        edge_variant=LEARNED_SECTOR_TOPK_EDGE_VARIANT,
    )
    for path, rebuilt in expected.items():
        disk = pd.read_csv(path).sort_index(axis=1)
        pd.testing.assert_frame_equal(disk, rebuilt.sort_index(axis=1), check_dtype=False)


def test_pruned_stable_builder_accepts_explicit_input():
    expanding = load_expanding_edges()
    subset = expanding[expanding["decision_year"].isin([2024, 2025])].copy()
    pruned = build_pruned_stable_edges(subset, top_k_per_node=3, min_stability=0.25)
    assert not pruned.empty
    assert pruned["rank_within_target_year"].max() <= 3
    assert set(pruned["decision_year"]).issubset({2024, 2025})


def test_stateful_builder_accepts_explicit_input():
    expanding = load_expanding_edges()
    subset = expanding[expanding["decision_year"].isin([2024, 2025])].copy()
    stateful = build_stateful_edges(subset)
    assert not stateful.empty
    assert set(stateful["decision_year"]).issubset({2024, 2025})
    assert set(stateful["edge_state"]).issubset(STATE_MULTIPLIERS)


def test_edge_audit_outputs_expected_manifest():
    type_year, degree, manifest = run_audit()
    assert not type_year.empty
    assert not degree.empty
    assert manifest["claim_status"] == AUDIT_CLAIM_STATUS
    assert manifest["base_edge_count"] > manifest["variant_edge_count"] > 0
    assert 0 < manifest["retained_edge_share"] < 0.5
    assert set(manifest["variant_edge_types"]) == {
        "cross_ze_same_sector",
        "intra_ze_sector",
        "ze_similarity",
    }
    assert set(type_year["claim_status"]) == {AUDIT_CLAIM_STATUS}
    assert set(degree["claim_status"]) == {AUDIT_CLAIM_STATUS}


def test_edge_audit_summary_handles_explicit_edges():
    edges = pd.read_csv(PRUNED_STABLE_EDGES_OUT_PATH)
    type_year, degree = summarize_edges(edges, "pruned_stable")
    manifest = compare_edge_tables(edges, edges, "self")
    assert not type_year.empty
    assert not degree.empty
    assert manifest["retained_edge_share"] == 1.0


def test_scripts_do_not_read_forbidden_legacy_inputs():
    for path in [BUILDER_PATH, AUDIT_PATH]:
        source_lines = path.read_text().splitlines()
        read_lines = [line for line in source_lines if "read_csv" in line or "Path(" in line or " / " in line]
        code_only = "\n".join(read_lines)
        for term in FORBIDDEN_TERMS:
            assert term not in code_only
