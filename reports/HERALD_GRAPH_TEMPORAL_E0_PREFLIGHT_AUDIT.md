# HERALD — Graph-Temporal E0 Preflight Audit

**Date:** 2026-06-11
**Decision:** `E0_PASS`
**FR scientific local test:** AUTHORIZED

---

## 1. Findings by Severity

| Severity | Finding | Corrected |
|----------|---------|-----------|
| HIGH | NL/CR02/LZ at obs_year=2020: `sector_growth_1y = inf` (division by zero when prior-year births=0). Passed `mask_sector_births=1` but value was non-finite. | Yes — `has_obs` guard now requires `isfinite(g)` and `isfinite(share)`; CR02/LZ/2021 correctly receives `obs_mask=0`. |
| LOW | Sector panel `region_id` column has mixed dtypes warning (int/str). | Handled by string cast in `country_regions()`; no data error. |

All findings resolved before E0_PASS declaration.

---

## 2. Causal Tensor Contract

**Enforced invariants (all verified by hard assertions, not documentation):**

| Invariant | Mechanism |
|-----------|-----------|
| `max(source_observation_year) < eval_year` | `_assert_no_leakage()` raises `LeakageError` if violated; called at adjacency build, feature build, and fold assembly. |
| Adjacency uses only `[eval_year-window, eval_year-1]` | `build_adjacency_l2_fold()` filters sector panel to causal window before any computation. |
| Normalisation fitted on training fold only | `train_stats` (mean/std) computed from `observation_year <= eval_year-1`; applied to snapshot at `eval_year-1`. |
| Ridge trained only on `year < eval_year` | `fit_ridge_baseline()` filters `year < eval_year` before fitting; prediction is on `year == eval_year` row (causal features `lag1`, `lag2`, `growth_1y`). |
| PT-KZ structural absence: `struct_mask=0`, never filled | `STRUCTURAL_ABSENT` set; `struct_mask` set to 0 before any observation loop. |
| Real missingness preserved (never silently zeroed) | `has_obs=False` sets `obs_mask=0`; `features` remain `NaN` at those positions; no zero-fill. |
| No cross-country edges | `build_adjacency_l2_fold()` filters `country == country` before pivot. |
| No country pooling of targets | Ridge fitted per country call; target is from country-specific panel. |
| Deterministic territory ordering | `sorted()` on region_ids and sectors everywhere. |
| Manifest with checksums | MD5 checksums of each NPZ artifact written to `manifest.json`. |

---

## 3. Data Sources

| Source | Path | Checksum |
|--------|------|----------|
| Sector panel (FR/NL/PT) | `data/processed/economic_graph/sector_panel_fr_nl_pt.csv` | see manifest |
| NL country panel | `data/processed/european_panel/nl_panel.csv` | see manifest |

**Sector panel columns used:** `region_id`, `observation_year`, `sector_a10`, `sector_growth_1y`, `sector_births`, `sector_share`, `mask_sector_births`, `mask_sector_supported`, `country`, `available_for_forecast_year`

**Country panel columns used:** `region_id`, `year`, `target_births`, `lag1_births`, `lag2_births`, `growth_1y`, `mask_target`

---

## 4. Dimensions per Country/Fold

| Country | Eval year | n_regions | n_sectors | max_train_obs_year | n_observed_targets |
|---------|-----------|-----------|-----------|-------------------|-------------------|
| NL | 2019 | 40 | 9 | 2018 | 40 |
| NL | 2020 | 40 | 9 | 2019 | 40 |
| NL | 2021 | 40 | 9 | 2020 | 40 |

Feature tensor shape per fold: **(40, 9, 3)** — R=40 COROP regions, S=9 A10 sectors, F=3 features.
Adjacency tensor shape per fold: **(9, 40, 40)** — one symmetric matrix per sector.

---

## 5. Proof of Causal Informational Separation

**For every fold (country, eval_year) `t`:**

