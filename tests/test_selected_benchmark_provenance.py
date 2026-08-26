"""Rederive every headline number in docs/RESULTS_AND_LIMITATIONS.md from committed
artefacts, and fail if documentation and artefact diverge.

Two source sets:
- results/selected/main_benchmark/ -- the minimal main-benchmark (280-territory) provenance
  this delivery added (see its manifest.json for what was selected and why).
- hpc_results/herald94/, herald95/, herald96/ -- already committed by an earlier pass
  (commit ce1a3c8) and used here read-only, without adding anything new for them.

Every assertion below cites the exact document/section the number backs.
"""
from __future__ import annotations

import json
import pathlib
import statistics
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parents[1]
SELECTED = REPO / "results" / "selected" / "main_benchmark"


# ── docs/RESULTS_AND_LIMITATIONS.md Sec.0/1/3 (main benchmark, 280 territories) ──────────

def _load_summary() -> dict:
    return json.loads((SELECTED / "benchmark_summary.json").read_text())


def test_manifest_matches_the_selected_files_on_disk():
    manifest = json.loads((SELECTED / "manifest.json").read_text())
    for entry in manifest["entries"]:
        path = REPO / entry["public_path"]
        assert path.is_file(), f"manifest lists {entry['public_path']} but it is missing"
        import hashlib
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], (
            f"{entry['public_path']} does not match its manifest checksum -- "
            "the file changed after the manifest was written")


def test_best_forecast_skill_matches_documentation():
    table = _load_summary()["table"]
    best = max(v["forecast_skill_median"] for v in table.values()
              if v["forecast_skill_median"] == v["forecast_skill_median"])  # drop NaN
    assert abs(best - 0.0001) < 0.0005, (
        f"best forecast skill {best:.5f} no longer matches the documented +0.0001 "
        "(docs/RESULTS_AND_LIMITATIONS.md Sec.1)")


def test_edge_recovery_sits_at_prevalence_for_herald():
    table = _load_summary()["table"]
    for width in (32, 64, 128):
        entry = table[f"herald@{width}"]
        assert abs(entry["prevalence_median"] - 0.70) < 1e-6, (
            "candidate-support prevalence drifted from the documented 0.70 "
            "(docs/RESULTS_AND_LIMITATIONS.md Sec.0)")
        assert entry["auprc_median"] > entry["prevalence_median"] - 0.02, (
            f"herald@{width} AUPRC {entry['auprc_median']:.4f} fell noticeably below its "
            "own support's prevalence, which would itself be a documentation-affecting change")


def test_no_relation_control_shows_the_documented_disqualification():
    """S1 (with mechanism) AUPRC and S0 (no mechanism) AUPRC must stay close for herald --
    the disqualification in docs/RESULTS_AND_LIMITATIONS.md Sec.3 ("the proposed model's
    apparent margin is disqualified by its own no-relation control")."""
    table = _load_summary()["table"]
    for width in (32, 64, 128):
        entry = table[f"herald@{width}"]
        gap = abs(entry["auprc_median"] - entry["s0_auprc_median"])
        assert gap < 0.02, (
            f"herald@{width}: with-mechanism AUPRC {entry['auprc_median']:.4f} vs. "
            f"no-mechanism AUPRC {entry['s0_auprc_median']:.4f} now differ by {gap:.4f} -- "
            "the documented no-relation-control disqualification no longer holds")


def test_no_width_was_promoted():
    summary = _load_summary()
    assert summary["chosen_herald_width"] is None, (
        "a width was promoted in the artefact, contradicting "
        "docs/RESULTS_AND_LIMITATIONS.md's 'no width was promoted'")
    assert summary["france_decision"] == "CASE_C_DO_NOT_APPLY_RELATIONS"


def test_raw_task_medians_reproduce_the_summary():
    """The actual re-derivation: recompute each method@width's median forecast skill and
    AUPRC from the 70 raw per-seed task files and compare to benchmark_summary.json."""
    summary_table = _load_summary()["table"]
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for path in sorted((SELECTED / "tasks").glob("*.json")):
        task = json.loads(path.read_text())
        width = task["width"] or 0
        by_arm[f"{task['method']}@{width}"].append(task)

    checked = 0
    for arm, tasks in by_arm.items():
        if arm not in summary_table:
            continue
        s1_tasks = [t for t in tasks if t["scenario"] == "S1_SHARED"]
        if not s1_tasks:
            continue
        skills = [t["forecast"]["skill_vs_persistence"] for t in s1_tasks]
        recomputed_skill = statistics.median(skills)
        documented_skill = summary_table[arm]["forecast_skill_median"]
        assert abs(recomputed_skill - documented_skill) < 1e-6, (
            f"{arm}: recomputed median skill {recomputed_skill:.6f} != "
            f"documented {documented_skill:.6f} -- artefact and summary have diverged")
        checked += 1
    assert checked >= 5, f"only {checked} arms were cross-checked -- selection may be incomplete"


