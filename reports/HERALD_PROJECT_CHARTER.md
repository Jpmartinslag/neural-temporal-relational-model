# HERALD Project Charter
**Version:** 1.0 — 2026-06-12
**Authority:** This document supersedes any informal description of the project scope. Changes require an explicit methodological decision (DEC-*) in the decision log.

---

**Addendum 2026-06-18:** Some statuses in the original Charter are superseded by
DEC-034→DEC-068. Sector→sector precedence is now implemented statistically through
Phase 7; recommendation remains future; neural graph prediction remains
unsupported/partial. The original text below is left unchanged — read it together with
the decision log, not as a standalone current-state claim. See
`reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` for the narrative version
and `reports/HERALD_CURRENT_STATE.md` for the current per-component status.

---

## 1. Official Name and Purpose

**HERALD** — *Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*

HERALD is a **European territorial economic intelligence system** that combines quantitative forecasting, economic state detection, territorial and sector graph analysis, associative explanation, and decision-support layers.

The birth of enterprises is **one indicator** of territorial dynamics. It is the first operational target because it is measurable and harmonisable across countries. It is not the sole objective of the system.

---

## 2. System Functions

### 2.1 Quantitative Forecasting
- Persistence and Ridge/AR estimate how much enterprise activity is expected.
- Uncertainty intervals must accompany point forecasts.
- Current validated scope: PT/IT/AT harmonized LOCO (persistence ~0.087 balanced). France WMAPE 0.0204 (HERALD Q7, Phase 3E) is PENDING_REAUDIT — potential pipeline dependency on pre-causal growth features; not usable as headline claim until causal audit is completed.

### 2.2 Economic States
The system must be able to label the economic state of a territory-sector pair:
- **Growth** — sustained positive trend
- **Acceleration** — rate of growth increasing
- **Deceleration** — positive but slowing
- **Stagnation** — near-zero change
- **Decline** — sustained negative trend
- **Recovery** — rebound from decline
- **Possible sectoral emergence** — tentative signal of new activity

States are descriptive labels derived from observed series. They are not predictions unless explicitly stated as forecasts with uncertainty.

### 2.3 Territorial Graph
- Relationships between territories within each sector.
- Geographic proximity is a **hypothesis/feature**, not an established truth.
- Cross-border relationships must be discovered and validated by the model, not assumed.
- Current validated layer: **G1-L2 co-growth** (FR/NL/PT, PASS DEC-019).

### 2.4 Sector Graph
- Sector → sector relationships.
- Attributes to track: direction (positive/negative), intensity, temporal lag, stability, uncertainty, variance/covariance.
- **Permitted language:** association, co-movement, predictive precedence.
- **Forbidden language:** structural economic causality, Granger causality as structural proof.
- Current status: **not yet implemented**. G2 territorial aggregate dynamics (territory↔territory within sector) exist but are not a sector→sector layer. Individual sector→sector associations remain untested. **[SUPERSEDED — see 2026-06-18 addendum above]** This is implemented as of Phase 7 (DEC-034, 2026-06-12): 20 observed sector→sector edges (FR=9, NL COROP=8, PT Municipal=3), bootstrap/permutation/FDR-validated. See `reports/HERALD_CURRENT_STATE.md` ("Sector→sector relations").

### 2.5 Explanation
- Identify which variables, sectors, and territories are associated with observed changes.
- Strict separation of: observed fact / statistical association / forecast / hypothesis.
- Attention weights are **not** validated explanations under current protocol.

### 2.6 Recommendation (FUTURE — NOT VALIDATED)
- Enterprise opportunity, employment, training, territorial decision support.
- This is the terminal layer and must **not** be presented as currently operational.
- Requires Bloco 1 + Bloco 2 complete.

---

## 3. Scope

### In scope
- European NUTS3 territorial forecasting (enterprise birth as primary indicator).
- Co-growth graph (G1-L2), aggregate dynamics (G2).
- Uncertainty quantification for forecasts.
- Incremental dashboard adaptation (France base).
- Observatory export format (territory, country, year, sector, forecast, state, evidence).

### Out of scope until explicitly re-opened
- Geographic/mobility graph as predictive component (closed under 4Q: queen-contiguity FAIL).
- Neural graph prediction (Phase 5 NOT_SUPPORTED; P6_DDEG_S1 FAIL).
- New GNN architecture search before integrated prototype is complete.
- Recommendation layer.
- New HPC submissions before S1-FR passes locally.

---

## 4. Permitted Claims

