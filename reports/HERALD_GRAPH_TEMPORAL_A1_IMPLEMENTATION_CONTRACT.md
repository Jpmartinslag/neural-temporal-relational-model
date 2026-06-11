# HERALD — Graph-Temporal A1 Implementation Contract

**Date:** 2026-06-11
**Status:** AUTHORIZED (DEC-028)
**Prerequisite:** `E0_V2_PASS`, `FR_ADJACENCY_READY`

This document is the implementation brief for GConvGRU (A1a), EvolveGCN-H (A1b),
and A0-neural. Read it before writing any model code. Everything in this contract
is pre-specified; do not change it during implementation.

---

## 1. Input Interface (common to A0-neural, A1a, A1b)

All models receive the same batch of schema 2.0 tensors:

```
features_seq      (B, T, R, S, F)  float32   # node features per time step
feature_mask_seq  (B, T, R, S, F)  int8/bool # per-feature validity mask
struct_mask       (B, R, S)        int8/bool # structural mask (PT-KZ = 0)
adjacency_seq     (B, T, S, R, R)  float32   # positive_topk per step and sector
y_ridge_canonical (B, R)           float32   # canonical H0b Ridge prediction
target_mask       (B, R)           int8/bool # 1 where y_true is observed
```

Where:
- B = batch size (number of folds in a mini-batch; often 1 in rolling-origin)
- T = 5 (T_SEQ, fixed)
- R = number of regions (NL: 40, FR: 280)
- S = number of sectors (9)
- F = 3 (growth, share, births_norm)

Optional:
```
time_mask         (B, T)           bool      # 1 where time step is valid
                                              # (all ones for NL/FR; reserved for PT)
```

---

## 2. Output Interface (common to A0-neural, A1a, A1b)

```
delta_raw     (B, R)  float32  # unclamped residual correction
delta_bounded (B, R)  float32  # clamped to ±clamp_frac × max(y_ridge, 0)
y_hat         (B, R)  float32  # y_ridge_canonical + delta_bounded
```

Optional secondary outputs (not part of the predictive gate):
```
territory_embeddings  (B, R, hidden_dim)  float32  # last-step territory state
sector_embeddings     (B, R, S, hidden_dim) float32 # optional per-sector states
```

**The gate is evaluated on `y_hat` only. Embeddings are not evaluated.**

---

## 3. Shared Rules (all models must follow exactly)

### 3.1 Masked pooling

Sector states are pooled to territory states using `struct_mask` and `feature_mask_seq`:

```python
# At each time step t:
# sector_state[b, r, s, :] = GraphTemporal(...)  shape (B, R, S, H)
# Pooling mask = struct_mask & any(feature_mask_seq[t], dim=-1)
# territory_state[b, r, :] = mean(sector_state[b, r, s, :] where mask[b, r, s])
```

Absent sectors (struct_mask=0) must never contribute to the territory state. Do not substitute with zeros — use masked mean.

If all sectors for a region are absent/masked at a time step, the territory state is NaN for that region/step. Propagate NaN and handle in loss masking.

### 3.2 Bounded residual head

```python
clamp_frac = 0.15  # or 0.10 — one value for all models in S1
ridge_ref = torch.clamp(y_ridge_canonical, min=0)
delta_bounded = torch.clamp(delta_raw, -clamp_frac * ridge_ref, clamp_frac * ridge_ref)
y_hat = y_ridge_canonical + delta_bounded
```

The clamp is applied elementwise. Regions where `y_ridge_canonical = 0` get delta=0.

`clamp_frac` is a hyperparameter fixed before S1. Choose one value in `{0.10, 0.15}` and use it for A0-neural, A1a and A1b.

### 3.3 Same target for all architectures

All models predict `y_true = business_sector_total` from the sector panel.
Never use `target_births` from the country panel.
Both `y_true` and `y_ridge_canonical` come from `fold["y_true"]` and `fold["y_ridge_canonical"]` in the schema 2.0 NPZ.

### 3.4 Loss function

```python
loss = masked_wmape(y_hat, y_true, target_mask)
# WMAPE = sum|y_hat - y_true| / sum|y_true| over target_mask == 1
```

Same loss for all architectures in all runs. Do not use MSE, MAE, or per-region normalization as the primary loss.

### 3.5 Same folds, same seeds, same random state

Rolling-origin protocol:
- Load folds from `data/processed/graph_temporal_v2/{country}/{eval_year}/fold_v2.npz`
- Train on all folds with `observation_year < eval_year` (causal)
- Evaluate on `eval_year` fold
- No data from `eval_year` enters training

Seeds: use `[42, 43, 44, 45, 46]` (5 seeds) for S1-FR. Seed controls all `torch.manual_seed`, `numpy.random.seed`, and `random.seed` calls. Set before model initialization.

