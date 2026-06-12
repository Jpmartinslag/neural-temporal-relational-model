# HERALD — Research Gantt

**Created:** 2026-06-10  
**Current date:** 2026-06-10  
**End date / defence / internship deadline:** `DATE_LIMITE_A_CONFIRMER`  
**Note:** No end date found in project documentation. Confirm with supervisors before fixing milestones.

---

## Methodological Audit — This Document

| Item | Value |
|------|-------|
| Purpose | Realistic planning from current state to report + article |
| Inputs | Phase audit table (Part A); current results (4N/4O/4P/4Q); bibliographic state |
| Constraints | No HPC batteries without pre-registered hypothesis; minimum viable version prioritized |
| Key risk | Unknown final deadline distorts all timeline estimates |
| Mitigation | All milestones relative to confirmed deadline; minimum viable version identified independently |

---

## Minimum Viable Version (MVP)

The MVP must be achievable even if the deadline is tight:

1. **Causal temporal baseline** — persistence + Ridge, rolling-origin, PT/IT/AT harmonized panel ✅ (DONE, Phase 4N)
2. **Observable economic graph (G1)** — sector similarity for FR + NL; PT pending `KZ` audit
3. **Graph validation (G4-lite)** — sparsity, bootstrap stability, permutation test
4. **Interpretive visualizations** — edge evolution, community maps, regime detection
5. **Written report** — scientific framing, honest limitations, no recommendation claim

**NOT in MVP:**
- Learned sparse graph (G2) — if time is short
- Forecast integration (G6) — only if G1–G5 complete
- Multi-country graph — only with new data
- Recommendation prototype — only if scope permits

---

## Phase 0 — Organisation and Freeze (current state)

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 0.1 Read all reports 4M–4Q | 2026-06-10 | 2026-06-10 | — | Context confirmed | All reports read | None | — |
| 0.2 Write decision log | 2026-06-10 | 2026-06-10 | 0.1 | `HERALD_METHODOLOGICAL_DECISION_LOG.md` | All decisions from 4A→4Q recorded | None | — |
| 0.3 Write evidence matrix | 2026-06-10 | 2026-06-10 | 0.1 | `HERALD_EVIDENCE_MATRIX.md` | All claims classified | None | — |
| 0.4 Update README.md | 2026-06-10 | 2026-06-10 | 0.2, 0.3 | Updated README | Superseded claims removed | None | — |
| 0.5 Update CODEX_MEMORY.md | 2026-06-10 | 2026-06-10 | 0.4 | Updated CODEX | Consistent with current state | None | — |
| 0.6 Write graph roadmap | 2026-06-10 | 2026-06-10 | 0.2 | `HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` | G0 gate documented | None | — |
| 0.7 Write Gantt | 2026-06-10 | 2026-06-10 | 0.6 | `HERALD_RESEARCH_GANTT.md` | Realistic plan with DATE_LIMITE_A_CONFIRMER | None | — |
| 0.8 Bibliography base | 2026-06-10 | 2026-06-11 | — | `HERALD_REFERENCES_MASTER.md`, `.bib`, audit CSV | All known references catalogued | None | — |
| 0.9 Confirm deadline | 2026-06-10 | 2026-06-10 | — | Confirmed date in writing | Date received from supervisors | CRITICAL: unknown | Block all downstream milestones until confirmed |

**Phase 0 status:** In progress (2026-06-10)

---

## Phase 1 — G0 Contract and Data Audit

