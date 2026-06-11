# HERALD — EconoGNN Transferability Audit

**Date:** 2026-06-11
**Status:** COMPLETE
**Decision:** `REFERENCE_ONLY`

## 1. Verified Source

Primary source:

- Marcus Araujo, Francisco Rodrigues, Elaine Sousa.
  "EconoGNN: A graph neural network framework for temporal economic
  resilience insights." *PLOS ONE* 21(4), e0343683, 2026.
  DOI: `10.1371/journal.pone.0343683`.
- Published: 2026-04-22.
- GitHub: `https://github.com/AraujoMarcus/ECONO_GNN`.
- Archive cited by the article: `https://doi.org/10.5281/zenodo.18751102`.

Corrections to the abandoned draft:

- The third author is **Elaine Sousa**, not "Parros" and not uncertain.
- The graph is a discrete-time dynamic trade graph. Its topology and node
  labels may change with time; it is not a fixed trade graph.
- The PLOS article is available and was used as the primary source.
- The public GitHub repository is incomplete and cannot be treated as a
  drop-in implementation.

## 2. What EconoGNN Actually Does

EconoGNN predicts a binary economic-resilience state for country-year nodes.
It uses:

- 183 countries as nodes;
- international trade relations as observed edges;
- macroeconomic node features;
- temporal graph neural networks, including GConvGRU;
- GNNExplainer for descriptive model interpretation.

The article reports GConvGRU as its best tested model, with F1 = 0.750,
AUC-ROC = 0.792 and PR-AUC = 0.757. The reported winning configuration uses
five temporal windows, 64 hidden channels, two layers, Adam, learning rate
`1e-3` and dropout `0.2`.

The article describes the study in two different ways: the abstract says
"25 years", while the body discusses a longer historical trade panel. HERALD
must not silently resolve this inconsistency or cite an exact snapshot count
without reproducing the released archive.

The paper states that moving to rolling-origin evaluation would strengthen
temporal validity. Therefore, its evaluation protocol is not sufficient to
validate HERALD's strict forecasting protocol.

## 3. What Transfers to HERALD

Transferable as methodological ideas:

- representing an economy as a discrete-time dynamic graph;
- combining graph propagation and temporal memory;
- comparing temporal GNNs with static and non-graph baselines;
- validating model explanations separately from predictive performance;
- treating interpretation as descriptive, not causal.

Not directly transferable:

- binary resilience classification instead of count forecasting;
- country nodes instead of territory-sector states;
- trade-flow edges instead of L2 co-growth associations;
- a much richer temporal panel than HERALD's short annual panels;
- the reported 64-channel, two-layer configuration;
- the published evaluation protocol;
- the incomplete GitHub code as a reusable implementation.

## 4. Implication for Architecture Selection

EconoGNN supports **considering** GConvGRU. It does not select GConvGRU for
HERALD and does not validate HERALD's architecture.

The correct use is:

1. cite EconoGNN as recent economic-domain evidence that temporal graph models
   can be useful when the graph and temporal sample are sufficiently rich;
2. keep GConvGRU as one candidate;
3. compare it against EvolveGCN and the existing Ridge baseline under the same
   target and rolling-origin protocol;
4. use far smaller capacity and fail-closed gates;
5. prohibit HPC submission until a local smoke test improves on the no-graph
   control.

## 5. Permitted and Prohibited Claims

Permitted:

> EconoGNN provides peer-reviewed evidence for temporal graph learning on an
> observed dynamic economic network, but its task, scale and validation
> protocol differ materially from HERALD.

Prohibited:

- "HERALD reproduces EconoGNN."
- "EconoGNN proves GConvGRU is the correct HERALD architecture."
- "The EconoGNN code can be reused directly."
- "Its explanation scores validate HERALD explanations."
- "Its reported performance transfers to short NUTS3/COROP/ZE panels."

## 6. Final Verdict

`REFERENCE_ONLY`.

EconoGNN is scientifically relevant but not a base implementation. HERALD must
retain its own causal rolling-origin protocol, low-capacity design, explicit
null graph controls and country-specific reporting.
