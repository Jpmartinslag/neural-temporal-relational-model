# HERALD — Graph-Temporal E0-v2 Audit (Schema 2.0)

**Date:** 2026-06-11
**Decision:** `E0_V2_PASS`
**Schema:** 2.0 (temporal sequence)
**DEC:** DEC-028
**S1 FR status:** `S1_FR_BLOCKED` — GConvGRU/EvolveGCN implementation required first

---

## 1. Context

This audit records the validation of schema 2.0 graph-temporal tensors, which correct five defects
found in schema 1.0 (reported in `HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md`, reclassified
as `E0_STATIC_SNAPSHOT_PASS`).

Schema 1.0 produced a static snapshot (R,S,F) and (S,R,R). Schema 2.0 produces temporal sequences
(T,R,S,F) and (T,S,R,R) with per-feature masks, canonical H0b Ridge, and positive_topk adjacency.

---

## 2. Schema 1.0 Defects Corrected

| # | Defect | Schema 2.0 Fix |
|---|--------|----------------|
| 1 | Static snapshot — exported only (R,S,F) and (S,R,R); GNNs need temporal sequences | `features_seq(T,R,S,F)` and `adjacency_seq(T,S,R,R)` with T=5 time steps |
| 2 | Simplified Ridge — used `target_births` from country panel with extra features; normalized target (wrong) | Canonical H0b: exact port of `corrector.py::predict_h0b`; source `business_sector_total` from sector panel; AR lags only; StandardScaler on features only; clip ≥ 0 |
| 3 | Single obs_mask — growth=Inf discarded births and share at same position | Per-feature mask `feature_mask_seq(T,R,S,F)`: each feature independently valid/invalid |
| 4 | Signed dense adjacency — 29–36% of off-diagonal correlations negative | Primary representation: positive_topk (top-5 positive, symmetrized); signed_split and shrinkage_dense available for ablation |
| 5 | tracemalloc for memory — unreliable for NumPy native buffers | `resource.getrusage(RUSAGE_SELF).ru_maxrss` for RSS; initial, final, delta reported |

---

## 3. Schema 2.0 Causal Contract

All invariants are enforced by hard `LeakageError` assertions, not documentation.

| Invariant | Mechanism |
|-----------|-----------|
| `max(observation_year) < eval_year` | `_assert_no_leakage()` called on every obs_years array and every DataFrame slice before use |
| `adjacency_seq[t]` uses only data ≤ `obs_years[t]` | `build_adjacency_at_step()` filters sector panel to window `[obs_years[t]-WINDOW+1, obs_years[t]]` and asserts no leakage |
| Ridge trained on `avail_year < fold_eval_year` | `canonical_ridge_h0b()` computes `train_years = [y for y in all_avail if y < fold_eval_year and y > min_avail + AR_LAGS]` |
| PT-KZ always `struct_mask=0` | `build_struct_mask()` sets column 0 for KZ before any observation loop; cannot be overwritten |
| Per-feature independence | Three independent mask slots `[...,0]`, `[...,1]`, `[...,2]` for growth, share, births |
| `y_true` same source as Ridge target | Both use `business_sector_total` at `available_for_forecast_year = fold_eval_year + 1` |
| Deterministic ordering | `sorted()` on region_ids and sectors everywhere; no set iteration |

---

## 4. E0-v2 Smoke Results (NL, 3 eval years, 2 runs)

**Command:** `python -m src.modeles.run_e0_smoke_nl_v2 --rebuild`

### 4.1 Sequence Dimensions

| Country | Eval year | features_seq | adjacency_seq | observation_years |
|---------|-----------|-------------|---------------|-------------------|
| NL | 2019 | (5, 40, 9, 3) | (5, 9, 40, 40) | [2014, 2015, 2016, 2017, 2018] |
| NL | 2020 | (5, 40, 9, 3) | (5, 9, 40, 40) | [2015, 2016, 2017, 2018, 2019] |
| NL | 2021 | (5, 40, 9, 3) | (5, 9, 40, 40) | [2016, 2017, 2018, 2019, 2020] |