> **Context (2026-06-10):** The intended sector nucleus is FR+NL+PT, but PT is
> temporarily ineligible for nine-sector graph validation because `KZ` is zero
> in every territory/year. The formal G0 contract is complete at 10/10.

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 1.1 Build clean unlagged sector preflight | 2026-06-10 | 2026-06-10 | G0 | `sector_panel_fr_nl_pt.csv` | Agriculture excluded; keys and masks audited | Source mismatch | DONE |
| 1.2 Write G0 node + edge definition (formal) | 2026-06-10 | 2026-06-10 | — | `HERALD_G0_FORMAL_CONTRACT.md` | territory×sector pair committed; 5 edge layers documented | None | DONE |
| 1.3 Write G0 null model specification | 2026-06-10 | 2026-06-10 | 1.2 | G0 contract § null | Priority null model list formalized | None | DONE |
| 1.4 Write G0 falsifiable hypothesis | 2026-06-10 | 2026-06-10 | 1.2 | G0 contract § hypothesis | One testable hypothesis per edge layer | None | DONE |
| 1.5 Pre-specify stability metrics + acceptance criteria | 2026-06-10 | 2026-06-10 | 1.3, 1.4 | G0 contract § validation | Thresholds written with justification before any experiment | None | DONE |
| 1.6 Write post-experiment audit plan | 2026-06-10 | 2026-06-10 | 1.5 | G0 contract § audit plan | Checklist of audit steps after G1 experiment | None | DONE |
| 1.7 G0 gate review | 2026-06-10 | 2026-06-10 | 1.2–1.6 | G0 gate at 10/10 | All items checked | Supervisor review pending | DONE technically; supervisor sign-off pending |
| 1.8 Literature review complete | 2026-06-11 | 2026-06-18 | 0.8 | `HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md` | ≥30 papers in table; refs in bibliography | None | Reduce to 25 if time-constrained |

**Criterion for Phase 1 completion:** G0 gate 10/10 in `HERALD_G0_FORMAL_CONTRACT.md`; supervisor sign-off; literature review done.

---

## Phase 2 — Observable Graph G1 (MVP core)

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 2.1 Build canonical FR/NL/PT sector dataset (territory×sector×year) | 2026-06-10 | 2026-06-10 | 1.7 | `data/processed/economic_graph/sector_panel_fr_nl_pt.csv` | PASS; masks and agriculture policy documented | None | DONE |
| 2.2 Build G1 observable graph (bipartite + sector-structure similarity) | 2026-06-10 | 2026-06-10 | 2.1 | `data/processed/economic_graph/g1_observable/` | Graph files generated | None | DONE |
| 2.3 G1-L3 audit: components, degrees and stability | 2026-06-10 | 2026-06-10 | 2.2 | `reports/HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md` | PASS in FR/NL; PT excluded by coverage gate | PT KZ unresolved | DONE with limitations |
| 2.4 G4-lite validation for L3 (bootstrap, permutation) | 2026-06-10 | 2026-06-10 | 2.3 | Null/FDR/LOYO metrics | 2/2 eligible countries pass; bootstrap stable edges available | Low T remains | DONE with limitations |
| 2.5 Economic-coherence review + L1 sector relatedness | 2026-06-10 | 2026-06-10 | 2.4 | `HERALD_G1_L1_SECTOR_GRAPH_AUDIT.md` | FAIL: NL passes, FR fails, PT ineligible | Stable composition dominates FR nulls | Keep L3 descriptive; do not retune L1 |
| 2.6 Resolve PT KZ source semantics | 2026-06-10 | 2026-06-10 | 2.5 | INE 0009703 audit: K absent in all years (DEC-018) | K is definitional exclusion per Eurostat/OECD convention | Financial sector excluded by INE | PT eligible for L2 with 8 sectors; excluded from 9-sector gate | DONE |
| 2.7 Build and validate L2 causal co-growth | 2026-06-10 | 2026-06-10 | 2.6 | `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`; `data/processed/economic_graph/g1_l2_cogrowth/` | PASS: FR 0.782, NL 0.789, PT 0.778; temporal q=0.005, territory q=0.005, LOYO pass, COVID-robust (DEC-019) | Rolling correlation ≠ causality; MAUP | L4 mobility and L5 geography next | DONE |
| 2.8 Community detection (static baseline) | 2026-06-10 | 2026-06-10 | 2.7 | `reports/HERALD_G1_COMMUNITIES_AUDIT.md`; aggregate community artefacts | FAIL 0/3 under valid temporal/territory nulls and modularity+AMI FDR gate | Louvain communities not distinguishable from nulls | Keep L2 as stable edge layer; do not promote communities | DONE |
| 2.9 COVID sensitivity L2 correction (DEC-020) | 2026-06-10 | 2026-06-10 | 2.7 | Corrected builder; tests pass | Full L2 gate applied; `COVID_ROBUST` | Bootstrap propagates exclusion; eval_year 2020 retained | DEC-020 | DONE |

**W = week when G0 gate is approved (depends on 0.9 deadline confirmation)**

---

