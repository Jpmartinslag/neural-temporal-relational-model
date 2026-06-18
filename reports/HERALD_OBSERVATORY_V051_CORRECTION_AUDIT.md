# HERALD Observatory v0.5.1 — Correction Audit

**Status:** `OBSERVATORY_V051_CORRECTION_IN_PROGRESS` while building; final
adopted decision (2026-06-18 traceability re-audit, see DEC-068 in
`HERALD_METHODOLOGICAL_DECISION_LOG.md`, `CODEX_MEMORY.md`,
`HERALD_CURRENT_STATE.md`): `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN`.
All 103/103 Part N tests pass, but this is the current best-draft candidate,
not a finally-accepted dashboard — it has never been visually validated (no
Playwright/screenshot) and the product owner's own next-step direction was a
modular, map-first redesign.

**Date:** 2026-06-17
**Supersedes (UX/dashboard-readiness decision only):** `OBSERVATORY_V05_NARRATIVE_READY`
→ corrected to `OBSERVATORY_V05_PARTIAL`. No prior scientific/statistical
DEC-0xx conclusion is altered by this document — only the dashboard/UX
readiness claim from the v0.5 milestone is corrected.

**Purpose:** Document, point by point, what the product owner found wrong in
v0.5 and exactly what v0.5.1 changed to fix each point.

---

## 1. Why v0.5 was rejected

v0.5 (`reports/dashboards/herald_observatory_v05_narrative_dashboard.html`,
`src/data/european_panel/build_observatory_v05_narrative_exports.py`,
`build_observatory_v05_narrative_dashboard.py`) passed its own 65/65 tests
but was rejected by the product owner as "a polished MVP" that did not
present HERALD as a complete method. Concretely:

1. The HERALD architecture explanation sat at the *bottom* of the page
   ("How it works", a 5-step row of generic boxes), after the map, the
   prediction table and the relation graph — a reader sees KPI cards and a
   map before any explanation of what HERALD is or how it works.
2. The entire UI was in English.
3. The prediction layer ("Above or below expected?") was a single section
   among several, not visually central, and was not a map view mode for FR
   (only for FR/NL when toggled — but PT had nothing at all).
4. PT had **no integrated forecast** at all, despite the v0.5 prediction-gap
   report (`HERALD_OBSERVATORY_V05_PREDICTION_GAP.md`) explicitly stating
   the gap was closeable with a CPU-only re-run of the existing
   persistence/Ridge code against the PT municipal panel — that re-run was
   never done.
5. There was no true geographic heatmap. The map *was* the only spatial
   visual (an acceptable design choice per the v0.5 brief), but it only had
   3 modes (state/velocity/prediction) and no "intensity"/"concentration"
   layer — i.e. no descriptive territorial-intensity/"bassins" view existed
   at all, only a placeholder string ("Similar dynamics (coming)").
6. The sector→sector graph rendered independently of the map: clicking an
   edge updated only the graph's own side panel (aggregate territory-state
   counts), it never changed what the map displayed (country, year, or
   sector).
