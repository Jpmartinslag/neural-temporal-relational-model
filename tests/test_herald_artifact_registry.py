"""
Automated validation for reports/herald_artifact_registry.json.
Run: pytest tests/test_herald_artifact_registry.py -v
"""
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
REGISTRY_PATH = REPO_ROOT / "reports" / "herald_artifact_registry.json"

VALID_STATUSES = {
    "ACTIVE",
    "FROZEN",
    "SUPERSEDED",
    "INVALID_FOR_CLAIMS",
    "INVALID_FOR_INTERPRETATION",
    "REGENERABLE",
    "ARCHIVED",
}

ESSENTIAL_IDS = {
    "PANEL_PT_IT_AT_HARMONIZED",
    "PANEL_FR_SECTOR_NUTS3",
    "PANEL_FR_NL_PT_SECTOR",
    "G1_L2_COGROWTH",
    "G2_PREFLIGHT",
    "P6_DDEG_S1_GATE_RESULT",
    "P6_DDEG_S1_LEARNED_SECTOR_EDGES",
    "RIDGE_PERSISTENCE_LOCO_RESULTS",
    "HERALD_Q7_FRANCE_RESULT",
    "GRAPH_TEMPORAL_V2_TENSORS",
}


@pytest.fixture(scope="module")
def registry():
    assert REGISTRY_PATH.exists(), f"Registry not found: {REGISTRY_PATH}"
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def artifacts(registry):
    return {a["id"]: a for a in registry["artifacts"]}


@pytest.fixture(scope="module")
def tracked_files():
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.splitlines())


def test_registry_loads_and_has_meta(registry):
    assert "artifacts" in registry
    assert "_meta" in registry
    assert isinstance(registry["artifacts"], list)
    assert len(registry["artifacts"]) > 0


def test_all_artifacts_have_required_fields(artifacts):
    required = {"id", "path", "status", "tracked_in_git", "origin_decision",
                "claim_authorized", "claim_forbidden", "can_regenerate"}
    for aid, a in artifacts.items():
        missing = required - set(a.keys())
        assert not missing, f"Artifact {aid} missing fields: {missing}"


def test_status_vocabulary(artifacts):
    for aid, a in artifacts.items():
        assert a["status"] in VALID_STATUSES, (
            f"Artifact {aid} has unknown status '{a['status']}'. "
            f"Valid: {VALID_STATUSES}"
        )


def test_tracked_in_git_is_boolean(artifacts):
    for aid, a in artifacts.items():
        assert isinstance(a["tracked_in_git"], bool), (
            f"Artifact {aid}: tracked_in_git must be bool, got {type(a['tracked_in_git'])}"
        )


def test_tracked_in_git_accuracy(artifacts, tracked_files):
    """Verify that tracked_in_git=True entries actually appear in git ls-files."""
    for aid, a in artifacts.items():
        path = a["path"].rstrip("/")
        if a["tracked_in_git"]:
            # For directories, check that at least one file under that path is tracked
            if a["path"].endswith("/"):
                prefix = path + "/"
                has_tracked = any(f.startswith(prefix) or f == path for f in tracked_files)
                assert has_tracked, (
                    f"Artifact {aid}: tracked_in_git=True but no files under '{path}/' "
                    f"found in git ls-files"
                )
            else:
                assert path in tracked_files, (
                    f"Artifact {aid}: tracked_in_git=True but '{path}' not in git ls-files"
                )


def test_no_false_negatives_for_known_tracked(artifacts, tracked_files):
    """Spot-check: known-tracked artefacts must not be marked false."""
    known_tracked_paths = {
        "data/processed/economic_graph/sector_panel_fr_nl_pt.csv": "PANEL_FR_NL_PT_SECTOR",
        "data/processed/economic_graph/g2_preflight/g2_corrected_controls_summary.json": "G2_PREFLIGHT",
        "data/processed/dual_graph_s1/gate_result.json": "P6_DDEG_S1_GATE_RESULT",
        "reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md": "HERALD_Q7_FRANCE_RESULT",
    }
    for path, expected_id in known_tracked_paths.items():
        if path in tracked_files:
            a = artifacts.get(expected_id)
            if a is not None:
                assert a["tracked_in_git"], (
                    f"Artifact {expected_id}: '{path}' IS in git but tracked_in_git=False"
                )


def test_essential_artifacts_present(artifacts):
    for eid in ESSENTIAL_IDS:
        assert eid in artifacts, f"Essential artifact '{eid}' missing from registry"


def test_invalid_for_interpretation_has_sector_label_note(artifacts):
    """P6 learned sector edges must document the label mapping problem."""
    a = artifacts.get("P6_DDEG_S1_LEARNED_SECTOR_EDGES")
    assert a is not None
    assert a["status"] == "INVALID_FOR_INTERPRETATION"
    assert "SECTOR LABEL MISMATCH" in a.get("notes", "") or \
           "sector" in a.get("claim_forbidden", "").lower(), (
        "P6_DDEG_S1_LEARNED_SECTOR_EDGES must document sector label mismatch"
    )


def test_p6_gate_result_is_frozen(artifacts):
    a = artifacts.get("P6_DDEG_S1_GATE_RESULT")
    assert a is not None
    assert a["status"] == "FROZEN", "P6 gate result must remain FROZEN (DEC-029)"
    assert a["can_regenerate"] is False


def test_herald_q7_has_pending_reaudit_note(artifacts):
    """HERALD Q7 France result must carry PENDING_REAUDIT note in claim_authorized."""
    a = artifacts.get("HERALD_Q7_FRANCE_RESULT")
    assert a is not None
    assert "PENDING_REAUDIT" in a.get("claim_authorized", ""), (
        "HERALD_Q7_FRANCE_RESULT must carry PENDING_REAUDIT in claim_authorized"
    )


def test_ids_are_unique(registry):
    ids = [a["id"] for a in registry["artifacts"]]
    assert len(ids) == len(set(ids)), "Duplicate artifact IDs found in registry"


def test_can_regenerate_is_boolean(artifacts):
    for aid, a in artifacts.items():
        assert isinstance(a["can_regenerate"], bool), (
            f"Artifact {aid}: can_regenerate must be bool"
        )


def test_non_regenerable_frozen_artifacts_have_sha(artifacts):
    """Frozen, non-regenerable artifacts with known content should have a sha256_prefix."""
    for aid, a in artifacts.items():
        if a["status"] == "FROZEN" and not a["can_regenerate"]:
            assert a.get("sha256_prefix"), (
                f"Artifact {aid}: FROZEN+non-regenerable should have sha256_prefix"
            )
