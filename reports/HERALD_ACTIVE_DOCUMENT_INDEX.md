# HERALD Active Document Index
**Updated:** 2026-06-12
**Rule:** Documents not listed here should be treated as historical/archived unless explicitly referenced by an active decision.

---

## Source of Truth Documents (read first)

| Document | Purpose | Status |
|----------|---------|--------|
| `CODEX_MEMORY.md` | Session handoff; points to all key documents | ACTIVE |
| `reports/HERALD_PROJECT_CHARTER.md` | Official direction, scope, permitted/forbidden claims | ACTIVE |
| `reports/HERALD_CURRENT_STATE.md` | State per component, blockers, next step | ACTIVE |
| `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` | All decisions DEC-001→DEC-031 | ACTIVE |
| `reports/HERALD_EVIDENCE_MATRIX.md` | All claims and their evidentiary status (32 claims) | ACTIVE |
| `reports/HERALD_RESEARCH_GANTT.md` | Timeline and task dependencies | ACTIVE |
| `hpc/HPC_PHASE_INDEX.md` | HPC phase registry and status | ACTIVE |
| `hpc/hpc_phase_registry.json` | Machine-readable HPC registry | ACTIVE |
| `reports/herald_artifact_registry.json` | Artefact manifest with status and claims | ACTIVE |

---

## Active Scientific Reports

### France / Phase 2–3
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md` | Q7 selection, WMAPE 0.0204 France | ACTIVE |
| `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` | France confirmatory result | ACTIVE |

### International Harmonization / Phase 4
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_PHASE4N_RESULTS_AUDIT.md` | LOCO baseline PT/IT/AT | ACTIVE |
| `reports/HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Spatial autocorrelation diagnostics | ACTIVE |
| `reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md` | Italy spatial lag FAIL | ACTIVE (closed branch) |
| `reports/HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md` | Italy Spatial Durbin FAIL | ACTIVE (closed branch) |
| `reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` | Target heterogeneity audit | ACTIVE |
| `reports/HERALD_PHASE4M_PT_IT_AT_PANEL_AUDIT.md` | PT/IT/AT harmonized panel | ACTIVE |
| `reports/HERALD_PHASE4M_COMMON_FEATURE_CONTRACT.md` | Feature contract LOCO | ACTIVE |
| `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md` | Causal baseline per country | ACTIVE |
| `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md` | Leakage audit 4A/4D | ACTIVE (historical reference) |
| `reports/HERALD_LEAK_AUDIT_FINAL_20260507.md` | Integrity audit | ACTIVE |

### Dynamic Economic Graph / Phase 5–6
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_G0_FORMAL_CONTRACT.md` | G0 conceptual contract (10/10) | ACTIVE |
| `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md` | G1-L2 PASS (DEC-019/020) | ACTIVE |
| `reports/HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md` | G2 dynamics descriptive (DEC-025) | ACTIVE |
| `reports/HERALD_G2_COVID_SENSITIVITY_AUDIT.md` | G2 COVID sensitivity (DEC-024d) | ACTIVE |
| `reports/HERALD_G1_COMMUNITIES_AUDIT.md` | Community detection NOT_SUPPORTED | ACTIVE (closed branch) |
| `reports/HERALD_PHASE5_HPC_SPEC.md` | Phase 5 NOT_SUPPORTED (DEC-023) | ACTIVE (closed branch) |
| `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md` | P6 FAIL results summary | ACTIVE (closed branch) |
| `reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` | P6 FAIL full audit (DEC-029) | ACTIVE (closed branch) |
| `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` | G0→G6 roadmap | ACTIVE |

### Graph-Temporal Architecture
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md` | A1 contract FROZEN (DEC-028) | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md` | E0-v2 PASS, schema 2.0 (DEC-028) | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` | FR adjacency READY (DEC-028) | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md` | DEC-027 preflight decision | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` | S1_FR_FAIL (DEC-031) — GConvGRU/EvolveGCN-H fail frozen gate | ACTIVE (closed branch) |

### Economic Observatory
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_OBSERVATORY_V01_DATA_CONTRACT.md` | Aggregate v0.1.1 + sector v0.2 contract, evidence separation and causal guarantees (DEC-032) | ACTIVE |

