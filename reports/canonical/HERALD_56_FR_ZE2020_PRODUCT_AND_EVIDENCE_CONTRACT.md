# HERALD 56 -- France ZE2020 Product and Evidence Contract

**Date:** 2026-07-27
**Status:** `PRODUCT_AND_EVIDENCE_CONTRACT_FROZEN`
**Decision:** DEC-081

## 0. Purpose and scope

This document freezes three answers so that they stop being re-litigated at the start of
every work cycle:

1. what the product's forecasting engine is;
2. what the relational layer is permitted to claim;
3. what single condition authorizes experimenting with a neural model again.

It is a contract, not a result. It validates no model, produces no metric, authorizes no
HPC job, and reopens no closed branch. It exists because, across 80 methodological
decisions, no relational candidate has justified promotion to a robust predictive or
neural product layer under the complete sequence of matched controls, while limited
analytical signals and exploratory results do exist (DEC-019/020, DEC-034, DEC-070,
HERALD_39 successor probe, HERALD_27 local pair gate). The recurring cost was not the
absence of signal but the re-testing of equivalent hypotheses under new model names.

Scope: France ZE2020 x A10, 280 zones x 9 sectors x 2012-2025.

## 1. Q1 -- What is the product's forecasting engine

### 1.1 Decision

| Role | Object | Status |
|---|---|---|
| Intended primary engine | sectoral persistence at ZE x sector | **CANDIDATE** -- not validated |
| Macro context layer | existing ZE-total baseline (persistence + Ridge) | exploratory smoke, dashboard context only |
| Not the engine | any neural model | closed for this role until Q3 is satisfied |

The product objective is sectoral, so the intended primary engine is defined at
ZE x sector granularity.

**Sectoral persistence is a candidate, not a validated engine.** No rolling-origin audit of
it exists. It may not be described as the product's engine, as validated, or as a
promoted baseline until that audit is delivered (HERALD_58, part a).

### 1.2 What must not be inferred from DEC-079 and DEC-080

Two baseline results exist and are frequently over-generalized. Their exact scope:

| Decision | Task | Result |
|---|---|---|
| DEC-079 | masked reconstruction of sector shares | temporal persistence MAE `0.009652` vs full MLP `0.013498`, winning 220/225 paired comparisons |
| DEC-080 | ranking of next-year signed share transitions | `past_delta` NDCG@3 `0.647044` vs `mlp_joint` `0.623920`; seed CV `0.47%` |

Each result holds in its own task. Neither, alone or combined, constitutes a validated
forecasting engine for the product. They establish that simple economic memory is a
demanding control, not that a specific engine has been audited for the product's target.

### 1.3 Current state of the ZE-total baseline

| Property | Value | Source |
|---|---|---|
| Script | `src/modeles/france_ze2020/train_fr_ze2020_baselines.py` | code |
| Models | persistence + Ridge, lag-only features | code |
| Granularity | **ZE x year -- no sector dimension** | `fr_ze2020_model_ready_panel.csv` has no sector column |
| Default evaluation years | **2019-2025** | `train_fr_ze2020_baselines.py`, `DEFAULT_EVAL_YEARS` |
| Claim status | `exploratory_smoke` | HERALD_16 |

Because the panel carries no sector dimension, this script cannot produce ZE x sector
states directly. Any sectoral state layer requires the separate component defined in
HERALD_58.

### 1.4 Evaluation protocol for the sectoral persistence audit

This subsection is normative for HERALD_58 part a.

Sectoral persistence is a deterministic identity with no fitted parameters:

```text
yhat(z, s, t) = y(z, s, t - 1)
```

Consequences that the audit must respect:

1. **No training.** There is no fit step, no hyperparameter, and no convergence criterion.
2. **Rolling-origin, each observation evaluated exactly once.** No observation may enter
   the metric more than once.
3. **Seeds add no evidence.** The estimator is deterministic; reporting multiple seeds for
   persistence inflates apparent sample size without adding information. Do not report
   seed dispersion for persistence.
4. **ZE-disjoint folds organize paired comparisons only.** They exist so that persistence
   and a fitted competitor are compared on identical populations. They must not be used to
   duplicate persistence observations across folds, and must not multiply its metric rows.
5. **Fitted competitors behave normally.** Ridge or any other fitted model uses training
   data, folds, and seeds in the usual way. Only the deterministic baseline is exempt.

Failure to respect points 2-4 produces an artificially precise persistence metric and
invalidates the comparison.

## 2. Q2 -- What the relational layer may claim

### 2.1 Permitted, inside the audited scope

- **Association / co-movement.** Example: G1-L2 co-growth, validated for FR/NL/PT
  (DEC-019/020).