| Claim | Scope | Evidence |
|-------|-------|----------|
| Persistence is best LOCO baseline for PT/IT/AT | 2008–2020, 151 NUTS3, 1-year horizon | Phase 4N |
| Italian residuals show robust spatial autocorrelation | Moran's I, FDR, LOO-stable | Phase 4O-C |
| Geographic lags (queen-contiguity) do not improve forecasts | Italy, 2008–2020 | Phase 4P/4Q |
| HERALD Q7 reported WMAPE 0.0204 in France (PENDING_REAUDIT) | 306 ZE, 2021–2025, rolling-window. **Not usable as headline claim** until causal pipeline audit is complete. | Phase 3E/2R |
| FR/NL/BE/PT targets are semantically heterogeneous | Documented by official sources | Phase 4J |
| G1-L2 co-growth field is temporally stable (FR/NL/PT) | 3/3 pass, q=0.005 | DEC-019/020 |
| G2 aggregate temporal signal robust for France | FR 9/9 COVID-robust | DEC-024c/d |
| P6_DDEG_S1 fails all 7 gate criteria | 275/275 runs, FAIL | DEC-029 |

---

## 5. Forbidden Claims

| Forbidden claim | Reason |
|-----------------|--------|
| "HERALD provides economic recommendations" | Module does not exist |
| "The geographic graph improves forecasts" | Refuted under current protocol |
| "The system generalises to any European country" | n=3–4 domains, conditional scope only |
| "LOCO is cold-start" | Target country history is available at inference |
| "Attention weights explain economic relations" | Not tested, not validated |
| "Granger predictability = structural economic causality" | Explicitly prohibited |
| "P6 learned sector edges represent economic structure" | Sector labels in artefacts are INVALID_FOR_INTERPRETATION (wrong mapping — see §6) |
| "Louvain communities are validated" | NOT_SUPPORTED under corrected controls |
| "Individual G2 edges are stable" | G2_EDGE_STABILITY_NOT_SUPPORTED (M2 0.06–0.26) |

---

## 6. P6 Sector Label Status

The `data/processed/dual_graph_s1/learned_sector_edges.csv` uses sector names (AZ, BE, C, DE, GI, JZ, KZ, LZ, MN) that **do not match** the actual tensor sector_ids (BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU) stored in the NPZ fold files. The origin of the divergent mapping cannot be proven from available code; the audit script that generated the CSV did not record the sector name source.

**Decision:** `learned_sector_edges.csv` and any claim referencing named P6 sector edges is classified as **INVALID_FOR_INTERPRETATION**. The file is preserved as historical record. The index-based gate metrics (Jaccard, density, MAE) remain valid because they use integer indices, not names. The gate decision (DUAL_GRAPH_S1_FAIL) is unaffected.

---

## 7. Frozen Scientific Decisions

The following decisions are **closed** and require a new DEC-* entry to reopen:

| Decision | Status |
|----------|--------|
| Ridge/AR as primary quantitative module | FROZEN |
| G1-L2 valid only as co-growth association field | FROZEN |
| G2 valid only for aggregate dynamics, COVID caveats | FROZEN |
| G2 individual edges not stable | FROZEN |
| Louvain communities not supported | FROZEN |
| P6_DDEG_S1: DUAL_GRAPH_S1_FAIL | CLOSED |
| Geographic queen-contiguity branch closed (4P/4Q) | CLOSED |
| Phase 5 fixed-L2 corrector: NOT_SUPPORTED | CLOSED |
| No new GNN before integrated prototype | FROZEN |
| No relaunch of P6 or architecture tuning | FROZEN |
| No new HPC submission — S1_FR_FAIL closes graph-temporal prediction branch | CLOSED |

---

## 8. Criteria for Changing Scientific Direction

A direction change requires:
1. A new DEC-* entry in `HERALD_METHODOLOGICAL_DECISION_LOG.md`.
2. Documented failure or new evidence that motivates the change.
3. Pre-registered gate before any new experiment.
4. Performance failure alone is **not** a reopen condition for closed branches.

---

## 9. Next Phase: HERALD Economic Observatory v0.1

The next implementation phase is **not** a new architecture search. It is the first integration:

1. Unified export per territory/country/year/sector containing:
   - Observed value
   - Ridge forecast + uncertainty interval
   - Economic state label
   - Velocity/acceleration signal
   - Available evidence tier

2. Two distinct graph layers:
   - Territory ↔ territory within same sector (G1-L2)
   - Sector → sector (to implement, simple and auditable method)

3. Sector → sector method constraints:
   - Positive/negative signal, lag, strength, stability
   - Bootstrap/permutation validation
   - Language: association or predictive precedence — never structural causality

4. Incremental dashboard adaptation based on `reports/dashboards/herald_france_final_dashboard.html`.

5. Intelligence layer: reuse structure from old layer. Do not promote old fixed weights. Do not use P6 graph. Rankings are opportunity hypotheses, not operational recommendations.

**Do not implement the prototype in the audit/consolidation phase.**
