# HERALD — Dual Graph Model Audit

**Date:** 2026-06-11
**Decision:** `DUAL_GRAPH_MODEL_READY`
**Scope:** France NUTS3, 101 regions, 9 A10 sectors, evaluation 2021-2025
**Contract:** `reports/HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md` (FROZEN_V2)
**Files this step:**
- `src/modeles/dual_graph_models.py`
- `tests/test_dual_graph_models.py`
- `src/modeles/run_dual_graph_smoke.py`

**Not authorized in this step:** trainer execution, HPC, SSH, commit, push.

---

## 1. Findings by Severity

| Severity | Finding |
|----------|---------|
| BLOCKER | None. |
| HIGH | None. |
| MEDIUM | Sector-graph sparsity is *soft* (L1 penalty), not a hard top-k. The contract gate (criterion 5: seed Jaccard ≥ 0.50 on top-k relations) requires deriving top-k from the learned weights at evaluation; this is a trainer/evaluation concern, not a model defect. |
| MEDIUM | Recovery and emergence are rare positives. Smoke uses a single seed and 4 training samples, so the reported numbers are liveness signals only — never accuracy/AUCPR results. |
| LOW | The optional temporal sector-graph modulation (`temporal_sector_graph=True`) adds a dense `Linear(H, S·S)`; symmetry and zero-diagonal are enforced post-hoc per step. It stays within budget (≤ 1,764 params) but is heavier; kept off by default. |
| INFO | `struct_mask` is not stored in the tensors (all 909 nodes present every fold). The model derives it from `feature_mask_seq` when not supplied; explicit and derived paths match (test T05). |

No finding blocks promotion to local training.

---

## 2. Mathematical Architecture

### 2.1 State and recurrence

Node states `H_t ∈ ℝ^{B×R×S×H}` evolve through a single shared GRU cell over the
`T=5` causal sequence steps. At step `t`:

```
x_t, valid_t = clean(features_seq[:,t], feature_mask_seq[:,t], struct_mask)
m^terr_t     = TerritoryMessage(H_{t-1}, A^terr_{t,s}, valid_t, adj_mask_{t,s})
m^sect_t     = SectorMessage(H_{t-1}, A^sect_t, valid_t)
g_t          = concat(x_t, embed(s), m^terr_t, m^sect_t)        ∈ ℝ^{·×(NF+E+2H)}
cand_t       = GRUCell(g_t, H_{t-1})
H_t          = where(valid_t, cand_t, H_{t-1})
```

Invalid nodes (no observed feature at step `t`) retain their previous state; no
observed-zero is injected.

### 2.2 Territory message (observed graph)

Per sector `s`, degree-normalised 1-hop aggregation over regions:

```
m^terr_t[r,s] = ( Σ_j A^terr_{t,s}[r,j] · valid_t[j,s] · H_{t-1}[j,s] ) / deg[r]
             ·  adj_mask_{t,s}
deg[r] = Σ_j A^terr_{t,s}[r,j] · valid_t[j,s],   m=0 where deg=0
```

When `adj_mask_{t,s}=0` (graph unavailable) or `deg[r]=0` (isolated), the
message is exactly zero. The self-state path lives in the GRU recurrence, so no
self-edge and no synthetic edge is added.

### 2.3 Sector message (learned graph)

The learned sector adjacency `A^sect ∈ ℝ^{B×S×S}`:

```
A = softplus(W_base)                 # non-negative
A = ½(A + Aᵀ)                        # symmetric
A = A ⊙ (1 − I)                      # zero diagonal
```

`W_base ∈ ℝ^{S×S}` is the only learned graph parameter (static path). With
`temporal_sector_graph=True`, a causal modulation `softplus(W_base + Linear(c_{t-1}))`
replaces the base, where `c_{t-1}` is the masked-mean node state of the previous
step (no target, no test-year information). Message:

```
m^sect_t[r,s] = ( Σ_{s'} A[s,s'] · valid_t[r,s'] · H_{t-1}[r,s'] ) / deg[r,s]
```

The learned graph is exported as `sector_adj_learned (B,T,S,S)` for seed-Jaccard
and visualization audits. It represents predictive association, not input-output
causality. The old observable L1 layer is never loaded.

