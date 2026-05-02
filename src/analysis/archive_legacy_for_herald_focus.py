"""
Move legacy exploratory artifacts out of the active repository surface.

This script is conservative: it moves files into old/ instead of deleting them
and writes a manifest with every move. The active surface is intentionally kept
small for HERALD training/publication work.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD_ROOT = ROOT / "old" / "legacy_before_herald_focus_2026_04_27"
MANIFEST = OLD_ROOT / "MANIFEST.csv"


ACTIVE_SRC = {
    "src/data/train_herald_v3.py",
    "src/data/plot_herald_v3_dashboard.py",
    "src/data/analyze_herald_v3_statistical_evidence.py",
    # Paper comparators retained as active baselines.
    "src/data/evaluate_dynamic_feature_panel_baselines_v1.py",
    "src/data/train_dynamic_stgnn_models_v1.py",
    # Feature-panel builder retained for reproducibility on a stronger machine.
    "src/data/build_dynamic_stgnn_feature_panel_v1.py",
}

ACTIVE_REPORTS = {
    "reports/README.md",
    "reports/PROJECT_STATE_INDEX_V0.md",
    "reports/PROJECT_JOURNEY.md",
    "reports/METHODOLOGICAL_POSITIONING_V0.md",
    "reports/HERALD_V3_MODEL_V1.md",
    "reports/herald_v3_metrics_v1.json",
    "reports/HERALD_V3_STATISTICAL_EVIDENCE_V1.md",
    "reports/herald_v3_statistical_evidence_v1.json",
    "reports/herald_v3_dm_tests_v1.csv",
    "reports/herald_v3_gamma_stability_v1.csv",
    "reports/herald_v3_top_neighbors_v1.csv",
    "reports/herald_v3_zone_strata_v1.csv",
    "reports/DYNAMIC_FEATURE_PANEL_BASELINE_V1.md",
    "reports/dynamic_feature_panel_baseline_metrics_v1.json",
    "reports/DYNAMIC_STGNN_MODEL_TRAINING_V1.md",
    "reports/dynamic_stgnn_model_metrics_v1.json",
    "reports/dynamic_stgnn_model_metrics_seed_0_v1.json",
    "reports/dynamic_stgnn_model_metrics_seed_7_v1.json",
    "reports/dynamic_stgnn_model_metrics_seed_42_v1.json",
}

ACTIVE_PROCESSED = {
    # HERALD-ready feature panel and walk-forward comparator predictions.
    "data/processed/dynamic_stgnn_feature_panel_v1.csv",
    "data/processed/dynamic_feature_panel_baseline_predictions_v1.csv",
    "data/processed/dynamic_stgnn_model_predictions_v1.csv",
    "data/processed/dynamic_stgnn_model_predictions_seed_0_v1.csv",
    "data/processed/dynamic_stgnn_model_predictions_seed_7_v1.csv",
    "data/processed/dynamic_stgnn_model_predictions_seed_42_v1.csv",
    # Graph priors and node order.
    "data/processed/graph_adjacency_core_v0.csv",
    "data/processed/graph_adjacency_mobility_v0.csv",
    "data/processed/graph_node_index_core_v0.csv",
    "data/processed/graph_edge_index_core_v0.csv",
    "data/processed/graph_edges_ze2020_core_v0.csv",
    "data/processed/graph_nodes_ze2020_core_v0.csv",
    # Source panels used to rebuild HERALD panel if needed.
    "data/processed/flores_panel_ze2020_annual_v1.csv",
    "data/processed/side_stocks_lagged_ze2020_annual_v1.csv",
    "data/processed/target_side_establishments_annual_core_v0.csv",
    # Current HERALD V3 outputs.
    *{f"data/processed/herald_v3_predictions_{ab}_seed_{seed}_v1.csv"
      for ab in [
          "full",
          "self_only",
          "static_adaptive",
          "fixed_geo_mob_only",
          "dynamic_adaptive_no_quarterly",
          "dynamic_adaptive_no_regime",
          "dynamic_adaptive_no_smooth",
      ]
      for seed in [0, 7, 42]},
    *{f"data/processed/herald_v3_internals_{ab}_seed_{seed}_v1.npz"
      for ab in [
          "full",
          "self_only",
          "static_adaptive",
          "fixed_geo_mob_only",
          "dynamic_adaptive_no_quarterly",
          "dynamic_adaptive_no_regime",
          "dynamic_adaptive_no_smooth",
      ]
      for seed in [0, 7, 42]},
}

ACTIVE_METADATA = {
    "metadata/dynamic_stgnn_walk_forward_splits_v1.csv",
    "metadata/data_catalog_dynamic_stgnn_v1.csv",
    "metadata/canonical_artifacts_v0.csv",
    "metadata/report_consolidation_inventory_v1.csv",
    "metadata/CATALOGUE_INSEE_DATASETS_FR.md",
    "metadata/CATALOGO_INSEE_DATASETS.md",
}

ACTIVE_FIGURES = {
    "reports/figures/herald_v3_finetuning_dashboard_v1.html",
}


def move_file(path: Path, bucket: str, moves: list[tuple[str, str, str]]) -> None:
    rel = path.relative_to(ROOT).as_posix()
    target = OLD_ROOT / bucket / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        suffix = 1
        while True:
            alt = target.with_name(f"{target.stem}__dup{suffix}{target.suffix}")
            if not alt.exists():
                target = alt
                break
            suffix += 1
    shutil.move(str(path), str(target))
    moves.append((rel, target.relative_to(ROOT).as_posix(), bucket))


def archive_top_level_files(folder: str, active: set[str], bucket: str, moves: list[tuple[str, str, str]]) -> None:
    base = ROOT / folder
    if not base.exists():
        return
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel not in active:
            move_file(path, bucket, moves)


def archive_reports_dirs(moves: list[tuple[str, str, str]]) -> None:
    # Keep reports/figures but move old non-HERALD-V3 figure files.
    fig_dir = ROOT / "reports" / "figures"
    if fig_dir.exists():
        for path in sorted(fig_dir.iterdir()):
            if path.is_file() and path.relative_to(ROOT).as_posix() not in ACTIVE_FIGURES:
                move_file(path, "reports_figures_legacy", moves)

    # Existing report archives are no longer part of the active surface.
    archive_dir = ROOT / "reports" / "archive"
    if archive_dir.exists():
        target = OLD_ROOT / "reports_archive_legacy" / "reports" / "archive"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(archive_dir), str(target))
        moves.append(("reports/archive", target.relative_to(ROOT).as_posix(), "reports_archive_legacy"))


def write_manifest(moves: list[tuple[str, str, str]]) -> None:
    OLD_ROOT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["original_path", "archived_path", "bucket"])
        writer.writerows(moves)


def main() -> None:
    moves: list[tuple[str, str, str]] = []
    archive_top_level_files("src/data", ACTIVE_SRC, "src_data_legacy", moves)
    archive_top_level_files("reports", ACTIVE_REPORTS, "reports_legacy", moves)
    archive_top_level_files("data/processed", ACTIVE_PROCESSED, "data_processed_legacy", moves)
    archive_top_level_files("metadata", ACTIVE_METADATA, "metadata_legacy", moves)
    archive_reports_dirs(moves)
    write_manifest(moves)
    print(f"Moved {len(moves)} files/directories into {OLD_ROOT.relative_to(ROOT)}")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
