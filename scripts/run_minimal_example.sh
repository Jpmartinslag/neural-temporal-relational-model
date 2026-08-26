#!/usr/bin/env bash
# Minimal reproducible example for the Neural Temporal-Relational Model project.
#
# Runs the FR ZE2020 persistence + Ridge(lag-only) baselines against the canonical,
# already-committed model-ready panel. No download, no HPC job. See docs/REPRODUCIBILITY.md
# for the full reproduction path (fast test suites, full test collection, HPC vs. local).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m pytest tests/test_fr_ze2020_baselines.py -q
