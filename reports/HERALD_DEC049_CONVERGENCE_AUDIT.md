# HERALD — DEC-049 Convergence Audit
**Phase 14 | Date: 2026-06-15 | Status: PROTOCOL_READY (implementation complete, execution pending)**
**Hypothesis under test: TRAINING_BUDGET_TOO_SMALL (DEC-048 principal cause)**

---

## 1. DEC-048 Audit Findings (Task 0 Corrections)

Four issues identified in the DEC-048 report have been corrected before implementing DEC-049:

### 1a. C10 (BEATS_FFILL) — Oracle vs Learned Distinction

**Issue:** The original C10 PASS note was ambiguous ("Best neural MAE ratio=0.929 (oracle locally trained)").
It was possible to misread this as learned HERALD beating ffill.

**Correction applied:** Added explicit clarification that C10 PASS is driven by oracle M4
(locally trained, frozen true attention) — NOT by learned zero-shot HERALD.
Learned HERALD zero-shot (M3) achieves MAE ratio ≈ 0.997, barely at ffill parity.
C10 confirms the architecture CAN beat ffill given correct graph structure; it does NOT
confirm that zero-shot learned HERALD beats ffill.

### 1b. "Gradient 400× Smaller" — Added Caveat

**Issue:** The phrase "The attention gradient is 400× smaller than MLP gradient" was stated
as a fact without qualifying it as diagnostic evidence.

**Correction applied:** Changed to "~400× smaller (diagnostic evidence, not proof that budget
is the sole cause — see Section 10)". The gradient ratio is a measurement from a single
backward pass on a small dataset; it is consistent with the budget hypothesis but does not
rule out other causes (e.g., learning rate, initialization, data diversity).

### 1c. SYNTHETIC-ONLY Constraint — Strengthened Labelling

**Issue:** The constraint on edge/sign/lag supervision was mentioned in Section 8 but not
prominently marked.

**Correction applied:** Added bold "SYNTHETIC-ONLY CONSTRAINT:" header in Section 8 to make
it impossible to miss when reading the pretraining results.

### 1d. Pretrain Seeds Disjointness — Verified

Seeds 200-249 (D2 datasets) are confirmed disjoint from TEST_SEEDS=[1000,2000,3000,4000,5000]
and from Phase 9/10 BENCHMARK_SEEDS=[42,123,456,789,1337]. No correction needed.
Phase 14 D2 seed range [200, 200+N_DATASETS) inherits this verified disjointness.

---

## 2. Protocol

### 2a. Epoch Budgets

| Budget | Purpose |
|--------|---------|
| 30 | Reference (DEC-048 pilot level) |
| 75 | Intermediate |
| 150 | Full scale (primary evaluation) |
| 300 | Only if E2 auto-trigger fires (E1+E2 PASS at 150 with monotone improvement) |

**Rule:** 300 epochs are NOT pre-authorized. They require programmatic trigger after 150.

### 2b. Pretraining Variants

| Variant | Description |
|---------|-------------|
| NO_PRETRAINING | Phase 11 T2 checkpoint (no additional pretraining) |
| TEMPORAL_MASKED | Masked NLL reconstruction (40% extra MCAR on observed cells), 50 D2 datasets |
| GRAPH_MASKED_MULTITASK | NLL + edge_BCE + sign_BCE + lag_BCE, 50 D2 datasets |

**SYNTHETIC-ONLY CONSTRAINT:** GRAPH_MASKED_MULTITASK uses `true_relations` ground truth
which does NOT exist for real country data (PT/IT/FR/NL/AT). This objective is a
synthetic-only diagnostic tool and must not be claimed to generalize to real data.

### 2c. D2 Datasets

```python
n_territories = 30  # same as novel_lag2/novel_highvar
n_sectors = 9
n_years = 20
seeds = range(200, 250)  # 50 datasets, disjoint from TEST_SEEDS
frac_nonlinear in [0.0, 0.9]  # uniform
territory_radius in [0.28, 0.38]  # avoids 0.25 (novel_lag2) and 0.42 (novel_highvar)
forced_lag = None  # avoids forced_lag=2 (novel_lag2)
structural_break_year = None  # avoids year=8 (novel_highvar)
```

### 2d. Validation Configuration (Phase 11 Convention)

```python
val_scenario = "nonlinear_heavy"
val_seeds = [100, 200, 300]
val_mask_key = "mcar_30"
```

Best checkpoint selected by minimum val NLL — NOT last epoch.

### 2e. Test Scenarios

