"""Tests for Phase 7 sector precedence HPC assets.

Uses machine-independent paths derived from __file__.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "hpc" / "phase7_sector_precedence" / "scripts"
CONFIGS_DIR = REPO_ROOT / "hpc" / "phase7_sector_precedence" / "configs"
MANIFEST_PATH = CONFIGS_DIR / "task_manifest.json"
PYTHON = sys.executable


def run_script(script: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, str(script), *args],
        capture_output=True,
        text=True,
    )


# ── Static asset existence ─────────────────────────────────────────────────


def test_prepare_task_manifest_exists():
    assert (SCRIPTS_DIR / "prepare_task_manifest.py").is_file()


def test_run_sector_precedence_task_exists():
    assert (SCRIPTS_DIR / "run_sector_precedence_task.py").is_file()


def test_merge_script_exists():
    assert (SCRIPTS_DIR / "merge_sector_precedence_results.py").is_file()


def test_audit_script_exists():
    assert (SCRIPTS_DIR / "audit_sector_precedence_results.py").is_file()


def test_sbatch_script_exists():
    assert (SCRIPTS_DIR / "run_sector_precedence_array.sbatch").is_file()


def test_full_run_config_exists():
    assert (CONFIGS_DIR / "full_run.json").is_file()


def test_manifest_exists():
    assert MANIFEST_PATH.is_file(), "task_manifest.json not found — run prepare_task_manifest.py"


# ── Manifest structure and content ────────────────────────────────────────


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text())


def test_manifest_is_list(manifest):
    assert isinstance(manifest, list)
    assert len(manifest) > 0


def test_manifest_total_count(manifest):
    assert len(manifest) == 710, f"Expected 710 tasks, got {len(manifest)}"


def test_manifest_task_ids_contiguous(manifest):
    ids = [t["task_id"] for t in manifest]
    assert ids == list(range(len(ids))), "task_ids are not contiguous from 0"


def test_manifest_required_fields(manifest):
    required = {
        "schema_version", "task_id", "country", "scenario",
        "window_start", "window_end", "source_sector", "targets",
        "seed", "n_permutations", "n_bootstraps",
        "panel_checksum", "commit_sha", "expected_output",
    }
    for task in manifest:
        missing = required - set(task.keys())
        assert not missing, f"Task {task['task_id']} missing fields: {missing}"


def test_manifest_no_duplicates(manifest):
    keys = [
        (t["country"], t["scenario"], t["window_start"], t["window_end"], t["source_sector"])
        for t in manifest
    ]
    assert len(keys) == len(set(keys)), "Duplicate task keys in manifest"


def test_manifest_no_placeholder_windows(manifest):
    """No window should span 2000–2005 (old placeholder range, pre-real-data)."""
    for task in manifest:
        assert not (
            task["window_start"] == 2000 and task["window_end"] == 2005
        ), f"Task {task['task_id']} has placeholder window 2000-2005"


def test_manifest_pt_no_kz(manifest):
    """PT should never have KZ as source_sector (structural absence)."""
    pt_sources = {t["source_sector"] for t in manifest if t["country"] == "PT"}
    assert "KZ" not in pt_sources, "PT has KZ as source sector — should be excluded"


def test_manifest_pt_no_kz_in_targets(manifest):
    """PT target lists should never include KZ."""
    for task in manifest:
        if task["country"] == "PT":
            assert "KZ" not in task["targets"], (
                f"Task {task['task_id']} (PT) has KZ in targets"
            )


def test_manifest_country_counts(manifest):
    from collections import Counter
    country_scenario_counts = Counter(
        (t["country"], t["scenario"]) for t in manifest
    )
    assert country_scenario_counts[("FR", "main")] == 99, \
        f"FR/main: expected 99, got {country_scenario_counts[('FR', 'main')]}"
    assert country_scenario_counts[("NL", "main")] == 144, \
        f"NL/main: expected 144, got {country_scenario_counts[('NL', 'main')]}"
    assert country_scenario_counts[("PT", "main")] == 112, \
        f"PT/main: expected 112, got {country_scenario_counts[('PT', 'main')]}"


def test_manifest_scenarios(manifest):
    scenarios = {t["scenario"] for t in manifest}
    assert scenarios == {"main", "without_2020"}


def test_manifest_expected_output_pattern(manifest):
    for task in manifest:
        assert task["expected_output"] == f"task_{task['task_id']:06d}.json", (
            f"Task {task['task_id']}: expected_output mismatch"
        )


def test_manifest_targets_exclude_source(manifest):
    for task in manifest[:50]:  # spot-check
        assert task["source_sector"] not in task["targets"], (
            f"Task {task['task_id']}: source_sector in targets"
        )


def test_manifest_windows_are_6_years(manifest):
    for task in manifest:
        span = task["window_end"] - task["window_start"] + 1
        assert span == 6, (
            f"Task {task['task_id']}: window span {span} != 6"
        )


# ── Builder import ─────────────────────────────────────────────────────────


def test_builder_importable():
    builder_path = REPO_ROOT / "src" / "data" / "european_panel" / "build_sector_precedence_graph.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("builder", builder_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "build"), "build function missing"
    assert hasattr(mod, "evaluate_edge"), "evaluate_edge function missing"
    assert hasattr(mod, "pair_samples"), "pair_samples function missing"
    assert hasattr(mod, "bh_fdr"), "bh_fdr function missing"


# ── Task executor interface ────────────────────────────────────────────────


def test_task_executor_exits_nonzero_on_bad_manifest(tmp_path):
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text('{"not": "a list"}')
    result = run_script(
        SCRIPTS_DIR / "run_sector_precedence_task.py",
        "--manifest", str(bad_manifest),
        "--task-id", "0",
        "--panel", str(tmp_path / "nope.csv"),
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode != 0


def test_task_executor_exits_nonzero_on_missing_panel(tmp_path):
    # Manifest with one task; panel doesn't exist
    panel_path = tmp_path / "panel.csv"
    manifest = [
        {
            "schema_version": "1.0",
            "task_id": 0,
            "country": "FR",
            "scenario": "main",
            "window_start": 2015,
            "window_end": 2020,
            "source_sector": "IND",
            "targets": ["AGR"],
            "seed": 42,
            "n_permutations": 9,
            "n_bootstraps": 9,
            "panel_checksum": "deadbeef" * 8,
            "commit_sha": "abc123",
            "expected_output": "task_000000.json",
        }
    ]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    result = run_script(
        SCRIPTS_DIR / "run_sector_precedence_task.py",
        "--manifest", str(tmp_path / "manifest.json"),
        "--task-id", "0",
        "--panel", str(panel_path),
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode != 0


def test_task_executor_exits_nonzero_on_checksum_mismatch(tmp_path):
    import pandas as pd
    panel = pd.DataFrame({
        "country": ["FR"],
        "territory_id": ["FR001"],
        "sector_id": ["IND"],
        "observation_year": [2020],
        "velocity": [0.1],
        "structural_mask": [1],
        "observation_mask": [1],
    })
    panel_path = tmp_path / "panel.csv"
    panel.to_csv(panel_path, index=False)

    manifest = [
        {
            "schema_version": "1.0",
            "task_id": 0,
            "country": "FR",
            "scenario": "main",
            "window_start": 2015,
            "window_end": 2020,
            "source_sector": "IND",
            "targets": ["AGR"],
            "seed": 42,
            "n_permutations": 9,
            "n_bootstraps": 9,
            "panel_checksum": "wrong_checksum_" + "0" * 48,
            "commit_sha": "abc123",
            "expected_output": "task_000000.json",
        }
    ]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    result = run_script(
        SCRIPTS_DIR / "run_sector_precedence_task.py",
        "--manifest", str(tmp_path / "manifest.json"),
        "--task-id", "0",
        "--panel", str(panel_path),
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode != 0


# ── Merge / audit with zero-promoted edges ────────────────────────────────


def _make_fake_task_json(task_id: int, out_dir: Path, panel_checksum: str, commit_sha: str) -> None:
    data = {
        "schema_version": "1.0",
        "task_id": task_id,
        "country": "FR",
        "scenario": "main",
        "window_start": 2015,
        "window_end": 2020,
        "source_sector": "IND",
        "targets": ["AGR"],
        "n_permutations": 9,
        "n_bootstraps": 9,
        "panel_checksum": panel_checksum,
        "commit_sha": commit_sha,
        "derived_seed": 42,
        "runtime_seconds": 0.1,
        "hostname": "test",
        "status": "complete",
        "edges": [
            {
                "target_sector": "AGR",
                "n_samples": 10,
                "beta": None,
                "delta_r2": None,
                "p_perm": None,
                "bootstrap_sign_stability": None,
            }
        ],
    }
    (out_dir / f"task_{task_id:06d}.json").write_text(json.dumps(data))


def test_merge_succeeds_with_zero_promoted(tmp_path):
    """Zero promoted edges is a valid scientific result, not an error."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    out_dir = tmp_path / "merged"
    chk = "a" * 64
    sha = "b" * 40
    manifest = [
        {
            "schema_version": "1.0",
            "task_id": 0,
            "country": "FR",
            "scenario": "main",
            "window_start": 2015,
            "window_end": 2020,
            "source_sector": "IND",
            "targets": ["AGR"],
            "seed": 42,
            "n_permutations": 9,
            "n_bootstraps": 9,
            "panel_checksum": chk,
            "commit_sha": sha,
            "expected_output": "task_000000.json",
        }
    ]
    _make_fake_task_json(0, raw_dir, chk, sha)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    result = run_script(
        SCRIPTS_DIR / "merge_sector_precedence_results.py",
        "--raw-dir", str(raw_dir),
        "--manifest", str(manifest_path),
        "--out-dir", str(out_dir),
    )
    assert result.returncode == 0, f"Merge failed: {result.stderr}"
    assert (out_dir / "all_edges.csv").is_file()
    decision = json.loads((out_dir / "decision.json").read_text())
    assert decision["verdict"] in ("SECTOR_PRECEDENCE_PROTOTYPE_READY", "SECTOR_PRECEDENCE_NOT_PROMOTED")
    assert decision["promoted_main_count"] == 0


