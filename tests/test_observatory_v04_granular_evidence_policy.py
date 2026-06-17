"""
Tests for Observatory v0.4 granular evidence policy (post-DEC-065 consolidation).

Hard rule: NL gemeente proxy (evidence_type=proxy_disaggregated_by_stock_share,
region_system=GEMEENTE_PROXY) must NEVER appear in granular_relation_edges.csv.
It may only appear in the territory state panel, tagged as context, never as a
relation/training source. blocked_proxy_edges.csv preserves the 121 blocked
NL gemeente proxy edges with allowed_for_training_label=false.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

OUT_DIR = Path("data/processed/herald_observatory_v04_granular")
TERRITORY_STATE = OUT_DIR / "granular_territory_state_panel.csv"
RELATION_EDGES = OUT_DIR / "granular_relation_edges.csv"
BLOCKED_EDGES = OUT_DIR / "blocked_proxy_edges.csv"
MANIFEST = OUT_DIR / "manifest.json"

POLICY_REPORT = Path("reports/HERALD_GRANULAR_EVIDENCE_POLICY.md")
CONTRACT_REPORT = Path("reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md")
DEC065_AUDIT = Path("reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md")

OBSERVED_EVIDENCE_TYPES = {"observed_births"}
PROXY_EVIDENCE_TYPES = {"proxy_disaggregated_by_stock_share"}
TRAINING_LABELS = {"ROBUST_ORIGINAL", "FINE_GRAIN_SUPPORTED"}
ALL_LABEL_CLASSES = {
    "ROBUST_ORIGINAL", "FINE_GRAIN_SUPPORTED", "EXPLORATORY_FINE_GRAIN",
    "BLOCKED_PROXY_ARTIFACT", "INSUFFICIENT_EVIDENCE",
}
CAUSAL_TERMS = ["causes", "drives", "leads to", "induces", "results in",
                "provoca", "causa ", "determines", "causal impact",
                "causal effect", "causally", "causa de"]
# NOTE: bare "causal" and "causal claim"/"structural-causal claim" are
# intentionally excluded — this codebase legitimately uses "strictly causal" /
# "causal lag" to mean "no future leakage" in temporal feature engineering
# (see CODEX_MEMORY.md), and policy documents must name the forbidden category
# ("structural-causal claim") to define what is prohibited.


@pytest.fixture(scope="module")
def territory_state() -> pd.DataFrame:
    return pd.read_csv(TERRITORY_STATE, low_memory=False)


@pytest.fixture(scope="module")
def relation_edges() -> pd.DataFrame:
    return pd.read_csv(RELATION_EDGES)


@pytest.fixture(scope="module")
def blocked_edges() -> pd.DataFrame:
    return pd.read_csv(BLOCKED_EDGES)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# File existence
# ─────────────────────────────────────────────────────────────────────────────

class TestFilesExist:
    def test_territory_state_exists(self):
        assert TERRITORY_STATE.exists()

    def test_relation_edges_exists(self):
        assert RELATION_EDGES.exists()

    def test_blocked_edges_exists(self):
        assert BLOCKED_EDGES.exists()

    def test_manifest_exists(self):
        assert MANIFEST.exists()

    def test_policy_report_exists(self):
        assert POLICY_REPORT.exists()

    def test_contract_report_exists(self):
        assert CONTRACT_REPORT.exists()

    def test_dec065_audit_exists(self):
        assert DEC065_AUDIT.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Hard rule: NL gemeente proxy NEVER in relation edges
# ─────────────────────────────────────────────────────────────────────────────

class TestNlGemeenteNeverInRelationGraph:
    def test_no_gemeente_proxy_region_system_in_relation_edges(self, relation_edges):
        assert "GEMEENTE_PROXY" not in relation_edges["region_system"].values

    def test_no_proxy_evidence_type_in_relation_edges(self, relation_edges):
        assert not relation_edges["evidence_type"].isin(PROXY_EVIDENCE_TYPES).any()

    def test_relation_edges_only_observed_evidence(self, relation_edges):
        assert relation_edges["evidence_type"].isin(OBSERVED_EVIDENCE_TYPES).all()

    def test_relation_edges_only_allowed_region_systems(self, relation_edges):
        allowed = {"ZE2020", "MUNICIPALITY", "COROP"}
        assert set(relation_edges["region_system"].unique()).issubset(allowed)

    def test_relation_edges_only_allowed_countries(self, relation_edges):
        assert set(relation_edges["country"].unique()).issubset({"FR", "PT", "NL"})

    def test_nl_relation_edges_are_corop_only(self, relation_edges):
        nl_rows = relation_edges[relation_edges["country"] == "NL"]
        assert len(nl_rows) > 0, "NL COROP must contribute relation edges"
        assert (nl_rows["region_system"] == "COROP").all()


# ─────────────────────────────────────────────────────────────────────────────
# NL gemeente proxy only in territory state, tagged as context
# ─────────────────────────────────────────────────────────────────────────────

class TestNlGemeenteOnlyInTerritoryContext:
    def test_gemeente_proxy_present_in_territory_state(self, territory_state):
        gm = territory_state[territory_state["region_system"] == "GEMEENTE_PROXY"]
        assert len(gm) > 0, "NL gemeente proxy should be present as territory context"

    def test_gemeente_proxy_evidence_type_tagged(self, territory_state):
        gm = territory_state[territory_state["region_system"] == "GEMEENTE_PROXY"]
        assert (gm["evidence_type"] == "proxy_disaggregated_by_stock_share").all()

    def test_gemeente_proxy_allowed_use_context_only(self, territory_state):
        gm = territory_state[territory_state["region_system"] == "GEMEENTE_PROXY"]
        assert (gm["allowed_use"] == "territory_state_context_only").all()

    def test_observed_sources_have_full_allowed_use(self, territory_state):
        observed = territory_state[territory_state["evidence_type"] == "observed_births"]
        assert len(observed) > 0
        assert observed["allowed_use"].str.contains("relation_graph").all()
        assert observed["allowed_use"].str.contains("training_label").all()

    def test_no_other_proxy_evidence_type_leaks_into_other_region_systems(self, territory_state):
        non_gemeente = territory_state[territory_state["region_system"] != "GEMEENTE_PROXY"]
        assert not non_gemeente["evidence_type"].isin(PROXY_EVIDENCE_TYPES).any()


# ─────────────────────────────────────────────────────────────────────────────
# Blocked proxy edges
# ─────────────────────────────────────────────────────────────────────────────

class TestBlockedProxyEdges:
    def test_blocked_edges_not_empty(self, blocked_edges):
        assert len(blocked_edges) > 0

    def test_blocked_edges_count_121(self, blocked_edges):
        assert len(blocked_edges) == 121

    def test_blocked_edges_label_class(self, blocked_edges):
        assert (blocked_edges["label_class"] == "BLOCKED_PROXY_ARTIFACT").all()

    def test_blocked_edges_not_allowed_for_training(self, blocked_edges):
        assert (~blocked_edges["allowed_for_training_label"]).all()

    def test_blocked_edges_reason_documented(self, blocked_edges):
        assert (blocked_edges["reason"] == "stock_share_induced_artifact").all()

    def test_blocked_edges_region_system_gemeente(self, blocked_edges):
        assert (blocked_edges["region_system"] == "GEMEENTE_PROXY").all()

    def test_blocked_edges_evidence_type_proxy(self, blocked_edges):
        assert (blocked_edges["evidence_type"] == "proxy_disaggregated_by_stock_share").all()

    def test_blocked_edges_region_system_never_corop(self, blocked_edges):
        """Blocked gemeente-proxy edges must never carry the COROP region_system
        (sector/window collisions with NL COROP are expected and harmless since
        region_system/evidence_type already separates them; this checks the
        separation itself, not pair/window numerology)."""
        assert not (blocked_edges["region_system"] == "COROP").any()


# ─────────────────────────────────────────────────────────────────────────────
# DEC-066 label classes
# ─────────────────────────────────────────────────────────────────────────────

class TestDec066LabelsApplied:
    def test_relation_edges_labels_valid(self, relation_edges):
        assert relation_edges["label_class"].isin(ALL_LABEL_CLASSES).all()

    def test_relation_edges_no_blocked_label(self, relation_edges):
        assert not (relation_edges["label_class"] == "BLOCKED_PROXY_ARTIFACT").any()

    def test_allowed_for_training_consistent_with_label(self, relation_edges):
        for _, row in relation_edges.iterrows():
            expected = row["label_class"] in TRAINING_LABELS
            assert bool(row["allowed_for_training_label"]) == expected, (
                f"{row['country']} {row['source_sector']}->{row['target_sector']} "
                f"label={row['label_class']} allowed={row['allowed_for_training_label']}"
            )

    def test_fr_pt_nl_corop_represented(self, relation_edges):
        countries = set(relation_edges["country"].unique())
        assert countries == {"FR", "PT", "NL"}


# ─────────────────────────────────────────────────────────────────────────────
# No causal language in new reports
# ─────────────────────────────────────────────────────────────────────────────

class TestNoCausalLanguage:
    """Flags causal terms used as an actual claim. Terms cited as examples of
    FORBIDDEN language inside a documented policy/rules section (preceded by
    markers like 'prohibited', 'forbidden', 'never', 'must not') are not
    overclaims — they are the policy specifying what not to say."""

    NEGATION_WINDOW = 150
    NEGATIONS = ["not ", "nao ", "não ", "prohibited", "forbidden", "proibido",
                 "never", "must not", "vetado", "vedado"]

    def _unnegated_hits(self, text: str) -> list[str]:
        hits = []
        for term in CAUSAL_TERMS:
            idx = text.find(term)
            while idx != -1:
                window = text[max(0, idx - self.NEGATION_WINDOW):idx]
                if not any(neg in window for neg in self.NEGATIONS):
                    hits.append(term)
                idx = text.find(term, idx + 1)
        return hits

    def test_policy_report_no_causal_language(self):
        text = POLICY_REPORT.read_text().lower()
        hits = self._unnegated_hits(text)
        assert not hits, f"Causal terms found in policy report: {hits}"

    def test_contract_report_no_causal_language(self):
        text = CONTRACT_REPORT.read_text().lower()
        hits = self._unnegated_hits(text)
        assert not hits, f"Causal terms found in contract report: {hits}"

    def test_relation_edges_no_causal_columns(self, relation_edges):
        assert not any("causal" in c.lower() for c in relation_edges.columns)


# ─────────────────────────────────────────────────────────────────────────────
# Manifest validity and checksums
# ─────────────────────────────────────────────────────────────────────────────

class TestManifest:
    def test_manifest_is_valid_json(self, manifest):
        assert isinstance(manifest, dict)

    def test_manifest_has_dec_references(self, manifest):
        for dec in ["DEC-063", "DEC-064", "DEC-065", "DEC-066"]:
            assert dec in manifest["dec_references"]

    def test_manifest_checksums_match(self, manifest):
        for fname, info in manifest["outputs"].items():
            path = OUT_DIR / fname
            assert path.exists(), f"{fname} referenced in manifest but missing"
            actual = sha256_file(path)
            assert actual == info["sha256"], f"Checksum mismatch for {fname}"

    def test_manifest_row_counts_match(self, manifest, territory_state, relation_edges, blocked_edges):
        assert manifest["outputs"]["granular_territory_state_panel.csv"]["rows"] == len(territory_state)
        assert manifest["outputs"]["granular_relation_edges.csv"]["rows"] == len(relation_edges)
        assert manifest["outputs"]["blocked_proxy_edges.csv"]["rows"] == len(blocked_edges)

    def test_manifest_rules_forbid_gemeente_relation_edges(self, manifest):
        assert manifest["rules"]["nl_gemeente_proxy_relation_edges_forbidden"] is True

    def test_manifest_nl_corop_status_valid_observed(self, manifest):
        assert manifest["rules"]["nl_corop_observed_status"] == "VALID_OBSERVED"

    def test_manifest_nl_gemeente_status_blocked(self, manifest):
        assert manifest["rules"]["nl_gemeente_proxy_status"] == "BLOCKED_FOR_RELATION_LABELS"


# ─────────────────────────────────────────────────────────────────────────────
# Preservation of NL COROP / FR / PT observed sources
# ─────────────────────────────────────────────────────────────────────────────

class TestObservedSourcesPreserved:
    def test_nl_corop_observed_preserved_in_territory_state(self, territory_state):
        nl_corop = territory_state[
            (territory_state["country"] == "NL") & (territory_state["region_system"] == "COROP")
        ]
        assert len(nl_corop) > 0
        assert (nl_corop["evidence_type"] == "observed_births").all()

    def test_fr_observed_preserved(self, territory_state):
        fr = territory_state[territory_state["country"] == "FR"]
        assert len(fr) > 0
        assert (fr["evidence_type"] == "observed_births").all()
        assert (fr["region_system"] == "ZE2020").all()

    def test_pt_observed_preserved(self, territory_state):
        pt = territory_state[territory_state["country"] == "PT"]
        assert len(pt) > 0
        assert (pt["evidence_type"] == "observed_births").all()
        assert (pt["region_system"] == "MUNICIPALITY").all()

    def test_state_values_valid(self, territory_state):
        valid_states = {"GROWTH", "DECLINE", "STAGNATION", "INSUFFICIENT_DATA"}
        assert territory_state["state"].isin(valid_states).all()

    def test_artifact_registry_marks_corop_valid_and_gemeente_blocked(self):
        registry = json.loads(Path("reports/herald_artifact_registry.json").read_text())
        ids = {a["id"]: a for a in registry["artifacts"]}
        assert "NL_COROP_PHASE7" in ids
        assert ids["NL_COROP_PHASE7"]["status"] == "VALID_OBSERVED"
        assert "NL_GEMEENTE_PROXY_PHASE7_BLOCKED" in ids
        assert ids["NL_GEMEENTE_PROXY_PHASE7_BLOCKED"]["status"] == "BLOCKED"
        assert ids["NL_GEMEENTE_PROXY_PHASE7_BLOCKED"]["relation_label_status"] == "INVALID_FOR_RELATION_LABELS"
