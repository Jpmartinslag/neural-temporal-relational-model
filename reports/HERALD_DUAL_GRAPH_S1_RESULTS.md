# HERALD Phase 6 — P6_DDEG_S1 Scientific Results

**Study ID:** P6_DDEG_S1
**Date:** 2026-06-12
**Slurm job:** 7453691
**Scope:** France NUTS3 · 101 regions · 9 A10 sectors · eval years 2021–2025
**Protocol:** 5 folds × 11 controls × 5 seeds = 275 jobs; rolling-origin; fail-closed gate §9
**Gate decision:** DUAL_GRAPH_S1_FAIL — all 7 criteria fail

---

## 1. Study Design

The P6_DDEG_S1 experiment tests whether a two-graph neural representation (territory graph + sector graph) improves sector-level log-growth prediction, regime classification, and recovery detection over strong non-graph baselines for French NUTS3 territories.

- **Territory graph**: observed causal dynamic co-growth adjacency (per-sector NUTS3, constructed from past years only)
- **Sector graph**: learned sparse symmetric adjacency (L1 + temporal-stability regularization, top-k=3)
- **Model**: 1,035 parameters (hidden_dim=8); rolling-origin; outer fold = eval year B, inner-val = B−1

The study is a representation-learning and early-warning experiment, NOT a forecast improvement claim. Evaluated with MAE (primary), macro-F1 (regime), and recovery AUCPR.

---

## 2. Gate Criteria (§9 of Experiment Contract)

| Criterion | Threshold | Result | Status |
|-----------|-----------|--------|--------|
| c1: MAE ≥ 1% better vs C1_ridge | C5 ≤ C1 × 0.99 | C5=0.1424 vs C1=0.1242 (+14.6%) | FAIL |
| c1: MAE ≥ 1% better vs C2_no_graph | C5 ≤ C2 × 0.99 | C5=0.1424 vs C2=0.1329 (+7.2%) | FAIL |
| c2: macro-F1 margin ≥ +0.02 vs C2 | C5 − C2 ≥ 0.02 | 0.2885 − 0.2870 = +0.0015 | FAIL |
| c2: macro-F1 margin ≥ +0.02 vs C8 | C5 − C8 ≥ 0.02 | 0.2885 − 0.2864 = +0.0021 | FAIL |
| c3: recovery AUCPR > prevalence+C2 in ≥ 3/5 folds | 3 of 5 folds | 0/5 folds beat C2 | FAIL |
| c4: C5 beats C7 AND C8 in ≥ 3/5 folds | 3 of 5 folds | 1/5 fold (2021 only) | FAIL |
| c5: mean seed Jaccard ≥ 0.50 | ≥ 0.50 | 0.3353 | FAIL |
| c6: no fold MAE regression > 10% vs C2 | max fold MAE ratio ≤ 1.10 | 2023: +17.4% | FAIL |
| c7: c1–c4 hold excluding fold 2021 | same thresholds | C5 worse in 4/4 remaining folds | FAIL |

**Overall gate: DUAL_GRAPH_S1_FAIL**

---

## 3. Per-Fold MAE Table

| Fold | C5_dual | C1_ridge | vs C1 | C2_no_graph | vs C2 | C7_terr_perm | vs C7 | C8_sect_perm | vs C8 |
|------|---------|----------|-------|-------------|-------|--------------|-------|--------------|-------|
| 2021 | 0.1441 | 0.1485 | **−3.0%** | 0.1486 | **−3.1%** | 0.1418 | +1.6% | 0.1456 | **−1.1%** |
| 2022 | 0.1487 | 0.1208 | +23.1% | 0.1420 | +4.7% | 0.1489 | **−0.2%** | 0.1399 | +6.3% |
| 2023 | 0.1862 | 0.1569 | +18.7% | 0.1586 | **+17.4%** | 0.1875 | **−0.7%** | 0.1726 | +7.9% |
| 2024 | 0.1270 | 0.0901 | +40.9% | 0.1161 | +9.4% | 0.1274 | **−0.3%** | 0.1201 | +5.7% |
| 2025 | 0.1061 | 0.1048 | +1.2% | 0.0993 | +6.8% | 0.1061 | −0.0% | 0.1045 | +1.6% |
| **Mean** | **0.1424** | **0.1242** | **+14.6%** | **0.1329** | **+7.2%** | **0.1423** | **+0.1%** | **0.1365** | **+4.3%** |