def test_audit_passes_with_zero_promoted(tmp_path):
    """Audit must not report an error when zero edges are promoted."""
    import pandas as pd

    out_dir = tmp_path / "audit_out"
    all_edges_path = tmp_path / "all_edges.csv"

    df = pd.DataFrame({
        "task_id": [0],
        "country": ["FR"],
        "scenario": ["main"],
        "window_start": [2015],
        "window_end": [2020],
        "source_sector": ["IND"],
        "target_sector": ["AGR"],
        "n_samples": [10],
        "beta": [None],
        "delta_r2": [None],
        "p_perm": [None],
        "bootstrap_sign_stability": [None],
        "q_fdr": [None],
    })
    df.to_csv(all_edges_path, index=False)

    manifest = [
        {
            "schema_version": "1.0",
            "task_id": 0,
            "country": "FR",
            "scenario": "main",
            "window_start": 2015,
            "window_end": 2020,
            "source_sector": "IND",
            "targets": ["AGR"],
            "seed": 42,
            "n_permutations": 9,
            "n_bootstraps": 9,
            "panel_checksum": "a" * 64,
            "commit_sha": "b" * 40,
            "expected_output": "task_000000.json",
        }
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    result = run_script(
        SCRIPTS_DIR / "audit_sector_precedence_results.py",
        "--all-edges", str(all_edges_path),
        "--manifest", str(manifest_path),
        "--out-dir", str(out_dir),
    )
    assert result.returncode == 0, f"Audit failed on zero-promoted edges (should PASS): {result.stderr}"
    report = json.loads((out_dir / "audit_report.json").read_text())
    assert report["errors"] == 0
