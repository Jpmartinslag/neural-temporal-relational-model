# HERALD 69 -- Corrected relational gate and top-k product metric

**Date:** 2026-08-11
**Sections 1-5:** `PRE_REGISTERED` (DEC-114). Written before the code existed.

## 1. Why this run exists

`HERALD_68`/DEC-111 is marked `AUDIT_FAILED_REQUIRES_CORRECTION` by DEC-112 and DEC-113. Two
independent audits, run without sight of each other, agreed that G-B, G-C and G-D were invalid.
This run replaces them. G-A is not re-litigated: it survived both audits as inconclusive and
sector-heterogeneous.

## 2. Every defect and its correction, binding

| defect | where | correction |
|---|---|---|
| placebo re-weighted random neighbours by their **true** affinity | `:119` | placebo weights are a **permutation of the real weight row**; never recomputed from `C` |
| placebo sampled with replacement | `:116` | sampling without replacement |
| placebo could select the node itself (426/2,520 rows in 2025) | `:116` | self explicitly excluded |
| a **single** placebo draw was used | `:300` | **50 draws**, mean reported with its across-draw sd |
| `K=50` averaged a fifth of the sector; effective K 49.1 | `:33` | `K` in {5, 10, 20, 50}, all reported; **K=10 is the pre-registered primary** |
| distance weighting inert on the real arm, cost 0.0057 | `:121` | unweighted top-K is the primary encoding |
| fifth feature was `wgt[:,0]`, an arm identifier | `:141` | replaced by **effective neighbours** `1/sum(w^2)` and mean affinity |
| `block_bootstrap_ci` resampled years iid | `:161` | **circular block bootstrap**, block length 2-3, both reported |
| synthetic null fitted a quadratic over all 14 years | `:76` | trend fitted **only on years <= t-1**; dispersion and class balance calibrated on training years |
| G-B compared absolute scores across panels of different difficulty | `:324` | compared as **lift over each panel's own mean-reversion baseline** |
| graph exported one family, 40/280 zones, 2.9% of edges, IDs cast `0051`->`51` | `:250` | all three families, all source zones, full top-K, `zfill(4)` IDs that join to official commuting |

**Harness self-test, added because it would have caught the central defect in one run:**
assert `placebo_score <= base_score + tolerance`. A placebo that beats the no-relational base is
contaminated by construction.

## 3. Primary metric changes to the product question

Mean Spearman does not answer *which zones will be at the top of this sector*. DEC-113 measured,
post-hoc and single-seed, relational minus its own base at **Precision@10 +0.0317
[+0.0175, +0.0476] over 7/7 origins** -- the first configuration in which the relational block
beat its no-relational twin consistently.

**Precision@10 and NDCG@10 are pre-registered here as primary**, macro-F1 and Spearman as
secondary. This is promotion of a post-hoc finding to a pre-registered test, and it counts only
because it is being re-run on the corrected harness.

## 4. Gates

**H1 -- relational block beats its matched placebo.** Primary metric, K=10, paired by origin,
circular block bootstrap, averaged over 50 placebo draws. The across-draw sd is reported beside
the interval; a lead that survives one draw and not the mean does not pass.

**H2 -- relational block beats its own no-relational twin.** Same architecture, same folds, only
the feature block differs. This is the comparison DEC-113 found positive and it must replicate.

**H3 -- the model beats mean reversion on the primary metric.** DEC-109 E1's rank-matched
`-g[t-1]`, in its top-k form.

**H4 -- multiplicity.** H1-H3 are tested at four values of K and on two metrics.
Benjamini-Hochberg at q = 0.10 across that family, fixed now.

**H5 -- the graph artifact must join.** A left join of the exported edges onto the official
commuting file on `zfill(4)` IDs must lose zero rows, and every pre-registered family must be
present for every year the availability mask marks available.

## 5. Reporting

`HERALD_62` B7 applies. Additionally: **the per-sector breakdown is reported always**, never
only the average. DEC-112 established that the aggregate hid three sectors passing decisively
(JZ +0.066, KZ +0.058, OQ +0.038) and one failing decisively (BE -0.053); an average that
cancels them is a worse description than either.

If H1 or H2 fail, the standing claim becomes: *the predictor converges on what a linear rule
achieves, and the relational layer's value rests on its own placebo-validated structure rather
than on forecast gain.* That claim is already supported by DEC-096 and DEC-099 and does not
depend on this run.