T=5, R=40 COROP regions, S=9 A10 sectors, F=3 features.

### 4.2 Check Results

| Check | Description | Result |
|-------|-------------|--------|
| C1 | Causal ordering: all obs_years < eval_year | PASS (all 3 folds) |
| C2 | Temporal sequence dimensions: (T,R,S,F) and (T,S,R,R) | PASS |
| C3 | Per-feature mask independence: values ∈ {0,1}, shape (T,R,S,F) | PASS |
| C4 | Adjacency per-step: non-negative, symmetric for all (t,s) slices | PASS |
| C5 | No NaN/Inf in observed feature positions (feature_mask_seq=1) | PASS |
| C6 | y_ridge_canonical ≥ 0; canonical WMAPE reported | PASS |
| C7 | Residual = y_true - y_ridge_canonical where target_mask=1 | PASS (max_diff=0.00e+00) |
| C8 | Determinism: two export runs identical NPZ checksums | PASS |

**Decision: `E0_V2_PASS`**

### 4.3 Canonical H0b WMAPE (engineering artefacts only)

| Eval year | WMAPE | n_targets |
|-----------|-------|-----------|
| NL/2019 | 0.0979 | 40 |
| NL/2020 | 0.0375 | 40 |
| NL/2021 | 0.0421 | 40 |

These are engineering artefacts. NL is COVID-sensitive (DEC-024d). These numbers
must not be used to promote any architecture or claim scientific significance.

### 4.4 Runtime and Memory

| Metric | Value | Limit | Status |
|--------|-------|-------|--------|
| Total runtime | 13.92 s | 600 s | PASS |
| RSS initial | 0.157 GB | — | — |
| RSS final | 0.192 GB | — | — |
| RSS delta | 0.035 GB | 4.0 GB | PASS |

Memory measured via `resource.getrusage(RUSAGE_SELF).ru_maxrss` (RSS) — reliable for NumPy native buffers.

---

## 5. Adjacency Audit (NL — static snapshot at eval_year-1)

| Eval year | neg_fraction_mean | density_mean | nan_fraction_mean | isolated@k=5 |
|-----------|-------------------|--------------|-------------------|-------------|
| NL/2019 | 0.356 | 0.656 | 0.111 | 40 |
| NL/2020 | 0.288 | 0.683 | 0.006 | 1 |
| NL/2021 | 0.313 | 0.682 | 0.006 | 1 |

**Key findings:**
- 29–36% of off-diagonal correlations are negative → signed dense adjacency would require explicit negative handling; positive_topk avoids this.
- NL/2019 isolated=40: one sector (OQ) has all-NaN growth in window [2014, 2018] due to sparse early reporting; all 40 regions are isolated in that sector. This matches the Phase 5 finding (OQ zero edges 2012–2019).
- Primary representation: `positive_topk`, k=5. Signed_split and shrinkage_dense available for ablation.

---

## 6. Test Results

**New tests (57 total — 33 from schema 1.0 + 24 schema 2.0):**

```
tests/test_graph_temporal_preflight.py — 33 passed in 1.16s
tests/test_graph_temporal_v2.py       — 24 passed in 1.49s
```

All invariants tested. Schema 2.0 tests cover: schema version (T19), sequence shapes (T20–T21), per-feature masks (T22), causal observation years (T23), per-step causality (T24), feature independence (T25), y_true source (T26), Ridge non-negative (T27), positive_topk correctness (T28–T29), signed_split structure (T30), shrinkage_dense (T31), LeakageError adjacency (T32), LeakageError features (T33), PT-KZ struct_mask (T34), mask no-NaN (T35), observation_years range (T36), audit neg_fraction (T37), fail-closed loading (T38), determinism (T39), Ridge finite (T40), residual consistency (T41), struct_mask static (T42).

---

## 7. Data Sources

| Source | Path | Role |
|--------|------|------|
| Sector panel (FR/NL/PT) | `data/processed/economic_graph/sector_panel_fr_nl_pt.csv` | Features, adjacency, Ridge target, y_true |

