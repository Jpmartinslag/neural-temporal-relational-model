"""
Documentary consistency checks for the France ZE2020 canonical vs legacy
data lineage (registry + HERALD_15 doc). No model is trained or evaluated
by this suite -- it only checks that artifact metadata and documentation
agree on what is current vs legacy.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
REGISTRY_PATH = REPO_ROOT / "reports" / "herald_artifact_registry.json"
HERALD_15_PATH = (
    REPO_ROOT / "reports" / "canonical" / "HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md"
)
HERALD_17_PATH = (
    REPO_ROOT / "reports" / "canonical" / "HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md"
)

CANONICAL_IDS = {"PANEL_FR_ZE2020_CLEAN_TREATED", "PANEL_FR_ZE2020_MODEL_READY_CAUSAL"}
LEGACY_ID = "FR_DYNAMIC_STGNN_LEGACY_FEATURE_PANEL"
SECTOR_GRAPH_ID = "FR_ZE2020_SECTOR_GRAPH_PROTOTYPE_PREDICTIONS_V1"

# Statuses that would incorrectly present the legacy panel as current.
NON_LEGACY_STATUSES = {"ACTIVE"}


@pytest.fixture(scope="module")
def artifacts():
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    return {a["id"]: a for a in data["artifacts"]}


@pytest.fixture(scope="module")
def herald_15_text():
    return HERALD_15_PATH.read_text()


@pytest.fixture(scope="module")
def herald_17_text():
    return HERALD_17_PATH.read_text()


def test_canonical_france_panels_present_in_registry(artifacts):
    for cid in CANONICAL_IDS:
        assert cid in artifacts, f"Canonical France panel '{cid}' missing from registry"


def test_legacy_stgnn_panel_not_marked_as_current(artifacts):
    a = artifacts.get(LEGACY_ID)
    assert a is not None, f"{LEGACY_ID} missing from registry"
    assert a["status"] not in NON_LEGACY_STATUSES, (
        f"{LEGACY_ID} has status '{a['status']}', which reads as a current/"
        f"trustworthy artifact -- it must carry a status that flags it as "
        f"not valid for current claims (e.g. INVALID_FOR_CLAIMS)"
    )


def test_legacy_stgnn_panel_documents_do_not_use_for_current_method(artifacts):
    a = artifacts.get(LEGACY_ID)
    assert a is not None
    haystack = " ".join(
        [a.get("claim_authorized", ""), a.get("claim_forbidden", ""), a.get("notes", "")]
    )
    assert "LEGACY_DO_NOT_USE_FOR_CURRENT_METHOD" in haystack or "LEGACY" in a["id"]
    assert "fr_ze2020_clean_panel.csv" in haystack, (
        f"{LEGACY_ID} should point readers to the current canonical source"
    )


def test_legacy_stgnn_panel_does_not_claim_forecast_safe_without_caveat(artifacts):
    a = artifacts.get(LEGACY_ID)
    assert a is not None
    forbidden = a.get("claim_forbidden", "")
    assert "feature_forecast_safe" in forbidden
    assert "leak" in forbidden.lower() or "leakage" in forbidden.lower()


def test_q7_result_still_pending_reaudit(artifacts):
    a = artifacts.get("HERALD_Q7_FRANCE_RESULT")
    assert a is not None
    assert "PENDING_REAUDIT" in a.get("claim_authorized", "")


def test_herald_15_doc_names_canonical_chain(herald_15_text):
    assert "fr_ze2020_clean_panel.csv" in herald_15_text
    assert "fr_ze2020_model_ready_panel.csv" in herald_15_text
    assert "build_fr_ze2020_clean_panel.py" in herald_15_text
    assert "build_fr_ze2020_model_ready_panel.py" in herald_15_text


def test_herald_15_doc_flags_legacy_panel_as_not_current(herald_15_text):
    assert "LEGACY_DO_NOT_USE" in herald_15_text
    assert "dynamic_stgnn_feature_panel_v1.csv" in herald_15_text


def test_sector_graph_registry_distinguishes_nodes_from_node_year_rows(artifacts):
    a = artifacts.get(SECTOR_GRAPH_ID)
    assert a is not None, f"{SECTOR_GRAPH_ID} missing from registry"
    haystack = " ".join([a.get("claim_authorized", ""), a.get("notes", "")])
    assert "2,520 unique nodes" in haystack
    assert "32,760 node-year rows" in haystack
    assert "32,760 nodes" not in haystack


def test_herald_17_distinguishes_nodes_from_node_year_rows(herald_17_text):
    assert "2.520 nós únicos" in herald_17_text
    assert "32.760 linhas nó-ano" in herald_17_text
    assert "32.760 nós" not in herald_17_text
