"""Tests for the ranking metric recomputation (HERALD_59 section 10, DEC-086).

The recomputer fits nothing, so these tests fix the rules that make its output
readable: source admissibility, the selection invariant, and above all the
zero-positive rule for Recall@3, which is the one place where a silent default
would corrupt every mean downstream.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.recompute_fr_ze2020_ranking_metrics import (  # noqa: E402
    FORBIDDEN_RUN_SUBSTRINGS,
    GROUP_KEYS,
    MAIN_RUNS,
    TARGET_SCENARIO,
    TARGET_SHUFFLE_RERUNS,
    TASK_PAIRS,
    TOP_K,
    EXPECTED_FILE_COUNT,
    assert_corpus_complete,
    assert_populations_identical,
    assert_sources_admissible,
    collect_prediction_files,
    group_metrics,
    paired_comparisons,
    summarize,
)

SUMMARY_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_ranking_metric_coverage_summary_v1.csv"
MANIFEST_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_ranking_metric_coverage_v1.json"


def _synthetic(positives: list[int], n_sectors: int = 9, config: str = "base_formula_features"):
    """One group per entry in `positives`, with that many positive labels.

    The top-`k` selected rows are the first `k` by `rank_predicted`, and the
    positives are placed on the selected rows first, so `hits` is known.
    """
    rows = []
    for index, n_pos in enumerate(positives):
        for sector in range(n_sectors):
            rows.append(
                {
                    "task": "top3",
                    "scenario": "full_control",
                    "seed": 42,
                    "ze2020": f"{index:04d}",
                    "decision_year": 2019,
                    "model": "logit_entry_classifier",
                    "feature_config": config,
                    "sector_code": f"S{sector}",
                    "rank_predicted": sector + 1,
                    "target_top3_label": 1 if sector < n_pos else 0,
                    "target_growth": float(sector),
                }
            )
    return pd.DataFrame(rows)


# --- the zero-positive rule ----------------------------------------------


def test_recall_is_undefined_not_zero_when_no_positive() -> None:
    """A group with no positive has no recall. Zero would be a silent lie."""
    out = group_metrics(_synthetic([0]))
    assert bool(out["recall_undefined"].iloc[0]) is True
    assert np.isnan(out["recall_at_3"].iloc[0])


def test_recall_is_undefined_not_one_when_no_positive() -> None:
    out = group_metrics(_synthetic([0]))
    assert out["recall_at_3"].iloc[0] != 1.0


def test_undefined_recall_is_excluded_from_the_mean_and_counted() -> None:
    """The mean must ignore the undefined groups, and their count must survive."""
    out = group_metrics(_synthetic([0, 3, 3]))
    summary = summarize(out)
    assert int(summary["recall_undefined_groups"].iloc[0]) == 1
    assert int(summary["groups"].iloc[0]) == 3
    # the two defined groups both have recall 1.0; a zero-imputed third would give 2/3
    assert summary["mean_recall_at_3"].iloc[0] == pytest.approx(1.0)


def test_recall_differs_from_precision_when_positives_vary() -> None:
    """If the two coincided, the metric would add nothing to the record."""
    out = group_metrics(_synthetic([1, 2, 3]))
    defined = out[~out["recall_undefined"]]
    assert not np.allclose(
        defined["recall_at_3"].to_numpy(dtype=float),
        defined["precision_at_selected"].to_numpy(dtype=float),
    )


def test_recall_matches_its_definition() -> None:
    out = group_metrics(_synthetic([2])).iloc[0]
    assert out["positives_in_group"] == 2
    assert out["hits"] == 2
    assert out["recall_at_3"] == pytest.approx(1.0)


def test_recall_below_one_when_a_positive_is_outside_the_selection() -> None:
    """Four positives, three selected: recall must be 3/4, not 1."""
    out = group_metrics(_synthetic([4])).iloc[0]
    assert out["hits"] == 3
    assert out["recall_at_3"] == pytest.approx(0.75)


# --- growth of the selected ----------------------------------------------


def test_mean_growth_selected_averages_the_selected_rows() -> None:
    out = group_metrics(_synthetic([3])).iloc[0]
    # growth equals the sector index; selected are ranks 1..3 -> 0, 1, 2
    assert out["mean_growth_selected"] == pytest.approx(1.0)


def test_growth_ceiling_is_the_attainable_maximum() -> None:
    out = group_metrics(_synthetic([3])).iloc[0]
    # the three largest growths in a 9-sector group are 6, 7, 8
    assert out["mean_growth_actual_top3"] == pytest.approx(7.0)
    assert out["mean_growth_actual_top3"] >= out["mean_growth_selected"]


# --- selection invariant --------------------------------------------------


def test_selection_is_min_three_and_group_size() -> None:
    small = _synthetic([1], n_sectors=2)
    out = group_metrics(small).iloc[0]
    assert out["group_size"] == 2
    assert out["selected"] == 2


def test_broken_selection_aborts() -> None:
    frame = _synthetic([3])
    frame.loc[frame["rank_predicted"] == 4, "rank_predicted"] = 1  # a fourth selected row
    with pytest.raises(AssertionError, match="min\\(3, group size\\)"):
        group_metrics(frame)


def test_no_lower_bound_on_group_size_is_enforced() -> None:
    """The two bounds tried earlier were sampled from one task; a group of two
    is legitimate and must not abort."""
    out = group_metrics(_synthetic([1], n_sectors=2))
    assert len(out) == 1


# --- population identity --------------------------------------------------


def test_identical_populations_pass() -> None:
    a = _synthetic([3, 2], config="base_formula_features")
    b = _synthetic([3, 2], config="no_relation_features")
    assert_populations_identical(group_metrics(pd.concat([a, b], ignore_index=True)))


def test_divergent_populations_abort() -> None:
    a = _synthetic([3, 2], config="base_formula_features")
    b = _synthetic([3], config="no_relation_features")
    with pytest.raises(AssertionError, match="different group population"):
        assert_populations_identical(group_metrics(pd.concat([a, b], ignore_index=True)))


# --- source admissibility -------------------------------------------------


def test_forbidden_source_aborts() -> None:
    for forbidden in FORBIDDEN_RUN_SUBSTRINGS:
        frame = pd.DataFrame(
            [{"task": "top3", "scenario": "full_control", "path": Path(f"/x/{forbidden}/p.csv")}]
        )
        with pytest.raises(AssertionError, match="forbidden source"):
            assert_sources_admissible(frame)


def test_superseded_target_shuffle_aborts() -> None:
    """target_shuffle inside a main run is INVALID_FOR_CLAIMS (HERALD_38 §8)."""
    bad = Path(f"/x/{MAIN_RUNS['top3']}/{TARGET_SCENARIO}/seed_42/p.csv")
    frame = pd.DataFrame([{"task": "top3", "scenario": TARGET_SCENARIO, "path": bad}])
    with pytest.raises(AssertionError, match="corrected rerun directories"):
        assert_sources_admissible(frame)


def test_corrected_target_shuffle_is_accepted() -> None:
    good = Path(f"/x/{TARGET_SHUFFLE_RERUNS['top3']}/{TARGET_SCENARIO}/seed_42/p.csv")
    frame = pd.DataFrame([{"task": "top3", "scenario": TARGET_SCENARIO, "path": good}])
    assert_sources_admissible(frame)


def test_real_source_set_is_admissible_and_complete() -> None:
    files = collect_prediction_files()
    assert len(files) == 40
    assert set(files["scenario"]) == {
        "full_control",
        "sector_shuffle",
        "temporal_shuffle",
        TARGET_SCENARIO,
    }
    assert set(files["task"]) == {"top3", "lift"}


# --- the recomputer fits nothing -----------------------------------------


def test_module_imports_no_estimator() -> None:
    source = (
        ROOT / "src/modeles/france_ze2020/recompute_fr_ze2020_ranking_metrics.py"
    ).read_text()
    for forbidden in ("sklearn", "torch", "fit(", "Ridge", "MLP"):
        assert forbidden not in source, f"the recomputer must not reference {forbidden}"


# --- paired comparison ----------------------------------------------------


def test_pairs_are_registered_per_task() -> None:
    assert set(TASK_PAIRS) == {"top3", "lift"}
    for pairs in TASK_PAIRS.values():
        for left, right in pairs:
            assert left != right


def test_paired_output_reports_group_counts() -> None:
    a = _synthetic([3, 1], config="base_formula_features")
    b = _synthetic([2, 0], config="no_relation_features")
    paired = paired_comparisons(group_metrics(pd.concat([a, b], ignore_index=True)))
    assert not paired.empty
    assert (paired["groups"] > 0).all()
    assert {"left_wins_share", "ties_share", "mean_left", "mean_right"} <= set(paired.columns)


# --- artifacts ------------------------------------------------------------


def test_manifest_declares_no_promotion() -> None:
    if not MANIFEST_PATH.exists():
        pytest.skip("recomputation not executed yet")
    import json

    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["models_fitted"] == 0
    assert manifest["jobs_launched"] == 0
    assert "not_promotion_evidence" in manifest["claim_status"]
    assert manifest["source_file_count"] == 40
    assert manifest["recall_undefined_groups"] > 0
    assert "never imputed" in manifest["recall_undefined_rule"]


def test_summary_reports_undefined_counts_beside_every_recall() -> None:
    if not SUMMARY_PATH.exists():
        pytest.skip("recomputation not executed yet")
    summary = pd.read_csv(SUMMARY_PATH)
    assert {"mean_recall_at_3", "recall_undefined_groups", "groups"} <= set(summary.columns)
    assert summary["recall_undefined_groups"].notna().all()
    assert np.isfinite(summary["mean_recall_at_3"].to_numpy(dtype=float)).all()


def test_recomputer_is_deterministic(tmp_path: Path) -> None:
    import hashlib

    script = ROOT / "src/modeles/france_ze2020/recompute_fr_ze2020_ranking_metrics.py"
    hashes = []
    for name in ("a", "b"):
        out = tmp_path / name
        result = subprocess.run(
            [sys.executable, str(script), "--output-dir", str(out)],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        hashes.append(
            hashlib.sha256(
                (out / "fr_ze2020_ranking_metric_coverage_summary_v1.csv").read_bytes()
            ).hexdigest()
        )
    assert hashes[0] == hashes[1]


# --- corpus completeness (item 5) -----------------------------------------


def test_partial_corpus_aborts() -> None:
    """A partially synced hpc_results would shrink the population in silence."""
    files = collect_prediction_files()
    with pytest.raises(AssertionError, match="incomplete"):
        assert_corpus_complete(files.iloc[1:])


def test_expected_file_count_is_two_tasks_four_scenarios_five_seeds() -> None:
    assert EXPECTED_FILE_COUNT == 2 * 4 * 5


# --- population identity now includes size (item 4) -----------------------


def test_same_groups_different_sizes_abort() -> None:
    """Two configs may cover the same territory-years with different candidate
    counts; comparing only the group set would let that pass."""
    a = _synthetic([3], n_sectors=9, config="base_formula_features")
    b = _synthetic([3], n_sectors=8, config="no_relation_features")
    with pytest.raises(AssertionError, match="different group sizes"):
        assert_populations_identical(group_metrics(pd.concat([a, b], ignore_index=True)))


# --- the manifest records what it read (item 6) ---------------------------


def test_manifest_records_input_hashes() -> None:
    if not MANIFEST_PATH.exists():
        pytest.skip("recomputation not executed yet")
    import json

    manifest = json.loads(MANIFEST_PATH.read_text())
    hashes = manifest["source_sha256"]
    assert len(hashes) == EXPECTED_FILE_COUNT
    assert set(hashes) == set(manifest["source_files"])
    assert all(len(v) == 64 for v in hashes.values())


# --- "indistinguishable" is a checkable claim (item 7) --------------------

MAX_CONFIG_SPREAD = 0.01
MIN_RECALL_TIE_SHARE = 0.70


def test_configs_are_indistinguishable_in_the_defined_sense() -> None:
    """Pins the claim made in HERALD_59 section 11.2.

    If a regeneration moves these numbers, this test fails and the wording in
    the report must change with it, rather than outliving its evidence.
    """
    if not SUMMARY_PATH.exists():
        pytest.skip("recomputation not executed yet")
    summary = pd.read_csv(SUMMARY_PATH)
    block = summary[(summary.task == "top3") & (summary.scenario == "full_control")]
    assert len(block) == 6
    for metric in ("mean_recall_at_3", "mean_growth_selected"):
        spread = float(block[metric].max() - block[metric].min())
        assert spread <= MAX_CONFIG_SPREAD, f"{metric} spread {spread:.4f} is no longer small"


def test_recall_pairs_are_tie_dominated() -> None:
    paired_path = ROOT / "data/processed/france_ze2020/fr_ze2020_ranking_metric_coverage_paired_v1.csv"
    if not paired_path.exists():
        pytest.skip("recomputation not executed yet")
    paired = pd.read_csv(paired_path)
    block = paired[
        (paired.task == "top3")
        & (paired.scenario == "full_control")
        & (paired.metric == "recall_at_3")
    ]
    assert not block.empty
    assert (block["ties_share"] >= MIN_RECALL_TIE_SHARE).all()


def test_temporal_shuffle_moves_the_two_metrics_in_opposite_directions() -> None:
    """The corrected reading: recall rises, growth falls. The earlier text said
    only that it did not degrade, which was the recall column alone."""
    if not SUMMARY_PATH.exists():
        pytest.skip("recomputation not executed yet")
    summary = pd.read_csv(SUMMARY_PATH)
    sel = summary[
        (summary.task == "top3")
        & (summary.model == "mlp_entry_classifier")
        & (summary.feature_config == "base_formula_features")
    ].set_index("scenario")
    assert sel.loc["temporal_shuffle", "mean_recall_at_3"] > sel.loc["full_control", "mean_recall_at_3"]
    assert sel.loc["temporal_shuffle", "mean_growth_selected"] < sel.loc["full_control", "mean_growth_selected"]