C5_dual wins vs C1_ridge and C2_no_graph **only in fold 2021**. Crucially, C5_dual is essentially tied with C7_territory_graph_perm (territory-only permutation null), indicating that the sector graph contributes no additional MAE improvement.

---

## 4. Macro-F1 by Fold

| Fold | C5_dual | C2_no_graph | C8_sect_perm |
|------|---------|-------------|--------------|
| 2021 | 0.2957 | 0.3134 | 0.2881 |
| 2022 | 0.2950 | 0.2735 | 0.3020 |
| 2023 | 0.2847 | 0.2890 | 0.2692 |
| 2024 | 0.2800 | 0.2586 | 0.2713 |
| 2025 | 0.2869 | 0.3005 | 0.3015 |
| **Mean** | **0.2885** | **0.2870** | **0.2864** |

The regime classification signal is near-uniform across all neural controls, including permutation nulls. C5_dual does not improve regime detection.

---

## 5. Recovery AUCPR by Fold

| Fold | C5_dual AUCPR | Prevalence | vs Prev | C2_no_graph AUCPR | vs C2 |
|------|--------------|------------|---------|-------------------|-------|
| 2021 | 0.3329 | 0.2068 | PASS | 0.3685 | **FAIL** |
| 2022 | 0.0937 | 0.0077 | PASS | 0.1673 | **FAIL** |
| 2023 | 0.1622 | 0.0231 | PASS | 0.1736 | **FAIL** |
| 2024 | 0.1248 | 0.1243 | PASS | 0.1598 | **FAIL** |
| 2025 | 0.1556 | 0.0319 | PASS | 0.3369 | **FAIL** |

C5_dual beats random (prevalence) in all 5 folds, but C2_no_graph (no-graph neural baseline) performs consistently better than C5_dual on recovery detection. The dual-graph structure confers no recovery detection advantage.

---

## 6. Seed Stability (Jaccard)

| Fold | Mean seed Jaccard | Gate (≥ 0.50) |
|------|-------------------|---------------|
| 2021 | 0.3720 | FAIL |
| 2022 | 0.2962 | FAIL |
| 2023 | 0.3230 | FAIL |
| 2024 | 0.3577 | FAIL |
| 2025 | 0.3275 | FAIL |
| **Mean** | **0.3353** | **FAIL** |

The sector graph structure is not reproducible across seeds. Different random initializations learn substantially different sparse adjacency patterns, indicating the optimization landscape is not sufficiently constrained to converge to a stable sector structure.

---

## 7. Full Control Summary

| Control | Overall MAE | Macro-F1 | Notes |
|---------|------------|----------|-------|
| C0_persistence | 0.1795 | n/a | Lag-1 baseline |
| C1_ridge | 0.1242 | n/a | Best MAE (non-neural) |
| C2_no_graph | 0.1329 | 0.2870 | Best neural non-graph |
| C3_territory_only | 0.1373 | 0.2859 | Territory graph only |
| C4_sector_only | 0.1373 | 0.2909 | Sector graph only |
| **C5_dual** | **0.1424** | **0.2885** | **Full model** |
| C6_territory_temporal_perm | 0.1437 | 0.2832 | Temporal permutation |
| C7_territory_graph_perm | 0.1423 | 0.2893 | Graph permutation null |
| C8_sector_identity_perm | 0.1365 | 0.2864 | Sector permutation null |
| C9_no_ardeco | 0.1393 | 0.2913 | No ARDECO features |
| C10_ardeco_temporal_perm | 0.1416 | 0.2902 | ARDECO temporal perm |

C5_dual ranks 8th out of 11 controls on MAE. C1_ridge dominates; C2_no_graph is the best neural baseline.

---

## 8. Learned Sector Graph (Descriptive)

Despite the predictive failure, C5_dual learns stable sector association patterns in terms of which edges appear consistently across fold × seed combinations. Top stable associations:

