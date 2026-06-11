# HERALD — Dual Graph Trainer Audit

**Date:** 2026-06-11 (revised 2026-06-12)
**Decision:** `DUAL_GRAPH_TRAINER_READY`
**Scope:** France NUTS3, 101 regions, 9 A10 sectors, evaluation 2021-2025
**Contract:** `reports/HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md` (FROZEN_V2) §8–§9
**Files this step:**
- `src/modeles/train_dual_graph_experiment.py`
- `tests/test_train_dual_graph_experiment.py`
- `src/modeles/run_dual_graph_pilot.py`

**Not authorized in this step:** full study, HPC, SSH, commit, push. The scientific
fail-closed gate is implemented and unit-tested but **not applied to real data**;
the pilot is a technical liveness check only.

**Revision (2026-06-12, this step):** the null controls C7 and C8 were corrected.
The previous versions co-permuted features, adjacency **and targets**, which is a
similarity/relabeling that preserves the achievable loss — not a valid null. C7
and C8 now keep targets canonical and break only the structure↔economic-identity
alignment. See §2.4 for the mathematical correction.

---

## 1. Findings by Severity

| Severity | Finding |
|----------|---------|
| BLOCKER | None. |
| HIGH (resolved) | **Degenerate null controls.** Old C7/C8 co-permuted features, adjacency and targets by the same `P`, i.e. `X→PX`, `A→PAPᵀ`, `Y→PY`. For a model with shared region weights and free per-sector parameters this is a relabeling: the loss against the permuted targets is unchanged, so it does not test the graph. **Fixed** — C7 permutes only the territory adjacency (`PAPᵀ`), C8 permutes only the sector-graph-relevant inputs; both keep targets canonical. Proven degenerate-vs-valid in §2.4 and by test. |
| MEDIUM | Gate criterion 4 ("full graph beats territory and sector null controls") names no metric in the contract; **registered explicitly** as per-fold primary regression MAE (lower is better), territory null = C7, sector null = C8, counting folds where C5 < null separately (≥3/5). Recorded in `apply_gate` return (`control_roles`, `criterion4_metric`, `criterion4_direction`). |
| MEDIUM | Criterion 6 ("no fold regresses more than 10%") has no explicit reference in the contract; implemented as C5 MAE ≤ 1.10 × C2 (equal-capacity no-graph encoder) per fold. Documented. |
| LOW | On FR/2021 with patience 5, early stopping did not trigger within 30 epochs (inner-val MAE still improving at epoch 29). The patience machinery is correct and unit-tested; it simply was not reached in the short pilot. |
| INFO | C1 (sector Ridge) is fit on inner-train + inner-validation (all historical/causal) since it has no early stopping; the neural controls fit on inner-train and select on inner-validation. Both exclude the outer year. |
| INFO | C6 (territory temporal permutation) remains a control but is **not** the gate's territory null; the gate uses C7 (spatial adjacency permutation), the cleaner spatial-structure null. Documented in `apply_gate`. |

No finding blocks promotion of the trainer to a full local pilot run. The
HIGH finding is resolved in this step.

---

## 2. Protocol Implemented

### 2.1 Rolling-origin and temporal inner validation

For each outer fold `T ∈ {2021…2025}` the fold tensor holds `B` samples whose
target years are `[firstyear … T]`. The split is strictly temporal:

```
outer evaluation  = sample B-1      (target year T)
inner validation  = sample B-2      (latest historical year)
inner training     = samples 0 … B-3
```

`temporal_split` returns and *proves* `max(train_years) < val_year < outer_year`
and `max_feature_obs_year_outer < outer_year`, raising `RuntimeError` otherwise.
Regions are never split randomly. Example (FR/2021):
`train=[2017,2018,2019] val=2020 outer=2021`.

### 2.2 Normalization, weights, early stopping

- Normalization is already frozen per fold inside the tensors (training-only).
- Class weights (regime) and positive weights (recovery, emergence) come from
  **inner-train labels only**, ignoring `-1`.
- Early stopping uses the **inner-validation MAE**, never the outer fold; the
  best inner-val state is restored before the single outer prediction.
- Hyper-parameters and gate thresholds are frozen constants
  (`HYPERPARAMS`, `GATE`) set before any run.

### 2.3 Leakage audit

`run_experiment` writes `leakage_audit.json` recording, per fold, the train
years, validation year, outer year, max outer feature observation year and the
`leakage_ok` flag. Temporal permutations (C6, C10) reorder only the 5 in-window
causal steps; the sample/year axis is never permuted, so no future value enters.

### 2.4 Null-control correction (mathematical)

Let `f_θ` be the model, `X` the node features, `A` the adjacency, `Y` the
targets, `M` the mask, and `P` a node permutation matrix.

