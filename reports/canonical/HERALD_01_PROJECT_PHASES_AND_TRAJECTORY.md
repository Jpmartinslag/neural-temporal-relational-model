# HERALD 01 — Project Phases and Trajectory

**Created:** 2026-06-18 (canonical consolidation pass).
**Status:** Documentation only — no scientific result, claim, or number in this file is
new; everything here restates `reports/HERALD_PROJECT_TRAJECTORY.md`,
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, and `reports/HERALD_CURRENT_STATE.md`.
If this document and any of those three disagree, they win — this is a reading aid, not
a new source of truth.
**Represents:** Phase 2/3 France reports, all `HERALD_PHASE4*.md`, the original Gantt's
Phase 0-7 plan, and `reports/HERALD_PROJECT_TRAJECTORY.md`. None of those are deleted —
see `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md` for the full per-cluster mapping.

---

## A note on dates

The earliest commit in this repository is **2026-04-08**. No report, decision-log entry,
or commit references March 2026. Any "March" framing in planning documents is therefore
an **undocumented pre-repo assumption**, not a verified fact — it is declared as such
wherever it appears below, never silently asserted.

---

## Phase Map

| Phase | Period | Objective | Data | Method | Decision | Status | Source documents |
|---|---|---|---|---|---|---|---|
| Pre-repo | "March 2026" (assumed) | — | — | — | — | **NOT DOCUMENTED** — no artefact found | — |
| France foundation | Apr–May 2026 (2026-04-08 → 2026-05-27) | Build a first territorial forecasting layer for France | FR ZE2020 (280 employment zones), SIDE/SIRENE `establishment_creation` | Architecture search (Phase 2 regime/latent-dim variants, Phase 3 Q-tensor/labor-tutor variants) | **Q7 selected** (Phase 3E, 2026-05-27), confirmed Phase 2R | Q7 WMAPE 0.0204 — **PENDING_REAUDIT** | `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md`, `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` |
| France dashboard | May 2026 (committed 2026-05-28) | First operational dashboard on top of the foundation | Same as above | Static HTML, built from Q7 outputs | — | ACTIVE, do-not-modify-casually | `reports/dashboards/herald_france_final_dashboard.html` |
| International harmonization | Late May–Jun 2026 (2026-05-28 → 2026-06-10) | Build a causal, leakage-free LOCO baseline across countries | PT/IT/AT, later BE/NL | Persistence/Ridge, causal rolling-origin | DEC-001 (leakage found) → DEC-006 (persistence = best LOCO baseline, no model promoted) | VALIDATED baseline; no promoted model beyond persistence | `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`, `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` DEC-001→DEC-011 |
| Graph branch pruning | Jun 2026 (2026-06-10 → 2026-06-12) | Test whether geographic/spatial or learned-graph structure improves forecasts | Italy NUTS3 residuals; FR/NL/PT panels | Queen-contiguity spatial lag, Spatial Durbin, P6 dual dynamic graph, GConvGRU/EvolveGCN-H graph-temporal | DEC-008/009 (4P/4Q FAIL), DEC-029 (P6 `DUAL_GRAPH_S1_FAIL`), DEC-031 (`S1_FR_FAIL`) | **All CLOSED** — Charter §8 governs reopening | `reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md`, `reports/HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md`, `reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md`, `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` |
| Sector precedence + Observatory v0.3 | Jun 2026 (2026-06-12) | Build a validated sector→sector relation layer and integrate it into a dashboard | FR/NL COROP/PT NUTS3 | Signed lag-1 regression, bootstrap/permutation/FDR | DEC-034 (`SECTOR_PRECEDENCE_PROTOTYPE_READY`), DEC-035/036 (Observatory v0.3) | DONE | `reports/HERALD_PHASE7_SECTOR_PRECEDENCE.md`, `reports/HERALD_OBSERVATORY_V03_AUDIT.md` |
| Granularity push | Jun 2026 (2026-06-15 → 2026-06-17) | Raise FR/PT/NL territorial granularity and explain France's weak relation signal | FR ZE2020 (280), PT Municipal (278), NL COROP (40) vs NL gemeente (355, proxy) | Same lag-1 precedence method at finer grain; fine-grain threshold policy | DEC-060 (France scale finding), DEC-061/062 (PT ready, NL blocked), DEC-063 (evidence model), DEC-064 (PT municipal Phase 7 complete), DEC-065 (**NL gemeente proxy BLOCKED**), DEC-066 (threshold policy) | PT municipal COMPLETE; NL gemeente proxy BLOCKED for relation labels | `reports/HERALD_DEC060_FRANCE_RELATION_SIGNAL_AUDIT.md` → `reports/HERALD_DEC066_FINE_GRAIN_THRESHOLD_CALIBRATION.md` |
| Observatory v0.4 → v0.5.1 | Jun 2026 (2026-06-16 → 2026-06-18) | Build the current candidate dashboard on the validated granular evidence | `granular_relation_edges.csv` (20 edges), PT geometry, PT municipal forecast (DEC-068) | Deterministic Python builders, no scientific recomputation | DEC-068 (`OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN`) | **v0.5.1 is current candidate, not final** — never visually validated | `reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md`, `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md` |
| Next work | Jul–Sep 2026 (planned) | Modular map-first dashboard, visual validation, figures, article writing | — | — | Not started | PLANNED | `reports/HERALD_RESEARCH_GANTT.md`, `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md` |