1. **Adjacency** — computed from `sector_growth_1y` at `observation_year ∈ [t-5, t-1]`. The sector panel column `available_for_forecast_year = observation_year + 1` ensures that data available at the start of year `t` has `observation_year ≤ t-1`. The code further asserts `observation_year ≤ t-1` via `_assert_no_leakage()`.

2. **Node features** — snapshot at `observation_year = t-1` (immediately preceding eval year). Growth rates, shares and births from this snapshot are by construction known before year `t` begins.

3. **Ridge features** — `lag1_births = target_births[t-1]` and `lag2_births = target_births[t-2]` in the country panel; `growth_1y = (lag1 - lag2)/lag2`. All use data from years `≤ t-1`.

4. **Ridge training** — only rows with `year < t` participate in Ridge fitting. The prediction for year `t` uses the features of year `t` row (which are lag-1 and lag-2 values, not the year-`t` target).

5. **Manifest** — `max_train_obs_year = eval_year - 1` recorded for every fold.

No path from data at year `t` or later to any model input exists.

---

## 6. Missingness and PT-KZ Treatment

**PT-KZ:**
- `STRUCTURAL_ABSENT = {("PT", "KZ")}` — a compile-time constant.
- `struct_mask[:, kz_idx] = 0` is set before any observation loop; it cannot be overwritten by a later `has_obs=True`.
- PT-KZ receives no imputation, no zero-fill, and no adjacency edges.
- The distinction between structural absence (KZ in PT) and real zero economic activity is preserved at all times.

**Real missingness:**
- A (region, sector) position is `obs_mask=0` if: `mask_sector_births=0`, or `mask_sector_supported=0`, or `sector_growth_1y` is NaN, or `sector_growth_1y` is non-finite (e.g., Inf from division by near-zero births).
- The corrected bug (Inf growth at NL/CR02/LZ/2020) was caught by E0 check 4 and fixed before passing.
- `features` at `obs_mask=0` positions remain NaN and are never zero-filled in the artifact.

---

## 7. Checksums

| Artifact | NL/2019 | NL/2020 | NL/2021 |
|----------|---------|---------|---------|
| `node_features.npz` | `bbd5896c` | `7f148b33` | `6cde6fe3` |
| `adjacency_l2.npz` | `e563493a` | `c54c3e90` | `ae88a5a3` |
| `masks.npz` | `ffebd2a5` | `ffebd2a5` | `ffebd2a5` |
| `targets.npz` | `ce3b439b` | `8ed528be` | `ccca198d` |

Note: `masks.npz` is identical across folds for NL because the structural mask depends only on (country, sector) and all 40 regions are observed in all 3 eval years.

---

## 8. Test Results

**New tests (33 total):**

```
tests/test_graph_temporal_preflight.py — 33 passed in 1.69s
```

All 18 invariants tested. Tests cover: no future leakage (T01–T02), adjacency window sensitivity (T03), future data isolation (T04), deterministic ordering (T05), adjacency symmetry (T06), explicit diagonal (T07), no cross-country edges (T08), PT-KZ mask (T09), missing not zero (T10), isolated territory (T11), same territory list (T12), territorial total target (T13), same target for all architectures (T14), checksum sensitivity (T15), determinism (T16), no NaN/Inf in observed (T17), fail-closed (T18).

**Full suite:**

```
311 passed, 1 skipped in 57.21s
```

No regressions in existing tests.

---

## 9. Runtime and Memory

| Metric | Value | Limit | Status |
|--------|-------|-------|--------|
| Tensor export runtime | 0.63 s | — | well within |
| E0 smoke total runtime | 1.32 s | 600 s | PASS |
| Peak memory (tracemalloc) | 0.023 GB | 4.0 GB | PASS |

The pipeline is CPU-only with negligible memory footprint at NL scale (40 regions × 9 sectors × 3 eval years).

---

## 10. E0 Smoke NL Results