**Key**: both `y_true` and `y_ridge_canonical` derive from `business_sector_total` in the sector panel. The v1 `y_true` used `target_births` from the country panel, which differs (only 1/40 NL regions match within 1 unit for 2015). Schema 2.0 uses the same source for both quantities, making the residual meaningful.

---

## 8. Comparison with Schema 1.0

| Dimension | Schema 1.0 | Schema 2.0 |
|-----------|-----------|-----------|
| features | (R,S,F) static snapshot | (T,R,S,F) temporal sequence |
| masks | (R,S) single obs_mask | (T,R,S,F) per-feature |
| adjacency | (S,R,R) dense signed | (T,S,R,R) per-step positive_topk |
| y_true source | country panel `target_births` | sector panel `business_sector_total` |
| Ridge | 3-feature simplified, target normalized | canonical H0b: AR lags only, features scaled, target unscaled, clipped ≥ 0 |
| Memory | tracemalloc (Python heap only) | RSS via getrusage (includes NumPy buffers) |
| Artifacts | `graph_temporal_preflight/` | `graph_temporal_v2/` |

---

## 9. Schema 2.0 Manifest

```
data/processed/graph_temporal_v2/manifest_v2.json
  schema_version: "2.0"
  params: {t_seq: 5, window: 5, min_periods: 4, top_k: 5, ridge_alpha: 10.0, ar_lags: 2}
  folds: 3 × NL (2019, 2020, 2021)
  adjacency_audit: 3 × NL
```

Each fold: `data/processed/graph_temporal_v2/NL/{eval_year}/fold_v2.npz`

NPZ keys: `features_seq`, `feature_mask_seq`, `struct_mask`, `adjacency_seq`,
`observation_years`, `y_true`, `y_ridge_canonical`, `residual`, `target_mask`, `eval_year`.

---

## 10. Decision and Gate

**`E0_V2_PASS`** — all 8 checks pass. Runtime 13.92s. RSS delta 0.035 GB. 57 tests pass.
Zero leakage violations. Zero mask errors. Deterministic outputs across two runs.

**`S1_FR_BLOCKED`** — FR scientific local test remains blocked until:

1. GConvGRU (A1a) and EvolveGCN-H (A1b) are implemented using schema 2.0 tensors.
2. Equal-capacity no-graph control (A0-GRU or Ridge) included.
3. Zero-adjacency control and graph permutation controls included.
4. At least five FR eval years; at least five seeds.
5. WMAPE reported per-country; no pooled cross-country mean.
6. `git diff --check` clean before FR run.

**HPC remains BLOCKED** until FR passes locally.

---

## 11. Limitations

1. **NL is engineering smoke only.** COVID-sensitive (DEC-024d). WMAPE figures are engineering artefacts.
2. **FR adjacency not yet audited.** NL/2019 OQ sparsity pattern may differ for FR.
3. **GNN architectures not yet instantiated.** Parameter count gate (≤ 5,000 parameters) not yet verified.
4. **Only positive_topk exported** in fold NPZ. Signed_split and shrinkage_dense are available via `build_adjacency_at_step()` for ablation at architecture-test time.
5. **T=5 is a hyperparameter.** Sequence length matches the rolling window (WINDOW=5) for conceptual consistency. Sensitivity to T is not tested in E0.

---

## 12. Files Produced or Modified

| File | Action |
|------|--------|
| `src/data/european_panel/build_graph_temporal_v2.py` | Created — schema 2.0 tensor builder |
| `src/modeles/run_e0_smoke_nl_v2.py` | Created — E0-v2 smoke harness |
| `tests/test_graph_temporal_v2.py` | Created — 24 schema 2.0 tests (T19–T42) |
| `data/processed/graph_temporal_v2/` | Created — schema 2.0 NL fold artifacts |
| `reports/HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` | Updated — marked E0_PASS as superseded/E0_STATIC_SNAPSHOT_PASS |
| `CODEX_MEMORY.md` | Updated — DEC-028 E0_V2_PASS, S1_FR_BLOCKED |
