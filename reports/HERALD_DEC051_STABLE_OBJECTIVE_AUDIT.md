# HERALD DEC-051: Stable Objective Audit

**Status:** IMPLEMENTATION_COMPLETE — experiment pending (requires local execution)
**Date:** 2026-06-15
**Predecessor:** DEC-050 (bug corrections)
**Decision:** DEC-051

---

## 1. Context and Motivation

DEC-050 identified and corrected three critical bugs in the Phase 14 pretraining code:

- **Bug A**: TEMPORAL_MASKED computed NLL on visible cells instead of artificially hidden cells
- **Bug B**: `_edge_bce` only marked lag-1 as positive (lag-2 edges treated as negative)
- **Bug C**: Sign and lag heads shared the same logit, making sign prediction architecturally impossible

With Bug A corrected, TEMPORAL_MASKED@75 achieved MAE=0.2327 on novel_lag2, beating ffill (0.2568) by 9.4% — first neural beat of ffill in zero-shot.

Additionally, the few-shot (A1, decoder-only) adaptation showed 78-80% MAE reduction across ALL variants — including NO_PRETRAINING. This raised two concerns:

1. **Is the few-shot gain genuine, or is it a leakage/evaluation artifact?** The identical reduction for NO_PRETRAINING suggests it may be independent of pretraining, which is suspicious.
2. **Can the graph multitask loss be stabilized?** GRAPH_MASKED_MULTITASK showed catastrophic variance collapse at 50 D2 datasets (val_loss → -421009 at 75 epochs).

DEC-051 addresses both by: (1) rigorous negative audit of the few-shot mechanism, (2) stable reconstruction loss (clamped NLL, Huber), and (3) independent graph heads for sign and lag.

---

## 2. Design Decisions (Frozen Before Results)

### 2.1 Reconstruction Loss Variants

| Variant | Loss Type | Variance Head | Notes |
|---------|-----------|---------------|-------|
| R1 | Clamped NLL | Yes (clamped to [-3,2]) | Entropy penalty λ=0.001 prevents boundary sitting |
| R2 | Huber (δ=1.0) | No | Robust to outliers; cannot produce variance collapse |
| R3 | MSE | No | Diagnostic baseline only |

All constants frozen: `LOG_SIGMA_MIN=-3.0`, `LOG_SIGMA_MAX=2.0`, `SIGMA_ENTROPY_LAMBDA=0.001`, `HUBER_DELTA=1.0`.

### 2.2 Training Variants (5 total)

| Variant | Reconstruction | Graph Heads |
|---------|---------------|-------------|
| NO_PRETRAINING | — (Phase 11 T2) | No |
| TEMPORAL_MASKED_NLL_CLAMPED | Clamped NLL | No |
| TEMPORAL_MASKED_HUBER | Huber | No |
| GRAPH_MULTITASK_NLL_CLAMPED | Clamped NLL | Yes (independent) |
| GRAPH_MULTITASK_HUBER | Huber | Yes (independent) |

### 2.3 Graph Auxiliary Heads (DEC-051 Fix for Bug C)

```
edge_presence_logit  = max(log_attn_lag1, log_attn_lag2)   ← from main model
edge_sign_logit      = GraphAuxHeads.sign_logit[t, s]       ← INDEPENDENT parameter
edge_lag_logit       = GraphAuxHeads.lag_logit[t, s]        ← INDEPENDENT parameter
```

Loss weights (frozen): `ALPHA=0.10` (presence), `BETA=0.05` (sign), `GAMMA=0.05` (lag).

### 2.4 Few-Shot Negative Test Battery (NT1-NT6)

| Test | What it corrupts | What must hold |
|------|-----------------|----------------|
| NT1 | Test targets → 9999 | Predictions and best_epoch unchanged |
| NT2 | Test targets → noise | Predictions unchanged |
| NT3 | Future targets shifted +100 | Support window predictions unchanged |
| NT4 | Support labels permuted | Few-shot gain < 50% of correct gain |
| NT5 | Empty support (k_frac=0) | MAE reproduces zero-shot (atol=1e-5) |
| NT6 | Random decoder reinit | Random-decoder MAE ≥ 80% of zero-shot |

### 2.5 Evaluation Protocol

- **Seeds (FROZEN):** 1000, 2000, 3000, 4000, 5000
- **Scenarios:** novel_lag2, novel_highvar
- **Masks:** mcar_30, block_30
- **Few-shot k_frac:** 5% and 10% of observed cells
- **Selection:** Top-2 variants by val_loss on nonlinear_heavy/mcar_30 — NOT on test
- **Budget:** 30, 75, 150 epochs (cumulative training)

---

## 3. Gates V1-V10 (Frozen Before Results)

| Gate | Description | Threshold |
|------|-------------|-----------|
| V1 | Safety: no leakage/NaN/Inf | NT verdict = PASS; no NaN MAE; log_sigma ∈ [-3,2] |
| V2 | Few-shot integrity | NT1-NT6 all pass |
| V3 | Temporal reconstruction | Best TEMPORAL_MASKED beats ffill AND no-graph; ≥4/5 seeds |
| V4 | Block robustness | Beats ffill on block_30 (not only mcar_30) |
| V5 | Shift robustness | Effect in both novel_lag2 and novel_highvar |
| V6 | Stable loss | Loss finite; log_sigma stays in [-3,2] across all results |
| V7 | Graph objective | GRAPH_MULTITASK beats TEMPORAL_MASKED in aggregate MAE |
| V8 | Relation recovery | Edge AUC ≥ 0.60, AUPRC > prevalence; sign/lag > chance |
| V9 | Few-shot value | Top-2 val-selected variant: 5% or 10% improves zero-shot |
| V10 | Replication | Effect in ≥4/5 seeds |