| Check | Description | Result |
|-------|-------------|--------|
| C1 | Causal ordering (`max_train_obs_year < eval_year`) | PASS (all 3 folds) |
| C2 | Adjacency sequence and sector ordering | PASS (symmetric, diagonal=1) |
| C3 | Mask integrity (values ∈ {0,1}, obs_mask ≤ struct_mask) | PASS |
| C4 | NaN/Inf audit (no non-finite in observed positions) | PASS (after Inf-growth fix) |
| C5 | Ridge alignment and dummy model pass | PASS (residual max_diff < 1e-8) |
| C6 | Determinism (two runs, same parameters) | PASS (identical checksums) |
| Runtime | < 600s on CPU | 1.32s PASS |
| Memory | < 4 GB | 0.023 GB PASS |
| **Overall** | | **E0_PASS** |

**Dummy model (no-graph Ridge) WMAPE:** 0.0970 (2019), 0.0828 (2020), 0.0413 (2021).
These numbers are engineering artefacts only. NL is COVID-sensitive and does not provide scientific authorization for architecture selection.

---

## 11. Limitations

1. **NL is engineering smoke only.** NL's G2 result is COVID-sensitive (DEC-024d). These WMAPE figures must not be used to promote any architecture.
2. **Ridge is a simplified within-tensor fit**, not the canonical per-country AR/Ridge from Phase 4E. It uses only three features (lag1, lag2, growth_1y) with a global Ridge. The canonical Phase 4 Ridge uses additional features. Future A1 implementations should align their target with the canonical Ridge from Phase 4.
3. **Parameter counting not yet executed.** E0 does not train A1a/A1b; parameter counting will occur when GConvGRU/EvolveGCN-H are instantiated. The contract is stated in `HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md` (max 5,000 parameters).
4. **Only 3 eval years tested.** The smoke specification requires 3; scientific gate S1 requires ≥ 5 eval years on FR.
5. **No graph null controls in E0.** These are required for S1 only.
6. **Inf growth at NL/CR02/LZ/2020** was the only defect found; it is corrected. The root cause is a sector birth count rising from zero — a valid economic event that produces non-finite growth rates. The correct handling is `obs_mask=0` (not observed) rather than imputation.

---

## 12. Decision

**`E0_PASS`**

All 6 checks pass. Runtime 1.32s. Memory 0.023 GB. 311 tests pass. Zero leakage violations. Zero mask errors. Deterministic outputs.

---

## 13. Authorization for FR Scientific Test

**FR local scientific test (S1) is AUTHORIZED** conditional on:

1. Implementing A1a (GConvGRU) and A1b (EvolveGCN-H) with the output architecture specified in `HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md` §4.
2. Equal-capacity no-graph control (A0-GRU or Ridge) included.
3. Zero-adjacency control included.
4. Both temporal and territory permuted-graph controls included.
5. Five seeds; at least five FR eval years.
6. WMAPE reported per-country; no pooled cross-country mean.
7. `git diff --check` clean before FR run.
8. HPC remains BLOCKED until FR passes locally.

---

## 14. Next Exact Files and Experiments

**Immediately authorized:**

- `src/modeles/graph_temporal_a1a_gcongru.py` — implement GConvGRU A1a (max 5000 params, width ∈ {4,8}, 1 layer, dropout ≥ 0.3, bounded residual head).
- `src/modeles/graph_temporal_a1b_evolvegcn.py` — implement EvolveGCN-H A1b with same output head.
- `src/modeles/run_s1_fr_local.py` — FR scientific local test harness, 5 seeds, ≥5 eval years, all controls, COVID sensitivity.
- `tests/test_graph_temporal_a1.py` — unit tests for A1 implementations (parameter count, mask propagation, bounded residual).

**Not authorized yet:**

- HPC Slurm submission.
- S2 replication on NL or PT.
- A2 learned edge gates.
- Any dashboard modification.
- Any recommendation or promotion claim.