| Scenario | Key Properties |
|----------|---------------|
| novel_lag2 | frac_nonlinear=0.85, forced_lag=2, territory_radius=0.25 |
| novel_highvar | frac_nonlinear=0.90, structural_break_year=8, high noise |

Both scenarios are strictly out-of-distribution from the D2 training distribution.

### 2f. Frozen Loss Weights

```python
MULTITASK_ALPHA = 0.1    # edge_presence BCE — FROZEN
MULTITASK_BETA  = 0.05   # sign prediction BCE — FROZEN
MULTITASK_GAMMA = 0.05   # lag prediction BCE — FROZEN
```

These values are frozen before execution. Do NOT change after seeing results.

---

## 3. Pretraining Convergence Curves

*Execution pending. Placeholder for results table.*

| Variant | Budget | Best Epoch | Best Val Loss | Train Loss (final) | Runtime (s) |
|---------|--------|-----------|---------------|-------------------|-------------|
| TEMPORAL_MASKED | 30 | — | — | — | — |
| TEMPORAL_MASKED | 75 | — | — | — | — |
| TEMPORAL_MASKED | 150 | — | — | — | — |
| GRAPH_MASKED_MULTITASK | 30 | — | — | — | — |
| GRAPH_MASKED_MULTITASK | 75 | — | — | — | — |
| GRAPH_MASKED_MULTITASK | 150 | — | — | — | — |

**E2 evaluation:** Val loss must improve by ≥0.5% per budget step for at least one variant.

---

## 4. Gradient Norms Per Variant

*Execution pending. Placeholder for results table.*

Measured during final epoch of training on a representative D2 dataset.

| Variant | Budget | grad_attn | grad_decoder | grad_multitask | aux_reaches_attn |
|---------|--------|-----------|-------------|----------------|-----------------|
| TEMPORAL_MASKED | 150 | — | — | N/A | N/A |
| GRAPH_MASKED_MULTITASK | 150 | — | — | — | — |

**Key measurement:** Whether auxiliary (edge/sign/lag) loss gradients propagate to
`log_sect_attn_lag1` (checked via `.grad is not None` after backward).

**DEC-048 reference for comparison:**
- NLL: grad_attn ≈ 0.0051, grad_mlp ≈ 2.034 (~400× ratio)
- L2 loss: grad_lag1_attn ≈ 0.0073 (2× vs NLL, but still small)

---

## 5. Zero-Shot Results

*Execution pending. Placeholder for results table.*

### novel_lag2 scenario

| Variant | Budget | MAE (herald) | AUC | vs ffill | vs no_graph |
|---------|--------|-------------|-----|----------|------------|
| NO_PRETRAINING | 30 | — | — | — | — |
| TEMPORAL_MASKED | 30 | — | — | — | — |
| TEMPORAL_MASKED | 75 | — | — | — | — |
| TEMPORAL_MASKED | 150 | — | — | — | — |
| GRAPH_MASKED_MULTITASK | 30 | — | — | — | — |
| GRAPH_MASKED_MULTITASK | 75 | — | — | — | — |
| GRAPH_MASKED_MULTITASK | 150 | — | — | — | — |

### novel_highvar scenario

| Variant | Budget | MAE (herald) | AUC | vs ffill |
|---------|--------|-------------|-----|----------|
| (same structure as above) | | | | |

---

## 6. Comparison vs Baselines

*Execution pending.*

| Model | novel_lag2 MAE | novel_highvar MAE | Note |
|-------|---------------|------------------|------|
| ffill | — | — | Reference baseline |
| ridge | — | — | Temporal-only reference |
| no_graph | — | — | Herald with adj=0 |
| herald_lagged (best) | — | — | Best variant × budget |
| herald_permuted | — | — | Null graph |
| oracle_lagged | — | — | Upper bound (SYNTHETIC-ONLY) |

**graph_contribution** = MAE(no_graph) − MAE(herald_lagged) per seed/mask.
Positive = graph helps; can be negative.

---

## 7. Few-Shot Results

*Execution pending.*

Few-shot strategy: A1 (decoder-only, frozen attention), 50 adaptation epochs.
Temporal split: 65% support / 15% val / 20% test.

| Variant | Budget | k_frac | MAE (few-shot) | vs zero-shot | AUC (preserved?) |
|---------|--------|--------|---------------|-------------|-----------------|
| GRAPH_MASKED_MULTITASK | 150 | 5% | — | — | — |
| GRAPH_MASKED_MULTITASK | 150 | 10% | — | — | — |
| TEMPORAL_MASKED | 150 | 5% | — | — | — |
| TEMPORAL_MASKED | 150 | 10% | — | — | — |