**300-epoch gate (V300):** Requires V1+V2+V6 PASS + monotone 30→75→150 + ≥4/5 seeds + no regression. Still requires explicit user authorization even if gate passes.

---

## 4. Implementation Files

### New (DEC-051)

| File | Purpose |
|------|---------|
| `src/modeles/synthetic/phase15_stable_objective/__init__.py` | Module marker |
| `src/modeles/synthetic/phase15_stable_objective/loss_functions.py` | R1 (clamped NLL), R2 (Huber), R3 (MSE), disjoint mask check |
| `src/modeles/synthetic/phase15_stable_objective/graph_heads.py` | GraphAuxHeads: independent sign/lag parameters |
| `src/modeles/synthetic/phase15_stable_objective/fewshot_audit.py` | NT1-NT6 negative test battery |
| `src/modeles/synthetic/phase15_stable_objective/pretrain_runner_v2.py` | Training loop for 5 variants × 3 budgets |
| `src/modeles/synthetic/phase15_stable_objective/evaluator_v2.py` | Zero-shot and few-shot evaluation |
| `src/modeles/synthetic/phase15_stable_objective/gates_dec051.py` | V1-V10 + V300 gate logic |
| `src/modeles/synthetic/phase15_stable_objective/run_dec051.py` | CLI orchestrator |
| `tests/test_phase15_stable_objective.py` | 38 tests (all passing) |

### Unchanged (DEC-050 bug fixes preserved)

- `src/modeles/synthetic/phase14_convergence/pretrain_runner.py` (bugs A/B/C fixed)
- `src/modeles/synthetic/phase14_convergence/run_convergence.py` (REPO_ROOT fix)
- `tests/test_phase14_convergence.py` (30 tests, all passing)

---

## 5. Test Coverage

38 tests in `tests/test_phase15_stable_objective.py` (all passing):

| Category | Tests |
|----------|-------|
| Loss functions (R1/R2/R3/disjoint check) | 7 |
| GraphAuxHeads (independence, BCE, gradient, formula) | 7 |
| Seed safety | 2 |
| Evaluator (result structure, MAE finite, eval/obs disjoint) | 5 |
| Few-shot (attention frozen, result fields) | 2 |
| Selection | 1 |
| Gate logic (V1/V2/V3/V6/V9/V300, format) | 8 |
| Negative tests (NT5, NT6) | 2 |
| Checkpoint immutability | 1 |
| Determinism | 1 |
| Reconstruction disjoint check in runner | 1 |
| Graph metrics | 1 |

---

## 6. To Run the Experiment

```bash
# Full run (5 variants × 3 budgets × 5 seeds × 2 scenarios × 2 masks)
python -m src.modeles.synthetic.phase15_stable_objective.run_dec051 \
    --output-dir data/processed/synthetic_benchmark/phase15_stable_objective \
    --device cpu \
    --n-datasets 50
```

Output files:
- `checkpoint_manifest.json` — all checkpoint paths + hashes
- `zero_shot_results.json` — per-seed results + aggregate summary
- `negative_audit.json` — NT1-NT6 verdict
- `fewshot_results.json` — few-shot results for top-2 selected variants
- `gate_results.json` — V1-V10 + V300 verdicts with evidence
- `gate_report.md` — markdown gate table
- `run_summary.json` — final status

**Note:** Do not proceed to 300-epoch run without explicit authorization, even if V300 gate passes.

---

## 7. Limitations

1. **`_nogr_baseline`** uses forward fill as proxy for the no-graph baseline, rather than running the HERALD model with zeroed adjacency (as in DEC-049 evaluator). Updated to use zeroed adjacency in the implementation.
2. **VAL_SCENARIO (`nonlinear_heavy`)** is not a novel test scenario — it overlaps with training scenarios by category (but uses different seeds). This maintains comparability with DEC-049/050.
3. **NT2 and NT3** test that evaluation is independent of held-out cells, but do not distinguish between genuine few-shot generalization and in-context fitting to the support distribution. NT4 (permuted labels) addresses this more directly.
4. **Graph head metrics** (AUC, sign_acc, lag_acc) are computed only on the D2 synthetic test scenarios where ground-truth relations are available. No claims about real-data relation recovery.

---

## 8. Provisional Interpretation (Pending Results)

From the DEC-050 finding (Bug A fix → TEMPORAL_MASKED beats ffill):

- If V1+V2 PASS: the 78-80% few-shot gain is real, not leakage. The question becomes whether pretraining contributes (NT4/NT6 will be informative).
- If V2 FAILS: there is evaluation leakage in the few-shot protocol. Stop and diagnose.
- If V6 FAILS: log_sigma is hitting clamp boundaries — increase clamping range or switch to Huber.
- If V7 FAILS: graph auxiliary heads add noise rather than signal. Consider dropping them and focusing on TEMPORAL_MASKED.

The 300-epoch run is authorized ONLY with V1+V2+V6 PASS + monotone improvement + explicit user authorization.