### Bibliography
| Document | Covers | Status |
|----------|--------|--------|
| `reports/bibliography/HERALD_REFERENCES_MASTER.md` | 25 master references | ACTIVE |
| `reports/bibliography/herald_references.bib` | BibTeX (Friedman 2008 verified) | ACTIVE |
| `reports/bibliography/HERALD_REFERENCE_AUDIT.csv` | Reference audit | ACTIVE |

### Dashboard
| Document | Covers | Status |
|----------|--------|--------|
| `reports/dashboards/herald_france_final_dashboard.html` | France operational dashboard | ACTIVE — do not modify without explicit decision |

---

## Historical / Archived Documents

The following documents are retained for audit trail but are superseded for active decision-making. They must not be cited as current results.

### Superseded by later phases
| Document | Superseded by |
|----------|--------------|
| `reports/HERALD_PHASE4H_B_RESULTS_AUDIT.md` | Phase 4N (corrected causal baseline) |
| `reports/HERALD_PHASE4I_A_RESULTS_AUDIT.md` | Phase 4N |
| `reports/HERALD_PHASE4J_A_FORECAST_COMBINATION_AUDIT.md` | Not promoted (DEC-004) |
| `reports/HERALD_PHASE4G_*.md` | Superseded by 4H–4J |
| `reports/HERALD_PHASE4E_C_*.md` | Superseded by 4N |
| `reports/HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` | Schema 1.0 — superseded by schema 2.0 (DEC-028) |
| `reports/HERALD_G2_PREFLIGHT.md` | Superseded by full corrected controls audit |
| `reports/HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md` | Partially superseded by L2/L3 specific audits |
| `reports/HERALD_G1_L1_SECTOR_GRAPH_AUDIT.md` | G1-L1 NOT_SUPPORTED (DEC-017); historical |
| `reports/HERALD_PHASE4D_DATA_AND_GRAPH_AUDIT.md` | Leaky (Phase 4A/4D affected) |
| All `reports/HERALD_PHASE2*.md` (except 2R) | Exploratory architecture search history |
| All `reports/HERALD_PHASE3*.md` (except 3E) | Steps toward 3E |

### Legacy (pre-2026 or v3/v4/v5)
- `reports/archive/herald_v4/`, `reports/archive/herald_v5/` — archived
- `reports/ATLAS_IAT_*.md` — pre-HERALD project, historical only

### Documents with P6 / A1 language (status corrected by DEC-029/030/031)
- Any document referencing "P6 pending" must be read in light of DEC-029 (P6 FAIL).
- Any document referencing "S1-FR BLOCKED" or "A1 pending implementation" must be read in light of DEC-031 (S1_FR_FAIL; branch closed).

---

## P6 Sector Label Status

`data/processed/dual_graph_s1/learned_sector_edges.csv` uses sector names (AZ, BE, C, DE, GI, JZ, KZ, LZ, MN) that do not match tensor sector_ids (BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU). Source of mapping unverifiable.

**Status: INVALID_FOR_INTERPRETATION.** Preserved as historical artefact. Index-based gate metrics remain valid.

---

## WMAPE 0.0204 France — PENDING_REAUDIT

The French WMAPE 0.0204 (HERALD Q7, Phase 3E) uses French SIDE/SIRENE data. **Status: PENDING_REAUDIT.** The causal audit of the full Phase 3E/2R pipeline features (`growth_1y/2y`, `effectifs_lag1`) is not yet formally complete for the French track. This result must not be cited as a headline claim until the audit is done. Scope limitation still applies: France only, 2021–2025, rolling-window.

---

## File Naming Policy

Active documents: `reports/HERALD_*.md`
Archived documents: `reports/archive/<phase>/` or marked SUPERSEDED in this index.
Do not create new Phase-N reports without a corresponding DEC-* entry.