### 3.6 Parameter count — strictly ≤ 5,000 trainable parameters

Count from implemented model:
```python
n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
assert n_params <= 5000, f"Too many parameters: {n_params}"
```

This check must run in the test suite. Do not estimate in prose.

### 3.7 Shared weights across sectors

The graph-temporal layer uses the same weights for all 9 sectors. Sector identity is encoded explicitly as a learnable embedding:

```python
sector_embed = nn.Embedding(n_sectors, sector_embed_dim)  # sector_embed_dim ∈ {4, 8}
```

The embedding is concatenated with the sector node features before the graph-temporal layer.

### 3.8 No cross-country edges, no country pooling

Adjacency is country-specific. Never mix regions from different countries. Country-level WMAPE is the primary metric; pooled WMAPE is not admissible.

### 3.9 No future information

No data with `observation_year >= eval_year` may enter any computation. This is enforced by the tensor builder (LeakageError). The model must not introduce new leakage paths (e.g., future batch normalization statistics).

### 3.10 Dropout ≥ 0.3

Apply dropout to the hidden state after the graph-temporal layer, before the residual head. Rate ≥ 0.3 for all architectures.

---

## 4. A0-neural — No-Graph Temporal Control

### Purpose

Equal-capacity neural baseline **without message passing**. Tests whether temporal memory alone (without graph topology) accounts for any improvement over Ridge.

If A1a and A1b improve over Ridge but A0-neural also improves, the graph is not the cause. If A1 improves and A0-neural does not, the graph is responsible.

### Architecture

```
sector_state[b, r, s, t] = GRU(features_seq[b, t, r, s, :] + sector_embed[s])
                             # no message passing; GRU applied per (r, s)
territory_state[b, r] = MaskedPool_s(sector_state[b, r, s, T-1])
delta_raw[b, r] = Linear(territory_state[b, r])
delta_bounded[b, r] = clamp(delta_raw[b, r], ...)
```

- One GRU layer, hidden size H ∈ {4, 8}
- Shared weights across all (r, s) pairs
- No adjacency input (A0-neural does not receive `adjacency_seq`)
- Same pooling, same head, same clamp as A1a and A1b

### Parameter budget estimate (H=8, F=3, sector_embed_dim=4)

GRU input_size = F + sector_embed_dim = 7; hidden_size = 8.
GRU parameters ≈ 3 × (7+8) × 8 + 3 × 8 = 384.
Sector embedding = 9 × 4 = 36.
Territory head = 8 × 1 + 1 = 9.
Total ≈ 429. Well within 5,000.

---

## 5. A1a — GConvGRU

### Architecture

```
# At each time step t:
# 1. Graph convolution (per sector s):
agg_state[r] = sum_j( adjacency_seq[b, t, s, r, j] * h_prev[j] ) / (deg[r] + 1)
# 2. GRU update:
h_t[r, s] = GRU_cell(features_seq[b, t, r, s, :] || sector_embed[s], agg_state[r] || h_prev[r])

# After last time step:
territory_state[b, r] = MaskedPool_s(h_T[r, s])
delta_raw[b, r] = Linear(territory_state[b, r])
```

- One layer. Hidden size H ∈ {4, 8}.
- Graph convolution is a 1-hop neighbour aggregation (degree-normalized mean), applied before the GRU gating.
- Adjacency varies by sector and time step: `adjacency_seq[b, t, s, :, :]`
- Zero-adjacency control: replace `adjacency_seq` with zeros — the model must still run (only self-message).
- Shared weights across sectors; sector identity via `sector_embed`.
- Dropout ≥ 0.3 on hidden state before head.

### Variable-topology contract

The adjacency matrix changes at every time step. Message passing at step t uses only `adjacency_seq[b, t, s]`. Do not cache or average adjacencies across steps.

### Isolated-node handling

If `adjacency_seq[b, t, s, r, :].sum() == 0`, the aggregated state is the node's own previous hidden state (not NaN, not zero from the GRU). This matches the Phase 5 self-value fallback (DEC-023).

---

## 6. A1b — EvolveGCN-H

### Architecture

EvolveGCN evolves the GCN weight matrix through a GRU mechanism, not the adjacency matrix.

```
# At each time step t:
# 1. Evolve GCN weight W via GRU:
W_t = GRU_cell(W_{t-1}, context_t)   # W is the GCN weight matrix, treated as hidden state
# 2. GCN with evolved weights:
h_t[r, s] = activation(W_t × (features_seq[b, t, r, s, :] || agg_neighbours[r, s]))

# After last time step:
territory_state[b, r] = MaskedPool_s(h_T[r, s])
delta_raw[b, r] = Linear(territory_state[b, r])
```