**Why a full co-permutation is not a null.** The model shares weights across
regions and reads region identity only through the adjacency. It is therefore
*permutation-equivariant*: for a consistent region permutation `P`,

```
f_θ(PX, P A Pᵀ) = P · f_θ(X, A).
```

If we ALSO permute the targets, `Y → PY`, then the masked loss is invariant:

```
L(f_θ(PX,PAPᵀ), PY, PM) = L(P f_θ(X,A), PY, PM) = L(f_θ(X,A), Y, M).
```

The "permuted problem" is the original problem with relabelled indices — the
achievable loss is identical, so it tests nothing about the graph. The same holds
for the sector axis once the free per-sector parameters (embedding, learned
graph) adapt. **This is the defect in the old C7/C8.** Verified exactly by
`test_full_copermutation_is_pure_relabeling` (region case, fixed weights):
`pred_degen = P · pred_canon` and `MAE` against the permuted targets is unchanged.

**Corrected C7 (territory null).** Permute only the territory adjacency:

```
X, Y, M canonical;   A → P A Pᵀ.
```

Now `f_θ(X, P A Pᵀ) ≠ P f_θ(X,A)` in general — and crucially `Y` is pinned at
canonical positions, so no relabeling of the (region-shared) parameters can
recover the canonical predictions. The graph aggregates the wrong neighbourhoods
for fixed node content and targets. The similarity transform `P A Pᵀ` preserves
the degree multiset, edge weights, density and symmetry exactly (no cross-country
edge is created — `P` only relabels the 101 French NUTS3).

**Corrected C8 (sector null).** Permute the sector axis of the features and of the
territory graph (kept internally aligned) by `σ`, with targets canonical:

```
X[...,s,:] → X[...,σ(s),:],   A_terr[...,s,:,:] → A_terr[...,σ(s),:,:];
Y, M canonical.
```

Position `s` now carries economic sector `σ(s)`'s features but must predict
economic sector `s`'s target with the position-`s` sector embedding and learned
sector-graph row. The sector economic identity is misaligned to the learned
structure and to the target; because `Y` is pinned, no parameter relabeling
restores the canonical loss. The per-sector territory matrices are preserved as a
set (only their sector slot is reindexed), so the territory region-structure is
not destroyed — the null is isolated to sector identity.

Both controls keep `Y, M` **bit-identical** to canonical (enforced by the
`targets_unchanged` guard, which raises on any target change), so prevalence is
unchanged and all metrics are computed against canonical targets.

---

## 3. Controls (C0–C10)

| ID | Key | Mechanism | Targets | Capacity |
|----|-----|-----------|---------|----------|
| C0 | persistence | previous observed log-growth (de-norm log-births diff) | — | n/a |
| C1 | ridge | `Ridge(α=10)` on flattened causal features (T·F per node) | — | n/a |
| C2 | no_graph | both graph messages off | canon | 1,035 |
| C3 | territory_only | territory message on, sector off | canon | 1,035 |
| C4 | sector_only | sector message on, territory off | canon | 1,035 |
| C5 | dual | both messages on | canon | 1,035 |
| C6 | territory_temporal_perm | territory adjacency **time** axis permuted | canon | 1,035 |
| **C7** | **territory_graph_perm** | **territory adjacency `P A Pᵀ` only** | **canon** | 1,035 |
| **C8** | **sector_identity_perm** | **sector axis of features + territory-sector axis by σ** | **canon** | 1,035 |
| C9 | no_ardeco | ARDECO channels (3,4,5) zeroed and masked | canon | 1,035 |
| C10 | ardeco_temporal_perm | ARDECO channels time-permuted | canon | 1,035 |

Control rules honoured:

- C2–C10 share identical capacity (graphs toggled by zeroing messages, not by
  removing parameters) — verified at **1,035 params** for all nine.
- Every permutation carries a recorded `perm_seed` and explicit `permutation`
  mapping; the seed depends only on `(base_seed, eval_year, control)` and never
  on any fold data (verified: corrupting the outer sample leaves the mapping
  unchanged), so no outer/future value influences the permutation.
- C7 and C8 keep targets canonical (guarded); the degenerate joint relabeling is
  rejected by `apply_control` (`ValueError`).
- No old L1 layer or ZE2020 edge file is referenced anywhere in code
  (AST string-literal audit in tests).

---

## 4. Metrics and Gate

### 4.1 Metrics per fold × seed