### 2.4 Heads

Four shared linear heads applied to the dropout-regularised final node state
`Ĥ = dropout(H_T)`:

```
pred_log_growth  = Linear(Ĥ → 1)        regime_logits = Linear(Ĥ → 3)
recovery_logits  = Linear(Ĥ → 1)        emergence_logits = Linear(Ĥ → 1)
```

Pooled embeddings: `territory_embeddings = mean_s H_T` (B,R,H);
`sector_embeddings = mean_r H_T` (B,S,H); both masked by `struct_mask`.

### 2.5 Loss (contract §7)

```
L = Huber(log_growth)
  + 0.20 · weighted_CE(regime)
  + 0.10 · weighted_BCE(recovery)
  + 0.05 · weighted_BCE(emergence)
  + 1e-3 · ‖A^sect‖₁
  + 1e-3 · Σ_t ‖A^sect_t − A^sect_{t-1}‖₁
```

WMAPE is forbidden for log-growth (targets may be zero/negative). Class weights
and positive weights are computed from training labels only. Coefficients are
fixed before any full run.

---

## 3. Parameter Count

Single temporal layer, `gru_in = NF(6) + E(4) + 2H`. All ≤ 10,000 (budget met).

| Config | Params | Breakdown (H=8 static) |
|--------|-------:|------------------------|
| H=4, static | 435 | — |
| H=4, temporal | 840 | — |
| **H=8, static** | **1,035** | sector_base 81 + sector_embed 36 + GRU 864 + heads 54 |
| H=8, temporal | 1,764 | static 1,035 + Linear(8, 81) = 729 |

Exact H=8 static breakdown (measured): `sector_base 9×9 = 81`;
`sector_embed 9×4 = 36`; GRU input `= NF(6)+E(4)+2H(16) = 26`, GRU
`weight_ih 24×26=624 + weight_hh 24×8=192 + biases 48 = 864`; four heads
`= 8+1 + 24+3 + 8+1 + 8+1 = 54`. Total `81+36+864+54 = 1,035`. All configs are
within the 10,000 budget and verified by test T02.

No parameter has a dimension equal to `R=101` (test T10): the model is shared
across territories.

---

## 4. Mask Behaviour

| Mask | Role | Verified |
|------|------|----------|
| `feature_mask_seq (B,T,R,S,F)` | Per-feature observation. Unobserved values zero-filled, never counted as observed. Node invalid at step `t` if no feature present → GRU keeps prior state. | T04, T05, T08 |
| `struct_mask (B,R,S)` | Structural node presence. Derived from `feature_mask_seq.any(1).any(-1)` if not supplied; explicit == derived for FR. | T05 |
| `territory_adj_mask (B,T,S)` | Graph availability per (step, sector). Zero → territory message disabled, temporal self-state path active. All-zero mask reproduces the no-graph variant bit-for-bit. | T06 |
| `target_mask (B,R,S)` | Evaluation cells. Losses ignore masked cells and `-1` labels. | T14 |

Observational masking of neighbours is enforced inside both message functions:
invalid source nodes are removed before degree normalisation (T05b).

---

## 5. Test Results

`tests/test_dual_graph_models.py`: **33 passed** (mlearning env, torch 2.x).

| Test | Coverage |
|------|----------|
| T01 output shapes | all 8 outputs at H=4 and H=8 |
| T02 parameter budget | ≤ 10,000 at H∈{4,8} × temporal∈{F,T}; H=16 rejected |
| T03 seed determinism | identical outputs for fixed seed (eval) |
| T04 no NaN/Inf | all 4 graph variants + fully-missing node |
| T05 masks | struct derived==explicit; invalid neighbours dropped |
| T06 no-graph fallback | masked territory == disabled territory |
| T07 real adjacency changes output | real vs zero adjacency differ |
| T08 sector graph gradient | `sector_base.grad` finite, nonzero |
| T09 sector adjacency structure | zero diagonal, symmetric, ≥0 (static + temporal) |
| T10 no per-territory parameter | no param dim == R; region-permutation equivariance |
| T11 no target in forward | `forward` signature has no target argument |
| T12 backward all four losses | each head backprops finite gradients |
| T13 batch B>1 | B∈{1,2,4}; sample independence |
| T14 loss helpers | mask/ignore-(-1) honoured; Huber value; inverse-freq weights |