---

## Narrative summary

### Pre-repo / "March" (undocumented)
No commit, report, or decision references March 2026. If real work happened outside this
repository before 2026-04-08, it is not represented here.

### April–May 2026: France prediction foundation
First commits (2026-04-08): data foundation, target/proxy definitions, annual baseline.
France-first scope chosen: **ZE2020** (280 employment zones) as the territorial grain,
**SIDE/SIRENE** establishment-creation data as the target. An architecture search (Phase
2: regime/latent-dim/autoregression variants; Phase 3: Q-tensor/labor-tutor variants) ran
2026-05-12→05-27 and selected **HERALD Q7** (WMAPE 0.0204, 306 ZE, 2021–2025,
rolling-window) — confirmed by Phase 2R. **Caveat that must travel with this number
everywhere it is cited:** PENDING_REAUDIT — the causal audit of `growth_1y/2y` and
`effectifs_lag1` features is not yet formally complete. A first operational dashboard
(`herald_france_final_dashboard.html`) was committed 2026-05-28.

### May–June 2026: Internationalization, LOCO, leakage, harmonization
2026-05-28: Phase 4 internationalization begins. 2026-06-03 (DEC-001): a temporal-leakage
bug in `growth_1y` is found across BE/NL/PT ingestion — all pre-DEC-001 cross-country
results are reclassified LEGACY/LEAKAGE-AFFECTED. DEC-002→DEC-011 (2026-06-04→06-10)
rebuild causal per-country baselines; **persistence confirmed as the best LOCO baseline
for PT/IT/AT, no model promoted** (DEC-006); Austria added as the third Path H country
(DEC-005); target semantics found heterogeneous across FR/NL/BE/PT (DEC-003).

### June 2026: Pruning, rejected graphs, sector precedence, Observatory
Two predictive-graph branches tested and **closed**: P6 Dynamic Dual Economic Graph
(`DUAL_GRAPH_S1_FAIL`, DEC-029, all 7 gates fail) and graph-temporal GConvGRU/EvolveGCN-H
(`S1_FR_FAIL`, DEC-031, indistinguishable from permutation nulls). Italy spatial-lag and
Spatial Durbin also closed (Phase 4P/4Q FAIL). 2026-06-12: **Phase 7 sector precedence**
delivers `SECTOR_PRECEDENCE_PROTOTYPE_READY` (DEC-034), integrated same day into
**Observatory v0.3** (DEC-035/036).

### Current (mid–late June 2026): Granularity, PT municipal, NL proxy blocked, v0.5.1
DEC-060 explains France's single promoted sector pair as a scale effect (280 small ZE →
systematically smaller |β|). DEC-061/062 confirm PT can go municipal, NL cannot (no
gemeente×births×sector table exists). DEC-064 closes **PT Municipal Phase 7** (2
COVID-robust pairs). DEC-065 finds the **NL gemeente proxy structurally invalid** for
relation labels — blocked, NL COROP remains the valid baseline. DEC-066 sets the
fine-grain threshold policy. Observatory v0.4→v0.4.1→v0.5 (rejected UX)→**v0.5.1**
(current candidate, French, 103/103 structural tests pass, never visually validated).

### July–September 2026: Next work (planned, not started)
Modular map-first dashboard redesign, visual (Playwright) validation, figure generation,
methodology/results/discussion writing, final review. See
`reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md` for the
detailed Gantt.

---

## Cross-reference

- Data provenance and granularity detail: `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`
- Methods and architecture: `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md`
- Results, evidence, closed branches: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
- Dashboard and article roadmap: `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md`
- Full decision history: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-068)
- Per-file classification: `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`