- One layer. Hidden size H ∈ {4, 8}.
- The GRU evolves the GCN weight matrix W, not the node states.
- Adjacency `adjacency_seq[b, t, s]` provides the neighbour structure for GCN at each step.
- Same output head, pooling, and clamp as A1a.
- Shared weights across sectors; sector identity via `sector_embed`.

### Implementation note

EvolveGCN-H uses the GCN weight matrix as the GRU hidden state. The GRU input at each step can be a summary of node features (e.g., mean of `features_seq[b, t, :, s, :]`). See the original EvolveGCN paper (Pareja et al., 2020) for the H variant formulation.

---

## 7. Controls (mandatory for S1-FR)

All controls use the same folds, seeds, loss, and evaluation protocol.

| Control | Description | Implementation |
|---------|-------------|----------------|
| Persistence | `y_hat[r] = business_sector_total[r, eval_year-1]` | Read from sector panel |
| Ridge H0b | `y_hat = y_ridge_canonical` from fold NPZ | No training |
| A0-neural | GRU without message passing (§4) | Trainable |
| Zero-adjacency | A1a/A1b with `adjacency_seq = 0` everywhere | Replace at eval time |
| Temporal permutation | Rebuild L2 from permuted time series (not permuted weights) | Rebuild `adjacency_seq` from shuffled `sector_growth_1y` time axis |
| Territory permutation | Rebuild L2 from row-permuted regions (not permuted weights) | Rebuild `adjacency_seq` from shuffled region axis |

**Permutation controls must rebuild the adjacency from the source series**, not permute already-computed edge weights. Permuting weights was invalidated in DEC-024b.

---

## 8. Mandatory Tests (before S1-FR)

For each model (A0-neural, A1a, A1b):

| Test | Description |
|------|-------------|
| T-shape | Input/output shapes match interface specification |
| T-mask | Masked positions produce no gradient through the loss |
| T-bounded | `|delta_bounded| <= clamp_frac * max(y_ridge, 0)` everywhere |
| T-zero-alpha | With `clamp_frac=0`, `y_hat = y_ridge_canonical` exactly |
| T-params | `n_trainable_params <= 5000` |
| T-determinism | Same seed → identical outputs and loss |
| T-zero-adj | Zero-adjacency run produces same `y_hat` as persistence (for H=0 initial state) |
| T-real-adj | Real adjacency changes `y_hat` relative to zero-adjacency |
| T-no-leakage | Future fold data does not alter past-fold predictions |
| T-no-nan | No NaN or Inf in `y_hat`, `delta_bounded`, or loss where target_mask=1 |
| T-shared-loss | A0, A1a, A1b use identical `masked_wmape` loss and identical fold loading |

All tests must be in `tests/test_graph_temporal_a1.py`.

---

## 9. S1-FR Gate (not in this task — for reference)

S1-FR is authorized only after all tests pass and after `git diff --check` is clean.

**S1-FR pass criteria (pre-registered, from DEC-027/HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md §6):**

1. ≥1% relative WMAPE improvement over both Ridge H0b and A0-neural
2. Model wins ≥ half of the evaluation years vs Ridge
3. No evaluation year > 10% worse than Ridge
4. Beats both reconstructed graph null controls with empirical p ≤ 0.05
5. WMAPE std across 5 seeds ≤ 0.005
6. All leakage and mask checks pass

Failure at S1-FR closes the tested architecture. It does not invalidate L2 as an analytical graph.

---

## 10. HPC Gate (not yet)

HPC submission requires:
1. S1-FR passes locally (§9)
2. Code, artifact checksums and config frozen
3. Per-job wall time and memory measured locally
4. Supervisor deadline and authorization recorded

---

## 11. What Is NOT Authorized

- Modifying the adjacency representation during training (learned edges, attention on edges, Gumbel-Softmax)
- A2 learned edge gates (blocked until at least one A1 passes S1-FR in ≥2 countries)
- S2 replication on NL or PT (blocked until S1-FR passes)
- Any dashboard modification
- Any recommendation claim
- Pooled cross-country WMAPE as primary metric
- HPC submission

---

## 12. File Checklist

Implement and test in this order:

1. `src/modeles/graph_temporal_models.py` — A0-neural, A1a (GConvGRU), A1b (EvolveGCN-H)
2. `src/modeles/graph_temporal_train.py` — rolling-origin training loop, WMAPE loss, seed control
3. `src/modeles/run_s0_fr_smoke.py` — 1-seed, 1-eval-year FR technical smoke (not S1)
4. `tests/test_graph_temporal_a1.py` — all 11 mandatory tests

After all tests pass and `git diff --check` is clean, S1-FR becomes authorized:

5. `src/modeles/run_s1_fr_local.py` — 5 seeds, 5 eval years, all controls, COVID sensitivity
