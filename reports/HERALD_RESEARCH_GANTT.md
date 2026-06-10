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
2. **Observable economic graph (G1)** — sector similarity or employment-based, Italy + Portugal
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

> **Context (2026-06-10):** Data inventory partially complete (DEC-012/DEC-013). Sector nucleus confirmed as FR+NL+PT. G0 gate is at 4/10. Phase 1 closes the 6 open items and writes the formal G0 contract.

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 1.1 Map bd_hgnace_r NACE→A10 for FR/NL/PT | 2026-06-11 | 2026-06-12 | — | Sector mapping table | All 9 A10 sectors mapped | Partial coverage | Document gaps; use available sectors |
| 1.2 Write G0 node + edge definition (formal) | 2026-06-11 | 2026-06-13 | 1.1 | `HERALD_G0_FORMAL_CONTRACT.md` § node + edge | territory×sector pair committed; 5 edge layers documented | None | — |
| 1.3 Write G0 null model specification | 2026-06-12 | 2026-06-13 | 1.2 | G0 contract § null | Priority null model list formalized | None | — |
| 1.4 Write G0 falsifiable hypothesis | 2026-06-12 | 2026-06-13 | 1.2 | G0 contract § hypothesis | One testable hypothesis per edge layer | None | — |
| 1.5 Pre-specify stability metrics + acceptance criteria | 2026-06-13 | 2026-06-14 | 1.3, 1.4 | G0 contract § validation | Thresholds written with justification before any experiment | None | — |
| 1.6 Write post-experiment audit plan | 2026-06-14 | 2026-06-14 | 1.5 | G0 contract § audit plan | Checklist of audit steps after G1 experiment | None | — |
| 1.7 G0 gate review (self + supervisor) | 2026-06-14 | 2026-06-16 | 1.2–1.6 | G0 gate at 10/10 | All items checked; supervisor sign-off | Supervisor unavailable | Self-approve with limitations document |
| 1.8 Literature review complete | 2026-06-11 | 2026-06-18 | 0.8 | `HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md` | ≥30 papers in table; refs in bibliography | None | Reduce to 25 if time-constrained |

**Criterion for Phase 1 completion:** G0 gate 10/10 in `HERALD_G0_FORMAL_CONTRACT.md`; supervisor sign-off; literature review done.

---

## Phase 2 — Observable Graph G1 (MVP core)

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 2.1 Build canonical FR/NL/PT sector dataset (territory×sector×year) | W+1 after G0 | W+5 | 1.7 | `data/graphs/sector_panel_fr_nl_pt.csv` | Dataset built, audit pass; masks documented | bd_hgnace_r coverage gaps | Use canonical panels first; bridge with bd_hgnace_r |
| 2.2 Build G1 observable graph (sector similarity + co-presence) | W+5 | W+10 | 2.1 | `data/graphs/g1_observable/` | Graph files generated, audit pass | None | Start with sector distribution similarity (no estimation needed) |
| 2.3 G1 audit: sparsity, components, degree distribution | W+10 | W+12 | 2.2 | `reports/HERALD_G1_GRAPH_AUDIT.md` | Audit document complete, PASS/FAIL | None | — |
| 2.4 G4-lite validation (bootstrap, permutation) | W+12 | W+16 | 2.3 | Stability metrics | Bootstrap Jaccard ≥ 0.5; permutation p ≤ 0.05 per edge | Low T limits bootstrap power | Report with explicit limitation |
| 2.5 Community detection (static baseline) | W+14 | W+18 | 2.3 | Community labels | Louvain or DSBM on average graph | None | Use Louvain first |

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
| 4.4 Dashboard update | W+40 | W+44 | 4.1–4.3 | Updated dashboard | Graph layer integrated with France dashboard | None | Separate static report if dashboard integration blocked |

---

## Phase 5 — Forecast Integration G6 (conditional on G1–G5 + gate)

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 5.1 Pre-register G6 gate | W+44 | W+45 | 4.3 | Pre-registered protocol | Gate document signed before any run | None | — |
| 5.2 G6 graph-augmented forecast experiment | W+45 | W+52 | 5.1 | Results + audit | Rolling-origin WMAPE; permuted-graph control | Graph may not improve WMAPE | Report honestly; graph remains interpretive tool |
| 5.3 G6 audit | W+52 | W+54 | 5.2 | `HERALD_G6_FORECAST_INTEGRATION_AUDIT.md` | Gate pass/fail documented | None | — |

**Phase 5 is OPTIONAL for MVP.** The graph has scientific value as an interpretive tool even if G6 fails.

---

## Phase 6 — Report Writing

| Task | Start | End | Depends | Deliverable | Done when | Risk | Contingency |
|------|-------|-----|---------|-------------|-----------|------|-------------|
| 6.1 Report outline | DATE_LIMITE_A_CONFIRMER − 10w | − 9w | 4.3 | Outline approved | Supervisor sign-off | None | — |
| 6.2 Methods chapter | − 9w | − 7w | 6.1 | Draft chapter | Causal protocol and graph methodology | None | — |
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
| Phase 0: Organisation | In progress | ✅ Required | 1 day |
| Phase 1: G0 + data audit + literature | Not started | ✅ Required | 1–2 weeks |
| Phase 2: G1 observable graph | Not started | ✅ Required | 3–4 weeks |
| Phase 3: G2/G3 dynamic graph | Not started | Optional | 4–6 weeks |
| Phase 4: G5 explanation + visualization | Not started | ✅ Required | 3–4 weeks |
| Phase 5: G6 forecast integration | Not started | Optional | 2–3 weeks |
| Phase 6: Report | Not started | ✅ Required | 10 weeks before deadline |
| Phase 7: Article | Not started | Optional | Parallel with Phase 4+ |

**Total minimum viable timeline (Phases 0+1+2+4+6):** ~20 weeks from today  
**Full timeline (all phases):** ~30+ weeks  
**Critical path:** `0.9 (deadline confirmation) → 1.6 (G0 gate) → 2.4 (G1 validation) → 4.3 (explanation) → 6.8 (report submission)`
