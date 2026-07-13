# HERALD 37 -- France ZE2020 top-3 entry relation-lift HPC spec

Status: SUPERSEDED_BY_HERALD_38

Date: 2026-07-10

This specification is retained for history. It used the pre-correction label split and
retrospective relation input. A future HPC specification must be registered separately
after the corrected local smoke.

## 1. Purpose

HERALD_36 found a small local MLP gain from target-aligned relation-lift
features on `future_top3_entry_3y_label`. This document prepares the HPC
falsification batch needed before any stronger claim.

This is not a final model result. It is a relation-layer robustness test.

## 2. New executable paths

| Path | Role |
|---|---|
| `src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_falsifications.py` | Runner that applies the existing HERALD_33 perturbations and then runs the HERALD_36 lift diagnostic |
| `hpc/france_ze2020_top3_entry_lift/run_fr_ze2020_top3_entry_lift_task.sh` | One Slurm task for one scenario and one seed |
| `hpc/france_ze2020_top3_entry_lift/run_fr_ze2020_top3_entry_lift_array.sbatch` | 20-task Slurm array |
| `hpc/france_ze2020_top3_entry_lift/submit_fr_ze2020_top3_entry_lift_hpc.sh` | Dry-run-safe submitter |
| `hpc/france_ze2020_top3_entry_lift/audit_fr_ze2020_top3_entry_lift_hpc_results.py` | Descriptive post-run audit |

## 3. Batch design

Scenarios:

- `full_control`
- `temporal_shuffle`
- `sector_shuffle`
- `target_shuffle`

Seeds:

- 42, 43, 44, 45, 46

Feature configs:

- `no_relation_features`
- `base_formula_features`
- `target_aligned_lift_features`
- `base_plus_target_aligned_lifts`
- `shuffled_target_aligned_lifts`

Decision years: 2017-2022.

Default max epochs: 120.

Expected output root:

`hpc_results/fr_ze2020_top3_entry_lift_<RUN_ID>/`

## 4. Gates

| Gate | Meaning |
|---|---|
| G1 | all 20 task outputs exist and parse |
| G2 | full-control `base_plus_target_aligned_lifts` MLP beats `no_relation_features` |
| G3 | full-control `base_plus_target_aligned_lifts` MLP beats `base_formula_features` |
| G4 | full-control `base_plus_target_aligned_lifts` MLP beats `shuffled_target_aligned_lifts` |
| G5 | temporal and sector shuffles degrade `base_plus_target_aligned_lifts` MLP |
| G6 | outputs contain no forbidden decision/causal columns |

These gates do not automatically promote a model. They decide whether the next
relation-layer construction is worth deeper development.

## 5. Preflight executed locally

Tests:

```bash
/usr/bin/python3.10 -m pytest -q \
  tests/test_fr_ze2020_top3_entry_lift_diagnostic.py \
  tests/test_fr_ze2020_top3_entry_lift_falsifications.py \
  tests/test_fr_ze2020_top3_entry_lift_hpc.py \
  tests/test_fr_ze2020_top3_entry_falsifications.py
```

Result: 16 passed.

Smoke CLI:

```bash
/usr/bin/python3.10 src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_falsifications.py \
  --output-dir /tmp/herald_top3_entry_lift_falsification_check \
  --eval-years 2020 \
  --seeds 42 \
  --scenarios full_control sector_shuffle \
  --feature-configs no_relation_features base_plus_target_aligned_lifts shuffled_target_aligned_lifts \
  --max-epochs 10
```

Result: completed and wrote the expected regenerable files under `/tmp`.

## 6. Claim boundary

Authorized:

- The HPC package is ready to test HERALD_36 under repeated seeds and
  falsification scenarios.
- The target-aligned lift is being tested as a relation-layer construction
  hypothesis.

Forbidden:

- Claiming a validated dynamic graph neural model.
- Claiming causal relations.
- Claiming operational or automatic sector recommendations.
- Treating a dry-run or spec as a completed HPC result.

## 7. Launch command

On `meso`, after the repo state is synced:

```bash
bash hpc/france_ze2020_top3_entry_lift/submit_fr_ze2020_top3_entry_lift_hpc.sh --confirm-submit
```

After completion, collect and audit:

```bash
python hpc/france_ze2020_top3_entry_lift/audit_fr_ze2020_top3_entry_lift_hpc_results.py \
  hpc_results/fr_ze2020_top3_entry_lift_<RUN_ID> \
  --out hpc_results/fr_ze2020_top3_entry_lift_<RUN_ID>/fr_ze2020_top3_entry_lift_hpc_audit_report.json
```