7. The KPI bar at the top used generic English labels ("Territories
   observed", "Valid relations", "Blocked relations (audit only)", "Sectors
   tracked") — a generic "AI dashboard" look, not an interpretable
   French-language evidence summary.
8. Technical vocabulary (`beta`, `q_fdr`, `bss`, `evidence_type`,
   `allowed_for_training_label`) appeared inside a `<details>` element, which
   is correct in spirit, but the KPI bar duplicated some evidence counts in
   the *main* (non-collapsible) body, and the wording throughout used
   English technical/causal phrasing ("not proof of causality") directly in
   the main narrative sentence shown for every relation.
9. The "How it works" section was five plain text boxes with no mention of
   the relational/neural candidate layer, no mention of validation
   mechanics (permutation, windows, robustness), and no visual distinction
   between the statistical baseline and the relational layer — it read as
   marketing copy, not a method figure.
10. v0.5 never explicitly distinguished a "neural candidate relation" layer
    from the validated Phase 7 relations — it implicitly implied (by
    omission) that the only relational layer was the validated one, without
    saying so explicitly, and without acknowledging that no neural-candidate
    dataset exists in this repository.

---

## 2. Point-by-point fix in v0.5.1

| # | v0.5 problem | v0.5.1 fix | Where |
|---|---|---|---|
| 1 | Architecture at the bottom | "Méthode HERALD" section is now the **first** content block after the title, before the evidence summary, before the prediction section, before the map | `_html_method_section()` in `build_observatory_v051_narrative_dashboard_template.py`; verified by `TestArchitectureAtTop` (Part N2) |
| 2 | English UI | Every visible string rewritten in French — title, subtitle, section titles, controls, legends, badges, table headers, footnotes | All `_html_*` functions in the template module; verified by `TestFrenchLanguage` (Part N1) |
| 3 | Prediction layer not central | "Prévision locale" is the second section (right after the method diagram), with Observé/Attendu/Écart/État columns; the map gained an "Écart à l'attendu" mode showing the same prediction data spatially, plus the side panel shows observed/expected/difference on click | `_html_prediction_section()`, `showTerritorySidePanel()` predBlock |
| 4 | PT municipal forecast missing | New script `build_pt_municipal_prediction_layer.py` re-runs the same causal persistence/Ridge AR(1) method (verbatim constants `RIDGE_ALPHA=1.0`, `RIDGE_MIN_TRAIN=4`) directly against `data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv` (observed, no proxy). Integrated into the unified `prediction_view.csv` alongside FR/NL. Leakage explicitly asserted in code. | `build_pt_municipal_prediction_layer.py`; `build_pt_municipal_prediction_layer()` in exports; `TestPtMunicipalPredictionIntegrated` (Part N3) |
| 5 | No geographic heatmap | New "Bassins économiques" map mode: territorial intensity score = mean velocity per (country, region, year), converted to a within-country-year quantile, rendered as a 4th choropleth colour mode (continuous quantile scale) | `build_economic_basins()` in exports; `economic_basins.json`; `renderMap()` basins branch in the template JS; `TestEconomicBasinsHeatmap` (Part N11) |
| 6 | Graph isolated from map | Clicking a relation edge now calls `applyGraphFilterToMap(edge)`, which sets the map's country selector to the edge's country and the year slider to the edge's `window_end`, then re-renders the map — a real, traceable wiring, not two independent click handlers | `applyGraphFilterToMap()`, `sector-graph` `plotly_click` handler; `TestGraphMapWiring` (Part N12) |
| 7 | Generic KPI cards | Replaced with a "Résumé d'évidence" — short French sentences ("3 pays comparés", "France et Portugal à granularité fine (…)", "Pays-Bas : relations observées au niveau COROP (…)", counts of validated/rejected relations) instead of bare numeric cards | `_html_evidence_summary()`; `TestFrenchLanguage`/visual review |
| 8 | Technical vocabulary leaking into main body | `beta`/`q_fdr`/`bss` now appear **only** inside the two `<details class="tech">` blocks (verified programmatically: these strings do not occur anywhere in the static HTML before the first `<script>` tag, and the elements that render them in JS are nested inside `<details>`) | `TestTechnicalTermsOnlyInDetails` (Part N10) |
| 9 | "How it works" too shallow | Replaced by the "Méthode HERALD" 6-stage diagram (territorial data → local forecast → economic state → sector relations → evidence level → decision signals) **plus** a 4-component card row (statistical baseline / relational-candidate layer / validation / output) — an article-figure structure, not a marketing strip | `_html_method_section()`; `TestArchitectureAtTop` |
| 10 | No explicit candidate-vs-validated distinction | New "Couche relationnelle" section with its own 5-step diagram (séries sectorielles → représentation relationnelle → candidats → validation → relations affichées) and an explicit French sentence stating no neural-candidate dataset exists in this repository today, and that only validated Phase 7 relations are shown | `_html_relational_layer_section()`; `renderRelationalCounts()` |

---

## 3. What was deliberately NOT changed

- No v0.4/v0.4.1/v0.5 file was modified. `git diff` against those paths is
  empty (verify with `git status` / `git diff --stat -- '*v05_narrative*' '*v04_granular*' '*v041*'`
  before this audit and confirm no changes outside the new v0.5.1 files).
- No scientific number, label, beta/q_fdr/bss value, or DEC-0xx conclusion
  was recomputed or altered. The v0.5.1 exports builder reads the exact same
  `granular_territory_state_panel.csv` / `granular_relation_edges.csv` /
  `blocked_proxy_edges.csv` produced for v0.4, with the same fail-closed
  assertions re-verified (`GEMEENTE_PROXY not in relation_view`,
  `allowed_for_training_label == False` for all blocked edges).
- No neural/candidate-relation dataset was fabricated. The "Couche
  relationnelle" section explicitly states, in French, that this repository
  has no such dataset today, exactly as instructed.

---

## 4. Hard rules re-verified for v0.5.1

- `GEMEENTE_PROXY` absent from `relation_view.csv` and from the embedded
  `RELATION_EDGES` JS blob (20 edges total: FR=9, NL COROP=8, PT
  Municipal=3) — asserted in both the exports and the dashboard builder.
- `blocked_proxy_edges_v04_copy.csv` (121 rows) carries
  `allowed_for_training_label=False` for every row and is rendered only
  inside the "Détails méthodologiques" collapsible panel, framed as
  "audit uniquement", never as a discovery or a validated relation.
- PT/KZ is `structural_absent` everywhere it appears (territory_view,
  sector_view, prediction_view, the PT municipal forecast script itself) —
  never a bare NaN, never an enabled sector-selector option for PT.
- No "causal"/"causes"/"not proof of causality" string appears in the main
  UI body. The one permitted causality statement
  ("Ces relations n'établissent pas de lien de causalité structurelle.") is
  nested inside a `<details class="tech">` block, framed as an explicit
  prohibition, per Part L of the brief.

---

*HERALD Observatory v0.5.1 Correction Audit | 2026-06-17*