Related suites re-run together: `test_dual_graph_targets.py`,
`test_dual_graph_tensors.py`, `test_graph_temporal_a1.py` →
**139 passed, 2 skipped**.

Cross-fold NaN/Inf + structural audit (all 5 folds fr_2021…fr_2025): outputs
finite; `sector_adj_learned` symmetric, zero-diagonal, non-negative on every
fold. `git diff --check`: clean. `py_compile`: pass.

---

## 6. Smoke Result

`python -m src.modeles.run_dual_graph_smoke` — fold FR/2021, seed 42, 20 epochs.

```
leakage check: max source year 2020 < eval_year 2021  OK
samples: 5 (train 4, eval 1)
features (5,5,101,9,6), territory_adj (5,5,9,101,101)

variant           params    eval_total    growth_mae
no_graph            1035       0.60362       0.14496
territory_only      1035       0.61244       0.13833
sector_only         1035       0.60473       0.14683
dual_graph          1035       0.61260       0.13662

SMOKE PASS — liveness only, no scientific claim.
```

All four controls: finite losses, finite gradients, complete and finite
outputs, identical capacity (1,035 params), no leakage. **These numbers are not
results** — four training samples and one seed cannot support any comparison
between controls. The smoke only proves the pipeline runs end-to-end.

**Reproduction (2026-06-11):** the smoke was re-run twice and produced
bit-identical figures both times (deterministic, seed 42). A targeted runtime
audit on the real folds independently confirmed: no leakage (max source year
2020 < 2021); learned sector graph symmetric, zero-diagonal, non-negative with
finite nonzero `sector_base` gradients; four controls at identical 1,035 params;
`compute_class_weights` ignores `-1` labels and is fed the training slice only;
recovery and emergence heads emit continuous scores scorable by AUCPR
(untrained model sits at prevalence, as expected: recovery prevalence 0.0955,
emergence 0.1672). No model defect was found; no code change was required.

---

## 7. Limitations

- The smoke trains on 4 historical samples for 20 epochs with one seed; it is a
  liveness test, not evidence. No control ranking may be inferred from it.
- Sparsity is a soft L1 penalty. The contract's seed-Jaccard gate (criterion 5)
  requires a top-k extraction step defined at evaluation, not in the model.
- Recovery and emergence are rare; per the contract they must be scored with
  AUCPR / precision@k against prevalence, never bare accuracy.
- Five outer years are a small effective temporal sample; regions and seeds are
  not independent replicates (contract §10).
- The territory graph is consumed as provided in the tensors; this audit does
  not re-validate its causal construction (covered by `DUAL_GRAPH_TENSORS_READY`).

---

## 8. Decision

`DUAL_GRAPH_MODEL_READY`

The frugal dual-graph model satisfies every implementation gate required before
local training:

- parameter budget (≤ 10,000) at H=4 and H=8, with and without temporal modulation;
- all input/output shapes match the contract interface;
- per-seed determinism, no NaN/Inf, correct mask behaviour;
- no-graph fallback reproduces the no-graph control exactly;
- real adjacency changes the output; learned sector graph receives gradient;
- learned sector adjacency is symmetric, zero-diagonal and non-negative;
- no per-territory parameter; no target access in forward;
- all four task losses backpropagate finite gradients;
- one-fold, one-seed smoke completes without leakage.

---

## 9. Exact Next Step

Implement `src/modeles/train_dual_graph_experiment.py` (and its tests) per
contract §8–§10:

1. rolling-origin trainer over folds 2021–2025 with inner time-based validation;
2. the eleven controls of contract §8, each at five seeds (42–46);
3. metric computation: log-growth MAE / median AE / Spearman / sign accuracy;
   regime macro-F1 and balanced accuracy; recovery and emergence AUCPR and
   precision@k against prevalence; learned-graph seed Jaccard on top-k;
4. apply the fail-closed gate of contract §9 and emit
   `DUAL_GRAPH_S1_PASS` or `DUAL_GRAPH_S1_FAIL` into
   `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md`.

Trainer execution and HPC submission remain blocked until the trainer and its
unit tests pass locally. No commit or push is authorized until requested.
