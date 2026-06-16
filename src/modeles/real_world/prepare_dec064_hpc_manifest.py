"""
DEC-064: Prepare HPC task manifest for PT municipal Phase 7 full run.

Generates one task per (scenario × window × source_sector).
Panel must already be built via build_pt_municipal_phase7_panel.py.
Output: data/processed/phase7_pt_municipal/hpc_task_manifest.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))

CONFIG_PATH = REPO_ROOT / "hpc/phase7_sector_precedence/configs/pt_municipal_observed.json"
PANEL_PATH = REPO_ROOT / "data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv"
MANIFEST_OUT = REPO_ROOT / "data/processed/phase7_pt_municipal/hpc_task_manifest.json"

SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def compute_valid_windows(
    available_years: list[int],
    window_years: int,
    exclude_years: frozenset,
    min_years: int = 4,
) -> list[tuple[int, int]]:
    windows = []
    for end_year in available_years:
        start_year = end_year - window_years + 1
        usable = [y for y in available_years if start_year <= y <= end_year and y not in exclude_years]
        if len(usable) >= min_years:
            windows.append((start_year, end_year))
    return windows


def main() -> None:
    if not PANEL_PATH.exists():
        sys.exit(f"Panel not found: {PANEL_PATH}\nRun build_pt_municipal_phase7_panel.py first.")

    cfg = json.loads(CONFIG_PATH.read_text())
    window_years = int(cfg["window_years"])
    seed = int(cfg["seed"])
    n_permutations = int(cfg["n_permutations"])
    n_bootstraps = int(cfg["n_bootstraps"])
    scenario_exclusions: dict = cfg.get("scenario_exclusions", {})

    panel = pd.read_csv(PANEL_PATH, dtype={"territory_id": str}, low_memory=False)
    panel_checksum = sha256_file(PANEL_PATH)
    commit_sha = git_head()

    obs = panel[panel["structural_mask"] == 1]
    available_years = sorted(obs["observation_year"].unique().tolist())
    valid_sectors = sorted(obs["sector_id"].unique().tolist())

    scenarios = [("main", frozenset())] + [
        (name, frozenset(yrs)) for name, yrs in scenario_exclusions.items()
    ]

    tasks: list[dict] = []
    task_id = 0

    for scenario_name, exclude_years in scenarios:
        windows = compute_valid_windows(available_years, window_years, exclude_years)
        for window_start, window_end in windows:
            for source_sector in valid_sectors:
                targets = [s for s in valid_sectors if s != source_sector]
                tasks.append({
                    "schema_version": SCHEMA_VERSION,
                    "task_id": task_id,
                    "country": "PT",
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
                })
                task_id += 1

    assert [t["task_id"] for t in tasks] == list(range(len(tasks)))
    keys = [(t["country"], t["scenario"], t["window_start"], t["window_end"], t["source_sector"]) for t in tasks]
    assert len(keys) == len(set(keys)), "Duplicate task keys"

    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(tasks, indent=2) + "\n")
    tmp.replace(MANIFEST_OUT)

    print(f"Manifest written: {MANIFEST_OUT}")
    print(f"  Total tasks: {len(tasks)}")
    print(f"  Panel checksum: {panel_checksum[:16]}...")
    print(f"  Commit: {commit_sha[:12]}")
    for sc in sorted({t["scenario"] for t in tasks}):
        sc_tasks = [t for t in tasks if t["scenario"] == sc]
        windows = sorted({(t["window_start"], t["window_end"]) for t in sc_tasks})
        print(f"  {sc}: {len(sc_tasks)} tasks, {len(windows)} windows × {len(valid_sectors)} sources")


if __name__ == "__main__":
    main()