| Target | Metrics |
|--------|---------|
| Regression (log-growth) | MAE, median AE, Spearman ρ, sign accuracy (WMAPE forbidden) |
| Regime (3-class) | macro-F1, balanced accuracy, per-class F1, confusion matrix |
| Recovery (binary) | AUCPR, prevalence, precision@{5,10,20} |
| Emergence (binary) | AUCPR, prevalence, precision@k, recall@k, NDCG@k |
| Learned graph | top-k (k=3) sector edges, density, mean weight |
| Stability | mean pairwise seed Jaccard of top-k edges |

Years (not regions or seeds) are the effective replicates: aggregation averages
seeds within a fold, then folds.

### 4.2 Fail-closed gate (`apply_gate`, pure)

| # | Criterion | Implementation |
|---|-----------|----------------|
| c1 | MAE improves ≥1% over Ridge and no-graph | C5 ≤ 0.99·min over C1 and C2 (overall mean) |
| c2 | Regime macro-F1 +0.02 over no-graph and sector null | C5 ≥ C2+0.02 **and** C5 ≥ C8+0.02 |
| c3 | Recovery AUCPR > prevalence and > no-graph in ≥3/5 folds | per-fold count |
| c4 | Dual beats territory and sector null in ≥3/5 folds | **C5<C7** (territory null) **and C5<C8** (sector null) on primary MAE, per-fold counts ≥3/5 each |
| c5 | Mean seed top-k Jaccard ≥ 0.50 | C5 overall |
| c6 | No fold regresses MAE >10% | C5 ≤ 1.10·C2 every fold |
| c7 | c1–c4 still hold without 2021 | re-evaluated on {2022…2025}, ≥3/4 folds |

The gate is **fail-closed**: any missing or non-finite value makes the affected
criterion `False`. An empty result set yields `DUAL_GRAPH_S1_FAIL` with all
criteria false. Thresholds are frozen in `GATE` and never edited after observing
results. The gate result records its control roles explicitly
(`control_roles = {territory_null: C7_territory_graph_perm, sector_null:
C8_sector_identity_perm, …}`) and the registered criterion-4 metric/direction
(`primary_regression_mae`, `lower_is_better`) — nothing is left implicit.

### 4.3 Mandatory outputs

`run_experiment` writes (atomically, via temp-file + `os.replace`):

- `per_run/<control>__fr<year>__seed<seed>.json` — one file per run;
- `manifest.json` — git commit, per-fold tensor SHA-256, hyper-parameters, gate
  thresholds, environment (python/platform/torch/numpy), folds/controls/seeds;
- `leakage_audit.json` — explicit per-fold causal record;
- `summary_aggregated.json` — by fold/seed/control plus the gate block;
- `gate_result.json` — the pure-gate verdict.

---

## 5. Tests

`tests/test_train_dual_graph_experiment.py`: **44 passed** (30 prior + 14 new
null-control audit tests).

| Area | Tests |
|------|-------|
| Rolling-origin / temporal | causal split proven; too-few-samples rejected |
| No outer target in train/selection | corrupting outer targets leaves training and predictions unchanged; forward has no target arg |
| Class weights | train-slice only; immune to val/outer label changes |
| Equal capacity | C2–C10 all 1,035 params |
| Determinism | identical predictions and val history for a fixed seed; C7/C8 mappings deterministic per seed |
| Permutations C6/C9/C10 | correct axis, causal window, recorded seed/mapping |
| **Null-control correction** | full co-permutation proven a relabeling (`pred_degen = P·pred_canon`, MAE invariant); C7 permutes adjacency only; C8 permutes sector inputs only; **targets bit-identical** in C7/C8; territory degree/weight/density preserved under `PAPᵀ`; territory graph preserved as a set under C8; predictions of C5/C7/C8 differ under the same weights; inverse permutation does **not** recover canonical predictions; metrics use canonical targets; permutation independent of outer data; degenerate co-permutation detected/rejected |
| Metrics known cases | regression (MAE/sign), regime (perfect→F1=1), binary rare-class AUCPR/precision@k/recall/NDCG, single-class→AUCPR None |
| Graph top-k / Jaccard | edge extraction, density, pairwise + mean seed Jaccard, <2 seeds→0 |
| Gate pass/fail fixtures | passes on good agg; **uses C7/C8 nulls + registered metric explicitly**; fails on weak null (C7/C8 as good as dual), weak Jaccard, no MAE gain, missing data (fail-closed); passes with strong null |
| Atomic writes | round-trip, overwrite, no leftover temp files |
| NaN/Inf fail-closed | aggregation skips non-ok runs |
| No legacy dependency | AST audit: no `g1_l1`/`ze2020`/`edges.csv`/`.geojson` in code literals |

Full related suite re-run: `test_train_dual_graph_experiment` +
`test_dual_graph_models` + `test_dual_graph_tensors` + `test_dual_graph_targets`
→ **136 passed**. `py_compile`: pass. `git diff --check`: clean.

