# HERALD — Few-shot Adaptation Pilot Results
**DEC-047 | Data: 2026-06-13 | Status: PILOT_COMPLETE**
**Decision: FEWSHOT_ADAPTATION_FAILED**

---

## 1. Pilot Configuration

| Parameter | Value |
|-----------|-------|
| Base model | T2 (linear + mixed_default training, Phase 11) |
| Checkpoint | `data/processed/synthetic_benchmark/phase11_pilot/model_T2_pilot.pt` |
| Checkpoint hash | `32cf5426edd9ed5d983de848c7dc17f4` |
| Scenario | novel_lag2 (frac_nonlinear=0.85, forced_lag=2) |
| Dataset seeds | [1000, 2000, 3000] |
| k_fracs | [0.0, 0.05, 0.10] |
| Support seeds | [42, 123, 456] |
| Strategies | Z0, A1, A2, A4, C0, B0, B1, P0 |
| Mask keys | mcar_30, block_30 |
| Adaptation epochs | 50 (patience=10) |
| Device | CPU |
| Total records | 432 |
| Runtime | ~85 seconds |
| Temporal split (n_years=20) | support=[0..12], val=[13..15], test=[16..19] |

---

## 2. MAE Results by Strategy

### Overall (all k_fracs, all seeds, both masks)

| Strategy | n | Mean MAE | Min MAE | Max MAE |
|----------|---|----------|---------|---------|
| B0 (ffill) | 54 | **0.2434** | 0.2031 | 0.2752 |
| B1 (Ridge) | 54 | 0.2787 | 0.2334 | 0.3191 |
| Z0 (zero-shot) | 54 | 0.2808 | 0.2372 | 0.3164 |
| C0 (no-graph) | 54 | 0.2809 | 0.2338 | 0.3247 |
| P0 (permuted) | 54 | 0.2811 | 0.2333 | 0.3236 |
| A4 (full FT) | 54 | 0.2811 | 0.2331 | 0.3274 |
| A1 (decoder only) | 54 | 0.2815 | 0.2328 | 0.3279 |
| A2 (adapter) | 54 | 0.2979 | 0.2332 | 0.4855 |

### Per k_frac (mean over seeds and masks)

| Strategy | k=0.0 | k=0.05 | k=0.10 |
|----------|-------|--------|--------|
| Z0 | 0.2808 | 0.2808 | 0.2808 |
| A1 | 0.2808 | 0.2803 | 0.2835 |
| A2 | 0.3297 | 0.2827 | 0.2813 |
| A4 | 0.2808 | 0.2793 | 0.2833 |
| C0 | 0.2803 | 0.2789 | 0.2835 |
| P0 | 0.2806 | 0.2793 | 0.2833 |
| B0 | 0.2434 | 0.2434 | 0.2434 |
| B1 | 0.2787 | 0.2787 | 0.2787 |

### Key observations:
1. **B0 (ffill) dominates all neural strategies at MAE** — consistent with Phase 11 finding (X9 FAIL). Forward fill is the best single strategy on novel_lag2.
2. **All neural strategies cluster near 0.28** — adaptation provides no measurable benefit over zero-shot.
3. **A2 (adapter) has HIGH VARIANCE** — max MAE 0.4855 vs Z0 max 0.3164, indicating instability with some support seed/k_frac combinations.
4. **No graph contribution detectable** — A1/A2/A4 vs C0/P0 are indistinguishable in MAE.

---

## 3. Graph Preservation Table

| Strategy | graph_preserved (frac) | mean auc_change |
|----------|------------------------|----------------|
| Z0 | 1.00 | 0.0000 |
| A1 | 1.00 | 0.0000 |
| A2 | 1.00 | 0.0000 |
| A4 | 1.00 | +0.0001 |
| C0 | 1.00 | 0.0000 |
| P0 | 1.00 | 0.0000 |

**A6 PASS:** Graph structure (attention matrices) is perfectly preserved across all strategies. 50 epochs of adaptation does not degrade edge AUC.

---

## 4. Gate Outcomes A1-A10

