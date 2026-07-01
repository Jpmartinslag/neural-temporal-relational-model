# HERALD 23 — Temporal-Relational Recommendation Objective

**Created:** 2026-07-01.  
**Status:** `OBJECTIVE_REFRAMED`.  
**Scope:** methodological objective only. This document does not validate a new model,
does not create a recommendation layer, does not reopen closed graph branches, and does
not authorize new HPC jobs by itself.

---

## 1. Reframed objective

The HERALD objective is no longer framed as "improve forecasting with a graph/neural
model".

The project objective is now:

> **HERALD learns temporal-relational representations of territories and sectors in
> order to produce auditable indicators and exploratory rankings for assisted territorial
> economic recommendation.**

Forecasting remains in the architecture, but its role changes:

> **Forecasting is a control and auxiliary learning task, not the final scientific
> objective.**

This reframing preserves the existing clean data chain, baseline forecasting work,
relational signal layer, graph/neural prototypes, and dashboard. It changes how those
pieces are interpreted and what future validation must prove.

---

## 2. Canonical architecture after reframing

```text
ZE2020 x year x sector
        |
        v
causal temporal features
lags, safe growth, masks
        |
        v
territorial and sector relations
ZE->ZE, ZE->sector, ZE x sector, sector->sector when validated
        |
        v
temporal-relational representation
        |
        +--> forecasting task as control / auxiliary learning
        |
        +--> indicators
             signal_strength
             stability_score
             specialization
             dynamism
             relational proximity
             uncertainty / availability
        |
        v
exploratory ZE x sector ranking
for assisted territorial economic recommendation
```

The phrase "temporal-relational representation" is intentionally broader and safer than
"validated STGNN". The current repository has clean causal panels, relational features,
exploratory signals, and graph/neural smoke prototypes. It does **not** yet have a final
validated temporal graph neural architecture.

The closest external family is dynamic graph representation learning, not static GNN.
HERALD can later be named and defended as a new model only if the next implementation
formally learns time-varying representations over ZE2020, sectors, and their relations.
Until then, the canonical wording remains "architecture" or "prototype", not "validated
new model".

---

## 3. Role of forecasting

Forecasting answers a limited diagnostic question:

> Does the representation carry useful temporal information under rolling-origin
> evaluation?

Forecasting metrics such as WMAPE, MAE, or RMSE remain useful, but they are not the only
success criterion. A model that does not beat persistence/Ridge on WMAPE is not promoted
as a superior forecaster. However, this alone does not invalidate the relational layer if
its signals are stable, interpretable, and useful for retrospective ranking.

Current interpretation of existing scripts:

| Existing component | New role |
|---|---|
| `fr_ze2020_clean_panel.csv` | Auditable observed base |
| `fr_ze2020_model_ready_panel.csv` | Causal temporal input |
| `lag_1/2/3`, `growth_*_safe` | Temporal memory |
| persistence / Ridge | Statistical controls |
| relational Ridge / MLP / graph smoke | Representation candidates, not final claims |
| `signal_strength` | Relational intensity indicator |
| `stability_score` | Temporal recurrence indicator |
| dashboard | Human inspection layer, not validation by itself |

---

## 4. Recommendation is not automatic yet

HERALD still must not claim operational recommendation.

Allowed wording:

- assisted territorial economic recommendation;
- exploratory ZE x sector ranking;
- candidate indicator;
- hypothesis for expert review;
- relation signal;
- temporal-relational representation.

Forbidden wording:

- automatic recommendation;
- policy prescription;
- causal effect;
- the model discovered the true economic relation;
- neural model improves forecasting, unless proven by the relevant gate;
- dashboard validates the method.

---

## 5. Required next technical module

The next central scientific module should be:

> **Retrospective ZE x sector ranking validation.**

Minimum design:

```text
train / build indicators using data up to year T
rank candidate sectors for each ZE
observe years T+1 ... 2025
compare the ranked sectors against realized future outcomes
```

Recommended baselines:

- random ranking;
- largest past volume;
- largest past growth;
- simple specialization share;
- persistence / temporal baseline;
- geography-only relation if a documented graph exists;
- sector-only baseline.

Recommended metrics:

- Precision@K;
- Recall@K;
- NDCG@K;
- Hit Rate@K;
- average future growth of top-K vs baseline top-K.

This module is what connects the internship title end to end:

```text
apprentissage sur graphes
        -> modelisation temporelle
        -> recommandation economique territoriale
```

---

## 6. Required falsification tests

Before any ranking or relational claim can be promoted, the signal layer needs placebo
and ablation tests:

| Test | Purpose |
|---|---|
| random graph | Check whether the real relation structure matters |
| temporal shuffle | Check whether temporal order matters |
| sector shuffle | Check whether sector structure matters |
| no graph | Check whether relation features add information |
| no sector | Check whether A10 structure adds information |
| geography-only | Check whether HERALD adds more than physical proximity |
| leave-one-year-out | Check whether a single year drives the result |
| bootstrap edges | Check whether relation signals are robust |

These tests evaluate representation and ranking quality. They do not prove causality.

---

## 7. Article-level claim after reframing

Recommended claim:

> HERALD proposes a frugal and auditable temporal-relational learning architecture for
> subnational territorial intelligence. It uses causal time panels and forecasting
> baselines as controls, while its main objective is to produce stable relational and
> sectoral indicators for exploratory ZE x sector ranking and assisted economic
> recommendation.

This claim is compatible with the current evidence. Stronger claims require new
validation:

- ranking retrospective validation;
- placebo tests;
- ablations with and without time / graph / sector;
- expert interpretation case studies;
- explicit non-causal caveats.

Positioning against recent literature:

- EconoGNN (`R-008`) motivates temporal graph learning in economics, but at country scale
  and for economic resilience classification. HERALD's intended contribution is
  subnational ZE2020 x sector ranking and assisted territorial recommendation.
- Dynamic graph surveys (`R-050`, `R-051`, `R-052`) justify treating topology, node
  attributes, and time jointly. They do not validate HERALD by themselves.
- Spatio-temporal GNN review evidence (`R-053`) reinforces the need for baselines,
  reproducibility, explainability caveats, and scalability checks before any strong model
  claim.
- Economic complexity / product-space references (`R-001`, `R-055`, `R-056`) support the
  idea of sector relatedness and subnational productive structure, but recommendation
  requires a formal objective and retrospective validation.
- Economic network forecasting (`R-054`) motivates testing network descriptors against
  linear and non-linear baselines.
- Spatial dynamic panel work (`R-057`) defines a serious econometric baseline family for
  future falsification.

---

## 8. Relationship to previous canonical documents

This document does not replace the data lineage, training audit, relation-signal audit,
or dashboard documentation. It changes the central framing used when interpreting them:

- `HERALD_15`: remains the canonical clean France ZE2020 data chain.
- `HERALD_17`: remains the relational-layer plan; its "representation before
  prediction" hypothesis becomes the central objective.
- `HERALD_18`: training scripts are reinterpreted as controls and representation
  candidates, not a final competition for WMAPE.
- `HERALD_20`/`HERALD_21`: relation signals become inputs to future ranking validation,
  not recommendation claims.
- `HERALD_22`: dashboard remains a human inspection layer, not scientific validation.
