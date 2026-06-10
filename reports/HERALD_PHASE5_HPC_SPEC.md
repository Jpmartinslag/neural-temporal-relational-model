# HERALD Phase 5 — HPC Battery Specification

**Status:** SMOKE TESTED v2 — HPC_BLOCKED (smoke gate not cleared, see §11)
**Drafted:** 2026-06-10  **Smoke test v2:** 2026-06-10 (3 seeds, linear + neural)
**Gate:** requires corrected L2 artifacts, a local smoke test and supervisor
confirmation of deadline before submission.

**Smoke result v2 (NL, eval_years=[2021,2022,2023], seeds=[42,43,44], mean):**

| Hypothesis | Mean WMAPE | Std | Alpha ratio | Type |
|---|---|---|---|---|
| H0 (persistence) | 6.96% | 2.47% | — | baseline |
| H0b (Ridge AR) | **3.41%** | 0.94% | — | baseline |
| H1-linear (Ridge, no graph) | 5.52% | 1.45% | 3.72% | linear |
| H2-linear (Ridge, L2 graph) | 5.56% | 1.51% | 3.56% | linear |
| PC-temporal-linear | 5.52% | 1.54% | 3.57% | control |
| PC-territory-linear | 5.49% | 1.57% | 3.54% | control |
| H1-neural (MLP, no graph) | 5.80% | 0.62% | 7.08% | neural |
| H2-neural (MLP, L2 graph) | 8.79% | 3.16% | 7.98% | neural |
| PC-temporal-neural | 9.81% | 4.85% | 5.50% | control |
| PC-territory-neural | 9.33% | 2.47% | 8.11% | control |

**Neural gate:** H2-neural shows graph specificity (diff vs H1-neural = 3.0% ✓) and
beats PC-temporal-neural (+1.02% ✓). Fails: PC-territory gain only +0.53% ✗;
regression vs H0b: H2=8.79% >> H0b*1.1=3.75% ✗.

**Naming note:** H1/H2-linear are Ridge regressors on 1D pooled graph features (NOT neural).
H1/H2-neural are sklearn MLPRegressor(hidden=(16,8)) on 9D per-sector features + 2 AR lags.
The term "neural" refers to the MLP, not a GNN or STGNN.

Leakage: OK all years/seeds. No NaN/Inf.

**HPC_BLOCKED.** MLP corrector regresses vs H0b (overfitting on small rolling-origin
windows, ~360 valid samples per eval year). Blocker: reduce capacity or increase
regularisation before resubmit.

---

## 1. Scientific Question

Does adding a validated observable economic graph (L2 co-growth, and L3 where
available) to a strong causal temporal baseline improve out-of-sample
territorial forecasting beyond what a structure-preserving null graph
achieves?

FR, NL and PT do not share the same target concept. Results are primary per
country and must not be pooled as evidence of European generalization.

**Permitted conclusion:** "Graph H2/H3/H4 beats permuted-graph control."
**Prohibited conclusion:** "The graph encodes economic causality" or "recommendation is valid."

---

## 2. Forecast Architecture

```
y_hat(t, r) = y_hat_baseline(t, r) + alpha * residual_neural(t, r, G)
```

Where:
- `y_hat_baseline`: persistence and a country-specific causal Ridge/AR baseline
- Phase 4N found persistence, not Ridge, to be the best balanced LOCO baseline
  on the distinct PT/IT/AT harmonized panel. It is supporting evidence, not a
  direct reproduction of the present FR/NL/PT experiment.
- `alpha ∈ [0, 1]`: scalar shrinkage weight; `alpha=0` collapses to H0
- `residual_neural`: low-capacity residual corrector conditioned on graph G
- `G`: fixed or learned sparse graph. L2 is a separate territory graph for
  each sector, not one pooled territory graph.

**Key constraints:**
- `alpha` learned jointly but regularized to reach zero if graph adds no signal
- No information from year `t` or future; all graph edges use data from ≤ t-1
- Graph edges are fixed at validation time for H2/H3/H4; only H5 allows learned edges
- Residual corrector: max 2 graph-convolution layers, ≤ 32 hidden units, dropout ≥ 0.3

---

## 3. Hypotheses

| ID | Description | Graph source | Notes |
|---|---|---|---|
| H0 | Persistence (`target[t-1]`) | — | Mandatory strongest simple baseline |
| H0b | Country-specific Ridge/AR | — | Causal trainable baseline; targets remain separate |
| H1 | Ridge + residual neural, no graph | Identity or no-edge | Same sector encoder and pooling as H2, but no message passing |
| H2 | Ridge + residual with L2 fixed | Sector-specific L2 co-growth (validated) | Primary graph hypothesis; pool sector embeddings only after message passing |
| H3 | Ridge + residual with L3 fixed | L3 territory-structure | FR/NL only; L3 is not validated for PT |
| H4 | Ridge + residual with L2+L3 combined | L2 + L3 | FR/NL only |
| H5 | Ridge + learned sparse graph + residual | Learned (GLASSO / soft-thresholded) | Only if H2/H4 pass gate |
| PC-temporal | H2 with temporally permuted graph | Permuted L2 | Primary null control |
| PC-territory | H2 with territory-permuted graph | Permuted L2 | Secondary null control |

**Promotion rule:** H2/H3/H4 accepted only if WMAPE improvement ≥ 1% vs both
H0 and H0b, no tail-risk violation, and empirical graph-control p ≤ 0.05
(against PC-temporal and PC-territory).

H5 launched **only if H2 or H4 passes** the gate above. Do not pre-launch H5.

---

## 4. Data

