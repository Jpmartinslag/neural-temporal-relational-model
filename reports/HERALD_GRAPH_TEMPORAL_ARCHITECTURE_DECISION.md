# HERALD — Graph-Temporal Architecture Decision

**Date:** 2026-06-11
**Status:** METHODOLOGICAL PREFLIGHT COMPLETE — IMPLEMENTATION NOT YET AUTHORIZED
**Decision:** local two-stage prototype only; no HPC submission

## 1. Scientific Objective

The current forecasting result is a strong causal AR/Ridge baseline. The
graph-temporal branch must answer a narrower question:

> Does a low-capacity model using the observed dynamic L2 graph predict a
> bounded residual correction that improves the same territorial target over
> AR/Ridge, beyond an equal-capacity no-graph model and graph null controls?

The graph branch is not asked to replace Ridge, infer structural causality or
produce recommendations.

## 2. Data Contract

### Forecast target

All models must predict the **same country-specific territorial total** used by
the canonical AR/Ridge baseline.

Sector births are graph-node attributes and covariates. They are not a
different forecast target in this experiment. A future sector-level forecasting
task requires its own baseline, metric and gate.

This corrects the prior draft, which compared total-territory A0 forecasts with
sector-level A1 forecasts.

### Nodes and edges

- node state: `(country, territory, sector_A10, observation_year)`;
- graph: one same-sector cross-territory L2 adjacency per observation window;
- PT KZ remains structurally unsupported and masked;
- no cross-country edges;
- no country pooling of raw targets or WMAPE.

### Temporal availability

For forecast year `t`, every node feature and adjacency must use observations
from years `<= t-1`. Normalization, imputation and graph construction are fit
inside each rolling-origin training fold.

## 3. Candidate Hierarchy

### A0 — Canonical no-graph baseline

`A0 = country-specific AR/Ridge`.

This is the baseline already supported by the repository. Persistence remains
a mandatory secondary baseline.

An optional small GRU without graph may be included only as a neural-capacity
control. It is called `A0-GRU`, not the canonical A0, and must predict the same
territorial target.

### A1a — GConvGRU over observed dynamic L2

- shared graph-recurrent weights across sectors;
- L2 adjacency supplied separately for every sector and time step;
- masked pooling of sector states to one territory state;
- bounded residual output added to the Ridge forecast;
- no freely learned adjacency.

The original GConvGRU literature does not by itself validate changing
topology. A variable adjacency per step is a HERALD adaptation and must be
tested explicitly.

### A1b — EvolveGCN-H over observed dynamic L2

- observed L2 topology varies by time step;
- EvolveGCN evolves GCN parameters through a recurrent mechanism;
- it does **not** evolve the adjacency matrix through a GRU;
- shared weights and the same output head as A1a.

EvolveGCN is methodologically aligned with dynamic observed graphs, but its
published tasks differ from HERALD. It is a candidate, not a preferred model.

### A2 — Prior-constrained learned edge gates

Deferred. A2 may only reweight edges already present in the causal L2 support.
No dense `N x N` learned graph, Gumbel-Softmax graph or new-edge discovery is
authorized with `T≈10–15`.

A2 is opened only if an A1 variant passes the predictive promotion gate in at
least two countries.

## 4. Common Output Architecture

For A1a and A1b:

```text
sector_state[r,s,t] = GraphTemporal(x[r,s,<=t-1], W_L2[s,<=t-1])
territory_state[r,t] = MaskedPool_s(sector_state[r,s,t])
delta[r,t] = BoundedHead(territory_state[r,t])
y_hat[r,t] = y_hat_ridge[r,t] + delta[r,t]
```

Constraints:

- one graph-temporal layer;
- hidden width in `{4, 8}`;
- one shared model across sectors, with sector identity encoded explicitly;
- residual clamp in `{10%, 15%}` of the positive Ridge forecast;
- dropout at least `0.3`;
- parameter count measured from the implemented model, not estimated in prose;
- maximum trainable parameters: `5,000`;
- masks propagated through message passing, pooling and loss.

The embedding is a secondary descriptive artefact. Edge weights, gates and
attention values are not explanations without a separate null-model audit.

## 5. Controls

Every A1 run requires:

1. persistence;
2. canonical AR/Ridge;
3. equal-capacity no-graph control;
4. zero-adjacency control;
5. temporal-series permutation followed by full L2 reconstruction;
6. row-wise territory permutation followed by full L2 reconstruction;
7. COVID sensitivity with the same definition used in DEC-024d.

Permuting already-computed edge weights is prohibited because that control was
invalidated in DEC-024b.

## 6. Execution Order

### Stage E0 — Engineering smoke

Country: NL, because the panel is small and sector coverage is complete.

Purpose: tensor alignment, masks, determinism, runtime and leakage only. An NL
smoke does not provide scientific authorization because NL's G2 result is
COVID-sensitive.

Required:

- one seed;
- three evaluation years;
- no NaN or Inf;
- exact repeated-seed determinism;
- all fold maxima satisfy `train_year < eval_year`;
- runtime below 10 minutes on CPU;
- measured memory below 4 GB.

### Stage S1 — Scientific local test

Country: FR, because FR is the only country with G2 aggregate temporal signal
robust in both COVID scenarios.

Compare A1a, A1b and the equal-capacity no-graph control using the same target,
folds, seeds and residual clamp.

Required before any HPC request:

- five seeds;
- at least five evaluation years;
- A1 improves mean WMAPE by at least 1% relative to both Ridge and the
  equal-capacity no-graph control;
- A1 wins at least half of the evaluation years against Ridge;
- no evaluation year is more than 10% worse than Ridge;
- A1 beats both reconstructed graph nulls with empirical `p <= 0.05`;
- WMAPE standard deviation across seeds `<= 0.005`;
- all leakage and mask checks pass.

Failure closes the tested architecture. It does not invalidate L2 as an
analytical graph.

### Stage S2 — Replication

Only after S1 passes:

- repeat on NL as a COVID-sensitive replication;
- repeat on PT as sensitivity with eight sectors;
- report each country independently.

Predictive promotion requires two countries to pass the full gate. A pooled
cross-country mean cannot satisfy the gate.

## 7. HPC Gate

HPC is `BLOCKED`.

Submission becomes eligible only after:

1. E0 passes;
2. S1 passes locally;
3. code tests, artifact checksums and exact configuration are frozen;
4. estimated per-job wall time and memory are measured;
5. supervisor deadline and explicit authorization are recorded;
6. the Slurm script retains `#SBATCH --constraint="mpi"`.

HPC is for confirmatory seeds/countries, not for discovering an architecture or
searching a large hyperparameter grid.

## 8. Decision

- EconoGNN: `REFERENCE_ONLY`.
- A0: existing AR/Ridge.
- A1 candidates: low-capacity GConvGRU and EvolveGCN-H, compared impartially.
- A2: blocked until A1 is supported.
- heterogeneous territory-sector graph: deferred; current evidence does not
  justify extra edge types.
- dashboard: unchanged.
- recommendation: unchanged and not implemented.

## 9. Next Exact Task

Implement only the **data/tensor preflight and E0 smoke harness**:

1. export causal per-fold L2 adjacency sequences;
2. align them with sector-node features and total territorial targets;
3. implement leakage and mask assertions;
4. implement parameter counting and runtime/memory measurement;
5. add unit tests;
6. stop for audit before training S1.

No HPC submission, dashboard modification or recommendation work is authorized
by this decision.
