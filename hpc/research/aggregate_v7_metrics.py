"""
Aggregate per-run metrics produced by the HERALD V7 battery.

Each run (V7 variant x seed, V6 control x seed, Semi V2 mode x seed, sector
baselines, etc.) writes to a unique JSON file under
$OUT_ROOT/reports/per_run/. This script merges them into family-level files
that match what the original launcher used to write:

  reports/herald_v7_metrics_v1.json
  reports/herald_v7_controls_metrics_v1.json
  reports/herald_v7_semi_probe_metrics_v1.json
  reports/herald_semi_v2_metrics_v1.json
  reports/sector_baselines_metrics_v1.json

Usage:
  python hpc/research/aggregate_v7_metrics.py --root hpc_results/herald_v7_g25_<ts>
"""

import argparse
import json
from pathlib import Path

FAMILIES = {
    "v7_": "herald_v7_metrics_v1.json",
    "v6ctrl_": "herald_v7_controls_metrics_v1.json",
    "semiv1_": "herald_v7_semi_probe_metrics_v1.json",
    "semiv2_": "herald_semi_v2_metrics_v1.json",
    "sector_baselines": "sector_baselines_metrics_v1.json",
}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  WARN failed to load {path}: {exc}")
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path,
                        help="OUT_ROOT used during the battery run")
    args = parser.parse_args()
    per_run_dir = args.root / "reports" / "per_run"
    out_dir = args.root / "reports"
    if not per_run_dir.is_dir():
        raise SystemExit(f"per_run dir not found: {per_run_dir}")

    aggregates = {fname: {} for fname in FAMILIES.values()}
    counts = {k: 0 for k in FAMILIES}

    for path in sorted(per_run_dir.glob("*.json")):
        name = path.name
        family = None
        for prefix, fname in FAMILIES.items():
            if name.startswith(prefix):
                family = (prefix, fname)
                break
        if family is None:
            print(f"  skip (unknown family): {name}")
            continue
        prefix, fname = family
        data = load_json(path)
        if not isinstance(data, dict):
            print(f"  skip (not a dict): {name}")
            continue
        # Merge keys into the family-level dict (single-run JSONs have 1
        # key; sector_baselines has 2 keys per file).
        for k, v in data.items():
            if k in aggregates[fname]:
                print(f"  DUP key '{k}' in {fname}, overwriting from {name}")
            aggregates[fname][k] = v
        counts[prefix] += 1

    for prefix, fname in FAMILIES.items():
        out_path = out_dir / fname
        out_path.write_text(json.dumps(aggregates[fname], indent=2), encoding="utf-8")
        print(f"wrote {out_path} (runs aggregated: {counts[prefix]})")

    print(f"\nDone. Aggregates under {out_dir}")


if __name__ == "__main__":
    main()
