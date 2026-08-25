# Phase 4 — international HPC batteries

SLURM batteries for generalizing the model to NL/BE/PT.
France scripts (Phase 2+3) live under `hpc/regime/`. Do not mix the two.

> **⚠️ Current status (2026-06-09) — this file describes the initial per-country
> batteries (Phase 4 NL/BE/PT). The work has since moved to a 4-country LOCO
> protocol (Phase 4G/4H/4I).** Validated result: persistence (~0.0939) is the best
> balanced baseline and unweighted Ridge (~0.0969) the best trainable model; the
> graph/residual mechanism does not transfer robustly **under this protocol** (which
> does not prove it never works elsewhere). Protocol = LOCO *zero-shot parameters
> with target-country history*, **not** cold-start. Next steps (2 gates): the
> official semantic target audit, then a persistence/Ridge combination benchmark.
> The three prose write-ups originally cited here — an independent-audit note and
> the Phase 4H-B / Phase 4I-A results audits — were consolidated into the
> repository's documentation history before this delivery branch existed and are
> not part of the current file tree; they remain recoverable from git history. The
> content below is kept as the historical record of the initial batteries.

---

## Starting candidate

**France Q7:** `Q7_effectifs_lag1` — features: `side_lag_1`, `growth_1y`, `effectifs_lag1` × A10.
The Phase 4 batteries test whether the same architecture generalizes outside France.

---

## Countries and panels

| Country | Zones | Modelling window | Tensor | Employment-equivalent |
|------|-------|---------------------|--------|----------|
| **Netherlands** | 40 COROP (CR01–CR40) | 2016–2024 | `qtensor_jobs` — CBS employee jobs × SBI-A10 | ✅ yes |
| **Belgium** | 42 arrondissements | 2009–2020 | `qtensor_jobs` — ONSS jobs × NACE-A10 | ✅ yes |
| **Portugal** | 25 NUTS3 (PT_111–PT_300) | 2009–2022 | `sector_births_tensor` — births × CAE-A10 | ⚠️ proxy |

Preflight before any launch: `python3 src/data/phase4_preflight.py`

---

## Planned structure

```text
hpc/phase4/
├── README.md                           ← this file
├── submit_herald_phase4_nl.sh          ← Netherlands battery
├── submit_herald_phase4_be.sh          ← Belgium battery
├── submit_herald_phase4_pt.sh          ← Portugal battery (tensor proxy)
├── smoke_test_phase4_nl.sh             ← NL smoke test (1 seed, 1 epoch)
├── smoke_test_phase4_be.sh             ← BE smoke test
├── smoke_test_phase4_pt.sh             ← PT smoke test
├── audit_phase4_results.py             ← aggregation + 4-country comparison
└── phase4_configs.sh                   ← central config registry
```

The filenames above keep the legacy `herald_phase4` naming from when they were
written; renaming ~80 files across `hpc/phase4/` was judged not worth the risk this
late in the delivery and does not change what they do.

---

## Planned configs (per country)

Each country tests the following configs, in parallel (NL/BE) or as a variant (PT):

| Config | Description | NL | BE | PT |
|--------|-------------|----|----|-----|
| `baseline_side2` | `side_lag_1 + growth_1y`, no tensor | ✅ | ✅ | ✅ |
| `qtensor_jobs_lag1` | + employment tensor lag1 | ✅ | ✅ | — |
| `sector_births_lag1` | + `sector_births_tensor` lag1 | — | — | ✅ |
| `no_qtensor_control` | features only, no employment tensor | ✅ | ✅ | ✅ |

Seeds: 20 per config. Estimated total: ~4 configs × 20 seeds × 3 countries = ~240 runs.

---

## Launch protocol

1. Check the preflight: `python3 src/data/phase4_preflight.py`
2. Copy the panels to the cluster (see the Transfer section)
3. Smoke test: `bash hpc/phase4/smoke_test_phase4_nl.sh` (1 seed, 1 epoch)
4. Verify the smoke artifacts
5. Submit: `STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/phase4/submit_herald_phase4_nl.sh`
6. Repeat for BE and PT

---

## Transferring data to the cluster

```bash
# Phase 4 panels (NL/BE/PT)
rsync -av \
  data/external/netherlands/processed/ \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/data/external/netherlands/processed/

rsync -av \
  data/external/belgium/processed/ \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/data/external/belgium/processed/

rsync -av \
  data/external/portugal/processed/ \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/data/external/portugal/processed/
```

## Retrieving results

```bash
rsync -av \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/<OUT_ROOT>/ \
  hpc_results/<OUT_ROOT>/

python3 hpc/phase4/audit_phase4_results.py --root hpc_results/<OUT_ROOT>
```

---

## Rules

- `OUT_ROOT` must be unique and dated per run.
- Never reuse an existing `OUT_ROOT`.
- The `sector_births_tensor` label is mandatory for PT — never write `qtensor_jobs`
  or an employment-tensor label for PT.
- A smoke test is mandatory before any submit.
- Results go to `reports/metrics/` after aggregation.