**E7 evaluation:** Few-shot (5% or 10%) must beat zero-shot by ≥0.5% MAE.
**E8 evaluation:** AUC must not drop >0.05 after few-shot adaptation.

---

## 8. Gates E1-E10 Outcome Table

*Execution pending.*

All thresholds FROZEN before execution — do NOT change after seeing results.

| Gate | Threshold | Result | Evidence |
|------|-----------|--------|---------|
| **E1 SAFETY** | no NaN/Inf, seeds disjoint | — | — |
| **E2 CONVERGENCE** | val_loss gain ≥0.5%/step | — | — |
| E3 RELATION_LEARNING | AUC≥0.60, AUPRC≥1.5×prev | — | — |
| E4 RECONSTRUCTION | herald < no_graph by ≥0.5% | — | — |
| E5 BASELINE_RELEVANCE | herald < ffill | — | — |
| E6 MULTITASK_VALUE | GRAPH_MULTITASK < TEMPORAL | — | — |
| E7 FEWSHOT_VALUE | few-shot < zero-shot by ≥0.5% | — | — |
| E8 GRAPH_PRESERVATION | AUC drop ≤5% after few-shot | — | — |
| E9 REPLICATION | effect in ≥2/3 seeds | — | — |
| E10 BLOCK_ROBUSTNESS | gain in block_30 ≥2/3 seeds | — | — |

---

## 9. 300-Epoch Rule

Auto-trigger condition (checked programmatically after 150-epoch run):
```
trigger = E1 PASS AND E2 PASS AND (val_loss[75→150] improvement ≥ 0.5%)
```

If triggered: run 300 epochs for all variants and re-evaluate.
If NOT triggered: report states 300 not triggered and why.

*Result: execution pending.*

---

## 10. Decision

*Execution pending.*

Decision vocabulary (from gate outcomes):
- `CONVERGENCE_HYPOTHESIS_SUPPORTED` — ≥6/10 gates PASS
- `CONVERGENCE_PARTIAL` — 4-5/10 gates PASS
- `CONVERGENCE_HYPOTHESIS_NOT_SUPPORTED` — <4/10 gates PASS
- `STOP_E1_SAFETY` — E1 fails (halt immediately)

---

## 11. Next DEC Recommendation

*Execution pending. Template:*

If decision = CONVERGENCE_HYPOTHESIS_SUPPORTED:
  → DEC-050: Full adaptation evaluation (DEC-047 strategies Z0/A1/A2) with best Phase 14 checkpoint.
     Primary question: does the 150-epoch pretrained model enable few-shot to beat ffill?

If decision = CONVERGENCE_PARTIAL:
  → DEC-050 with 300-epoch checkpoint if trigger fires.
  → Also: investigate structural_break generalization (novel_highvar specifically).

If decision = CONVERGENCE_HYPOTHESIS_NOT_SUPPORTED:
  → Re-examine architecture. Consider whether the attention bottleneck is inherent.
  → Investigate data quantity scaling (n=100+ datasets).

**Forbidden per DEC-009:** No geographic graph for real country data.
**Claim restriction:** ALL findings from Phase 14 apply to SYNTHETIC data only.
Do NOT claim any result generalizes to PT/IT/FR/AT/NL.

---

## Implementation Details

### Package

```
src/modeles/synthetic/phase14_convergence/
  __init__.py           — package declaration
  pretrain_runner.py    — D2 generation, multitask losses, budget grid
  evaluator.py          — zero-shot and few-shot evaluation
  gates_dec049.py       — E1-E10 gates (frozen thresholds)
  run_convergence.py    — CLI script with pilot/full mode
```

### Tests

`tests/test_phase14_convergence.py` — 25 tests (all pass in ~15s)

### Run Command

```bash
# Pilot (fast validation):
python src/modeles/synthetic/phase14_convergence/run_convergence.py \
    --device cpu --pilot \
    --output-dir data/processed/synthetic_benchmark/phase14_convergence

# Full run:
python src/modeles/synthetic/phase14_convergence/run_convergence.py \
    --device cpu \
    --output-dir data/processed/synthetic_benchmark/phase14_convergence
```

### Output Files

```
data/processed/synthetic_benchmark/phase14_convergence/
  checkpoints/           — model_*.pt files per variant × budget
  pretrain_results.json  — pretraining history and grad norms
  records.json           — flat list of evaluation records
  gates_dec049.json      — E1-E10 gate outcomes
  run_summary.json       — run configuration and totals
```