| Sector pair | Stability fraction | Economic interpretation |
|-------------|-------------------|------------------------|
| C (manufacturing) ↔ KZ (finance/real-estate) | 0.80 | 20/25 combinations |
| FZ (construction) ↔ HZ (transport/storage) | 0.76 | 19/25 combinations |
| HZ (transport) ↔ KZ (finance/real-estate) | 0.76 | 19/25 combinations |
| AZ (agriculture) ↔ DE (energy/extractives) | 0.72 | 18/25 combinations |
| AZ (agriculture) ↔ GI (trade/hospitality) | 0.72 | 18/25 combinations |

**Claim status:** These associations are descriptive patterns from an optimization process that FAILS the predictive gate. They do not constitute validated economic structure. The sector graph co-occurrence is interesting but not reproducible enough (mean Jaccard 0.3353) to constitute stable structure. These patterns should not be used to support causal or recommendation claims.

---

## 9. Scientific Interpretation

### What the FAIL means

The dynamic dual economic graph does not provide predictive improvement over simpler baselines for French territorial enterprise births. Specifically:

1. **Ridge dominates** at MAE (+14.6% gap): the neural architecture adds capacity without predictive benefit.
2. **No-graph neural matches or beats dual-graph**: learning graph structure is not better than ignoring it for this prediction task and dataset.
3. **Sector graph contributes nothing beyond territory graph alone**: C5_dual ≈ C7_territory_graph_perm, confirming the learned sector adjacency does not help.
4. **Sector graph is not reproducible across seeds**: Jaccard 0.3353 — different random initializations learn different adjacencies.
5. **Recovery detection**: C5_dual beats prevalence but not C2_no_graph; the graph structure does not help early-warning either.
6. **2023 fold anomaly**: C5_dual degrades sharply in fold 2023 (+17.4% vs C2), suggesting the model may overfit sector structure learned on pre-2023 data.

### What the FAIL does NOT mean

- It does not refute the L2 co-growth sector-territory association graph (G-10, validated separately).
- It does not preclude a different graph architecture (e.g., GConvGRU, EvolveGCN-H) from passing a different experimental gate.
- It does not prove that graph structure can never help; it proves that this architecture at this parameter budget does not help under this protocol.

### Permitted claims

- "The dynamic dual-graph architecture (≤10,000 params, hidden_dim=8) does not improve territorial enterprise-birth prediction in France NUTS3 under 5-fold rolling-origin evaluation (2021–2025)."
- "The learned sector adjacency is not reproducible across random seeds (mean Jaccard 0.34), suggesting multiple near-optimal sparse structures exist under the current regularization."
- "Descriptively, the optimization consistently selects C↔KZ and FZ↔HZ pairs in approximately 76–80% of fold×seed runs."

### Forbidden claims

- "The sector graph reveals the true economic structure of French territories."
- "C↔KZ is a causal economic link."
- "The failure is due to insufficient data or training budget."
- Any forecast improvement claim.

---

## 10. Provenance and Integrity

| Item | Value |
|------|-------|
| Slurm job | 7453691 |
| Completed tasks | 275 / 275 |
| Failed tasks | 0 |
| Trainer commit | 9521264 |
| Tensor manifest | `data/processed/dual_graph_tensors/manifest.json` |
| Gate artifacts | `data/processed/dual_graph_s1/gate_result.json` |
| Raw results | `hpc_results/dual_graph_s1/raw/` (275 JSON files) |
| Aggregation | `data/processed/dual_graph_s1/summary_by_{run,fold_control,control}.csv` |
| Audit | `data/processed/dual_graph_s1/audit_summary.json` |

All 275 jobs have status=ok, no NaN/Inf in primary metrics, no leakage violations, correct temporal ordering, and consistent git commit hashes.

---

## 11. Next Steps After FAIL

Per contract §9 (fail-closed):

1. **Predictive dual-graph branch closed.** Do not relaunch P6_DDEG_S1.
2. **Do not modify hyperparameters, architecture, or tensors** based on this result.
3. **A1 graph-temporal track (GConvGRU/EvolveGCN-H)** remains blocked until A1a/A1b implementation and S1-FR local gate.
4. **Bloco 2 descriptive graph** (L2 co-growth, G-10) remains valid — it is a separate validated analytical track.
5. **Bloco 1 temporal forecasting** remains the primary predictive track.

Reopen condition (contract §9): demonstrated concrete operational failure in the protocol (not in model performance). Examples: tensor leakage discovered, gate misapplied, wrong controls. Performance alone is not a reopen condition.