## Phase 3 — Dynamic Graph G2/G3 (conditional on data + time)

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 3.1 TVGL / GLASSO on sector-growth panel | W+18 | W+24 | 2.4 | Dynamic precision matrix | TVGL converges; results audited | T≈13 is very short | Strong regularization; explicit limitation |
| 3.2 Temporal community detection | W+22 | W+28 | 3.1 | Community time series | DSBM or spectral temporal clustering | None | Use sliding-window Louvain |
| 3.3 Change-point detection on edge weights | W+24 | W+30 | 3.1 | Break points aligned with known shocks | CUSUM or BOCPD | Few observations per edge | Aggregate to country-sector level |
| 3.4 G3 dynamics characterization | W+28 | W+32 | 3.2, 3.3 | `HERALD_G3_ECONOMIC_DYNAMICS.md` | Growth/crisis/stagnation/recovery patterns labeled | None | — |

**Phase 3 is OPTIONAL for MVP.** If deadline is tight, skip or reduce to 3.1 only.

---

## Phase 4 — Explanation and Visualization G5

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 4.1 Edge ranking and influence maps | W+32 | W+36 | 2.5, 3.2 | Visualizations | Maps interpretable by domain expert | None | — |
| 4.2 Community evolution plots | W+34 | W+38 | 3.2 | Animation or multi-panel plot | Year-by-year community structure visible | None | — |
| 4.3 Correlation with forecast residuals | W+36 | W+40 | 4.1 | `HERALD_G5_EXPLANATION.md` | Association documented; causality NOT claimed | None | — |
| 4.4 Dashboard adaptation (from France base) | W+40 | W+44 | 4.1–4.3 + L1/L2/L3 validated | Adapted `herald_france_final_dashboard.html` — country/sector/year selectors + validated graph layers | Country selector, edge legend, territory click, association≠causality labels | Dashboard complexity unknown until observable layers are finalized | Deliver static multi-panel report if dashboard integration blocked |

---

## Phase 5b-P6 — Dynamic Dual Economic Graph (P6_DDEG_S1) — CLOSED FAIL (2026-06-12)

**Status:** Gate DUAL_GRAPH_S1_FAIL (all 7 criteria fail). Slurm job 7453691, 275/275 complete.
C5_dual MAE 0.1424 vs C1_ridge 0.1242 (+14.6%), vs C2_no_graph 0.1329 (+7.2%). Seed Jaccard 0.3353.
Predictive dual-graph branch CLOSED per contract §9. DEC-029.

| Task | Status | Deliverable |
|------|--------|-------------|
| P6 pilot (5×11×2) | DONE — DUAL_GRAPH_S1_FAIL (6/7) | `data/processed/dual_graph_pilot_all_folds/gate_result.json` |
| P6 full HPC study (5×11×5=275 jobs) | **DONE — DUAL_GRAPH_S1_FAIL (7/7)** | `data/processed/dual_graph_s1/gate_result.json` |
| P6 scientific results report | DONE 2026-06-12 | `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md` |
| P6 final audit | DONE 2026-06-12 | `reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` |

---

## Phase 5 — Forecast Integration G6 — CLOSED NOT_SUPPORTED (2026-06-10)

**Status:** Ablation v3 NL 2021-2023 (5 seeds, widths (2,)(4,)(8,)(16,8)) → NOT_SUPPORTED.
H2-neural best 5.53% vs H0b 3.41%. H2 worse than H1-neural (no graph). DEC-023.
Fixed-L2 residual corrector branch closed. L2 remains validated as analytical graph (G-10).
Ridge AR (H0b) remains best predictive baseline. No HPC submission.

| Task | Start | End | Status | Deliverable | Notes |
|------|-------|-----|--------|-------------|-------|
| 5.1 Pre-register G6 gate | 2026-06-10 | 2026-06-10 | DONE | `HERALD_PHASE5_HPC_SPEC.md` | Gate pre-registered |
| 5.2 G6 fixed-L2 corrector | 2026-06-10 | 2026-06-10 | **CLOSED** | Ablation v3 results | NOT_SUPPORTED — G-12 |
| 5.3 G6 audit | 2026-06-10 | 2026-06-10 | **CLOSED** | DEC-023 in decision log | HPC not submitted |

## Phase 5b — Bloco 2 Descritivo: G2 Temporal Graph Dynamics

Separate from forecast utility. L2 graph as analytical tool for characterising sector-territory
economic relations, their evolution, and temporal patterns. NOT forecast improvement.

