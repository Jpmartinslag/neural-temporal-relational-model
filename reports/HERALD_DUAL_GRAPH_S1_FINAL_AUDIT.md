# HERALD Phase 6 — P6_DDEG_S1 Final HPC Audit

**Date:** 2026-06-12
**Study:** P6_DDEG_S1 — Dynamic Dual Economic Graph, France NUTS3
**Slurm job:** 7453691
**Auditor:** automated (`hpc/phase6_dynamic_dual_graph/scripts/audit_dual_graph_hpc_results.py`)
**Gate:** DUAL_GRAPH_S1_FAIL

---

## 1. Completeness

| Check | Expected | Found | Status |
|-------|----------|-------|--------|
| Total JSON files | 275 | 275 | PASS |
| Unique (fold, control, seed) combinations | 275 | 275 | PASS |
| Duplicate runs | 0 | 0 | PASS |
| Missing (fold, control, seed) | 0 | 0 | PASS |
| All 5 folds present | [2021,2022,2023,2024,2025] | all 5 | PASS |
| All 11 controls present | C0–C10 | all 11 | PASS |
| All 5 seeds present | [42,43,44,45,46] | all 5 | PASS |

---

## 2. Integrity Checks

| Check | Result |
|-------|--------|
| All runs status=ok | PASS (275/275) |
| No NaN/Inf in MAE | PASS |
| No NaN/Inf in regime_macro_f1 (neural runs) | PASS |
| No NaN/Inf in recovery_aucpr (neural runs) | PASS |
| Temporal ordering: best_epoch ≤ stopped_epoch | PASS |
| No fold leakage (eval year not in training) | PASS (checked via trainer timestamps in JSON) |
| n_params ≤ 10,000 | PASS (1,035 for C5_dual, hidden_dim=8) |
| C7/C8 corrected permutations valid | PASS (targets_unchanged guard active) |
| Filename matches (fold, control, seed) | PASS |
| No truncated JSON | PASS |
| Consistent git commit in all runs | PASS (commit 9521264) |
| Consistent hostname pattern | PASS (meso cluster nodes) |

---

## 3. Aggregation Validation

Two independent aggregations were run and produced identical gate decisions:
1. `hpc/phase6_dynamic_dual_graph/scripts/audit_dual_graph_hpc_results.py` (primary)
2. Standalone inline script (independent verification)

Both produce `DUAL_GRAPH_S1_FAIL` with all 7 criteria failing.

Aggregation method: for each (fold, control), mean metrics over 5 seeds; for overall statistics, mean over 5 folds.

---

## 4. Criterion Verification

### c1 — MAE improvement ≥ 1% vs baselines

```
C5_dual overall MAE:   0.1424
C1_ridge overall MAE:  0.1242  →  C5 is +14.6% WORSE  (required: ≤-1%)
C2_no_graph overall:   0.1329  →  C5 is  +7.2% WORSE  (required: ≤-1%)
```

FAIL. C5_dual is worse than both non-neural (C1_ridge) and neural-no-graph (C2_no_graph) baselines.

### c2 — Macro-F1 margin ≥ +0.02 vs no-graph controls

```
C5_dual macro_f1:        0.2885
C2_no_graph macro_f1:    0.2870  →  margin = +0.0015  (required: ≥+0.02)
C8_sect_perm macro_f1:   0.2864  →  margin = +0.0021  (required: ≥+0.02)
```

FAIL. The F1 gain is an order of magnitude below the pre-registered threshold.

### c3 — Recovery AUCPR > (prevalence AND C2) in ≥ 3/5 folds

```
Fold 2021: C5=0.3329, prev=0.2068, C2=0.3685  →  vs_prev=PASS, vs_C2=FAIL
Fold 2022: C5=0.0937, prev=0.0077, C2=0.1673  →  vs_prev=PASS, vs_C2=FAIL
Fold 2023: C5=0.1622, prev=0.0231, C2=0.1736  →  vs_prev=PASS, vs_C2=FAIL
Fold 2024: C5=0.1248, prev=0.1243, C2=0.1598  →  vs_prev=PASS, vs_C2=FAIL
Fold 2025: C5=0.1556, prev=0.0319, C2=0.3369  →  vs_prev=PASS, vs_C2=FAIL
```

FAIL. C5_dual beats prevalence in all 5 folds, but C2_no_graph beats C5_dual in all 5 folds. The graph does not improve recovery detection over a neural no-graph baseline.

### c4 — C5 beats both C7 (territory perm) AND C8 (sector perm) in ≥ 3/5 folds

```
Fold 2021: C5=0.1441, C7=0.1418, C8=0.1456  →  C5 beats C8 only (PARTIAL)
Fold 2022: C5=0.1487, C7=0.1489, C8=0.1399  →  C5 beats neither
Fold 2023: C5=0.1862, C7=0.1875, C8=0.1726  →  C5 beats C7 only (PARTIAL)
Fold 2024: C5=0.1270, C7=0.1274, C8=0.1201  →  C5 beats C7 only (PARTIAL)
Fold 2025: C5=0.1061, C7=0.1061, C8=0.1045  →  C5 ties C7 only (PARTIAL)
```

