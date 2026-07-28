"""Recompute the two recoverable HERALD_23 ranking metrics from stored predictions.

Implements HERALD_59 section 10 exactly, pre-registered under the DEC-086
correction addendum in a commit that precedes this file.

This module **fits nothing**.  It imports no estimator, reruns no gate and
launches no job.  It reads the per-cell predictions the corrected HERALD_38
section 8 runs already wrote and computes two metrics that were never reported:

  * ``Recall@3``, undefined when a group holds no positive;
  * the average future growth of the three selected sectors.

It **cannot promote anything**.  DEC-069, DEC-078 and DEC-080 closed their
targets, and the HERALD_38 section 8 conclusion -- that the relation layer fails
against no-relation, base-formula and shuffled controls -- stands regardless of
these numbers.  A favourable figure here is a coverage completion, not evidence.

Run with ``python3.10``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HPC_RESULTS = ROOT / "hpc_results"
DEFAULT_OUT_DIR = ROOT / "data/processed/france_ze2020"

# HERALD_59 section 10.2.  The target_shuffle scenario INSIDE the two main
# directories is INVALID_FOR_CLAIMS (HERALD_38 section 8) and is replaced by the
# corrected rerun directories.  The smoke run is excluded entirely.
MAIN_RUNS = {
    "top3": "fr_ze2020_top3_entry_temporal_fix_top3_20260713_143828",
    "lift": "fr_ze2020_top3_entry_lift_temporal_fix_lift_20260713_143828",
}
TARGET_SHUFFLE_RERUNS = {
    "top3": "fr_ze2020_top3_entry_temporal_fix_target_top3_20260713_145326",
    "lift": "fr_ze2020_top3_entry_lift_temporal_fix_target_lift_20260713_145326",
}
MAIN_SCENARIOS = ("full_control", "sector_shuffle", "temporal_shuffle")
TARGET_SCENARIO = "target_shuffle"

FORBIDDEN_RUN_SUBSTRINGS = (
    "fr_ze2020_sector_ranking_20260701",
    "fr_ze2020_sector_ranking_falsifications_20260701",
    "fr_ze2020_dynamic_graph_ranker_20260702",
    "fr_ze2020_top3_entry_20260708",
    "smoke",
)

GROUP_KEYS = ["ze2020", "decision_year", "model", "feature_config"]
PAIR_KEYS = ["ze2020", "decision_year", "model", "seed", "scenario"]

# HERALD_59 section 10.3, amended: group size varies 3..9 with candidate
# availability and label maturity; selection is min(3, size).  The size is
# identical across feature configs within a cell, which is what keeps the paired
# comparison on identical populations.
# No lower or upper bound on group size is registered: none is justified by the
# corpus, and the two bounds tried earlier were sampled from one task.  What is
# registered are the invariants that hold everywhere.
TOP_K = 3

# HERALD_59 section 10.6, amended: the two tasks carry different config sets.
TASK_PAIRS = {
    "top3": (
        ("base_formula_features", "no_relation_features"),
        ("base_formula_features", "shuffled_relation_features"),
        ("no_relation_features", "shuffled_relation_features"),
    ),
    "lift": (
        ("base_formula_features", "no_relation_features"),
        ("base_plus_target_aligned_lifts", "no_relation_features"),
        ("target_aligned_lift_features", "no_relation_features"),
        ("base_plus_target_aligned_lifts", "shuffled_target_aligned_lifts"),
        ("target_aligned_lift_features", "shuffled_target_aligned_lifts"),
    ),
}

# 2 tasks x 4 scenarios x 5 seeds.  Registered so a partial corpus aborts
# instead of silently shrinking the population.
EXPECTED_SEEDS = (42, 43, 44, 45, 46)
EXPECTED_FILE_COUNT = 40

# Per-file schema, closed.  A stored prediction table is the only evidence this
# module has; if it is malformed the metrics below are meaningless, so every
# assumption is checked at the door rather than inferred later.
REQUIRED_COLUMNS = (
    "ze2020",
    "sector_code",
    "decision_year",
    "target_growth",
    "target_top3_label",
    "target_horizon_years",
    "model",
    "rank_predicted",
    "feature_config",
    "seed",
    "claim_status",
    "falsification_scenario",
)
ESSENTIAL_NON_NULL = REQUIRED_COLUMNS
EXPECTED_HORIZON = 3
EXPECTED_DECISION_YEARS = (2019, 2020, 2021, 2022)
EXPECTED_MODELS = ("logit_entry_classifier", "mlp_entry_classifier")
EXPECTED_LABELS = (0, 1)
TASK_FEATURE_CONFIGS = {
    "top3": (
        "base_formula_features",
        "no_relation_features",
        "shuffled_relation_features",
    ),
    "lift": (
        "base_formula_features",
        "no_relation_features",
        "base_plus_target_aligned_lifts",
        "target_aligned_lift_features",
        "shuffled_target_aligned_lifts",
    ),
}
FILE_GROUP_KEYS = ["ze2020", "decision_year", "model", "feature_config"]

CLAIM_STATUS = "ranking_metric_coverage_completion_not_promotion_evidence"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_prediction_files(hpc_results: Path = HPC_RESULTS) -> pd.DataFrame:
    """Enumerate the admissible prediction files, refusing forbidden sources."""
    rows: list[dict[str, object]] = []
    for task, run in MAIN_RUNS.items():
        for scenario in MAIN_SCENARIOS:
            for path in sorted((hpc_results / run / scenario).glob("seed_*/*predictions_v1.csv")):
                rows.append({"task": task, "scenario": scenario, "path": path})
    for task, run in TARGET_SHUFFLE_RERUNS.items():
        for path in sorted(
            (hpc_results / run / TARGET_SCENARIO).glob("seed_*/*predictions_v1.csv")
        ):
            rows.append({"task": task, "scenario": TARGET_SCENARIO, "path": path})

    frame = pd.DataFrame(rows)
    assert not frame.empty, "no admissible prediction file found"
    assert_sources_admissible(frame)
    assert_corpus_complete(frame)
    return frame


def assert_corpus_complete(frame: pd.DataFrame) -> None:
    """Refuse a partial corpus.

    A partially synced ``hpc_results/`` would otherwise yield a smaller and
    silently different population, and every mean below would be computed over
    it without complaint.
    """
    expected = {
        (task, scenario, seed)
        for task in MAIN_RUNS
        for scenario in MAIN_SCENARIOS + (TARGET_SCENARIO,)
        for seed in EXPECTED_SEEDS
    }
    found = {
        (row.task, row.scenario, int(Path(row.path).parent.name.split("_")[-1]))
        for row in frame.itertuples(index=False)
    }
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    assert not missing, f"prediction corpus is incomplete; missing {missing}"
    assert not extra, f"prediction corpus holds unexpected members: {extra}"
    assert len(frame) == EXPECTED_FILE_COUNT, (
        f"expected {EXPECTED_FILE_COUNT} prediction files, found {len(frame)}"
    )


def assert_sources_admissible(frame: pd.DataFrame) -> None:
    """Blocking: no INVALID_FOR_CLAIMS run, and no superseded target_shuffle."""
    for path in frame["path"]:
        text = str(path)
        for forbidden in FORBIDDEN_RUN_SUBSTRINGS:
            assert forbidden not in text, f"forbidden source read: {path}"
        if f"/{TARGET_SCENARIO}/" in text:
            assert any(run in text for run in TARGET_SHUFFLE_RERUNS.values()), (
                "target_shuffle must come from the corrected rerun directories; "
                f"the superseded scenario inside a main run was read: {path}"
            )


def validate_prediction_file(
    part: pd.DataFrame, task: str, scenario: str, seed: int, path: Path
) -> None:
    """Close the schema of one stored prediction file.

    Runs immediately after the read and **before** `task` and `scenario` are
    attached, so the file is judged on what it contains rather than on what the
    directory tree asserts about it.  Every check below is a way the metrics
    downstream could be silently wrong.
    """
    where = f"{path}"

    missing = [c for c in REQUIRED_COLUMNS if c not in part.columns]
    assert not missing, f"{where}: missing required columns {missing}"

    for column in ESSENTIAL_NON_NULL:
        assert part[column].notna().all(), f"{where}: nulls in {column}"

    # The directory tree and the file contents must agree; either could be wrong.
    file_seeds = set(part["seed"].unique())
    assert file_seeds == {seed}, f"{where}: internal seed {file_seeds} != directory seed {seed}"
    file_scenarios = set(part["falsification_scenario"].unique())
    assert file_scenarios == {scenario}, (
        f"{where}: internal scenario {file_scenarios} != directory scenario {scenario!r}"
    )

    horizons = set(part["target_horizon_years"].unique())
    assert horizons == {EXPECTED_HORIZON}, f"{where}: horizon {horizons} != {EXPECTED_HORIZON}"

    years = set(int(y) for y in part["decision_year"].unique())
    unexpected = sorted(years - set(EXPECTED_DECISION_YEARS))
    assert not unexpected, f"{where}: decision years outside 2019-2022: {unexpected}"

    models = set(part["model"].unique())
    assert models <= set(EXPECTED_MODELS), f"{where}: unknown model {sorted(models - set(EXPECTED_MODELS))}"

    labels = set(int(v) for v in part["target_top3_label"].unique())
    assert labels <= set(EXPECTED_LABELS), f"{where}: target_top3_label not binary: {sorted(labels)}"

    for column in ("target_growth", "rank_predicted"):
        values = part[column].to_numpy(dtype=float)
        assert np.isfinite(values).all(), f"{where}: {column} carries a non-finite value"

    ranks = part["rank_predicted"].to_numpy(dtype=float)
    assert np.all(ranks == np.floor(ranks)), f"{where}: rank_predicted is not integral"
    assert (ranks >= 1).all(), f"{where}: rank_predicted is not a positive integer"

    expected_configs = set(TASK_FEATURE_CONFIGS[task])
    found_configs = set(part["feature_config"].unique())
    assert found_configs == expected_configs, (
        f"{where}: feature configs {sorted(found_configs)} != expected {sorted(expected_configs)} "
        f"for task {task}"
    )

    statuses = set(part["claim_status"].dropna().unique())
    assert len(statuses) == 1, f"{where}: claim_status is not uniform: {sorted(statuses)}"
    assert str(next(iter(statuses))).strip(), f"{where}: claim_status is empty"

    duplicated = part.duplicated(FILE_GROUP_KEYS + ["sector_code", "seed"]).sum()
    assert duplicated == 0, f"{where}: {duplicated} duplicated ZE-year-model-config-sector rows"

    # Ranks must be a permutation of 1..n inside each group: a duplicate or a gap
    # would make "top 3" ambiguous.
    for key, block in part.groupby(FILE_GROUP_KEYS, sort=False):
        observed = sorted(int(r) for r in block["rank_predicted"])
        assert observed == list(range(1, len(block) + 1)), (
            f"{where}: ranks in group {key} are {observed}, not 1..{len(block)}"
        )


def load_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for row in frame.itertuples(index=False):
        path = Path(row.path)
        seed = int(path.parent.name.split("_")[-1])
        part = pd.read_csv(path, dtype={"ze2020": str})
        validate_prediction_file(part, row.task, row.scenario, seed, path)
        part["task"] = row.task
        part["scenario"] = row.scenario
        parts.append(part)
    out = pd.concat(parts, ignore_index=True)
    assert np.isfinite(out["target_growth"].to_numpy(dtype=float)).all(), (
        "target_growth carries a non-finite value"
    )
    return out


def group_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """One row per (task, scenario, seed) x group, with both registered metrics.

    Recall@3 is NaN, never zero and never one, when the group holds no positive:
    the denominator does not exist, so neither does the quantity.
    """
    keys = ["task", "scenario", "seed"] + GROUP_KEYS
    grouped = predictions.groupby(keys, sort=True)

    sizes = grouped.size().rename("group_size")
    assert (sizes >= 1).all(), "an empty group reached the metric stage"

    selected = predictions[predictions["rank_predicted"] <= TOP_K]
    selected_sizes = selected.groupby(keys, sort=True).size().rename("selected")
    expected = sizes.clip(upper=TOP_K)
    assert (selected_sizes == expected).all(), (
        "selection is not min(3, group size) in every group"
    )

    positives = grouped["target_top3_label"].sum().rename("positives_in_group")
    hits = selected.groupby(keys, sort=True)["target_top3_label"].sum().rename("hits")
    growth_selected = (
        selected.groupby(keys, sort=True)["target_growth"].mean().rename("mean_growth_selected")
    )
    growth_ceiling = (
        grouped["target_growth"]
        .apply(lambda s: s.nlargest(TOP_K).mean())
        .rename("mean_growth_actual_top3")
    )

    out = pd.concat(
        [sizes, selected_sizes, positives, hits, growth_selected, growth_ceiling], axis=1
    ).reset_index()
    # Cross-check only; Precision@3 is already published by the original runs.
    out["precision_at_selected"] = out["hits"] / out["selected"]
    # The zero-positive rule, fixed in HERALD_59 section 10.4.
    out["recall_at_3"] = np.where(
        out["positives_in_group"] > 0,
        out["hits"] / out["positives_in_group"].replace(0, np.nan),
        np.nan,
    )
    out["recall_undefined"] = out["positives_in_group"] == 0
    return out


def summarize(groups: pd.DataFrame) -> pd.DataFrame:
    """Means per task, scenario, model and feature config, with the undefined count."""
    keys = ["task", "scenario", "model", "feature_config"]
    rows = []
    for key, block in groups.groupby(keys, sort=True):
        defined = block[~block["recall_undefined"]]
        rows.append(
            {
                **dict(zip(keys, key)),
                "groups": int(len(block)),
                "recall_undefined_groups": int(block["recall_undefined"].sum()),
                "mean_recall_at_3": float(defined["recall_at_3"].mean()),
                "mean_precision_at_selected": float(block["precision_at_selected"].mean()),
                "mean_growth_selected": float(block["mean_growth_selected"].mean()),
                "mean_growth_actual_top3": float(block["mean_growth_actual_top3"].mean()),
            }
        )
    return pd.DataFrame(rows)


def paired_comparisons(groups: pd.DataFrame) -> pd.DataFrame:
    """Paired within (ze2020, decision_year, model, seed, scenario), per task."""
    rows = []
    for (task, scenario, model), block in groups.groupby(
        ["task", "scenario", "model"], sort=True
    ):
        pairs = TASK_PAIRS[task]
        wide = block.pivot_table(
            index=["ze2020", "decision_year", "seed"],
            columns="feature_config",
            values=["recall_at_3", "mean_growth_selected"],
        )
        for metric in ("recall_at_3", "mean_growth_selected"):
            for left, right in pairs:
                if (metric, left) not in wide or (metric, right) not in wide:
                    continue
                pair = wide[[(metric, left), (metric, right)]].dropna()
                if pair.empty:
                    continue
                a = pair[(metric, left)].to_numpy(dtype=float)
                b = pair[(metric, right)].to_numpy(dtype=float)
                rows.append(
                    {
                        "task": task,
                        "scenario": scenario,
                        "model": model,
                        "metric": metric,
                        "left": left,
                        "right": right,
                        "groups": int(len(pair)),
                        "mean_left": float(a.mean()),
                        "mean_right": float(b.mean()),
                        "left_wins_share": float((a > b).mean()),
                        "ties_share": float((a == b).mean()),
                    }
                )
    return pd.DataFrame(rows)


def assert_populations_identical(groups: pd.DataFrame) -> None:
    """Feature configs must cover the same groups, and the same sizes, within a cell."""
    keys = ["task", "scenario", "model", "seed"]
    for key, block in groups.groupby(keys, sort=True):
        # Compare the groups AND their sizes: two configs could cover the same
        # territory-years with different candidate counts and still look aligned.
        universes = {
            config: {
                (row.ze2020, int(row.decision_year), int(row.group_size))
                for row in part.itertuples(index=False)
            }
            for config, part in block.groupby("feature_config")
        }
        reference = None
        for config, universe in universes.items():
            if reference is None:
                reference = universe
            assert universe == reference, (
                f"feature config {config} covers a different group population or "
                f"different group sizes at {key}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hpc-results", type=Path, default=HPC_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    files = collect_prediction_files(args.hpc_results)
    predictions = load_predictions(files)
    groups = group_metrics(predictions)
    assert_populations_identical(groups)

    summary = summarize(groups)
    paired = paired_comparisons(groups)

    for frame, name in ((summary, "summary"), (paired, "paired")):
        numeric = frame.select_dtypes(include=[float])
        assert np.isfinite(numeric.to_numpy(dtype=float)).all(), (
            f"{name} carries a non-finite figure"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "fr_ze2020_ranking_metric_coverage_summary_v1.csv"
    paired_path = args.output_dir / "fr_ze2020_ranking_metric_coverage_paired_v1.csv"
    manifest_path = args.output_dir / "fr_ze2020_ranking_metric_coverage_v1.json"

    summary.to_csv(summary_path, index=False)
    paired.to_csv(paired_path, index=False)

    manifest = {
        "artifact": "fr_ze2020_ranking_metric_coverage",
        "specification": "reports/canonical/HERALD_59_FR_ZE2020_RANKING_GAP_AUDIT.md section 10",
        "decision": "DEC-086 correction addendum",
        "claim_status": CLAIM_STATUS,
        "cannot_promote": (
            "DEC-069, DEC-078 and DEC-080 closed their targets; the HERALD_38 section 8 "
            "conclusion stands regardless of these figures. This completes a metric "
            "checklist and is not evidence for promotion."
        ),
        "models_fitted": 0,
        "jobs_launched": 0,
        "source_files": [str(p.relative_to(ROOT)) for p in files["path"]],
        "source_file_count": int(len(files)),
        "source_sha256": {
            str(p.relative_to(ROOT)): sha256(p) for p in files["path"]
        },
        "groups": int(len(groups)),
        "recall_undefined_groups": int(groups["recall_undefined"].sum()),
        "recall_undefined_rule": (
            "a group with no positive has no Recall@3; reported NaN, excluded from every "
            "mean, counted, never imputed"
        ),
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "output_sha256": {
            summary_path.name: sha256(summary_path),
            paired_path.name: sha256(paired_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"Read {len(files)} prediction files, {len(groups)} groups")
    print(f"Recall undefined in {int(groups['recall_undefined'].sum())} groups")
    print(f"Wrote {summary_path}")
    print(f"Wrote {paired_path}")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
