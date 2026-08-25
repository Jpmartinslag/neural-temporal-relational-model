#!/usr/bin/env bash
# Real smoke test for the Neural Temporal-Relational Model's neural architecture.
#
# scripts/run_minimal_example.sh proves the data pipeline and the persistence/Ridge
# baselines run. It does NOT exercise the neural model at all. This script does:
# it runs the actual temporal encoder and relational learner, on CPU, on a small
# synthetic panel with a known relational graph, checks that every component receives a
# real gradient, checks the no-mechanism scenario does not explode, and checks
# determinism by running twice and diffing the result.
#
# This is a smoke test, not a reproduction of any reported result -- see
# docs/RESULTS_AND_LIMITATIONS.md and docs/REPRODUCIBILITY.md. It makes no scientific
# claim. Runs in well under a minute on a laptop CPU, no SLURM, no download.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== [1/4] architecture guards (leakage, gradients, fairness between arms) ==="
python3 tests/test_herald93_guards.py

echo
echo "=== [2/4] anti-substitution mutation tests ==="
echo "    (proves each guard above actually catches the defect it names)"
python3 tests/run_herald93_mutations.py

echo
echo "=== [3/4] entrypoint smoke, both scenarios ==="
python3 scripts/run_temporal_relational_model.py --smoke --scenario with-mechanism \
  --out /tmp/model_smoke_with_mechanism.json
python3 scripts/run_temporal_relational_model.py --smoke --scenario no-mechanism \
  --out /tmp/model_smoke_no_mechanism.json

echo
echo "=== [4/4] determinism: same seed, same config, run twice, diff ==="
python3 scripts/run_temporal_relational_model.py --smoke --scenario with-mechanism \
  --out /tmp/model_smoke_repeat_a.json > /dev/null
python3 scripts/run_temporal_relational_model.py --smoke --scenario with-mechanism \
  --out /tmp/model_smoke_repeat_b.json > /dev/null
python3 -c "
import json, sys
a = json.load(open('/tmp/model_smoke_repeat_a.json'))
b = json.load(open('/tmp/model_smoke_repeat_b.json'))
same = a['forecast'] == b['forecast'] and a['relational'] == b['relational'] and a['gradients'] == b['gradients']
print('deterministic: same forecast, connection scores, and gradients both times' if same
      else 'NOT DETERMINISTIC -- two runs with the same seed disagree')
sys.exit(0 if same else 1)
"

echo
echo "=== [extra] structural anti-substitution guards on the entrypoint itself ==="
python3 -m pytest tests/test_model_smoke_entrypoint.py -q

echo
echo "All smoke checks passed. This proves the architecture runs, trains, produces a real"
echo "gradient in every component, and is deterministic. It is NOT evidence for any"
echo "scientific claim -- see docs/RESULTS_AND_LIMITATIONS.md."