FAIL. C5_dual never beats BOTH permutation nulls in the same fold. Criteria requires 3/5 dual wins; achieved 0/5.

### c5 — Mean seed Jaccard ≥ 0.50

```
Jaccard by fold: 0.3720 / 0.2962 / 0.3230 / 0.3577 / 0.3275
Mean Jaccard: 0.3353  (required: ≥0.50)
```

FAIL. The sector graph is not reproducible across seeds. Top-k edges differ substantially between random initializations.

### c6 — No fold MAE regression > 10% vs C2_no_graph

```
Fold 2021: C5=0.1441 vs C2=0.1486  →  −3.1%  (OK)
Fold 2022: C5=0.1487 vs C2=0.1420  →  +4.7%  (OK)
Fold 2023: C5=0.1862 vs C2=0.1586  →  +17.4% (FAIL — exceeds 10% threshold)
Fold 2024: C5=0.1270 vs C2=0.1161  →  +9.4%  (OK, borderline)
Fold 2025: C5=0.1061 vs C2=0.0993  →  +6.8%  (OK)
```

FAIL. Fold 2023 shows a 17.4% MAE regression vs no-graph baseline. Note: the pilot study (2 seeds) had c6=PASS; the full study (5 seeds) has c6=FAIL, indicating the 2023 fold failure was masked by seed variance in the pilot.

### c7 — c1–c4 hold excluding fold 2021

Excluding 2021 (where C5_dual wins), MAE comparison over folds 2022–2025:
- C5_dual mean: 0.1420
- C2_no_graph mean: 0.1290
- C5 is +10.1% worse than C2 without 2021

FAIL. The 2021 win is anomalous; the dual-graph model is uniformly worse in all subsequent evaluation years.

---

## 5. Parameter Count Verification

C5_dual runs log `n_params=1035` (hidden_dim=8, 101 regions, 9 sectors). Consistent across all 275 runs. Under the 10,000-parameter cap specified in the contract.

---

## 6. C7 / C8 Permutation Validity

The `targets_unchanged` guard in the trainer ensures:
- **C7** permutes only the territory adjacency P-A-Pᵀ; targets remain canonical
- **C8** permutes sector feature axes via σ; targets remain canonical
- The degenerate joint co-permutation (P × X, P-A-Pᵀ, P × Y) is explicitly rejected

All 50 C7 runs and 50 C8 runs passed the `targets_unchanged` assertion. No guard was triggered (which would have aborted the run).

---

## 7. Summary of All Controls (MAE)

Ranked by overall mean MAE:

| Rank | Control | MAE |
|------|---------|-----|
| 1 | C1_ridge | 0.1242 |
| 2 | C2_no_graph | 0.1329 |
| 3 | C3_territory_only | 0.1373 |
| 4 | C4_sector_only | 0.1373 |
| 5 | C8_sector_identity_perm | 0.1365 |
| 6 | C9_no_ardeco | 0.1393 |
| 7 | C10_ardeco_temporal_perm | 0.1416 |
| 8 | **C5_dual** | **0.1424** |
| 9 | C7_territory_graph_perm | 0.1423 |
| 10 | C6_territory_temporal_perm | 0.1437 |
| 11 | C0_persistence | 0.1795 |

C5_dual ranks 8th, essentially tied with C7_territory_graph_perm. The learned sector graph contributes no MAE benefit beyond a random territory-graph permutation.

---

## 8. Gate Metadata

```json
{
  "decision": "DUAL_GRAPH_S1_FAIL",
  "criteria": {
    "c1_mae_improve": false,
    "c2_macro_f1_margin": false,
    "c3_recovery_aucpr_folds": false,
    "c4_graph_beats_nulls_folds": false,
    "c5_seed_jaccard": false,
    "c6_no_fold_regression": false,
    "c7_holds_without_2021": false
  },
  "study": "P6_DDEG_S1",
  "slurm_job": "7453691",
  "n_runs": 275
}
```

Full provenance: `data/processed/dual_graph_s1/gate_result.json`

---

## 9. Audit Verdict

All 9 integrity checks pass. Completeness is 275/275. Aggregation is deterministic and independently verified. The gate is applied exactly as pre-registered in the experiment contract.

**AUDIT VERDICT: VALID — DUAL_GRAPH_S1_FAIL confirmed.**

This result is final. The predictive dual-graph branch is closed. No relaunch is authorized without a documented operational failure in protocol or data integrity (not in model performance).

---

## 10. Files Produced

| Artifact | Path |
|----------|------|
| Raw results (275 JSON) | `hpc_results/dual_graph_s1/raw/` |
| Audit summary | `data/processed/dual_graph_s1/audit_summary.json` |
| Per-run CSV | `data/processed/dual_graph_s1/summary_by_run.csv` |
| Per fold-control CSV | `data/processed/dual_graph_s1/summary_by_fold_control.csv` |
| Per-control CSV | `data/processed/dual_graph_s1/summary_by_control.csv` |
| Learned sector edges | `data/processed/dual_graph_s1/learned_sector_edges.csv` |
| Gate result | `data/processed/dual_graph_s1/gate_result.json` |
| Run manifest | `data/processed/dual_graph_s1/run_manifest.json` |
| Scientific results | `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md` |
| This audit | `reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` |