- **Predictive precedence, within the scope where it was measured.** Phase 7 established
  lagged sector-to-sector precedence with bootstrap, permutation and FDR control
  (DEC-034). Its scope is country grain, 20 promoted edges, of which France has one
  (RU->MN, COVID-sensitive, DEC-060). Statements must carry that scope.
- **Exploratory relational indicators**, labelled as such, with their evidence level
  visible.

### 2.2 Forbidden

- **Generalized incremental predictive value** -- asserting that a relation improves
  prediction outside the scope in which it was measured.
- **Causality** in any form, including implicit verbs of influence.
- **Automatic recommendation** or policy prescription.
- Describing the architecture as a validated dynamic GNN.

The distinction is deliberate: precedence inside an audited scope is a real, citable
finding; incremental predictive value is what failed repeatedly under matched placebos.

## 3. Q3 -- What authorizes experimenting with a model again

### 3.1 The single condition

An **exogenous sectoral structure, independent of the enterprise-birth panel**, that
survives a matched placebo.

Minimum requirements of that test:

- the placebo uses the **same representation** as the real object (the lesson of DEC-075,
  where matched uniform randomized endpoints reached `0.643529` against the real uniform
  topology's `0.635586`);
- at least **60% paired wins** across seed / year / fold;
- degradation under **target shuffle of the complete future-target bundle** (the lesson of
  HERALD_38 section 8, where an incomplete shuffle left the effective label attached);
- identical populations, finite metrics, zero train/test ZE overlap;
- the gate is pre-registered before any metric is inspected.

### 3.2 What passing authorizes -- and what it does not

Passing authorizes **only experimenting with a small temporal-relational encoder. That
encoder must then beat its own controls.**

Passing does **not** authorize: the final model, a dynamic-GNN claim, causal language,
automatic recommendation, or skipping the encoder's own gate.

### 3.3 What never counts as a new hypothesis

More epochs; more seeds; a different top-k; a different horizon; a different threshold; a
different normalization; swapping an MLP for a GNN on the same input and target; retuning
DEC-079 or DEC-080.

Reopening a closed branch requires a materially different economic object and a new DEC
entry, per DEC-075, DEC-077 and DEC-078.

## 4. Structural failure patterns, each with its own scope

Recorded here so that a future proposal can be checked against the actual cause rather
than a general impression.

1. Strong annual persistence in the level and reconstruction tasks tested.
2. A node's own history dominating external relations in the ranking tasks tested.
3. Real relations indistinguishable from matched randomized endpoints -- DEC-069
   (lift `+0.0003`), DEC-075 (real below placebo).
4. **Edge-target circularity, restricted to trajectory-similarity tests.** The
   `ze_similarity` edges are trajectory correlations computed from the same
   enterprise-birth panel that defines the target. Attribution, kept precise:
   - **DEC-069** supports this reading through its sector shuffle and its
     randomized-endpoint placebo -- real relation change lost to sector-shuffled
     relations (lift `-0.0002`) and was effectively tied with randomized endpoints
     (`+0.0003`). DEC-069 did not evaluate a temporal shuffle.
   - **Temporal shuffle failing to degrade** is attributed only to the corrected top-3
     and relation-lift runs that actually evaluated it (HERALD_38 section 8, jobs
     `7755806` / `7755807`).
   - It does **not** apply to DEC-080, which used no relational edge and whose sector and
     temporal shuffles degraded as expected.
5. **Target degeneracy, independent of any edge.** Shares sum to one, and within-ZE
   ranking has only nine candidates. This is a plausible structural limitation consistent
   with the outcomes of DEC-078 (current target RCA wins), DEC-079 (persistence wins) and
   DEC-080 (`past_delta` wins). It is an interpretation, not a demonstrated mechanism: no
   test has isolated compositional closure as the cause, and doing so would require a
   target that is not closed by construction.
6. Nine A10 sectors and T = 14 years, giving 72 ordered sector pairs.
7. No exogenous **sectoral structure** in the panel. Commuting and geography are exogenous
   and were already tested and closed (DEC-073/074/075, DEC-008/011).
8. National-trend information already exists as a feature in the ranking panel
   (`national_sector_share_lag_1`, `national_sector_growth_lag_1`) and was not sufficient.
   Residualizing the **target** by sector and year remains untested, but is less novel
   than it appears.

## 5. Delivery sequence

| Stage | Document | Type |
|---|---|---|
| E1 | HERALD_56 (this document) + DEC-081 | documentary audit |
| E2 | HERALD_57 -- observational A10 mask and relational availability mask, separately | audit plus code where an executable transformation exists |
| E3 | HERALD_58 -- (a) rolling-origin audit of sectoral persistence, then (b) forecast-derived states | audit plus code |
| E4 | HERALD_59 -- retrospective ranking gap audit against HERALD_23 sections 5-6 | documentary audit |
| E5 | HERALD_60 -- graph-first dashboard, layers separated by grain and evidence scale | code |
| E6 | HERALD_61 -- Atlas/IAT provenance and mapping preflight, no metric | documentary audit |
| E7 | new DEC -- exogenous-structure gate, conditional on E6 | pre-registered gate |

Rules that apply across stages:

- A documentary audit produces no script and no test. Code and tests are created only
  where a real executable transformation exists.
- Each stage that carries a methodological decision appends a DEC entry.
- No HPC job at any stage.

## 6. Facts verified for this contract

Every number below was checked against the artifact, not quoted from another document.

| Fact | Value | Verified against |
|---|---|---|
| Clean ZE panel | 3,920 rows, 2012-2025 | `fr_ze2020_clean_panel.csv` |
| Model-ready panel | 3,920 rows, 2012-2025, no sector column | `fr_ze2020_model_ready_panel.csv` |
| Sector panel | 35,280 rows, 14 years, 2012-2025 | `fr_ze2020_sector_panel.csv` |
| `mask_sector_available = 0` | **0 cells** | `fr_ze2020_sector_panel.csv` |
| Observed zeros | **1 cell** | `fr_ze2020_sector_panel.csv` |
| Positive cells | **35,279** | `fr_ze2020_sector_panel.csv` |
| Baseline default evaluation years | 2019-2025 | `train_fr_ze2020_baselines.py` |

The single observed zero is the known cell `5218 / 2016 / JZ`, completed as zero only
because the other eight sectors equal the independent official total (DEC-076). The A10
observational mask therefore has effectively no missing-data work; the real availability
work is relational, not observational, and belongs in HERALD_57 as a separate object.

## 7. Documentary sweep for inconsistent ranges

Performed as part of E1 over `reports/` and `reports/canonical/`.

| Finding | Verdict |
|---|---|
| `HERALD_CURRENT_STATE.md` stated the baseline evaluation range as 2019-2024 | **inconsistent with code (2019-2025)** -- corrected in this pass |
| `2019-2024` occurrences in DEC-060 and DEC-066 | correct -- these are Phase 7 six-year estimation windows, not evaluation ranges |
| `2019--2024` in HERALD_39 | correct -- the successor probe has 30 paired seed-year evaluations because successor year 2025 lacks a complete next-snapshot feature vector |
| Evaluation ranges in HERALD_40/42/43/45 (2020-2022), HERALD_26 (2017-2024), HERALD_24 (default last year 2022) | correct and internally justified |
| `DEC-001 to DEC-068` decision-range pointers | **stale** in `HERALD_CURRENT_STATE.md`, `HERALD_ACTIVE_DOCUMENT_INDEX.md` and `canonical/HERALD_01` -- corrected in this pass |
| `DEC-001 to DEC-011` in `canonical/HERALD_11` | correct -- scoped to the Phase 4 sub-phases |
| Stale pointers in untracked root reports (`HERALD_PROJECT_TRAJECTORY.md`, `HERALD_REPOSITORY_STRUCTURE.md`, `HERALD_RESEARCH_GANTT.md`) | not corrected -- these files are outside the git index; noted for a future consolidation pass |

No other temporal-range inconsistency was found.

## 8. Decisions still reserved for the project owner

1. The state thresholds for HERALD_58 part b, pre-registered before the distribution is
   inspected.
2. The evidence scale specific to the ZE-to-ZE similarity layer. The DEC-066 tiers apply
   to sector-to-sector relations and must not be applied to this layer.
3. Whether the written contribution is the falsification protocol plus product, or
   requires a positive neural result. In the latter case the constraint is data, not
   architecture.
4. Whether to authorize a fine-sector availability preflight, that is, whether SIDE
   publishes establishment creations by ZE2020 at A38. The nomenclature hierarchies exist
   in the Atlas/IAT database; the fine time series would have to come from SIDE. This is a
   verification, not an established fact.
5. Written confirmation that the France Q7 figure (WMAPE 0.0204) stays outside every
   claim while it remains `PENDING_REAUDIT`.

## 9. Cross-reference

- Decision: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, DEC-081.
- Objective framing: `reports/canonical/HERALD_23_TEMPORAL_RELATIONAL_RECOMMENDATION_OBJECTIVE.md`.
- Closed branches: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`.
- Temporal integrity rules: `reports/canonical/HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md`.
- Gates that produced patterns 1-8: `reports/canonical/HERALD_40` through `HERALD_55`.
- Atlas/IAT audits: `reports/ATLAS_IAT_DATABASE_AUDIT.md`,
  `reports/ATLAS_IAT_ANNUAL_RECONSTRUCTION_STANDBY.md`,
  `reports/ATLAS_IAT_TO_HERALD_EXPERIMENT_PLAN.md`.
