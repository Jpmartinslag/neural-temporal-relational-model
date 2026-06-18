# HERALD Project Trajectory

**Created:** 2026-06-18 (documentation/curation pass — no scientific result, claim, or
number in this file is new; everything here restates what is already frozen in
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, `reports/HERALD_PROJECT_CHARTER.md`,
and `reports/HERALD_CURRENT_STATE.md`. If this document disagrees with any of those,
they win.)

**Purpose:** Tell the real evolution of HERALD — not just the latest dashboard — so a
supervisor can see the path, a future AI session knows what to read vs ignore, and an
economist can see the method was built incrementally and audited at each step.

---

## A note on dates before anything else

The working brief for this document assumed the project began in **March 2026**. The
verifiable evidence in this repository does not support that:

- The earliest commit in `git log` is **2026-04-08** ("build sprint 1 data foundation
  and governance").
- No report, decision-log entry, or commit references March 2026 activity.

This document therefore anchors the "foundation" period to **April–May 2026**, which is
what the repository actually shows. If genuine March 2026 work exists outside this
repository (e.g. proposal writing, literature search before any code was committed), it
is not represented here and should be added explicitly if/when evidence (notes, an
earlier repo, dated documents) surfaces. Per project rule, nothing is asserted here
without a traceable source.

---

## April–May 2026: France prediction foundation

**What happened:**
- First commits (2026-04-08 onward): core data foundation, target/proxy definitions,
  annual baseline, initial spatial/STGNN tensor packages.
- France-first scope: the territorial grain chosen was **ZE2020 (Zones d'Emploi)**, 280
  employment zones, using **SIDE/SIRENE** establishment-creation data as the observed
  target (`establishment_creation`).
- An architecture search ran across Phase 2 (regime/latent-dimension/autoregression
  variants) and Phase 3 (Q-tensor/labor-tutor variants), from roughly 2026-05-12 through
  2026-05-27 — see the historical Phase2*/Phase3* reports listed in
  `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` under "Historical/superseded".
- **Phase 3E selected HERALD Q7** (2026-05-27) as the best France architecture: WMAPE
  0.0204 (306 ZE, 2021–2025, rolling-window). Confirmed by Phase 2R.
- A first operational dashboard was built on this foundation:
  `reports/dashboards/herald_france_final_dashboard.html` (first committed 2026-05-28).
- This is the origin of the "France first" framing still present in the Charter (§1):
  enterprise birth chosen as the first indicator because it is measurable and
  harmonisable, not because it is the only target of interest.

**Current caveat (do not drop this when citing the period):**
> **France Q7 WMAPE 0.0204 is PENDING_REAUDIT.** The causal audit of the full Phase
> 3E/2R pipeline features (`growth_1y/2y`, `effectifs_lag1`) is not yet formally
> complete. This result must not be cited as a headline claim until that audit is done
> (see `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`, "WMAPE 0.0204 France" section, and
> Charter §4).

**Source audits for this period:** `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md`,
`reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` (both ACTIVE/citable); the rest of
Phase2*/Phase3* are historical search-process records, not standalone results.

---

## Late May–June 2026: European harmonization and failure-driven pruning

**What happened:**
- 2026-05-28: Phase 4 internationalization begins (commit "Consolidate Phase 3C/3E
  results and start Phase 4 internationalisation").
- 2026-06-03 (DEC-001): a temporal-leakage bug is found in `growth_1y` across the
  Belgium/Netherlands/Portugal ingestion — all pre-DEC-001 cross-country baselines are
  reclassified LEGACY/LEAKAGE-AFFECTED. This is the start of the formal decision log.
- DEC-002→DEC-011 (2026-06-04 → 2026-06-10): causal per-country baselines rebuilt;
  target semantics audited and found heterogeneous across FR/NL/BE/PT (DEC-003); Austria
  added as the third Path H country, FR/ES/CZ blocked for that harmonized panel
  (DEC-005); **persistence confirmed as the best LOCO baseline for PT/IT/AT, no model
  promoted** (DEC-006); Italy spatial-lag and Spatial Durbin branches both **closed
  FAIL** (DEC-008/009-ish, Phase 4P/4Q).
- Parallel branch: G1/G2 economic-graph work (Phase 1–3 of the graph roadmap).
  G1-L2 co-growth **PASS** for FR/NL/PT (DEC-019/020). G1-L1 sector relatedness
  **NOT_SUPPORTED**. Community detection (Louvain) **FAIL** (DEC-0xx, closed branch).
  G2 aggregate dynamics descriptive-only, FR-robust, NL/PT COVID-sensitive.
- Two larger predictive-graph branches were tested and **closed**:
  - **P6 Dynamic Dual Economic Graph** — `DUAL_GRAPH_S1_FAIL`, all 7 gate criteria fail
    (DEC-029, 2026-06-12).
  - **Graph-temporal (GConvGRU/EvolveGCN-H)** — `S1_FR_FAIL`, both models
    indistinguishable from permutation nulls (DEC-031, 2026-06-12).
- These closures are why the prediction layer that survives into the Observatory is
  **plain statistics** (persistence/Ridge/AR(1)), not a neural model — every learned
  alternative tested on real territorial data so far has failed its pre-registered gate.

**Status of these branches:** CLOSED. Per Charter §8, reopening requires a new DEC-*
entry with new evidence — performance failure alone does not reopen them.

**Source audits for this period:** `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`,
`reports/HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md`,
`reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md` (closed),
`reports/HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md` (closed),
`reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`,
`reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` (closed),
`reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` (closed).

---

## June 2026: Economic Observatory and sector relations

**What happened:**
- 2026-06-12: **Phase 7 sector precedence** delivers `SECTOR_PRECEDENCE_PROTOTYPE_READY`
  (DEC-034) — a signed, lag-1, bootstrap/permutation-validated sector→sector method.
  Integrated into **Observatory v0.3** the same day (DEC-035/036): choropleth map +
  sector graph + economic states + territory heatmaps, built on top of
  `herald_france_final_dashboard.html`.
- 2026-06-15→06-16: **DEC-060** finds why France has only 1 promoted sector-pair label
  (RU→MN): ZE2020's 280 small zones produce systematically smaller effect sizes
  (|β|=0.076–0.097) below the |β|≥0.10 threshold — a scale/granularity finding, not a
  methodology gap. **DEC-061/062** audit whether PT and NL can be raised to municipal
  grain: **PT_READY_NL_BLOCKED** (NL has no gemeente×births×sector table in CBS Open
  Data). **DEC-063** builds the granular FR/PT/NL evidence model, including an NL
  gemeente proxy disaggregated from COROP by stock share. **DEC-064** closes **PT
  Municipal Phase 7** (2 COVID-robust pairs, 278 municipalities, INE enterprise_birth).
  **DEC-066** sets the fine-grain threshold policy (0.10 original / 0.09
  fine-grain-supported / 0.07–0.09 exploratory-only).
- 2026-06-17: **DEC-065** finds a structural validity defect in the NL gemeente proxy —
  its 121 apparently-promoted edges are an artefact of the stock-share proxy method
  itself (cross-sector-correlated noise unrelated to births), not a real relation. **The
  NL gemeente proxy is blocked for relation labels**, overriding what an automated
  gate-count alone would have called SUPPORTED. NL COROP (8 promoted, 3 COVID-robust,
  observed) remains the valid NL baseline.
- 2026-06-16→06-17: **Observatory v0.4 / v0.4.1** ship — clean observed-only exports
  (`granular_relation_edges.csv`: 20 edges, FR=9/NL COROP=8/PT Municipal=3),
  PT continental municipality geometry (278/278, geoapi.pt/DGT-CAOP), dynamic
  timeline/graph, map↔graph linking. 241/241 tests pass.
- 2026-06-17: **Observatory v0.5** adds a layperson narrative layer — rejected by the
  product owner as a polished MVP, not a complete-method presentation (English UI, PT
  prediction gap left open, sector graph not wired to map).
- 2026-06-17→06-18: **Observatory v0.5.1** corrects every v0.5 point: French UI, a
  "Méthode HERALD" architecture diagram opens the page, PT municipal prediction closed
  via direct causal persistence/Ridge AR(1) (DEC-068, no proxy, no HPC), real
  "Bassins économiques" geographic heatmap, graph-to-map wiring. 103/103 structural
  tests pass — **but it has never been visually validated** (no Playwright/screenshot,
  DOM/JS string assertions only). Decision: `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN`
  (DEC-068) — committed as the current best-draft candidate, not a final deliverable.

**Source audits for this period:** `reports/HERALD_PHASE7_SECTOR_PRECEDENCE.md`,
`reports/HERALD_OBSERVATORY_V03_AUDIT.md`,
`reports/HERALD_DEC060_FRANCE_RELATION_SIGNAL_AUDIT.md`,
`reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md`,
`reports/HERALD_DEC064_PT_MUNICIPAL_PHASE7_AUDIT.md`,
`reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md`,
`reports/HERALD_DEC066_FINE_GRAIN_THRESHOLD_CALIBRATION.md`,
`reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`,
`reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md`.

---

## Current state (2026-06-18)

- **Prediction layer exists but is conservative:** persistence/Ridge/AR(1), causal,
  rolling-origin. Validated as best LOCO baseline for PT/IT/AT (DEC-006). France HERALD
  Q7 (WMAPE 0.0204) is richer but **PENDING_REAUDIT**, not a headline claim. PT municipal
  prediction closed the same conservative way (DEC-068).
- **Graph/statistical relations exist:** 20 observed sector→sector edges (FR=9, NL
  COROP=8, PT Municipal=3), bootstrap/permutation/FDR-validated. G1-L2 territorial
  co-growth PASS for FR/NL/PT. All of this is **simple statistics** (linear regression +
  resampling), not a learned model.
- **Neural relation layer remains research/partial:** `SharedRelationEncoder`
  (DEC-055) is strong on synthetic data (unseen-pair AUC=0.690) but only
  `REAL_WEAK_LABEL_TUNING_PARTIAL` on real data (DEC-059) — sign concordance
  0.438–0.667, no robust cross-country replication, not wired into any dashboard.
- **Recommendation layer not implemented.** 0%. Requires Bloco 1 + Bloco 2 complete per
  the Charter; no weights or rankings are validated.
- **Observatory v0.5.1 is a candidate**, French, 103/103 structural tests pass, never
  visually validated, next iteration signalled as a modular map-first redesign.

## Next scientific step

1. Organize the next dashboard iteration around a **modular, map-first** architecture —
   split the map into its own reusable/testable module before extending the
   graph/prediction layers on top of it (signalled direction, not started).
2. Visual (Playwright/screenshot) validation of whatever dashboard is current — every
   Observatory version through v0.5.1 has only been structurally validated.
3. Figure generation and article/methods/results writing — no figure-export pass has
   happened since Phase 8; no outline exists yet (`reports/HERALD_CURRENT_STATE.md`,
   "Writing/article" row, ~5%).

---

## Cross-reference

- Full decision history: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-068).
- Document classification: `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`.
- What's represented where: `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md`.
- Current per-component state and completion estimates: `reports/HERALD_CURRENT_STATE.md`.
