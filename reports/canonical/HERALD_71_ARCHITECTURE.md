# HERALD 71 -- The architecture: a graph that is built, used, and mutated

**Date:** 2026-08-11
**Status:** `PRE_REGISTERED_ARCHITECTURE` (DEC-116). Written before the code existed.

## 1. What the model must do

One model, one pass, six stages:

1. ingest the observed data;
2. build the relational prior from official sources, without learning it;
3. encode each node's history;
4. **learn which relational patterns are active in each year**;
5. predict;
6. **emit that year's graph**, including which edges entered and which left.

Stage 6 is the point. A model that consumes a fixed graph is a forecaster with side
information. A model that emits a different, defensible graph per year is a relational
instrument, and that is what the project is for.

MTGNN is cited below only where it anchors a parameter. It learns **one** adjacency; the
architecture here learns a **per-year** one, so it is a different object, not an extension.

## 2. Nodes

`ZE2020 x A10`, 2,520, with a **per-year presence mask**: a node is absent in a year when its
sector has no recorded activity in that zone. Presence is observed, never inferred, and the
mask is what lets nodes enter and leave without the count changing.

## 3. The graph

```text
A_t  =  softmax_topk( C_prior  +  U diag(z_t) V^T ,  k )
```

| term | what it is | learned |
|---|---|---|
| `C_prior` | official commuting, release-aware per decision year (DEC-073) | **no** |
| `U`, `V` | persistent relational patterns, `280 x r` each | yes |
| `z_t` | how strongly each pattern is active in year `t`, `r` values | yes |
| `k` | top-k retained per row | fixed, see 5 |

Edges enter and leave because `z_t` moves and the top-k cut then falls elsewhere. **The
mutation is driven by `r` latent regimes, not by 78,120 independent per-year decisions.** That
is the whole reason it can be identified from 14 years.

The graph is **zone x zone**; messages carry the nine sectors as separate channels. This is
deliberately *not* the `C[i,j] x S[s,q]` factorisation that DEC-094 rejected, which forced one
sector-affinity matrix onto every zone and made heterogeneous local relations impossible.

**No temporal smoothness penalty.** DEC-091 established that such a penalty is what froze the
previous graph at r = 0.9994. Its absence here is a design decision, recorded.

## 4. The parameter budget, declared

The learned graph has `2 x 280 x r + 14 x r` parameters against roughly 17,640 node-year
observations in the training folds.

| r | parameters | observations per parameter |
|---|---|---|
| 2 | 1,148 | 15.4 |
| **4** | **2,296** | **7.7** |
| 8 | 4,592 | 3.8 |

**`r = 4` is the pre-registered value**, chosen as the largest rank keeping at least 5
observations per parameter. `r` in {2, 4, 8} is reported as a sensitivity. For contrast, a free
per-year adjacency would be 1.09 M parameters, and MTGNN's own node-embedding form at `d = 40`
would be 22,400 -- both far past what this panel supports, which is why DEC-091 arm D produced
seed disagreement of 0.695.

## 5. Parameters and their sources

| parameter | value | source |
|---|---|---|
| hidden dimension | 64 | EconoGNN best configuration |
| graph layers | 2 | EconoGNN; MTGNN `gcn_depth` |
| learning rate | 1e-3 | EconoGNN; MTGNN |
| dropout | 0.2 | EconoGNN |
| temporal window | 5 | EconoGNN |
| **top-k** | **28** | MTGNN `subgraph_size` 20 of 207 nodes = 9.7%, scaled to 280 |
| state threshold | 10% | Eurostat-OECD, EU Implementing Regulation |
| rank `r` | 4 | section 4, from the observation budget |

Every value above has a citation or a declared arithmetic rule. Anything not in this table is
swept, not chosen. This is the correction demanded by DEC-115.

## 6. Outputs

1. next-year prediction per node, as a distribution over the three states and as a magnitude;
2. `A_t` per year, exported with `zfill(4)` IDs that join to the official commuting file;
3. **edge births and deaths per year**, with the pattern `z_t` responsible for each;
4. aggregation from node to zone to employment basin to France, by summation, so a macro
   change can always be opened into the micro edges that produced it.

## 7. Dynamism must pass its own tests, separately from prediction

A graph that mutates is worthless if the mutation is noise. Six tests, none of which touches
forecast error:

| test | requirement |
|---|---|
| seed stability | the same mutations reappear under different initialisation |
| temporal placebo | shuffling years destroys the learned dynamics |
| relational placebo | permuting neighbours at preserved degree degrades it |
| leave-one-year-out | no single year, especially 2020, carries the result alone |
| noise floor | movement exceeds negative-binomial resampling of the counts |
| out-of-sample precedence | `A_t` built from data to `t-1` helps explain relations at `t` |

**The dynamism criterion is bounded from both sides and set externally**: the graph must move
**more** than the noise floor and **less** than the temporal placebo. Neither bound is chosen by
me, which is the defect DEC-115 recorded in the old 0.90 threshold -- that number was derived
from the very result it judged, so every verdict resting on it is void.

## 8. What a pass authorises, and what it does not

A pass authorises: *a per-year relational structure over France ZE2020 x A10, built on an
official prior with a low-rank learned deviation, whose year-to-year mutations survive temporal
and relational placebos.*

It does not authorise a causal claim, an automatic recommendation, or the assertion that
forecast accuracy improved -- that is a separate gate and DEC-109 through DEC-113 have already
shown how easily it is mis-measured.

`HERALD_62` B7 applies throughout.