| Task | Status | Deliverable |
|------|--------|-------------|
| G2 Preflight: inventory, density, persistence, turnover, sensitivity | DONE 2026-06-10 | `HERALD_G2_PREFLIGHT.md` |
| G2 Negative control: 199 temporal permutations, BH/FDR, gate | SUPERSEDED — prior control permuted pre-computed weights (invalid); corrected control pending (`build_g2_corrected_controls.py`) | `HERALD_G2_PREFLIGHT.md` §7 (DEC-024b/c) |
| G2 Corrected controls: N1+N2 from source series, M1/M2/M3, gate | DONE 2026-06-11 — edge stability NOT_SUPPORTED; aggregate result requires COVID sensitivity interpretation | `build_g2_corrected_controls.py`; DEC-024c/d; `g2_corrected_controls*.csv` |
| G2 COVID sensitivity | DONE 2026-06-11 — FR robust; NL/PT sensitive; no robust two-country replication | `HERALD_G2_COVID_SENSITIVITY_AUDIT.md`; DEC-024d |
| G2 Main: aggregate variation, period comparisons, sector patterns | DONE 2026-06-11 — descriptive rolling-window analysis; FR stable, NL/PT modest variation, PT largest Δweight. 45 tests pass. DEC-025. | `HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md`; `build_g2_aggregate_dynamics.py`; `g2_dynamics/` |
| G2 Evidence: G-13 PARTIALLY_SUPPORTED (DEC-024c); G-14 SUPPORTED as a descriptive computed statement (DEC-025) | DONE 2026-06-11 | Evidence matrix G-13, G-14 |

### Graph-temporal architecture preflight

| Task | Status | Deliverable |
|------|--------|-------------|
| Literature and EconoGNN audit | DONE 2026-06-11 | 20-method matrix + 22-source audited bibliography |
| Same-target architecture decision | DONE 2026-06-11 | DEC-027; A0 Ridge, A1a GConvGRU, A1b EvolveGCN-H |
| E0 schema 1.0 tensor preflight | DONE 2026-06-11 — reclassified `E0_STATIC_SNAPSHOT_PASS` (DEC-028) | `HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` |
| E0-v2 schema 2.0 smoke (NL, 3 folds) | DONE 2026-06-11 — **`E0_V2_PASS`**: 13.92s, 0.035 GB RSS, 57/57 tests (DEC-028) | `reports/HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md` |
| FR adjacency audit (5 eval years, schema 2.0) | DONE 2026-06-11 — **`FR_ADJACENCY_READY`**: 280 ZE, 0 isolated @k=3/5/10, all 8 criteria pass | `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` |
| A1 implementation contract | DONE 2026-06-11 — **FROZEN** (DEC-028): interface, rules, A0/A1a/A1b specs, 11 mandatory tests | `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md` |
| GConvGRU A1a + EvolveGCN-H A1b + A0-neural | DONE 2026-06-12 — implemented (DEC-031) | `src/modeles/graph_temporal_models.py`, `tests/test_graph_temporal_a1.py` |
| FR scientific local test (S1-FR) | **DONE 2026-06-12 — S1_FR_FAIL (DEC-031)** — GConvGRU/EvolveGCN-H fail all 5 criteria | `data/processed/graph_temporal_s1/s1_fr_results.json`; `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` |
| HPC confirmatory battery | NOT AUTHORIZED — S1_FR_FAIL closes prediction branch (DEC-031) | New information hypothesis + new DEC-* required |

---

## Phase 6 — Report Writing

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 6.1 Report outline | DATE_LIMITE_A_CONFIRMER − 10w | − 9w | 4.3 | Outline approved | Supervisor sign-off | None | — |
| 6.2 Methods chapter | − 9w | − 7w | 6.1 | Draft chapter | Causal protocol and graph methodology | None | — |
| 6.2b G2 Dynamics section | DRAFT 2026-06-11 | — | — | `HERALD_G2_REPORT_SECTION_FR.md` | Draft written in French | None | — |
| 6.3 Results chapter | − 7w | − 5w | 6.2, all experiments | Draft chapter | Phase 4N/4O/G1/G4 results | Missing results | Describe planned experiments explicitly |
| 6.4 Discussion / limitations | − 5w | − 4w | 6.3 | Draft chapter | Honest limitations, permitted claims | None | — |
| 6.5 Introduction / abstract | − 4w | − 3w | 6.4 | Draft chapter | Scientific problem framed correctly | None | — |
| 6.6 Supervisor review round 1 | − 3w | − 2w | 6.5 | Annotated draft | All corrections received | Supervisor delay | Start 1 week early |
| 6.7 Corrections | − 2w | − 1.5w | 6.6 | Revised draft | All high-severity issues fixed | None | — |
| 6.8 Final submission | − 1.5w | DATE_LIMITE_A_CONFIRMER | 6.7 | Final report | Submitted | Formatting issues | Reserve 2 days buffer |

