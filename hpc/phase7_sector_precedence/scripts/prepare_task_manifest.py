"""
Generate the task manifest for the Phase 7 distributed sector precedence study.

Each task covers one (country, scenario, window_end, source_sector) combination.
Targets for each task are all structurally present sectors != source in that country.
BH/FDR is applied by the merge script after all raw p-values are collected; this
script records only the task decomposition and provenance.

Outputs: hpc/phase7_sector_precedence/configs/task_manifest.json
"""
from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PANEL_PATH = (
    REPO_ROOT
    / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
)
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "full_run.json"
MANIFEST_OUT = Path(__file__).resolve().parents[1] / "configs" / "task_manifest.json"
SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def compute_valid_windows(
    available_years: list[int],
    window_years: int,
    exclude_years: frozenset[int],
    min_years: int = 4,
) -> list[tuple[int, int]]:
    windows = []
    for end_year in available_years:
        start_year = end_year - window_years + 1
        usable = [
            y
            for y in available_years
            if start_year <= y <= end_year and y not in exclude_years
        ]
        if len(usable) >= min_years:
            windows.append((start_year, end_year))
    return windows


def main() -> None:
    import pandas as pd

    if not PANEL_PATH.is_file():
        sys.exit(f"Panel not found: {PANEL_PATH}")

    cfg = json.loads(CONFIG_PATH.read_text())
    window_years = int(cfg["window_years"])
    seed = int(cfg["seed"])
    n_permutations = int(cfg["n_permutations"])
    n_bootstraps = int(cfg["n_bootstraps"])
    scenario_exclusions: dict[str, list[int]] = cfg.get("scenario_exclusions", {})

    print(f"Loading panel: {PANEL_PATH}", flush=True)
    panel = pd.read_csv(PANEL_PATH, low_memory=False)
    panel_checksum = sha256_file(PANEL_PATH)
    commit_sha = git_head()
    print(f"Panel checksum: {panel_checksum[:20]}...", flush=True)
    print(f"Commit: {commit_sha}", flush=True)

    scenarios = [("main", frozenset())] + [
        (name, frozenset(yrs)) for name, yrs in scenario_exclusions.items()
    ]

    tasks: list[dict] = []
    task_id = 0

    for country in sorted(panel["country"].unique()):
        country_data = panel[panel["country"] == country]
        # Sectors structurally present in this country
        valid_sectors = sorted(
            country_data[
                country_data["structural_mask"].eq(1)
                & country_data["observation_mask"].eq(1)
            ]["sector_id"].unique()
        )
        available_years = sorted(country_data["observation_year"].unique())

        for scenario_name, exclude_years in scenarios:
            windows = compute_valid_windows(
                available_years, window_years, exclude_years
            )
            for window_start, window_end in windows:
                for source_sector in valid_sectors:
                    # targets = all valid sectors in this country != source
                    targets = [s for s in valid_sectors if s != source_sector]
                    if not targets:
                        continue
                    tasks.append(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "task_id": task_id,
                            "country": country,
                            "scenario": scenario_name,
                            "window_start": window_start,
                            "window_end": window_end,
                            "source_sector": source_sector,
                            "targets": targets,
                            "seed": seed,
                            "n_permutations": n_permutations,
                            "n_bootstraps": n_bootstraps,
                            "panel_checksum": panel_checksum,
                            "commit_sha": commit_sha,
                            "expected_output": f"task_{task_id:06d}.json",
                        }
                    )
                    task_id += 1

    if not tasks:
        sys.exit("ERROR: manifest is empty — no valid tasks derived from panel.")

    # Validate: all task_ids are contiguous from 0
    ids = [t["task_id"] for t in tasks]
    assert ids == list(range(len(ids))), "task_ids are not contiguous from 0"

    # Validate: no duplicates (country, scenario, window_end, source_sector)
    keys = [
        (t["country"], t["scenario"], t["window_start"], t["window_end"], t["source_sector"])
        for t in tasks
    ]
    if len(keys) != len(set(keys)):
        sys.exit("ERROR: duplicate (country, scenario, window_start, window_end, source_sector) tuples")

    # Convert numpy int64 → Python int for JSON serialization
    def _to_python(obj):
        if hasattr(obj, "item"):
            return obj.item()
        return obj

    tasks_serializable = json.loads(json.dumps(tasks, default=_to_python))

    out_tmp = MANIFEST_OUT.with_suffix(".tmp")
    out_tmp.write_text(json.dumps(tasks_serializable, indent=2) + "\n")
    out_tmp.replace(MANIFEST_OUT)

    # Summary
    countries = sorted({t["country"] for t in tasks})
    print(f"\nManifest written: {MANIFEST_OUT}")
    print(f"  Total tasks: {len(tasks)}")
    print(f"  Countries: {countries}")
    for c in countries:
        c_tasks = [t for t in tasks if t["country"] == c]
        for sc in sorted({t["scenario"] for t in c_tasks}):
            sc_tasks = [t for t in c_tasks if t["scenario"] == sc]
            windows = sorted({(t["window_start"], t["window_end"]) for t in sc_tasks})
            sources = sorted({t["source_sector"] for t in sc_tasks})
            print(
                f"  {c}/{sc}: {len(sc_tasks)} tasks, "
                f"{len(windows)} windows, {len(sources)} sources"
            )


if __name__ == "__main__":
    main()
