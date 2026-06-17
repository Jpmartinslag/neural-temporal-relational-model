# HERALD Current State
**Updated:** 2026-06-17 (DEC-065 CONSOLIDATED — NL_GEMEENTE_PROXY_PHASE7_BLOCKED, all 121 proxy edges INVALID_FOR_TRAINING_LABELS, NL COROP VALID_OBSERVED preserved. New `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md` + Observatory v0.4 granular contract/exports ready: GRANULAR_OBSERVATORY_V04_DATA_READY, 159/159 tests PASS. DEC-066 COMPLETE — FINE_GRAIN_THRESHOLD_POLICY_READY. DEC-064: PT_MUNICIPAL_PHASE7_COMPLETE, 2 COVID-robust pairs. DEC-063: GRANULAR_FR_PT_NL_PREFLIGHT_READY.)
**Source of truth:** `HERALD_PROJECT_CHARTER.md`, `HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-049), `HERALD_EVIDENCE_MATRIX.md`.

---

## Overall Completion

| Layer | Completion | Notes |
|-------|-----------|-------|
| Data | **87%** | PT/IT/AT harmonized; FR/NL/BE complete; European preflight DEC-038 complete; FI eligible, ES/IT/DE eligible with download |
| Quantitative forecasting | **75%** | Ridge+persistence validated; conformal intervals exploratory |
| Territorial graph (G1-L2) | **75%** | FR/NL/PT PASS; community detection NOT_SUPPORTED |
| Aggregate dynamics (G2) | **75%** | FR robust; NL/PT COVID-sensitive |
| Economic states | **60%** | Deterministic observed states exported for aggregate PT/IT/AT and sector FR/NL/PT |
| Sector→sector graph | **90%** | SECTOR_PRECEDENCE_PROTOTYPE_READY: 12 COVID-robust edges (NL=3, PT=9); integrated in Observatory v0.3 (DEC-034/035) |
| Explanation | **30%** | Descriptive co-growth associations; no attention/associative explanation validated |
| Dashboard | **85%** | Observatory v0.3: choropleth map + sector graph + economic states + territory heatmaps + Phase 8 territorial contribution layer (Section 6, toggle, divergent scale); 14,095 KB self-contained (DEC-036/037) |
| Recommendation | **35%** | Intelligence layer structure exists; weights/claims not validated |
| Territorial movement attribution | **55%** | Phase 8 DESCRIPTIVE_ONLY: 91 HIGH + 78 MODERATE + 8 LOW DESCRIPTIVE territories localised per ROBUST relation; integrated in dashboard; no causal claim (DEC-037 + addendum) |
| **Integrated prototype** | **~82%** | Sector→sector layer validated; territorial attribution descriptive layer added; explanation and recommendation remain |
| **European product** | **~40%** | Multi-country sector observations integrated; influence and recommendation layers remain |

---

## State by Component

### Bloco 1 — Temporal Forecasting

| Country | Best model | WMAPE | Status |
|---------|-----------|-------|--------|
| France | HERALD Q7 | 0.0204 (2021–2025) | PENDING_REAUDIT — potential pre-causal growth feature dependency; not headline-ready |
| PT/IT/AT balanced | Persistence | ~0.0874 | VALIDATED |
| NL | Persistence | LOCO result | VALIDATED |
| BE | Persistence (Phase 4E-B b3) | 0.1488 | VALIDATED |
| Cross-country combination | 50/50 persistence+Ridge | 0.0871 | EXPLORATORY, not promoted |

**Last valid decision:** DEC-006 (Phase 4N persistence baseline); DEC-010 (Phase 4P spatial lag FAIL); DEC-011 (Phase 4Q Spatial Durbin FAIL).
**Blocker:** Conformal intervals are exploratory; no promoted interval method.
**Next step:** Observatory v0.3 complete (DEC-035). Immediate next step: extend sector panel to AT/BE; refine explanation layer; report writing.

### Bloco 2 — Dynamic Economic Graph

#### G1-L2 Co-growth (territorial)
- **Status:** PASS for FR/NL/PT (DEC-019, DEC-020).
- **Scope:** Dense weight field within each sector; statistical co-movement association.
- **Forbidden:** Individual edge claims; causal interpretation; Louvain communities.
- **Artefact:** `data/processed/economic_graph/g1_l2_cogrowth/`

#### G2 Aggregate Dynamics (territorial co-growth temporal evolution)
- **Status:** G-14 SUPPORTED (descriptive); G-13 PARTIALLY_SUPPORTED (aggregate coherence FR-robust only).
- **Scope:** FR aggregate temporal signal robust. NL/PT COVID-sensitive.
- **Forbidden:** Individual edge stability; cross-country pooling; causal attribution.
- **Artefact:** `data/processed/economic_graph/g2_preflight/`

#### G1-L3 Territory-structure projection
- **Status:** PASS for FR/NL (DEC-016). PT excluded (KZ definitional exclusion, DEC-018).

#### G1-L1 RCA co-specialization
- **Status:** NOT_SUPPORTED (NL pass, FR fail — DEC-017).

#### Phase 5 fixed-L2 corrector
- **Status:** NOT_SUPPORTED (DEC-023). Closed.

#### P6_DDEG_S1 Dynamic dual graph
- **Status:** DUAL_GRAPH_S1_FAIL (DEC-029). All 7 gate criteria fail. Closed.
- **Sector edge labels:** INVALID_FOR_INTERPRETATION (wrong mapping in CSV, see Charter §6).
- **Index-based metrics** (MAE, Jaccard) remain numerically valid.
- **Artefact:** `data/processed/dual_graph_s1/` (frozen, historical only).

#### Graph-temporal tensors (schema 2.0 / A1 contract)
- **Status:** S1_FR_FAIL (DEC-031). GConvGRU and EvolveGCN-H both fail all 5 frozen gate criteria. Mean WMAPE: Ridge 0.06486, GConvGRU 0.06492, EvolveGCN-H 0.06497. Both models indistinguishable from temporal and territory permutation nulls (p=1.0 for GConvGRU). Leakage/seed-stability checks pass.
- **Branch status:** Graph-temporal prediction branch CLOSED. No HPC authorized. Non-graph frugal improvements (Bloco 1) and descriptive graph (Bloco 2) remain valid. Observatory v0.1 proceeds without graph-temporal correction.
- **Artefacts:** `data/processed/graph_temporal_v2/` (schema 2.0 tensors, ACTIVE); `data/processed/graph_temporal_s1/` (S1 results, FROZEN/FAIL, DEC-031)

### Bloco 3 — Economic Recommendation
- **Status:** NOT STARTED. Requires Bloco 1 + Bloco 2 complete.
- **Intelligence layer structure** exists from earlier work. Weights not validated. Rankings are hypotheses.

---

## Data Assets

| Panel | Path | Status | Rows |
|-------|------|--------|------|
| FR NUTS3 sector panel | `data/processed/economic_graph/sector_panel_fr_nuts3.csv` | ACTIVE | — |
| FR/NL/PT sector panel | `data/processed/economic_graph/sector_panel_fr_nl_pt.csv` | ACTIVE | 45 945 |
| Observatory aggregate v0.1.1 | `data/processed/herald_observatory_v01/` | ACTIVE/REGENERABLE | 1 963 |
| Observatory sector v0.2 | `data/processed/herald_observatory_v02/` | ACTIVE/REGENERABLE | 45 945 |
| PT/IT/AT harmonized LOCO | `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv` | ACTIVE | 1 963 |
| PT/IT panel (pre-AT) | `data/processed/european_panel/enterprise_birth_pt_it_panel.csv` | SUPERSEDED by AT panel | — |
| G1-L2 co-growth artefacts | `data/processed/economic_graph/g1_l2_cogrowth/` | ACTIVE (analytical) | — |
| G2 preflight artefacts | `data/processed/economic_graph/g2_preflight/` | ACTIVE (analytical) | — |
| Graph-temporal v2 tensors | `data/processed/graph_temporal_v2/` | ACTIVE (A1 blocked) | — |
| Dual graph S1 artefacts | `data/processed/dual_graph_s1/` | FROZEN/FAIL historical | — |

---

## Blocked Items

| Item | Blocker | Reopen condition |
|------|---------|-----------------|
| HPC new submission | S1_FR_FAIL (DEC-031) — graph-temporal branch closed | New information hypothesis + new DEC-* required |
| Sector→sector graph | Full 999-permutation/500-bootstrap run pending | Execute DEC-033 contract, then audit before visualization |
| Recommendation layer | Bloco 1 + Bloco 2 complete | — |
| New GNN architecture | Integrated prototype complete | New hypothesis + new data |
| Conformal intervals | Method selection | Choose between conformal or bootstrap |
| Phase 9 HPC full run | Smoke PASS (DEC-039) — full benchmark script not yet written | Implement run_full_benchmark.py, review, authorise |

---

## Phase 9 — Synthetic Benchmark (DEC-039)

**Status:** SMOKE PASS (2026-06-13). Architecture validated.

- Generator: 10T × 5S × 12Y synthetic economic panel with ground truth relations, crises, structural breaks, MCAR/MAR/block missing patterns
- Baselines B1–B8 implemented and tested
- Temporal features: strictly causal (no future leakage, verified)
- Smoke: 2 seeds, MCAR 20%, 100 epochs → 1.7s, no NaN, leakage PASS
- G1/G3 gates NOT yet evaluable at smoke scale (require full HPC run, not yet authorised)

**Next:** Implement `run_full_benchmark.py`; authorise HPC after review.

---

## DEC-066 — Fine-Grain Threshold Calibration (2026-06-16)

**Status:** `FINE_GRAIN_THRESHOLD_POLICY_READY`. 10/10 gates PASS. 43/43 tests PASS.

- **Original threshold 0.10 (ROBUST_ORIGINAL):** unchanged — pre-registered DEC-034/DEC-064.
- **Supplementary threshold 0.09 (FINE_GRAIN_SUPPORTED):** adopted. Requires bss≥0.80 PLUS one of: (a) COVID-robust; (b) ≥2 consecutive windows same sign; (c) cross-country replication.
- **EXPLORATORY_FINE_GRAIN (0.07-0.09, bss≥0.90):** documented, NOT a training label.
- Ecological scale effect confirmed: PT NUTS3 max|β|=0.362 → NL COROP 0.285 → FR/PT_MUNI ≈0.10-0.13.
- NL proxy (DEC-065) may now proceed under this policy. KZ→FZ FR cannot transfer to PT labels.

**Label counts:** FR=1 ROBUST + 3 FINE_GRAIN + 5 EXPLORATORY; NL=8 ROBUST; PT_NUTS3=16 ROBUST; PT_MUNI=2 ROBUST + 1 EXPLORATORY.

**Policy:** `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json`

**Next:** DEC-065 (NL gemeente proxy, now authorised); DEC-067 (FR/PT label export).

---

## DEC-065 — NL Gemeente Proxy Phase 7 (2026-06-17)

**Status:** `NL_GEMEENTE_PROXY_PHASE7_BLOCKED` (manual override). 71/71 tests PASS. HPC job 7475756 (252/252 complete).

- **Automated gate-count verdict would have been `SUPPORTED`** (121 promoted, 97 nominally COVID-robust, 7/8 COROP pairs preserved) — but this is overridden.
- **Critical structural finding:** DEC-063 proxy method (`estimated_births_gemeente = corop_births × stock_share`) injects cross-sector-correlated noise unrelated to births precedence. Decomposition: `share_velocity` coefficient (13.0) ~10x larger than `corop_velocity` coefficient (1.33), R²=0.635. `share_velocity` cross-sector correlation 0.34-0.82 (general local stock co-movement, e.g. gentrification — not births dynamics).
- This explains the implausible 15x jump in promoted edges (8 COROP observed → 121 gemeente proxy), opposite of the ecological-fragmentation pattern (finer units → fewer effects) confirmed in DEC-064/066.
- **None of the 121 promoted/97 COVID-robust gemeente edges may be used as DEC-066 training labels under any tier.**
- NL COROP (8 promoted, 3 COVID-robust, observed) remains the valid NL baseline.

**Artefacts:** `data/processed/phase7_nl_gemeente_proxy/results/` (all_edges.csv, decision.json, structural_validity_diagnostic.json), `nl_corop_vs_gemeente_proxy_comparison.csv`, `nl_gemeente_proxy_label_summary.json`

**Full audit:** `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md`

**Consolidation (2026-06-17):** All 121 gemeente proxy edges explicitly marked
`INVALID_FOR_TRAINING_LABELS` (label_class=`BLOCKED_PROXY_ARTIFACT`,
`allowed_for_training_label=false`). Artifact registry adds explicit
`NL_GEMEENTE_PROXY_PHASE7_BLOCKED` (status=`BLOCKED`,
relation_label_status=`INVALID_FOR_RELATION_LABELS`) and `NL_COROP_PHASE7`
(status=`VALID_OBSERVED`) entries. New policy document
`reports/HERALD_GRANULAR_EVIDENCE_POLICY.md` defines observed vs proxy evidence
boundaries, label classes (`ROBUST_ORIGINAL`/`FINE_GRAIN_SUPPORTED`/
`EXPLORATORY_FINE_GRAIN`/`BLOCKED_PROXY_ARTIFACT`/`INSUFFICIENT_EVIDENCE`), and
language rules. Observatory v0.4 granular contract
(`reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md`, 4 layers) + clean exports
in `data/processed/herald_observatory_v04_granular/`:
- `granular_territory_state_panel.csv` (142,650 rows: FR ZE2020 + PT Municipal +
  NL COROP observed + NL gemeente proxy tagged `allowed_use=territory_state_context_only`)
- `granular_relation_edges.csv` (20 rows: FR=9, NL COROP=8, PT Municipal=3 — NL
  gemeente proxy structurally excluded)
- `blocked_proxy_edges.csv` (121 rows, `BLOCKED_PROXY_ARTIFACT`)
- `manifest.json` (checksums, DEC references, hard rules)

159/159 tests pass (71 DEC-065 + 45 `test_observatory_v04_granular_evidence_policy.py`
+ 43 DEC-066). **Decision: `GRANULAR_OBSERVATORY_V04_DATA_READY`** — data layer
complete and tested; dashboard build is a separate, larger task not yet authorised.

**Next:** DEC-065b (proposed) — re-specify gemeente regression with COROP-clustered SEs or COROP×year FE before re-testing. DEC-068 (cross-country granular training) must exclude NL gemeente proxy edges, limit NL contribution to COROP scale. DEC-067 (FR/PT label export, unaffected by this finding) remains open. Observatory v0.4 dashboard build requires separate authorisation.

---

## Phase 7: DEC-064 — PT Municipal Phase 7 (2026-06-16)

**Status:** `PT_MUNICIPAL_PHASE7_COMPLETE`. 10/10 gates PASS. Job 7472757 (208/208 complete).

- **2 COVID-robust promoted pairs** — both in window 2015-2020 only:
  - GI→OQ: β=+0.130, q_fdr=0.028, bss=1.00, n=1668 (COVID-robust: β_wo2020=+0.108)
  - MN→JZ: β=−0.104, q_fdr=0.037, bss=1.00, n=999 (COVID-robust: β_wo2020=−0.125)
- Both pairs are **period-specific** (2015-2020); no other window produces promotions.
- Ecological fragmentation: NUTS3 max|β|=0.362 vs municipal max|β|=0.130 (smaller units, smaller effects).
- NUTS3 baseline: 0 promoted in all 14 windows. Municipal 278 territories provides 11× statistical power.
- DEC-065 DRAFT preparado: `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_DRAFT.md`.

**Artefacts:** `data/processed/phase7_pt_municipal/results/` (all_edges.csv, latest.csv, covid_robust_edges.csv)

**Next:** DEC-065 (NL gemeente proxy — now authorised, policy DEC-066 in place); DEC-067 (FR/PT label export with fine-grain policy).

---

## Phase 4: DEC-063 — Granular FR/PT/NL Evidence Model (2026-06-16)

**Status:** COMPLETE. Decision: `GRANULAR_FR_PT_NL_PREFLIGHT_READY` — 10/10 gates PASS, 66/66 tests PASS.

- **FR ZE2020 (280 units):** observed_births, SIDRE establishment_creation. READY.
- **PT Municipal (278 units):** observed_births, INE enterprise_birth. KZ structural_absent. READY_WITH_LIMITATION.
- **NL COROP (40 units):** observed_births, CBS 83631NED. KZ present. READY.
- **NL Gemeente proxy (355 units):** proxy_disaggregated_by_stock_share. 73% proxy_computed. Reaggregation exact (max_abs=0.0).
- CBS API 10k-row limit resolved: year-loop strategy (19 calls × 9,177 rows).
- Contract: `reports/HERALD_GRANULAR_FR_PT_NL_TRAINING_CONTRACT.md` — evaluation must report observed-only and proxy-excluded sensitivity separately.

**Next:** HPC authorisation for full run (208 tasks); or await local medium run (~6h). DEC-065 draft prepared (awaiting DEC-064 completion).

---

## Phase 13 — DEC-048 Failure Cause Diagnostic (DEC-048)

**Status:** PILOT_COMPLETE (2026-06-15). Decision: TRAINING_BUDGET_TOO_SMALL.

- OFAT design: 4 axes (D/M/L/S) + functional scenario test + gradient diagnostics + masked pretraining
- 6/10 gates PASS. 21 tests PASS. Runtime: 79s.
- C2 PASS: Oracle beats ffill by 27% in functional scenario (ratio=0.732) — architecture NOT inadequate
- Attention gradient 400x smaller than MLP under NLL — flat gradient landscape for graph learning
- GRAPH_MASKED_MULTITASK pretraining +1.1% MAE benefit vs NO_PRETRAINING (25 datasets, 50 epochs)
- S3 (structural_break_year=8) causes catastrophic degradation (ratio=1.45)
- Package: `src/modeles/synthetic/phase13_diagnostic/`
- Report: `reports/HERALD_DEC048_FAILURE_CAUSE_DIAGNOSTIC.md`

**Next:** DEC-049 — Full-scale pretraining (n_epochs=150, 50 D2 datasets, GRAPH_MASKED_MULTITASK), then rerun DEC-047 few-shot strategies.

---

## Reference Documents

- Direction and claims: `reports/HERALD_PROJECT_CHARTER.md`
- All decisions: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-039)
- Claims classification: `reports/HERALD_EVIDENCE_MATRIX.md`
- Gantt: `reports/HERALD_RESEARCH_GANTT.md`
- HPC registry: `hpc/hpc_phase_registry.json`
- Artefact manifest: `reports/herald_artifact_registry.json`
- Active document index: `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`