---

## 6. Pilot Result

`python -m src.modeles.run_dual_graph_pilot` — FR/2021, seeds {42,43}, ≤30
epochs, patience 5, controls C0–C5 + C6 + **C8 (corrected)** (C7/C9/C10 not run).

```
leakage check: train_years=[2017,2018,2019] val_year=2020 outer_year=2021  OK
samples: 5 (train 3, val 1, outer 1)

control                      seed  status  params       mae  stop@  best@
C0_persistence                 42      ok       0   0.22508      —      —
C1_ridge                       42      ok       —   0.14848      —      —
C2_no_graph                    42      ok    1035   0.13002     30     29
C3_territory_only              42      ok    1035   0.12557     30     29
C4_sector_only                 42      ok    1035   0.13107     30     29
C5_dual                        42      ok    1035   0.12317     30     29
C6_territory_temporal_perm     42      ok    1035   0.12620     30     29
C8_sector_identity_perm        42      ok    1035   0.12315     30     29
(seed 43: C5=0.14435 vs C8=0.13662 — C8 now differs from C5, as expected for a
 non-relabeling null; all status=ok, finite MAE)

runtime=9.3s  peak_rss=0.454 GB  deterministic=True
PILOT PASS — technical liveness only, no scientific claim.
```

All 16 runs: status `ok`, finite losses, complete and finite outputs, identical
1,035-param capacity for neural controls, no leakage. C5/seed-42 reproduced
bit-identical predictions across two independent fits (determinism). The
corrected C8 produces MAE distinct from C5 (e.g. seed 43: 0.13662 vs 0.14435),
confirming it is no longer a relabeling. **These MAE numbers are not results** —
one fold, two seeds, three training samples and 30 epochs cannot support any
control comparison, and the scientific gate is deliberately not applied here.

---

## 7. Runtime and Memory

| Metric | Value |
|--------|-------|
| Pilot runtime (16 runs + determinism rerun) | 8.8 s |
| Peak RSS | 0.452 GB |
| Per-neural-run forward cost | ~18k nodes × 5 steps × GRUCell(H=8), CPU |
| 15-minute guard | not approached |

Extrapolation (informative only, not a commitment): the full study is
5 folds × 11 controls × 5 seeds = 275 runs, of which 9×5×5 = 225 are neural at
≤200 epochs. At the observed per-run cost this is well within a single local
session, but the run remains gated behind `--confirm-full-run`.

---

## 8. Limitations

- The pilot proves plumbing, not science: no metric here is interpretable as a
  result, and the gate is not applied.
- Early stopping did not fire on FR/2021 within 30 epochs (val MAE still falling);
  the full run uses patience 20 / max 200 epochs.
- Gate criteria 4 and 6 required a metric/reference choice the contract left
  implicit; both are documented in §1 and `apply_gate`.
- Recovery and emergence remain rare; AUCPR/precision@k against prevalence are
  computed, but small fold sizes make per-fold AUCPR noisy — years are the
  replicates, and 2021 (COVID) is excluded in criterion 7.
- The learned sector graph top-k is extracted from the seed-mean adjacency;
  seed-Jaccard stability is only meaningful at the full five-seed run.

---

## 9. Decision

`DUAL_GRAPH_TRAINER_READY`

The trainer implements the full §8–§9 protocol: causal rolling-origin with
temporal inner validation, all eleven controls at equal neural capacity, the
four-task loss with train-only weights, the complete metric suite, the pure
fail-closed gate (passing/failing on fixtures), atomic outputs with a reproducible
manifest, and an explicit leakage audit. Unit tests (30) and the related suites
(122 total) pass; the FR/2021 technical pilot runs in 8.8 s at 0.45 GB,
deterministically, with finite losses and complete outputs and no leakage.

---

## 10. Exact Next Step

Run the **rolling-origin pilot-to-full sequence locally, still without HPC**:

1. Local validation pilot at reduced budget across all five folds and two seeds
   (e.g. `--folds 2021…2025 --seeds 42 43 --max-epochs 50 --patience 10`) to
   confirm runtime/memory at full fold count and to exercise C7/C9/C10 end-to-end.
2. If healthy, launch the full study locally with
   `--confirm-full-run` (5 folds × 11 controls × 5 seeds, max 200 epochs,
   patience 20), writing `data/processed/dual_graph_s1/`.
3. Apply `apply_gate` to the aggregated results and record the verdict
   (`DUAL_GRAPH_S1_PASS` / `DUAL_GRAPH_S1_FAIL`) in
   `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md`.

HPC submission stays blocked until the local full run completes and its gate
verdict is recorded. No commit or push is performed in this step.
