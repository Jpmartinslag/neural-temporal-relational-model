"""Single Phase 5 HPC job: one (country, hypothesis, seed) combination.

Called by run_phase5_array.sbatch. Writes one JSON result file per job.
Output includes commit hash, L2 checksums, WMAPE by year, correction norms.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import pandas as pd

from src.modeles.phase5.manifest import verify_manifest, MANIFEST, md5
from src.modeles.phase5.rolling_origin import run_country, summarise, gate_h2_neural


PANEL_PATH = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=BASE, text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--eval-years", nargs="+", type=int,
                        default=[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023])
    parser.add_argument("--out-dir", default="hpc_results/phase5/raw")
    args = parser.parse_args()

    t0 = time.time()
    out_dir = BASE / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Artifact verification (non-strict: log but continue)
    manifest_ok = verify_manifest(strict=False)
    actual_checksums = {rel: md5(BASE / rel) for rel in MANIFEST if (BASE / rel).exists()}

    # Load panel
    panel = pd.read_csv(PANEL_PATH, low_memory=False)

    # Run
    results = run_country(
        panel=panel,
        country=args.country,
        eval_years=args.eval_years,
        hypotheses=(args.hypothesis,),
        seed=args.seed,
    )
    summary = summarise(results)
    elapsed = time.time() - t0

    # Output
    out = {
        "metadata": {
            "country": args.country,
            "hypothesis": args.hypothesis,
            "seed": args.seed,
            "eval_years": args.eval_years,
            "commit": git_hash(),
            "runtime_seconds": round(elapsed, 2),
            "manifest_ok": manifest_ok,
            "actual_checksums": actual_checksums,
        },
        "summary": summary,
        "results_by_year": [asdict(r) for r in results],
    }

    fname = f"{args.country}_{args.hypothesis.replace('-', '_')}_{args.seed:03d}.json"
    out_path = out_dir / fname
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)

    hyp_sum = summary.get(args.hypothesis, {})
    print(
        f"DONE country={args.country} hyp={args.hypothesis} seed={args.seed} "
        f"mean_wmape={hyp_sum.get('mean_wmape', float('nan')):.4f} "
        f"runtime={elapsed:.1f}s → {out_path.name}"
    )


if __name__ == "__main__":
    main()