---

## Phase 7 — Article Writing (parallel, from Phase 4 onward)

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 7.1 Target venue selection | W+36 | W+38 | 4.3 | Target journal/conference confirmed | Venue + deadline known | None | — |
| 7.2 Article outline | W+38 | W+40 | 7.1 | Outline | Supervisor approval | None | — |
| 7.3 Methods + results draft | W+40 | W+50 | 5.3 or 4.3 | Draft article | All sections drafted | None | — |
| 7.4 Internal review | W+50 | W+52 | 7.3 | Reviewed draft | Co-author feedback incorporated | None | — |
| 7.5 Submission | Per venue deadline | Per venue deadline | 7.4 | Submitted article | Receipt confirmed | Venue delay | Target backup venue |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Deadline unknown (DATE_LIMITE_A_CONFIRMER) | High | Critical | Confirm in 24h; block Phase 1+ until confirmed |
| Italy NUTS3 sector data incomplete | High | High | Use commuting or country-level I-O; document restriction |
| T≈13 too short for TVGL/GLASSO | Medium | High | Strong regularization; explicit limitation in paper |
| G0 gate rejected by supervisor | Low | Medium | Re-specify; do not bypass gate |
| G6 graph integration fails WMAPE gate | Medium | Low | Graph remains interpretive tool; honest reporting |
| Benchmark HPC jobs exceed time | Low | Medium | Run local first; HPC only if local passes smoke test |
| Missing post-2020 data | Medium | Medium | Plan with 2008–2020; note limitation |
| Granger edges misinterpreted as causal | High | High | Explicit labeling in all outputs; prohibited claims documented |

---

## Summary Table

| Block | Status | MVP | Duration estimate |
|-------|--------|-----|------------------|
| Phase 0: Organisation | 8/9 complete; deadline confirmation pending | ✅ Required | 1 day |
| Phase 1: G0 + data audit + literature | Technically complete; supervisor sign-off pending | ✅ Required | Complete |
| Phase 2: G1 observable graph | In progress (L3 FR/NL PASS; L1 FAIL; L2 FR/NL/PT PASS) | ✅ Required | Community detection baseline (2.8) remaining |
| Phase 3: G2/G3 dynamic graph | G2 descriptive complete; edge stability not supported; G3 not started | Optional | Remaining scope depends on report deadline |
| Phase 4: G5 explanation + visualization | Not started | ✅ Required | 3–4 weeks |
| Phase 5: G6 forecast integration | Fixed-L2 corrector closed NOT_SUPPORTED; DEC-027 preflight only | Optional | Local E0/S1 gates before any HPC |
| Phase 6: Report | Not started | ✅ Required | 10 weeks before deadline |
| Phase 7: Article | Not started | Optional | Parallel with Phase 4+ |

**Total minimum viable timeline (Phases 0+1+2+4+6):** ~20 weeks from today  
**Full timeline (all phases):** ~30+ weeks  
**Critical path:** `0.9 (deadline confirmation) → 1.6 (G0 gate) → 2.4
(L1/L2/L3 validation) → 4.3 (explanation) → 6.8 (report submission)`

### Progress estimate

Planning estimate, not an empirical metric:

- Integrated Observatory prototype: approximately **70% complete**.
- Full product through economic recommendation: approximately **40% complete**.

Completed: temporal baselines, G0, sector preflight, G1-L3, G1-L1, PT KZ audit,
G1-L2 and G4-lite validation, aggregate Observatory v0.1.1 and sector
Observatory v0.2. Community and predictive graph branches were tested and
rejected. Remaining prototype work: signed lagged sector association layer,
bounded visualization/explanation, uncertainty intervals and report completion.