- **Countries:** FR (280 ZE2020), NL (40 COROP), PT (25 NUTS3)
- **Targets:** country-specific administrative outcomes documented in the
  target-equivalence audit. They are not interchangeable.
- **Training window:** rolling-origin (no fixed test split); evaluation years per country:
  - FR: candidate graph/target intersection 2017–2025
  - NL: candidate graph/target intersection 2012–2025
  - PT: candidate graph/target intersection 2013–2024 (8 sectors)
- **No cross-country pooling of raw counts**
- **Graph edges:** pre-built from L2 builder with `available_for_forecast_year = t`
  (window ≤ t-1); no re-estimation inside the evaluation loop

---

## 5. Metrics

Primary: **WMAPE** (weighted mean absolute percentage error) per country per year.

```
WMAPE(t) = sum_r |y_hat(t,r) - y(t,r)| / sum_r |y(t,r)|
```

Reported:
- Mean WMAPE per country (FR, NL, PT)
- **Worst-country WMAPE** as a robustness summary, not a pooled target metric
- **Tail risk:** 90th-percentile WMAPE across territory-years
- Year-over-year WMAPE stability (no year ≥ 10 % worse than H0)
- Multiple seeds (≥ 5); report mean ± std

Prohibited:
- Claiming improvement based on cross-country mean that masks per-country regression
- Reporting only best-seed result

---

## 6. Leakage and Causality Checklist

Before each experiment run:

- [ ] All graph edges for eval_year `t` use only `observation_year ≤ t-1`
- [ ] AR features for year `t` use only lags from `t-1, t-2, …`
- [ ] No sector-growth or target value from year `t` enters the input
- [ ] Graph learned on H5: re-estimated at each rolling-origin step using only past data
- [ ] `alpha` and neural weights NOT re-estimated using the evaluation-year target

---

## 7. Null Control Protocol

For each evaluation year `t` and model H2/H3/H4:

1. **Temporal permutation:** shuffle observation-year order within territory-sector
   before computing L2 edges (199 permutations, seed cascade from 42)
2. **Territory permutation:** permute territory labels within year-sector
3. **Empirical p-value:** `(1 + count(null_WMAPE ≤ obs_WMAPE)) / (1 + N)`
   (lower WMAPE = better, so null "beats" observed when null_WMAPE ≤ obs_WMAPE)
4. Report median null WMAPE, 95th-percentile null, and empirical p

Promotion requires p ≤ 0.05 on both permutation types for each claimed
country. Replication in at least two countries is required, but raw target
errors are never pooled.

---

## 8. Residual Neural Architecture

```
For each sector s:
    h[r,s,t] = GraphConv_L2_s(x[r,s,t], G_L2[s,t])

territory_state[r,t] = masked_pool_s(h[r,s,t])
delta[r,t] = Linear(territory_state[r,t])
output[r,t] = alpha * delta[r,t]
```

For H1, `GraphConv_L2_s` is replaced by the same-capacity node MLP. For H3,
the pooled territory state is propagated through the L3 territory graph. H4
combines the H2 sector-specific branch and the H3 territory branch by
concatenation followed by one linear head. PT pooling uses its eight supported
sectors; missing or structurally unsupported sectors are masked, never zeroed.

- No attention weights called "explanations"
- No recurrent state across rolling-origin steps (each step is independent)
- Weight initialization: He uniform (fixed seed per experiment)
- Maximum two graph-convolution layers total per branch, hidden width <= 32

---

## 9. Smoke Test (local, before HPC submission)

Run on a single country (NL, 40 regions), 3 eval years, 1 seed:

```bash
python3 hpc/phase5/smoke_phase5_h2.py \
    --country NL \
    --eval-years 2021 2022 2023 \
    --seed 42
```

Expected runtime: < 5 minutes.
Checks: leakage audit passes, WMAPE computed, no NaN in output.

---

## 10. HPC Script Structure (design, not yet written)

```
hpc/phase5/
├── configs/
│   ├── phase5_h0.yaml        # H0/H0b: persistence and Ridge
│   ├── phase5_h1.yaml        # H1: Ridge + neural, no graph
│   ├── phase5_h2.yaml        # H2: Ridge + neural + L2
│   ├── phase5_h3.yaml        # H3: Ridge + neural + L3
│   ├── phase5_h4.yaml        # H4: Ridge + neural + L2+L3
│   └── phase5_controls.yaml  # PC-temporal, PC-territory
├── run_phase5_array.sbatch
├── run_phase5_seed.py        # one (country, eval_year, seed, hypothesis) job
├── smoke_phase5.sh
└── audit_phase5_results.py   # post-hoc analysis + gate check
```

Slurm constraints:
- `#SBATCH --constraint="mpi"` (avoid affected nompi nodes)
- `#SBATCH --array=0-N` where N = n_hypotheses × n_seeds - 1
- Estimated wall time: 2 h per job (NL 40 regions × 14 years × 199 permutations)

---

## 11. Authorization Gate

This battery is NOT authorized to run until:

1. COVID-corrected L2 result and its exact checksums are frozen
2. Failed community result is retained as `NOT_SUPPORTED`; community labels
   are not model inputs
3. Sector-specific L2-to-territory pooling implementation passes unit tests
4. Supervisor confirms deadline and HPC allocation
5. Smoke test passes locally on NL

**Do not submit to HPC or freeze the training implementation until this gate is cleared.**

---

## 12. Prohibited Actions at This Stage

- No HPC neural training before Phase 5 is formally opened
- No STGNN, GNN, or attention-based graph neural network
- No dashboard modification
- No claim that graph improves forecast before Phase 5 results exist
- No recommendation engine or policy claim
- No reinterpretation of L2/L3 correlation as economic causality