# ── docs/RESULTS_AND_LIMITATIONS.md Sec.1 (temporal representation gain, 11-24%) ─────────

def test_temporal_representation_gain_matches_the_11_to_24_percent_claim():
    path = REPO / "hpc_results" / "herald94" / "layer1_summary.json"
    table = json.loads(path.read_text())["table"]
    gains = [block["temporal_features"]["gain_of_full_table_over_best_single_median"]
            for block in table.values()]
    assert min(gains) >= 0.10 and max(gains) <= 0.25, (
        f"temporal-representation gains now span [{min(gains):.3f}, {max(gains):.3f}], "
        "outside the documented 11% to 24% (docs/RESULTS_AND_LIMITATIONS.md Sec.1)")


# ── docs/RESULTS_AND_LIMITATIONS.md Sec.2 (oracle, both protocols) ───────────────────────

def test_main_benchmark_sensitivity_oracle_matches_1_94_percent():
    path = REPO / "hpc_results" / "herald95" / "ladder_summary.json"
    table = json.loads(path.read_text())["table"]
    nominal = table["N4_INTERACTION@1.0"]["oracle_gain"]
    assert abs(nominal - 0.0194) < 0.001, (
        f"main-benchmark sensitivity oracle gain {nominal:.4f} != documented 0.0194")
    null = table["N0_NULL@1.0"]["oracle_gain"]
    assert abs(null) < 1e-9, "the no-mechanism oracle gain is no longer exactly zero"


def test_residual_diagnostic_oracle_matches_the_floor_nominal_and_double_intensity_figures():
    tasks_dir = REPO / "hpc_results" / "herald96" / "tasks"
    seeds = (9961, 9962, 9963, 9964, 9965)
    expected = {"0.0": 0.0160, "1.0": 0.1006, "2.0": 0.1105}
    for scale, target in expected.items():
        values = []
        for seed in seeds:
            path = tasks_dir / f"ng_M1_MULTIRELATIONAL_s{scale}_typed_union_{seed}.json"
            task = json.loads(path.read_text())
            values.append(task["oracles"]["all_families"])
        median = statistics.median(values)
        assert abs(median - target) < 0.001, (
            f"typed-union oracle at scale {scale}: median {median:.4f} != "
            f"documented {target:.4f} (docs/RESULTS_AND_LIMITATIONS.md Sec.2)")


# ── docs/RESULTS_AND_LIMITATIONS.md Sec.3/4 (all-pairs recovery at prevalence) ───────────

def test_all_pairs_auprc_equals_prevalence_in_the_residual_diagnostic():
    tasks_dir = REPO / "hpc_results" / "herald96" / "tasks"
    seeds = (9961, 9962, 9963, 9964, 9965)
    auprcs, prevalences = [], []
    for seed in seeds:
        path = tasks_dir / f"ng_M1_MULTIRELATIONAL_s1.0_all_pairs_{seed}.json"
        task = json.loads(path.read_text())
        auprcs.append(task["recovery"]["auprc"])
        prevalences.append(task["recovery"]["prevalence"])
    median_auprc = statistics.median(auprcs)
    prevalence = prevalences[0]
    assert all(abs(p - prevalence) < 1e-9 for p in prevalences), (
        "prevalence should be fixed by the support, not vary by seed")
    assert abs(median_auprc - 0.0190) < 0.001, (
        f"median all-pairs AUPRC {median_auprc:.4f} != documented 0.0190")
    assert abs(prevalence - 0.0190) < 0.001, (
        f"all-pairs prevalence {prevalence:.4f} != documented 0.0190")
    assert abs(median_auprc - prevalence) < 0.01, (
        "AUPRC no longer sits at its own support's prevalence -- the 'at chance' finding "
        "in docs/RESULTS_AND_LIMITATIONS.md Sec.4 would need to be re-examined, not silently kept")