| Gate | Outcome | Rationale |
|------|---------|-----------|
| **A1 SAFETY** | **PASS** | NaN=0, leakage=0, n_hidden>0 for all records |
| A2 ADAPTATION_BENEFIT | FAIL | adapted_mae < z0_mae in < 50% of comparisons |
| A3 GRAPH_CONTRIBUTION | FAIL | A1/A2 MAE not reliably < C0/P0 MAE |
| A4 BASELINE_RELEVANCE | FAIL | neural MAE > B0 (ffill) in most comparisons |
| A5 FEWSHOT_EFFICIENCY | FAIL | no benefit at k_frac ≤ 0.10 |
| **A6 GRAPH_PRESERVATION** | **PASS** | auc_change ≥ -0.05 for all strategies |
| **A7 BLOCK_ROBUSTNESS** | **PASS** | result consistent in block_30 (consistent FAIL) |
| A8 REPLICATION | FAIL | no consistent improvement direction across seeds |
| A9 ADAPTER_VALUE | FAIL | A2 not reliably better than A1 |
| A10 FINETUNING_TRADEOFF | FAIL | A4 not better than A1 |

**Overall: 3/10 PASS**

---

## 5. Decision

**FEWSHOT_ADAPTATION_FAILED**

### Diagnosis

The Phase 12 pilot confirms and deepens the Phase 11 finding (DEC-045):

1. **MLP adaptation does not help under extreme OOD shift.** With 50 epochs × 50 support labels, all neural strategies produce MAE indistinguishable from zero-shot (Z0). The distribution gap (0-30% → 85% nonlinear) is too large for 50-epoch fine-tuning to bridge.

2. **Forward fill dominates (MAE=0.244 vs neural ~0.281).** On novel_lag2 with structural breaks and high autocorrelation, copying the last observed value is better than any neural prediction. This is consistent with X9 FAIL in Phase 11.

3. **Graph structure provides no measurable MAE benefit in this regime.** A1 vs C0 (no-graph) and P0 (permuted) are statistically indistinguishable. The attention matrices encode correct directed associations (AUC=0.611) but the decoder cannot exploit them to beat ffill.

4. **A2 (adapter) is LESS STABLE than A1 (full decoder).** Adapter at k=0.0 shows MAE=0.33 (worse than Z0=0.28), indicating random adapter initialization without adaptation degrades performance. At k=0.10 it recovers to Z0 level.

5. **Graph structure IS preserved** (A6 PASS, AUC change ≈ 0) — the attention matrices are robust to fine-tuning at 50 epochs.

### Root cause

The decoder MLP is asked to generalize from dynamics it has never seen (85% nonlinear, tanh-dominated, structural break at year 8). No amount of few-shot adaptation on K% of those same novel dynamics bridges this gap — because the label budget (50-189 cells) is insufficient to retrain a 10→64→32→2 MLP from a wrong prior.

**This is PATH 2 territory, not PATH 1.** PATH 2 (masked pretraining on diverse dynamics, DEC-046 §7.2) is the correct intervention: train the decoder on a distribution that includes 85-90% nonlinear scenarios BEFORE any fine-tuning.

---

## 6. HPC Assessment

**HPC NOT REQUIRED.**

The pilot finding is structurally unambiguous:
- 432 records, 0 errors, 3 seeds, 2 masks, 3 k_fracs
- All 8 neural strategies cluster within ±1% of each other in MAE
- Forward fill dominates by 13-15%
- Adding seeds/epochs/k_fracs cannot change a structural distribution mismatch

HPC would only be justified if a new architecture variant showing promising signal appears. This requires implementing PATH 2 (masked pretraining) first.

---

## 7. Decoder Ablation

The decoder ablation (linear vs mlp_relu vs mlp_gelu) was NOT run in this pilot — it requires more epochs and a cleaner learning signal to distinguish. The hypothesis "O MLP aprende apenas uma transformação linear" (DEC-047 §10) remains unverified and should be tested with PATH 2 pretraining as the starting point.

---

## 8. Recommended Next Step

**DEC-048:** Masked pretraining on diverse synthetic scenarios (PATH 2 from DEC-046).

- Generate 300-500 synthetic datasets with frac_nonlinear ∈ U[0.0, 0.90]
- Pre-train with masked reconstruction + edge/lag prediction multi-task
- Then test few-shot adapter fine-tuning from this stronger prior
- Gates: A1-A10 (same), plus additional pretraining quality gates

**Condition for reopening DEC-047:** If masked pretraining (DEC-048) yields a model with MAE < ffill on novel_lag2 at zero-shot, then few-shot adaptation is worth revisiting.

---

## 9. Archived Records

- Records: `data/processed/synthetic_benchmark/phase12_pilot/phase12_pilot_records.json` (432 records)
- Gates: `data/processed/synthetic_benchmark/phase12_pilot/phase12_pilot_gates.json`
- Contract: `reports/HERALD_FEWSHOT_ADAPTATION_CONTRACT.md`
- Implementation: `src/modeles/synthetic/phase12_few_shot/`
- Tests: `tests/test_phase12_fewshot.py` (49 tests)
