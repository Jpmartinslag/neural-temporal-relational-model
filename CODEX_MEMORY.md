# HERALD Codex Memory

## ENTRY POINT — read this block first (2026-06-18 consolidation/freeze)

**Status (10-15 lines):** Repo just went through an Observatory dashboard cycle
ending at v0.5.1. v0.4/v0.4.1 are stable, scientifically valid, historical
dashboards (still pass 192/192 tests). v0.5 was rejected by the product owner
as a "polished MVP" — its readiness decision is corrected
`OBSERVATORY_V05_NARRATIVE_READY` → `OBSERVATORY_V05_PARTIAL` (DEC-067/068);
the v0.5 files remain untouched and their 65/65 tests still pass, but it is
NOT the current dashboard. v0.5.1 (`herald_observatory_v051_narrative_dashboard.html`,
103/103 tests pass, re-verified 2026-06-18) is the CURRENT dashboard:
French UI, architecture-first layout, FR+NL+PT prediction (PT closed via a
direct causal persistence/Ridge re-run on the observed PT municipal panel, no
proxy, no HPC), real geographic heatmap, graph wired to the map. **None of
v0.4.1/v0.5/v0.5.1's files are committed to git yet** — all still untracked
working-tree files as of this consolidation. Many unrelated parallel
workstreams (Italy/Austria/Belgium/Netherlands ingestion, economic_graph
tensors, dual_graph experiments, synthetic_benchmark phases) are also dirty
in the working tree — NOT part of this consolidation, not touched here.

**Authorized next steps:**
- Commit/push the Observatory v0.4.1/v0.5/v0.5.1 files (a separate session will do this).
- Modularize the next dashboard iteration, **starting with the map** (product
  owner's signaled direction — not yet implemented, no code written for this yet).
- Visual validation of v0.5.1 with Playwright once available in-environment.
- Extend PT municipal prediction validation; close out remaining July/August
  Gantt items (see `reports/HERALD_RESEARCH_GANTT.md`).
- Fix the artifact-registry schema drift documented below (6 pre-existing
  test failures in `tests/test_herald_artifact_registry.py` — entries added
  since DEC-038 lack `path`/`type`/`status`/`tracked_in_git`/`can_regenerate`).

**Forbidden next steps:**
- Do NOT relaunch any HPC job (no new DEC-* authorizes one; graph-temporal,
  P6 dual-graph, and geographic-graph branches remain CLOSED).
- Do NOT reopen any closed/frozen branch (S1_FR_FAIL, DUAL_GRAPH_S1_FAIL,
  Phase 4P/4Q geographic branch, Phase 5 fixed-L2 corrector) without a new
  DEC-* entry with a pre-registered gate.
- Do NOT promote NL gemeente proxy edges to `observed` or to any relation
  training label tier (DEC-065 BLOCKED is final until a corrected
  COROP-clustered-SE/COROP×year-FE proxy specification is validated under a
  new DEC).
- Do NOT fabricate predictions, geometry, or relation edges where none exist
  (PT/KZ stays `structural_absent`; NL gemeente stays context-only).
- Do NOT renumber, delete, or silently overwrite any DEC-* entry — only
  append corrections/superseding notes (see DEC-067→DEC-068 pattern).
- Do NOT claim Observatory v0.5.1 is visually validated — it has only been
  validated structurally (DOM/JS parsing), never with a real screenshot/Playwright.

**Current dashboards and limitations:**
- v0.4 / v0.4.1 (`herald_observatory_v04_granular_dashboard.html`, 10.0 MB) —
  STABLE, HISTORICAL. Scientifically correct, FR/NL COROP/PT Municipal real
  choropleth, dynamic relation graph. No visual/Playwright validation ever done.
- v0.5 (`herald_observatory_v05_narrative_dashboard.html`, 14.8 MB) — SUPERSEDED
  for readiness purposes (English UI, MVP-feel, PT prediction gap, no real
  heatmap). Kept for audit trail; do not present as current.
- v0.5.1 (`herald_observatory_v051_narrative_dashboard.html`, 18.2 MB) —
  CURRENT. French, PT prediction integrated, real heatmap, graph-to-map
  filter wired. Limitation: not committed to git; no Playwright/screenshot
  validation in this environment, only structural (DOM id / embedded JSON /
  handler cross-reference) checks.

**Active data sources:** FR ZE2020 (observed, SIDE/SIRENE), PT Municipal 278
continental municipalities (observed, INE 0009703/0014099), NL COROP 40
regions (observed, CBS 83631NED), NL Gemeente 355 communes (proxy,
context-only, never relation labels — DEC-065 BLOCKED), IT/AT NUTS3
(harmonized Path H, LOCO only, no sector graph).

**Forward-looking decision (not implemented yet):** the product owner has
signaled the next dashboard iteration should be **modular, starting with the
map component**. This is recorded here as direction only — no modularization
code has been written.

**Deadline:** No confirmed internal/thesis deadline found in any document
(`HERALD_RESEARCH_GANTT.md` still says `DATE_LIMITE_A_CONFIRMER` as of its
last edit). Per this consolidation's own planning (see the rebuilt Gantt),
the working target is: June = freeze/organize/modularize-map-start; July =
PT municipal validation/extension + dynamic map + spatial relations +
Playwright validation; August = consolidate results + figures/tables +
methodology writing; early September = final writing/review/submission.
**This is a planning estimate, not a confirmed external deadline** — confirm
with supervisors before treating any of these dates as binding.

**Rule:** Do not reopen closed branches without a new DEC-* entry. Read
`reports/HERALD_PROJECT_CHARTER.md` §7-8 before proposing any direction change.

---

**LEIA PRIMEIRO (legacy).** Updated 2026-06-17 (OBSERVATORY_V051_NARRATIVE_READY —
corrects the OBSERVATORY_V05_NARRATIVE_READY entry below, which the product
owner rejected as a polished MVP, not a complete-method presentation of
HERALD: English UI, architecture explanation at the bottom of the page
(after the map/KPIs), PT prediction gap never closed despite the gap report
saying it was pure data engineering, no real geographic heatmap, sector
graph never wired to the map, generic English KPI cards, technical
vocabulary (beta/q_fdr/bss) not fully confined to a collapsible section.
v0.5.1 (new files only, v0.4/v0.4.1/v0.5 untouched) fixes every point: (1)
a "Méthode HERALD" architecture diagram — 6 stages (données territoriales →
prévision locale → état économique → relations sectorielles → niveau
d'évidence → signaux pour la décision) plus 4 components (base statistique /
couche relationnelle-candidats / validation / sortie) — is now the first
content block after the title, before the map; (2) every visible string is
in French; (3) "Prévision locale" is the section right after the
architecture, plus a new "Écart à l'attendu" map mode and side-panel
observed/expected/difference fields; (4) PT municipal prediction CLOSED via
a new script `build_pt_municipal_prediction_layer.py` that re-runs the
exact same causal persistence/Ridge AR(1) method already validated for
FR/NL (`RIDGE_ALPHA=1.0`, `RIDGE_MIN_TRAIN=4`, reused from
`build_observatory_export.py`) directly against the observed PT municipal
panel (`data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv`,
278 municipalities × 16 years × 8 sectors, KZ structurally absent for every
row) — no proxy, no HPC; an explicit leakage assertion in the script
confirms every `valid_forecast` row's persistence forecast equals the prior
year's observed value (28,974/28,974 checked rows pass);
`reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md` updated to CLOSED; (5) a
real "Bassins économiques" geographic-intensity heatmap mode (territorial
velocity converted to a within-country-year quantile, rendered as a 4th
choropleth colour mode) — never called a "causal cluster"; (6) the sector
relation graph now filters the map: clicking an edge calls
`applyGraphFilterToMap()`, which sets the map's country and year to the
edge's country/window and re-renders; (7) generic KPI cards replaced by a
French "Résumé d'évidence" (e.g. "3 pays comparés", "20 relations
validées", "121 relations proxy rejetées"); (8) beta/q_fdr/bss and the one
permitted causality-prohibition sentence ("Ces relations n'établissent pas
de lien de causalité structurelle.") confined to two collapsible "Détails
méthodologiques" blocks, verified absent from the static HTML body outside
them; (9) a new "Couche relationnelle" section explicitly states, in
French, that no neural candidate-relation dataset exists in this repository
today — only validated Phase 7 relations are shown, kept separate from the
blocked proxy edges (preserved for audit only). All v0.4 hard rules
re-verified: GEMEENTE_PROXY absent from the relation graph (20 edges
unchanged), 121 blocked proxy edges isolated
(`allowed_for_training_label=false`), PT/KZ always structurally absent and
disabled in the sector selector, never a bare NaN. Determinism verified for
all three new builders. 103/103 new tests pass
(`tests/test_observatory_v051_narrative_dashboard.py`); all 192 prior
v0.4/v0.4.1/v0.5 tests unaffected (re-run, still pass). New dashboard:
`reports/dashboards/herald_observatory_v051_narrative_dashboard.html` (18.2
MB). Full point-by-point correction record:
`reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md`. New DEC-068 in
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`. No prior scientific/
statistical DEC-0xx conclusion was altered — only this dashboard-readiness
decision is corrected.)
**Previously updated 2026-06-17 (OBSERVATORY_V05_NARRATIVE_READY [CORRECTED
above to OBSERVATORY_V05_PARTIAL — see DEC-068] — built a new
layperson-friendly dashboard on top of v0.4's data, v0.4 untouched. New presentation-only
export pipeline `src/data/european_panel/build_observatory_v05_narrative_exports.py`
re-shapes the v0.4 granular exports (territory state/relation edges/blocked proxy) into
`data/processed/herald_observatory_v05_narrative/` (territory_view, sector_view,
relation_view, prediction_view, map_state_by_year_sector.json, relation_timeline.json,
manifest.json) — no scientific number recomputed, only human labels/badges/sentences
added. Map IS the heatmap now (colour changes by year/sector/view directly on the
choropleth, no separate chart); year timeline + play/pause; sector graph is dynamic and
spatial (clicking an edge updates an aggregate territory-context table and shows a
plain-language sentence, e.g. "Between 2015 and 2020, in Portugal, X precedes Y... This
is observed evidence, not proof of causality"); persistent mode shows all valid relations
faint with the active window highlighted. Prediction layer: audited whether validated
observed-vs-expected data exists across FR/PT/NL — found it already does for FR+NL
(`data/processed/herald_observatory_v03/herald_observatory_v03_panel.csv`, causal
rolling-origin AR(1) Ridge, same ZE2020/COROP grain as v0.4 granular) but NOT for PT at
municipal grain (v0.3 PT forecast is NUTS3-scale, 25 territories, vs v0.4 granular PT
Municipality, 278 — different grains, no validated join; closing this needs only a
data-engineering re-run of the existing forecast script against the PT municipal panel,
not HPC). Full audit: `reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md`. PT/KZ
structural absence (every PT/KZ row has state=INSUFFICIENT_DATA, value=NaN by
construction per DEC-064) is now explicitly labelled "Sector not available for Portugal"
(never a bare NaN) and the KZ option is disabled in the sector selector when
country=PT. NL gemeente proxy re-verified absent from the embedded relation graph
(fail-closed assert in both builders); 121 blocked proxy edges kept in a separate
technical panel, framed only as "audit only", never a discovery. No causal language, no
ML jargon (GNN/attention/encoder/AUC) in the main UI body — both verified by test. GSAP
loaded from CDN (same pattern already used in `herald_architecture_diagram.html`) for
the timeline/window playback transitions only, no decorative animation. Dashboard:
`reports/dashboards/herald_observatory_v05_narrative_dashboard.html` (14.8 MB, Plotly
embedded locally/offline). 65/65 new tests pass
(`tests/test_observatory_v05_narrative_dashboard.py`); all 127 prior v0.4/v0.4.1 tests
unaffected. Playwright still unavailable in this environment — validated via embedded
JSON-blob parsing, DOM id cross-reference (all `getElementById`/`querySelector` targets
exist), and onclick/onchange handler cross-reference (all referenced JS functions
defined) instead of a screenshot. Builders:
`src/data/european_panel/build_observatory_v05_narrative_exports.py`,
`src/data/european_panel/build_observatory_v05_narrative_dashboard.py`.
**Previously updated 2026-06-17 (OBSERVATORY_V041_VISUAL_READY —
PT continental municipality geometry obtained (278/278, DGT/CAOP via geoapi.pt,
crosswalked by normalised name to the panel's 7-digit geocods, simplified
0.001° for embedding, 1.18 MB). PT now renders as a REAL choropleth in
`reports/dashboards/herald_observatory_v04_granular_dashboard.html` (10.0 MB)
instead of a table fallback. Sector→sector graph (Section 2) is now dynamic:
timeline slider over 6 windows, play/pause animation, 3 modes (current/
cumulative/recurring edges only), recurring/sign-change/exclusive markers
(🔁/⚠/⭐), per-window edge-detail history table, and a relation×window mini
heatmap (β sign/intensity). Map↔graph linking: selecting a country on the map
syncs the graph's country filter; selecting a sector highlights its incoming/
outgoing edges; clicking an edge shows aggregate territory-state context
(never edge-specific territorial attribution). NL gemeente proxy re-verified
absent from the relation graph; 121 blocked edges still isolated; DEC-066
labels untouched. 241/241 tests pass (41 new
`test_observatory_v041_visual_upgrade.py` + 200 prior). Playwright still
unavailable — validated via HTML/JS structural + embedded-data checks.
Builders: `src/data/european_panel/build_pt_municipality_geometry.py`,
`src/data/european_panel/build_observatory_v04_dashboard.py` (updated).
**Previously updated 2026-06-17 (OBSERVATORY_V04_DASHBOARD_READY —
`reports/dashboards/herald_observatory_v04_granular_dashboard.html` (9.0 MB,
Plotly embedded locally/offline). Map: FR ZE2020 + NL COROP choropleth
(geometry available); PT Municipality + NL gemeente proxy as sortable
table/heatmap fallback (no municipal/gemeente geometry). Sector graph built
ONLY from `granular_relation_edges.csv` (20 edges, FR/PT/NL COROP observed) —
NL gemeente proxy structurally absent from the graph (verified programmatically).
121 blocked NL gemeente proxy edges shown only in a separate "Blocked proxy
artifacts" panel, `allowed_for_training_label=false`. Builder:
`src/data/european_panel/build_observatory_v04_dashboard.py` (reuses v0.3
patterns: local Plotly embed, NL_COROP_TO_NUTS3 crosswalk, circular sector
layout). 41/41 new dashboard tests PASS (200/200 total incl. DEC-065/066/
Observatory-policy suites). Playwright unavailable — validated via embedded
JSON-blob assertions + HTML structural checks instead of screenshot (see
report for manual validation steps).
**Previously updated 2026-06-17 (DEC-065 COMPLETE — `NL_GEMEENTE_PROXY_PHASE7_BLOCKED`.
NL gemeente proxy Phase 7 (job 7475756, 252/252 complete) found a structural validity
defect: the DEC-063 stock-share weighting term injects cross-sector-correlated noise
unrelated to births precedence (share_velocity coefficient ~10x corop_velocity;
cross-sector correlation 0.34-0.82), explaining an implausible 15x inflation in
promoted edges (8 COROP observed -> 121 gemeente proxy). All 121 promoted/97
COVID-robust gemeente proxy edges are marked `INVALID_FOR_TRAINING_LABELS` /
`BLOCKED_PROXY_ARTIFACT`. NL COROP observed (8 promoted, 3 COVID-robust) remains
`VALID_OBSERVED`. Post-DEC-065 evidence policy: `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`.
Observatory v0.4 granular contract + clean exports (territory_state/relation_edges/
blocked_proxy_edges/manifest) ready: `reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md`,
`data/processed/herald_observatory_v04_granular/`. 159/159 tests PASS (71 DEC-065 + 45
Observatory v0.4 policy + 43 DEC-066). Decision: `GRANULAR_OBSERVATORY_V04_DATA_READY`.)
**Previously updated 2026-06-16 (DEC-061 COMPLETE — PT_READY_NL_BLOCKED. PT municípios (308, 278 continente, 8/9 A10, 2008-2023) confirmados via INE API. NL gemeente births bloqueados via CBS Open Data (83631NED só COROP; 81575NED é stock não births). 39/40 testes PASS + 1 SKIP-expected. DEC-060 COMPLETE — AUDIT_COMPLETE 10/10 PASS. FR tem 1 label Phase 7 pois o critério vinculante é |β| ≥ 0.10 (não FDR). 8 pares near-miss-beta: passam FDR+Δr²+bss mas |β|=0.076-0.097. MN→BE o par mais consistente (6 janelas p≤0.01) mas anti-correlação beta-FDR impede promoção. RU→MN classificado FR_COVID_SENSITIVE (p_perm pre-COVID=0.127). 63 testes PASS. Outputs em data/processed/france_relation_audit/.).
Read this file, then verify drift with `rtk git status --short`.

## Quick orientation (start here)
- **Direction:** `reports/HERALD_PROJECT_CHARTER.md` — official scope, permitted/forbidden claims, frozen decisions.
- **Current state by component:** `reports/HERALD_CURRENT_STATE.md` — completion %, blockers, next step.
- **All decisions:** `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-039).
- **Claims classification:** `reports/HERALD_EVIDENCE_MATRIX.md`.
- **Active document list:** `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`.
- **Artefact manifest:** `reports/herald_artifact_registry.json`.
- **S1_FR_FAIL (DEC-031):** GConvGRU and EvolveGCN-H fail all 5 frozen gate criteria on France (GConvGRU WMAPE 0.064922 vs Ridge 0.064856; p_temporal=1.0). Graph-temporal prediction branch CLOSED. No HPC authorized.
- **Observatory exports:** aggregate PT/IT/AT v0.1.1 (1,963 rows); sector FR/NL/PT v0.2 (45,945 rows) via `build_observatory_export.py`; Observatory v0.3 (45,945 rows + sector relations) via `src/data/european_panel/build_observatory_v03.py`.
- **Phase 7 result (DEC-034):** SECTOR_PRECEDENCE_PROTOTYPE_READY — 12 COVID-robust edges (NL=3, PT=9); 25 total promoted main edges. Slurm 7455266, meso. Audit PASS.
- **Observatory v0.3 (DEC-035/036):** Sector precedence layer integrated. Geographic map (FR=ZE2020/NL=COROP/PT=NUTS3 mainland), Plotly self-contained. Dashboard includes Phase 8 territorial contribution layer (Section 6 toggle, divergent colorscale): `reports/dashboards/herald_observatory_v03_dashboard.html` (14,095 KB). 48 tests pass.
- **Phase 8 (DEC-037 + addendum):** TERRITORIAL_MOVEMENT_LAYER = DESCRIPTIVE_ONLY. LOTO influence decomposition for 12 ROBUST relations. Nomenclature: HIGH_DESCRIPTIVE_INFLUENCE (91) + MODERATE_DESCRIPTIVE_INFLUENCE (78) + LOW_DESCRIPTIVE_INFLUENCE (8) + DESCRIPTIVE_ONLY (168). No HPC. Builder: `src/data/european_panel/build_territorial_sector_movements.py`. 44 tests pass. Data in `data/processed/herald_observatory_v04/` (not committed — regenerable). Decision fields: interpretation_scope=descriptive_relative_influence, independent_replication=false, spatial_flow_supported=false, causal_effect_supported=false.
- **DEC-038 — European sector coverage preflight:** 27 countries evaluated. IN_OBSERVATORY: FR/NL/PT. ELIGIBLE_WITH_MAPPING: FI (19 NUTS3, 2013-2021, Eurostat BD_HGNACE_R, K_L combined). ELIGIBLE_WITH_DOWNLOAD: AT, CZ, DE, DK, ES, IT, PL, RO, SE. BLOCKED_SEMANTICS: BE (vat_first_registration). PARTIAL: 13 small EU countries (only 2021-2023 in Eurostat, no national source documented). KEY LIMIT: Eurostat BD_HGNACE_R has only 3 years (2021-2023) for all countries except FI; K_L always combined. Script: `src/data/european_panel/audit_european_sector_coverage.py`. 53 tests pass.
- **DEC-039 — Phase 9 synthetic benchmark (smoke PASS):** Controlled benchmark with known ground truth. Generator: AR(1) + cross-sector effects (lags 1-2, linear/tanh) + territory propagation + crises + structural breaks; MCAR/MAR/block masking. 6 baselines (B1 mean, B3 ffill, B5 Ridge, B6 neural-no-graph, B7 HERALD-graph, B8 HERALD-permuted). All temporal features strictly causal (verified). Smoke: 10T×5S×12Y, 2 seeds, MCAR 20%, 100 epochs → 1.7s, no NaN, leakage PASS. G1/G3 not evaluable at smoke scale. 37 tests pass. Contract: `reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md`.
- **DEC-040 — Phase 9 full benchmark infra (pilot PASS 6/6):** 4 scenarios (linear/nonlinear_heavy/mixed_default/generalization), 5 seeds, 12 models (incl. KNN causal, random-graph null, oracle), G1-G8 gates, run_full_benchmark.py (atomic writes, resume, 20-task manifest), gates.py. Pilot: 6/6 PASS, 86s, no NaN, leakage PASS, herald < ridge all tasks. G4 (cal90) FAIL expected (MC Dropout undercalibrated: 0.26-0.29 vs 0.80 threshold). 86 tests pass. HPC scripts ready: `hpc/phase9_synthetic_generalization/`.
- **DEC-041 — G3 block-masking convergence probe (G3_NOT_CONFIRMED):** Block masking G3 failure STRUCTURAL and SEED-SPECIFIC for linear/seed=123. FULL_HPC_AUTHORIZED (500 epochs). Script: `src/modeles/synthetic/run_convergence_probe.py`.
- **HPC full run COMPLETE (job 7457617):** 20/20 tasks completed, 4-7 min each. Results: `data/processed/synthetic_benchmark/full/`. All G1 FAIL, oracle MAE=0.307, herald MAE=0.308, ffill MAE=0.255 (ffill dominates all scenarios). G2 falsely FAIL (AUC evaluation bug B1). G5 PASS. G4 FAIL (cal90≈0.27 vs 0.80 threshold).
- **DEC-042 — Graph usage diagnostic (IMPLEMENTATION_BUG_FIXED + ARCHITECTURE_STRUCTURALLY_INADEQUATE):** Three bugs found: B1=AUC transposition in evaluate_imputation.py (FIXED: `attn[cols,rows]`; corrected AUC=0.727, G2 PASS), B2=symmetric adj passed to oracle (documented), B3=contemporaneous aggregation misses lag-1/lag-2 effects (architectural; prototype HERALDGraphImputerLagged in run_diagnostic.py). Diagnostic gates: D1/D2/D3/D5 PASS, D4 ceiling effect on trivial. 12/12 tests PASS. Report: `reports/HERALD_PHASE9_GRAPH_USAGE_DIAGNOSTIC.md`.
- **DEC-043 — Phase 10 lagged graph benchmark (HPC_AUTHORIZED):** `HERALDGraphImputerLagged` (lag-1+lag-2 directed sector attention, MLP 10→64→32→2). 15 models (7 baselines + 5 contemp neural + 3 lagged neural). Directed oracle AUC=1.000 (wiring verified). Pilot gates (200 epochs, 2 scenarios × 3 seeds): L1 PASS, L2 PASS, L4 PASS, L5 PASS, L7 PASS (NaN=0, leakage PASS). HPC_AUTHORIZED=True (L1+L2+L7). Pilot decision=PHASE10_PARTIAL (L3 requires >5% MAE improvement not visible at 200 epochs). 34/34 tests PASS. Contract: `reports/HERALD_PHASE10_LAGGED_CONTRACT.md`. Next: `git push` + rsync to meso + smoke + sbatch.
- **DEC-043 ADDENDUM — Phase 10 HPC COMPLETE (PHASE10_PARTIAL):** Job 7457885, 20/20 tasks, 500 epochs. Gates: L1 PASS (oracle_lagged < oracle_contemp 4/4), L2 PASS (AUC=1.000), L3 FAIL (+1–2% MAE, need 5%), L4 PASS (specific to true graph), L5 PASS (no regression), L6 FAIL (generalization +2.4%), L7 PASS (NaN=0, leakage PASS), L8 FAIL (marker). Edge AUC: herald_lagged 0.64–0.71 vs herald_contemp 0.39–0.43 (+70%). MAE improvement: +0.7–2.4% vs contemp. L3 failure is structural (AR-dynamics ceiling ~2%). Full results: `reports/HERALD_PHASE10_LAGGED_RESULTS.md`. Next DEC options: (A) lower L3 threshold; (B) stronger generator signal; (C) accept PARTIAL for publication.
- **DEC-044 — Phase 10 metric reconciliation + OFAT signal sensitivity (OFAT_PARTIAL 4/8):** AUC B1 bug fixed (inverted, was 0.273, corrected to 0.727). 48-task OFAT: B_high +13% MAE benefit, D_lag AUC=0.71, O7 finding inverted (high AR → MORE graph contribution). Factorial runner NOT_AUTHORIZED. Report: `reports/HERALD_PHASE10_SIGNAL_SENSITIVITY.md`.
- **DEC-045 — Phase 11: True Synthetic Generalization (SYNTHETIC_RELATIONS_GENERALIZE):** Multi-dataset training (T1/T2) on linear+mixed, zero-shot test on novel_lag2 (frac_nonlinear=0.85, lag-2) + novel_highvar (frac_nonlinear=0.90, structural break). 51 tests. Pilot 36s. Gates 6/9 PASS: X4 PASS (T2 marginal), X6 PASS (edge AUC=0.611), X5/X8/X9 FAIL (MLP doesn't generalize to 85-90% nonlinear under extreme dynamics shift). HPC NOT REQUIRED — finding structurally unambiguous from pilot. Reopen: new DEC needed for partial adaptation (frozen attention + MLP fine-tune). Package: `src/modeles/synthetic/phase11_generalization/`. Report: `reports/HERALD_PHASE11_SYNTHETIC_GENERALIZATION.md`.
- **DEC-046 — Pesquisa arquitetural pós-DEC-045 (RESEARCH_ONLY):** Diagnóstico: atenção transfere (AUC=0,611), MLP não transfere sob shift extremo. 18 referências verificadas (R-026 a R-042, 5 eixos: imputação grafal/domain adaptation/relational inference/masked pretraining/conformal). RECOMMENDED_NOW: PATH 1 — frozen attention + adapter MLP (bottleneck 32→16→32) treinado com K% labels alvo + pretraining multi-task (reconstrução mascarada + edge/lag/sign prediction) + EnbPI conformal. SECONDARY: PATH 2 — pretraining em 2000 mini-datasets cobrindo frac_nonlinear=0-0,9. FUTURE_ONLY: PATH 3 — NRI/GTS graph structure learning (T curto aumenta risco de sobreajuste; requer validação com T≥25). GRIN/SAITS reclassificados para SECONDARY_BASELINE. Report (corrigido): `reports/HERALD_POST_DEC045_ARCHITECTURE_RESEARCH.md`.
- **DEC-047 — Few-shot adaptation benchmark (PILOT_COMPLETE, FEWSHOT_ADAPTATION_FAILED):** 9 estratégias (Z0/A1/A2/A3/A4/C0/P0/B0/B1), 432 registos, 85s. Resultados: B0 (ffill) MAE=0.244 domina todos os neurais (~0.281). Nenhuma estratégia de adaptação melhora sobre zero-shot. A6 PASS (estrutura grafal preservada). Causa-raiz: gap de distribuição demasiado largo para 50 épocas de fine-tuning sem pretraining prévio em dinâmicas não-lineares. HPC NOT REQUIRED. Próximo: DEC-048 — pretraining mascarado em cenários com frac_nonlinear=0-0.9. Package: `src/modeles/synthetic/phase12_few_shot/`. Relatórios: `reports/HERALD_FEWSHOT_ADAPTATION_CONTRACT.md`, `reports/HERALD_FEWSHOT_ADAPTATION_PILOT.md`. 49 testes PASS.
- **DEC-048 — Failure cause diagnostic (PILOT_COMPLETE, TRAINING_BUDGET_TOO_SMALL):** 4 eixos OFAT (D/M/L/S) + functional scenario + gradient diagnostics + masked pretraining. 105 registos, 79s. RESULTADO PRINCIPAL: C2 PASS (oracle_ratio=0.732) — arquitetura NÃO inadequada. M3 locally trained tambem bate ffill. Gradiente atenção 400x menor que MLP (landscape plano). C3/C4 FAIL = artefacto de 30 épocas insuficientes. C5 PASS: GRAPH_MASKED_MULTITASK +1.1% sobre NO_PRETRAINING. S3 (structural_break) = degradação catastrófica (ratio=1.45). Gates 6/10 PASS. Principal cause: TRAINING_BUDGET_TOO_SMALL + distribuição shift demasiado larga. Próximo: DEC-049 — pretraining 150 épocas, 50 datasets D2, GRAPH_MASKED_MULTITASK, rerun DEC-047 estratégias. Package: `src/modeles/synthetic/phase13_diagnostic/`. Relatório: `reports/HERALD_DEC048_FAILURE_CAUSE_DIAGNOSTIC.md`. 21 testes PASS.
- **DEC-049 — Phase 14 convergence audit (PARTIAL — supersedido por DEC-050):** Piloto com código bugado (3 bugs em pretrain_runner.py encontrados após piloto). Gradiente: GRAPH_MASKED_MULTITASK aux→attn=True (ratio 101-331×), TEMPORAL_MASKED aux→attn=False (ratio 3000-6438×). Pretraining com 10 datasets PIORA reconstrução vs NO_PRETRAINING (artefacto de Bug A). Ver aviso no relatório DEC-049.
- **DEC-050 — Bug audit + run corrigido (TEMPORAL_MASKED_CONFIRMED; GRAPH_MULTITASK_UNSTABLE):** 3 bugs corrigidos: A=TEMPORAL_MASKED reconstruía células visíveis (não escondidas); B=lag-2 tratado como negativo em edge BCE; C=sign_bce compartilhava logit com lag_bce (impossível em softmax — removido). Resultado: TEMPORAL_MASKED@75 MAE=0.2327 BATE ffill=0.2568 (novel_lag2, zero-shot). GRAPH_MASKED_MULTITASK instável (colapso σ→0 em val_loss: -3→-32000→-421000). Few-shot A1: 78-80% redução MAE. 30 testes PASS. 300-epoch trigger disparado, NÃO executado. Package: `src/modeles/synthetic/phase14_convergence/` (5 ficheiros). Relatório: `reports/HERALD_DEC050_BUG_AUDIT.md`.
- **DEC-051 — Stable Objective Audit (EXPERIMENT_COMPLETE via DEC-052):** Objectivo: confirmar se ganho few-shot é real (NT1-NT6) + estabilizar loss (R1=NLL clamped, R2=Huber, R3=MSE) + cabeças grafais independentes (sign_logit, lag_logit como nn.Parameter separados). 5 variantes × 3 budgets (30/75/150) × 5 seeds × 2 cenários × 2 máscaras. Top-2 seleccionadas por val_loss (NOT test). Gates V1-V10 congelados. 47 testes PASS. Package: `src/modeles/synthetic/phase15_stable_objective/` (9 ficheiros). Relatório: `reports/HERALD_DEC051_STABLE_OBJECTIVE_AUDIT.md`.
- **DEC-052 — NT Audit Fix + Results (COMPLETE; 11/11 PASS):** Causa NT1/NT2: Dropout não-determinístico (DROPOUT=0.1) + bug inversão de máscara na avaliação. Leakage real: NÃO — `_build_temporal_features` zera test cells via support_mask; confirmado por `params_identical=True, max_diff=0.00e+00` com adapt_seed=12345. Correcções: `adapt_seed` em `adapt_model()`; `_mae_at_eval_cells` com convenção correta; V1/V6 gates scoped a NLL_CLAMPED, limiar explosão 4.05. NT1-NT6: TODOS PASS. Hashes: 15 checkpoints inalterados. Zero-shot: TEMPORAL_MASKED_NLL_CLAMPED@75 MAE=0.2327 (ffill=0.2568). Few-shot: ganho real ~0.6% (78-80% DEC-050 era artefacto). 11/11 PASS incluindo V300 técnico. 300 épocas aguardam autorização explícita. Addendum: `reports/HERALD_DEC051_STABLE_OBJECTIVE_AUDIT.md §9`.
- **DEC-053 — Decoupled Graph Audit (DEC053_PARTIAL; 7/10 PASS; UTILITY_GATE_NOT_SUPPORTED; GRAPH_ASSIST_NOT_SUPPORTED; ANALYTIC_GRAPH_PENDING_OUT_OF_SAMPLE_VALIDATION):** Backbone: TEMPORAL_MASKED_NLL_CLAMPED_ep75 (n_sectors=9, n_territories=30). ANALYTIC: AUC=1.000, sign=1.00, lag=1.00 (in-sample). TEMPORAL: mae=0.174-0.195 bate ffill (confirmado). GATED: gate_mean≈0.005 (praticamente fechado). D3 PASS após fix: `GatedGraphModel.train()` override mantém backbone em eval (sem dropout). D4/D8 FAIL: gate não abre sem utility supervision (λ_gate=0.01 regularisation domina, gradiente recon ≈0.007× residual). D6 FAIL: logit_diff=0.149 < 0.2 em F6 (fixture demasiado pequena, 21 epochs). Achado chave: UtilityGate precisa de supervisão directa (compute_utility=True com y_oracle) para aprender a abrir em ≤75 epochs. Backbone: `data/processed/synthetic_benchmark/phase15_stable_objective/checkpoints/model_TEMPORAL_MASKED_NLL_CLAMPED_ep75.pt`. Results: `data/processed/phase16_dec053/dec053_results.json`. Package: `src/modeles/synthetic/phase16_decoupled/` (8 ficheiros). Relatório: `reports/HERALD_DEC053_DECOUPLED_GRAPH_AUDIT.md`. Superseded by DEC-054 for utility gate question.
- **DEC-054 — Oracle Utility Gate OOS Audit (COMPLETE; 8/10 PASS; UTILITY_GATE_NOT_SUPPORTED):** Oracle correction (true_relations + obs_mask) como utility supervision. G0(λ_u=0)/G1(λ_u=0.1)/G2(λ_u=1.0)/G3(oracle analítico)/T0/A0/P0. CONFOUND CRÍTICO: P0 (permuted) tem AUROC=0.599 = G1/G2 → melhoria 0.462→0.599 é artefacto de msg_magnitude, NÃO utility learning. U2 FAIL: AUROC 0.599 < 0.70 E confundido por P0. U3 FAIL: gate_mean_useful≈0.013 (threshold 0.15). G3 oracle: MAE 0.1800→0.1637 (−9.1%) — grafo É útil. GraphRelationHead OOS: IS AUC=1.000 (memorização), transfer AUC=0.529, test IS AUC=1.000, permuted=0.471. R1/R2/R3 PASS: head aprende quando dado novos dados; não é transferível. Decisões: UTILITY_GATE_NOT_SUPPORTED (3-input MLP insuficiente); GRAPH_ASSIST_NOT_SUPPORTED (gate ineficaz); ANALYTIC_GRAPH_OOS_FAILED (head não transferível). 71/71 testes PASS. Elapsed: 8.8s. Results: `data/processed/phase16_dec054/dec054_results.json`. Report: `reports/HERALD_DEC054_UTILITY_GATE_OOS_AUDIT.md`.
- **DEC-055 — Shared Relation Encoder (COMPLETE; 9/10 PASS; SHARED_RELATION_ENCODER_SUPPORTED + LOCAL_CONTEXT_ADAPTER_SUPPORTED):** Substitui GraphRelationHead (S×S lookup table com memorização: OOS AUC=0.529) por SharedRelationEncoder (mesmos pesos para todos os pares). Arquitectura: feature extraction estateless (26 features: 2×8 sector history + 7 cross-sector incl. direction_asymmetry antissimétrica + 3 contexto) → MLP 26→32→32 → 5 cabeças independentes (presence, direction, sign, lag, strength, confidence). 2215 parâmetros encoder + 656 adapter = 2871 total. Resultados (5 seeds): IS AUC=0.960, unseen-pair AUC=0.690 (S3≥0.65 PASS), OOS-env AUC=0.719 (S4>old_head 0.551>permuted 0.457 PASS), sign=0.870, lag=0.580, direction=0.561 (S5 PASS), controles permutados delta=0.129/0.227 (S8 PASS), 4/5 seeds>0.60 (S9 PASS). S7 FAIL: temporal dynamics (janela correta) não detectada — encoder não tem objectivo de detecção de regime. Elapsed: 198.6s CPU. Package: `src/modeles/synthetic/phase16_decoupled/` (+5 ficheiros novos). Results: `data/processed/phase16_dec055/`. Report: `reports/HERALD_DEC055_SHARED_RELATION_ENCODER.md`. Próximo: validar em dados reais FR/NL/PT, leave-one-country-out, protótipos económicos.

- **DEC-056 — Real Shared Relation Encoder Validation (COMPLETE; 7/10 PASS; REAL_SHARED_RELATION_PARTIAL):** Valida SharedRelationEncoder TREINADO (hash=39b30a52da2ad330, DEC-055 best_seed=30, OOS_AUC=0.752) em dados reais FR/NL/PT. RUN ANTERIOR INVÁLIDA (encoder não treinado, run prévia = DEC056_PREVIOUS_RUN_INVALID_FOR_MODEL_VALIDATION, válida apenas como pipeline preflight). Corrigido: DEC-055 runner atualizado para salvar checkpoint + manifest. P0 (zero-shot real, log1p norm). 1096 registos pair-window. R1 PASS (sem leakage; PT KZ excluído). R2 PASS: sector permutation degrada presence de 0.687→0.509 (Δ=0.178). R3 PASS: stability Spearman FR=0.820, NL=0.412, PT=0.593. R4 FAIL: Phase 7 sign concordance=0.438 < 0.50 (sinal não transfere de sintético para real). R5/R6 FAIL: 194 pares COVID_SENSITIVE, 0 replicados cross-country (encoder over-predicts em janelas incluindo 2020). R7/R8/R9/R10 PASS. Nota: year permutation NÃO degrada (confirma S7 failure DEC-055: encoder captura correlações médias, não onset temporal). 77/77 testes PASS. Checkpoint: `data/processed/phase16_dec055/shared_relation_encoder_best.pt`. Run corrigido: `src/modeles/real_world/run_p0_checkpointed.py`. Results: `data/processed/real_shared_relations_checkpointed/`. Report: `reports/HERALD_DEC056_REAL_SHARED_RELATION_AUDIT.md`.
- **DEC-057 — Real relation learning research correction (REVISED; RESEARCH_ONLY):** Draft inicial recomendava `Lag-Aware Encoder` como Path 1, mas isso foi refutado como prioridade. Problema real pós-DEC-056 não é apenas lag: é weak real labels, sign transfer fraco (0.438), falta de replicação cross-country e COVID/window sensitivity. Recomendação corrigida: usar Phase 7 como weak/noisy labels com confidence-weighted presence/sign/lag losses, leave-one-country-out, group/environment weighting, e classificação explícita `replicated` vs `country_specific` vs `COVID_sensitive` vs `not_supported`. Lag-aware fica componente secundário, não solução central. Report: `reports/HERALD_REAL_RELATION_LEARNING_RESEARCH.md`. Bibliografia Axis 15: R-043..R-051.
- **DEC-058 — Real Weak-Label Relation Tuning (COMPLETE; 8/10 PASS; REAL_WEAK_LABEL_TUNING_PARTIAL — corrigido por DEC-059):** Fine-tuning do SharedRelationEncoder com 12 COVID_ROBUST Phase 7 labels (MAIN_ONLY=0, COVID_SENSITIVE excluído do treino). Variantes V0/V1/V2 + controles C1/C2. LOCO (FR+NL→PT, FR+PT→NL, NL+PT→FR). V1 LOCO sign concordance=0.667 (PT=0.500, NL=0.500, FR=1.000 n=1) vs V0=0.313. W3 PASS (≥0.50 e >V0). W4 PASS (58 replicated pairs; GI→OQ, FZ→JZ, BE→GI, RU→OQ, GI→RU em 3 países). W5 PASS (COVID_SENSITIVE não promovidos). W2 FAIL (C1=0.646, C2=0.688 ≥ V1=0.667 — 12 labels insuficientes para degradação clara dos controles). W6 FAIL (0 abstentions — todos os 72 pares recebem score, nenhum classificado como INSUFFICIENT_EVIDENCE). 60/60 testes PASS. Checkpoints: inicial=39b30a52da2ad330, final=254c6efe61f94d49. Artefactos: `src/modeles/real_world/train_real_relation_weak_labels.py`, `build_phase7_weak_labels.py`, `gates_dec058.py`, `tests/test_real_relation_weak_labels.py`. Data: `data/processed/real_weak_label_results/`. Report: `reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md`. Próximo: validação multi-janela com V1, mecanismo de abstention, mais países para aumentar labels.

- **DEC-059 — Weak-Label Tuning Revalidation (COMPLETE; 8/10 PASS; REAL_WEAK_LABEL_TUNING_PARTIAL):** Revalidação rigorosa da DEC-058 com 7 controles (C1-C7), scoring multi-janela (8 janelas por par), marcação LOW_EVIDENCE (FR fold n=1), abstention mecanismo. V1 sign concordance=0.500 (valid folds NL+PT) vs V0=0.312. M2 FAIL: C1/C2/C3/C5 todas dentro de 0.021 do V1=0.667 (margin exigido: 0.05). M4 FAIL: 0 abstentions (encoder dá score ≥0.50 para todos os 72 pares). M5 PASS (FR marcado LOW_EVIDENCE). M7 PASS (59 replicated pairs multi-window). DEC-058 decisão corrigida para PARTIAL. 49/49 testes PASS. Próximo: mais países (AT/BE) para aumentar labels, ou calibração conformal para abstention. Artefactos: `gates_dec059.py`, `run_dec059_weak_label_revalidation.py`, `tests/test_dec059_weak_label_revalidation.py`. Report: `reports/HERALD_DEC059_WEAK_LABEL_REVALIDATION.md`.

- **DEC-060 — France Relation Signal Recovery Audit (COMPLETE; AUDIT_COMPLETE 10/10 PASS):** Audita por que FR tem apenas 1 label Phase 7. Critério vinculante identificado: |β| ≥ 0.10 (não FDR). FR ZE2020 tem 280 zonas de emprego pequenas → efeitos |β|=0.076-0.097 sistematicamente abaixo do threshold. 8 near-miss-beta: passam FDR+Δr²+bss mas |β|<0.10. 7 near-miss-fdr: passam |β|+Δr²+bss mas q_fdr>0.05. MN→BE: par mais consistente (6 janelas p≤0.01, bss=1.000) mas anti-correlação beta-FDR impede promoção simultânea. RU→MN (único promovido): FR_COVID_SENSITIVE (p_perm pre-COVID=0.127, sem sinal pré-2015). NUTS3 sem colunas de sector — comparação de escala indisponível. Sensibilidade: com |β|≥0.08, 7 pares adicionais qualificariam (não promovidos — requer novo DEC). Labels FR_*: 1 FR_COVID_SENSITIVE, 3 FR_BETA_BELOW_THRESHOLD, 5 FR_FDR_ONLY_BLOCKED, 63 FR_WEAK_SIGNAL. 63/63 testes PASS. Artefactos: `gates_dec060_france_audit.py`, `run_dec060_france_signal_audit.py`, `tests/test_dec060_france_relation_audit.py`. Dados: `data/processed/france_relation_audit/`. Report: `reports/HERALD_DEC060_FRANCE_RELATION_SIGNAL_AUDIT.md`.

- **DEC-061 — PT/NL Municipal Sector Data Availability Audit (COMPLETE; PT_READY_NL_BLOCKED; 39/40 tests PASS + 1 SKIP-expected):** Audita se PT e NL podem elevar granularidade para nível municipal, aproximando-se de FR ZE2020 (280 zonas). RESULTADO: PT confirmado disponível via INE API (0009703/0014099): 308 municípios, 297 continente+madeira, 17 sectores CAE (K ausente por definição per DEC-018), anos 2008-2023, 8/9 A10 mapeáveis → Phase 7 viável (278 territorial × 15 anos = 4.170 amostras). NL BLOQUEADO: CBS Open Data (83631NED, 81841NED) só tem oprichtingen (nascimentos) ao nível COROP — sem gemeente. Tabela 81575NED tem gemeente (483 GM codes) mas é STOCK não nascimentos. Catálogo CBS (5.927 tabelas) pesquisado — nenhuma tabela gemeente × oprichtingen × SBI encontrada. Caribbean NL ausente (confirmado). Gates G1/G2/G3/G4/G6/G7/G8/G9/G10 PASS; G5 FORMALLY_BLOCKED. Decisão: PT_READY_NL_BLOCKED. Próximo: DEC-062 para construir painel municipal PT; NL requer CBS Microdata (acesso restrito) ou fonte alternativa. Conceitos documentados: FR=establishment_creation, PT=enterprise_birth, NL=local_unit_opening. Artefactos: `src/data/european_panel/gates_dec061_municipal_granularity.py`, `tests/test_dec061_municipal_granularity.py`, `data/processed/municipal_granularity_audit/`. Report: `reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md`.

## Observatory v0.4.1 Visual Upgrade — OBSERVATORY_V041_VISUAL_READY (2026-06-17)

**Part A — PT municipality geometry (previously missing):**
- No municipal-level PT geometry existed in the repo. Evaluated Eurostat/GISCO
  LAU 2021 (official, but freguesia-level n=3092 for PT, would need dissolve
  by LAU_ID[:4]==INE Dicofre) vs geoapi.pt (redistributes DGT/CAOP municipal
  boundaries directly, GeoJSON properties Dicofre/Concelho/Distrito match the
  official CAOP schema — verified Dicofre="1006" for Caldas da Rainha matches
  GISCO LAU_ID prefix "1006").
- Used geoapi.pt: fetched 308 municipalities (278 continental + 19 Açores + 11
  Madeira), crosswalked to our panel's 278 distinct 7-digit geocods by
  NORMALISED NAME match (no code-to-code assumption across the two schemes) —
  **278/278 matched, 0 unmatched panel names, 30 unmatched geoapi names = exactly
  the Açores+Madeira set (confirms correct continental filtering)**.
- Simplified geometry 0.001° (≈110m) for embedding: 29.7 MB → 1.18 MB, no
  invalid/empty geometries after `buffer(0)` repair.
- Output: `data/processed/geometries/pt_municipalities_continental.geojson` (278
  features) + `..._manifest.json` (source, checksum, coverage, status=COMPLETE_278_278).
- Raw per-municipality JSON cache (181 MB) in `data/external/portugal/geometry/raw/`
  — NOT committed (gitignored, regenerable via the builder script).
- Builder: `src/data/european_panel/build_pt_municipality_geometry.py`.

**Part B — PT now a real choropleth** (was table fallback): dashboard builder
loads the PT geojson, falls back to table ONLY if the file or its
COMPLETE_278_278 manifest status is missing (never fabricates geometry).

**Part C — dynamic sector→sector graph:** timeline slider (6 windows:
2009-2014…2020-2025) + play/pause animation (1.1s/frame) + 3 modes (current
window / cumulative until window / recurring edges only) + 🔁/⚠/⭐ markers
(recurring/sign-changing/exclusive-to-one-window) + per-window edge history
table in the detail panel + relation×window mini heatmap (β sign/intensity,
Plotly heatmap trace).

**Part D — map↔graph linking:** map country selection syncs
`graph-country` filter + re-renders graph; map sector selection sets
`HIGHLIGHT_SECTOR` and dims non-matching edges/nodes; clicking a graph edge
shows an aggregate territory-state distribution (GROWTH/DECLINE/STAGNATION
counts) for the edge's country/region_system/window — explicitly NOT an
edge-specific territorial attribution claim.

**Part E — protection re-verified:** `GEMEENTE_PROXY` still absent from
`RELATION_EDGES` (asserted in builder + tested); 121 `BLOCKED_EDGES` still
isolated in their own panel; DEC-066 label classes unchanged; no forbidden
causal language (only benign Plotly.js bundle comment).

**Tests:** `tests/test_observatory_v041_visual_upgrade.py` (41/41 PASS).
241/241 total across all Observatory v0.4/v0.4.1 + DEC-065/066 suites.

**Dashboard:** `reports/dashboards/herald_observatory_v04_granular_dashboard.html`
(10.0 MB, Plotly embedded locally). v0.3 dashboard untouched.

**Decision:** `OBSERVATORY_V041_VISUAL_READY`.

## Observatory v0.4 Dashboard — OBSERVATORY_V04_DASHBOARD_READY (2026-06-17)
- `reports/dashboards/herald_observatory_v04_granular_dashboard.html` (9.0 MB, offline-capable).
- Layer 1 (map): FR ZE2020 + NL COROP choropleth (geometry from `data/external/ze2020_geometry.geojson`
  + NUTS3 via NL_COROP_TO_NUTS3 crosswalk). PT Municipality + NL gemeente proxy render as a
  sortable/colour-coded table (no municipal/gemeente geometry available — explicit fallback,
  not a fabricated map).
- Layer 2 (relation graph): circular sector layout, edges from `granular_relation_edges.csv`
  ONLY (20 edges). Style: solid=ROBUST_ORIGINAL, dashed=FINE_GRAIN_SUPPORTED,
  dotted/low-opacity=EXPLORATORY_FINE_GRAIN. Colour by sign, width by |β|.
- Layer 3 (blocked panel): 121 NL gemeente proxy edges, `allowed_for_training_label=false`,
  isolated in its own panel/table, never rendered as graph edges (asserted in builder +
  verified in tests by parsing the embedded JS blobs).
- Layer 4 (evidence/export): KPI counts, manifest checksums, DEC references, CSV/manifest links.
- Builder: `src/data/european_panel/build_observatory_v04_dashboard.py` (fail-closed asserts:
  GEMEENTE_PROXY never in relation edges; blocked edges always allowed_for_training_label=false).
- Tests: `tests/test_observatory_v04_dashboard.py` (41/41 PASS) — extracts JS consts by regex
  and validates hard rules, UI elements, language rules, checksum/determinism.
- No Playwright/headless browser available — validated via HTML structural checks + embedded
  data assertions instead of screenshot.
- v0.3 dashboard untouched (`herald_observatory_v03_dashboard.html`, no git diff).
- Decision: `OBSERVATORY_V04_DASHBOARD_READY`.

## DEC-065 — NL Gemeente Proxy Phase 7 BLOCKED + Granular Evidence Policy (2026-06-17)
**`NL_GEMEENTE_PROXY_PHASE7_BLOCKED`** | 71/71 tests PASS | HPC job 7475756, 252/252 complete.
- Automated gate-count verdict (121 promoted, 97 nominally COVID-robust) was overridden
  to BLOCKED after finding the DEC-063 stock-share weighting term injects cross-sector
  correlation unrelated to births precedence (decomposition regression: share_velocity
  coefficient 13.0 vs corop_velocity 1.33; cross-sector correlation 0.34-0.82).
- All 121 gemeente proxy edges marked `INVALID_FOR_TRAINING_LABELS` /
  `BLOCKED_PROXY_ARTIFACT`, `allowed_for_training_label=false`,
  `reason=stock_share_induced_artifact`. NEVER usable as sector→sector relation labels.
- NL COROP observed (8 promoted, 3 COVID-robust) unaffected — `VALID_OBSERVED`,
  `NL_COROP_PHASE7` entry in artifact registry.
- New policy `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`: observed (FR ZE2020, PT
  Municipal, NL COROP) may feed relation labels/training; NL gemeente proxy may ONLY
  feed territory-state visual context, never relation graph or training.
- Observatory v0.4 granular contract (`reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md`,
  4 layers) + clean exports in `data/processed/herald_observatory_v04_granular/`
  (territory_state 142,650 rows incl. NL gemeente tagged proxy/context;
  relation_edges 20 rows FR/PT_MUNI/NL_COROP observed only;
  blocked_proxy_edges 121 rows BLOCKED_PROXY_ARTIFACT; manifest.json with checksums).
- 159/159 tests pass total (71 DEC-065 + 45 `test_observatory_v04_granular_evidence_policy.py` + 43 DEC-066).
- Decision: `GRANULAR_OBSERVATORY_V04_DATA_READY` (data layer ready; dashboard build not yet authorised).
- Artefacts: `src/data/european_panel/build_observatory_v04_granular_exports.py`,
  `tests/test_observatory_v04_granular_evidence_policy.py`.
- Next: DEC-068 cross-country granular training must exclude NL gemeente proxy edges.

## DO NOT change direction without a new DEC-* entry
No new GNN architecture search. No geographic graph reopen. No P6 relaunch.
P6 sector-edge CSV (`data/processed/dual_graph_s1/learned_sector_edges.csv`) is **INVALID_FOR_INTERPRETATION** — wrong sector names, see Charter §6 and DEC-030.

## Rules
- Repo `/home/jpdark/Downloads/project_recomm/dataset`.
- Prefix shell commands `rtk`; raw Python/SSH/rsync: `rtk proxy <command>`.
- Dirty worktree: never reset/revert unrelated changes. Exclude raws, `hpc_results/`, large generated artifacts from commits.
- Branch `main`; use `rtk git rev-parse HEAD` and `rtk git rev-parse origin/main`
  to verify the current revision instead of storing a commit hash here.
- Forecast `t` uses data available through `t-1` only.
- Phase 4A/4D metrics are legacy/leaky (`growth_1y[t]` used `target[t]`). Scientific baseline starts at causal Phase 4E.

## Scientific state
Goal: frugal territorial enterprise-birth forecasting. Design: strong
persistence/AR-Ridge base + low-capacity residual correction + graph only if it
adds out-of-sample value. Forecasting now; recommendation/policy claims later.

Original targets differ: FR `establishment_creation`; NL `local_unit_opening`;
BE `vat_first_registration`; PT `enterprise_birth`. Their cross-country mean
does not prove European generalization. Path M = heterogeneous multitask,
primary metrics per country. Path H = harmonized target.

Harmonized Path H: PT 23 + IT 93 + AT 35 stable mainland NUTS3, 2008-2020,
151 regions, total demographic `enterprise_birth`.
Panel: `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv`.

## Results
Phase 4N LOCO: persistence balanced WMAPE ~0.0939; Ridge ~0.0969.
Residual/mix not promoted. Direct Ridge has cross-country target-scale mismatch.
See `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`.

Phase 4O-C: Moran's I + BH/FDR q=.05 + 999 permutations + 999 graph controls
`P W P^T` + leave-one-region-out.

Critical correction: causal years qualify only when every region has its own
past-residual scale (`region_mad`/`region_std`). Country fallback is descriptive
only: one common scalar leaves Moran's I unchanged from absolute residuals.

Final gate:
- IT PASS: robust relative + causal spatial residual signal.
- PT FAIL: relative signal fails strict LOO; early causal years use fallback.
- AT FAIL: signal mainly absolute, possibly heteroscedasticity.
- Multi-country Phase 4P NOT authorized: 1/3; threshold 2/3.
- Italy-only linear spatial-lag diagnostic was authorized; no
  GNN/generalization claim.

Phase 4P Italy-only rolling-origin result (`r2`, canonical):
- Persistence mean yearly WMAPE 0.054946.
- Residual Ridge 0.056204.
- Real queen-neighbour lag 0.056185.
- Permuted-graph median 0.056242; 18/99 controls tie/beat real, empirical p=.19.
- Real graph wins vs persistence 4/9 years and vs residual Ridge 4/9.
- Mean residual Moran does not fall: absolute 0.116848 -> 0.121740; relative
  0.264240 -> 0.269176.
- Phase 4P FAIL. Reject tested `W × births[t-1]` feature. Keep persistence.
- Post-run audit gate now explicitly requires >=1% gain vs persistence and
  no-graph Ridge, graph-control p<=.05, >=5/9 yearly wins, and worst-year
  regression <=10%. Do not call these thresholds pre-registered for 4P; use
  prospectively. Current FAIL is unchanged under the original weaker gate.
- Do not launch Italy graph training, multi-country Phase 4P, STGNN, or HERALD
  from this result.

Validation: 46 repo tests pass (`python3 -m pytest -q tests`); causal audit
passes; deterministic; Phase 4P `git diff --check` clean. Root-wide pytest
collects vendored `tools/external/graphify/tests` and fails on 26 unrelated
package-import collisions.

Key files:
- `hpc/phase4/run_phase4n_harmonized_loco.py`
- `hpc/phase4/run_phase4o_c_residual_spatial_diagnostic.py`
- `hpc/phase4/audit_phase4o_b_results.py`
- `hpc/phase4/run_phase4p_italy_spatial_lag.py`
- `tests/test_phase4o_spatial.py`
- `tests/test_phase4p_italy_spatial_lag.py`
- `reports/HERALD_PHASE4M_COMMON_FEATURE_CONTRACT.md`
- `reports/HERALD_PHASE4M_PT_IT_AT_PANEL_AUDIT.md`
- `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`
- `reports/HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md`
- `reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md`

## State as of 2026-06-10 (Phase 4Q complete)

Phase 4Q fixed Italy Spatial-Durbin block: gate FAIL (p=.32, −5.95% vs persistence).
Geographic queen-contiguity branch CLOSED under 2008-2020 data.
Do NOT launch STGNN/HERALD graph training or multi-country Phase 4P.
Reopen only with: new harmonized country, justified functional/mobility network, or revised data window.

## New strategic direction (2026-06-10)

Three scientific tracks, in priority order:

### Bloco 1 — Temporal Forecasting (active, no architecture restart)
- Persistence is best LOCO baseline. No model promoted for PT/IT/AT LOCO.
- Permitted: non-graph frugal country-specific improvements; conformal intervals.
- Forbidden: STGNN, neural graph, multi-country Phase 4P.

### Bloco 2 — Dynamic Economic Graph (L3 FR/NL PASS; L1 FAIL; L2 FR/NL/PT PASS)
New scientific question: what sector-territory economic relations exist and evolve?
NOT about improving forecast accuracy (that question was answered: geographic graph FAIL).
Role: represent relations, track evolution, detect growth/crisis/stagnation, explain dynamics.
The formal contract is `reports/HERALD_G0_FORMAL_CONTRACT.md` (10/10).
G1-L3 territory-structure projection passed for FR/NL with temporal and
territory-label nulls, FDR, leave-one-year-out and bootstrap stability. PT is
excluded from nine-sector gate because KZ has zero mass in every territory/year.
PT KZ audit (DEC-018): INE indicator 0009703 never includes section K; verified
definitional exclusion per Eurostat/OECD enterprise demography convention.
G1-L1 RCA co-specialization failed the common gate (NL pass, FR fail, PT ineligible).
G1-L2 same-sector cross-territory co-growth PASSED (DEC-019): FR 0.782, NL 0.789,
PT 0.778 (8 sectors); temporal q=0.005, territory q=0.005, LOYO pass.
COVID_ROBUST (DEC-020): all 3 pass full gate with 2020 excluded from windows
(eval_year=2020 retained; its window covers pre-COVID years 2015-2019).
COVID stability: FR 0.744, NL 0.762, PT 0.738 — all still pass.
3/3 countries pass, 2 required. Edges are statistical co-movement
associations, not Granger predictability or structural economic causality.
L2 builder corrected bugs: (1) eval_year exclusion removed; (2) bootstrap
propagates exclude_years; (3) full 4-criterion gate applied to COVID run.
27 tests pass. Second run confirms determinism.
Corrected community baseline (DEC-021): FAIL 0/3. Symmetric top-k=5 graphs,
valid temporal/territory series nulls, equal Louvain budget, modularity+AMI
BH/FDR. Some AMI signal survives, but modularity is reproduced by nulls.
L4 mobility and L5 geography remain unvalidated.
Artifacts: `data/processed/economic_graph/g1_l2_cogrowth/`; `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`.
HPC spec: `reports/HERALD_PHASE5_HPC_SPEC.md` (DEC-022). Community failure
does not invalidate L2.
**Phase 5 ablation v3 (NL, 2021-2023, 5 seeds, widths (2,)(4,)(8,)(16,8)): NOT_SUPPORTED.**
Two root-cause fixes before ablation:
  1. `message_pass_1hop` self-value fallback for isolated regions (OQ sector: zero edges
     t=2012-2019 → h=NaN for all 40 NL regions).
  2. Column-mean imputation in `predict_neural_corrector` for sectors with missing growth
     data (OQ t=2011-2016: all-NaN → imputed from t=2017-2020 means, training only).
     n_train: 39 → 440 for eval=2021.
Best H2-neural (width=(8,)): 5.53% vs H0b 3.41% (62% regression), vs H1=5.14% (H2 WORSE).
H2 beats permuted controls (6.34%, 5.94%) confirming graph specificity, but fails regression
gate (H2>H0b×1.1=3.75%) and fails to beat H1-neural. NOT_SUPPORTED all widths.
Linear correctors also fail: H2-linear=5.56% vs H0b=3.41%.
Conclusion: L2 co-growth graph does NOT improve territorial forecasting over AR-Ridge.
H0b remains best; all corrector branches closed.
65/65 tests pass. 15/65 tests updated (zero-edge semantics, self-value fallback).
See `reports/HERALD_PHASE5_HPC_SPEC.md` (status: NOT_SUPPORTED).
DEC-023 added to decision log.

**G2 Preflight (2026-06-10): descriptive findings valid.**
Script: `src/data/european_panel/build_g2_temporal_preflight.py`. 42+1 tests pass.
Artefacts: `data/processed/economic_graph/g2_preflight/` (compact, no raw edges).
Preflight findings (FR/NL/PT, top-k=5, criteria pre-registered per DEC-024):
- LOYO Pearson: 0.10-0.19; LOYO Jaccard: 0.07-0.26 — all FAIL ≥0.70 stability threshold
- Persistent edges (≥70% years): 0.4% — highly transient; turnover 59%/yr
- COVID: no measurable step-change in density or weight

**G2 Corrected controls (DEC-024c, 2026-06-11): COMPLETE.**
Module: `src/data/european_panel/build_g2_corrected_controls.py`. 25 tests pass.
Source: `sector_panel_fr_nl_pt.csv`. 199 perms N1 (temporal) + 199 perms N2 (row-wise territory).
Seeds: N1=42, N2=137. COVID: obs_year=2020 excluded from windows; eval_year=2020 retained.
N2 column permutation verified DEGENERATE for M1/M2 Jaccard (null std=0, p=1.0 always).
Metrics: M1 consecutive Jaccard · M2 mean pairwise Jaccard · M3 LOYO observed only (null BLOCKED).

Verdicts:
- Corrected COVID comparison (DEC-024d): FR 9/9 with and without obs-year
  2020 (`COVID_ROBUST`); NL 4/9→5/9 and PT 4/8→0/8
  (`COVID_SENSITIVE`). The 2/3 gate passes with different country pairs, so
  there is no robust two-country replication.
- G2_EDGE_STABILITY_NOT_SUPPORTED — M2 0.06-0.26, far below 0.70 threshold; 0/3 countries.
- PT: 0/8 sectors significant → temporal signal not validated for PT.
- M3 LOYO observed: FR 0.287 · NL 0.500 · PT 0.578. Null BLOCKED.
- G-13: PARTIALLY_SUPPORTED; inferential aggregate claim robust only for FR.

Prior control (commit cc48924) INVALID: permuted pre-computed edge weights — p=0.005/26/26 invalid.
Language: "associação estatística temporal observada", NOT causal attribution.
No individual edge claims. No cross-country pooling. No recommendation.

**G2 Aggregate Dynamics (DEC-025, 2026-06-11): COMPLETE.**
Module: `src/data/european_panel/build_g2_aggregate_dynamics.py`. 45 tests pass.
Source: `sector_panel_fr_nl_pt.csv`. 321 annual metric rows. Pair-resampling
sensitivity intervals use 200 draws; they are not confidence intervals because
territory pairs share nodes.
Artifacts: `data/processed/economic_graph/g2_dynamics/` (7 CSVs/JSONs + 16 figures).
Findings:
- FR: density Δ < 0.001, weight Δ < 0.01, turnover 79%. COVID_ROBUST.
- NL: density +0.006, weight +0.011, turnover 59%. COVID_SENSITIVE.
- PT: density +0.001, weight +0.048 (RU/MN sectors Δ > 0.13), turnover 51%. COVID_SENSITIVE.
- G-14 SUPPORTED as a descriptive computed statement.
  G2_CROSS_COUNTRY_REPLICATION_NOT_SUPPORTED.
- FR_AGGREGATE_TEMPORAL_SIGNAL_SUPPORTED.
Period `2020` means a five-year rolling graph ending in observation year 2020
(available at eval_year=2021), not a graph based only on 2020.
Next: G4-G5 explanation/visualization.
Reports written: HERALD_G2_REPORT_SECTION_FR.md, HERALD_G2_REPORT_FIGURE_SELECTION.md, HERALD_G2_DASHBOARD_INTEGRATION_SPEC.md
No dashboard modification (DEC-014). No HPC, GNN, recommendation.

**Graph-temporal tensor preflight and E0 smoke (DEC-027): E0_STATIC_SNAPSHOT_PASS (reclassified).**
**Graph-temporal schema 2.0 and E0-v2 smoke (DEC-028): E0_V2_PASS (2026-06-11). CLOSED.**
**FR adjacency audit (DEC-028): FR_ADJACENCY_READY (2026-06-11).**
**A1 implementation contract: FROZEN (DEC-028, 2026-06-11).**
- EconoGNN: `REFERENCE_ONLY`; dynamic observed trade graph, different task,
  scale and evaluation; public GitHub incomplete.
- A0 remains country-specific AR/Ridge.
- A1 candidates: low-capacity GConvGRU (A1a) and EvolveGCN-H (A1b) over per-year causal L2.
- A0-neural (GRU without message passing): equal-capacity control — mandatory for S1-FR.
- All candidates predict the same territorial total; sector births are graph
  features, not a separate target.
- NL is engineering smoke only (COVID-sensitive). FR is first scientific local
  test because only FR is robust under both G2 COVID scenarios.
- E0_V2_PASS: 13.92s runtime, 0.035 GB RSS delta, 57/57 tests, zero leakage,
  zero mask errors, deterministic outputs. Schema 2.0 corrects 5 schema 1.0 defects.
- Schema 2.0 tensors: `data/processed/graph_temporal_v2/` — 3 NL folds,
  features_seq (5,40,9,3), adjacency_seq (5,9,40,40). Canonical H0b Ridge
  (corrector.py port), per-feature masks, positive_topk adjacency.
- Schema 1.0 tensors: `data/processed/graph_temporal_preflight/` — SUPERSEDED
  by schema 2.0; kept for audit trail only.
- FR adjacency (5 eval years 2021–2025): 280 ZE, 9 sectors, 0 isolated nodes at k=3/5/10,
  1 connected component (all years), perfect symmetry, 26–39% raw negative correlations.
  All 8 fail-closed criteria pass. Tensors ready for GConvGRU/EvolveGCN-H.
- A1 contract: interface (B,T,R,S,F), bounded residual head (clamp_frac∈{0.10,0.15}),
  masked pooling, ≤5,000 params, shared weights across sectors, 11 mandatory tests in
  `tests/test_graph_temporal_a1.py`, 5 seeds {42–46}, rolling-origin folds, masked WMAPE loss.
- Evidence matrix: 33 claims; SUPPORTED=11, PARTIALLY_SUPPORTED=3, NOT_SUPPORTED=5,
  NOT_TESTED=4, REFUTED=8, PENDING_REAUDIT=1. G-17 added (S1_FR_FAIL). MET-05 updated REFUTED.
- **S1_FR_FAIL (DEC-031)**: FR scientific local test COMPLETED — GConvGRU and EvolveGCN-H
  fail all gate criteria. Graph-temporal prediction branch CLOSED. HPC NOT authorized.
- Adjacency audit (NL): 29–36% negative correlations; 0–1 isolated regions at
  k=5 (NL/2019 is sparse: 40 isolated across one sector). Primary repr: positive_topk.

**Branch CLOSED.** S1_FR_FAIL confirmed and committed (DEC-031). No A1 implementation outstanding.


### Bloco 3 — Economic Recommendation (NOT STARTED)
Terminal use case. Requires Bloco 1 + Bloco 2 complete.
Cannot be claimed as a current capability.

## Documents créés/révisés 2026-06-11 (DEC-027 tensor + E0)
- `src/data/european_panel/build_graph_temporal_preflight.py` — causal tensor builder
- `src/modeles/run_e0_smoke_nl.py` — E0 engineering smoke (NL, 3 eval years)
- `tests/test_graph_temporal_preflight.py` — 33 tests, 18 methodological invariants
- `data/processed/graph_temporal_preflight/` — 3 NL fold artifacts + manifest
- `reports/HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` — E0_STATIC_SNAPSHOT_PASS (reclassified)

## Documents créés/révisés 2026-06-11 (DEC-028 schema 2.0 + FR adjacency + A1 contract)
- `src/data/european_panel/build_graph_temporal_v2.py` — schema 2.0 tensor builder + CLI
- `src/modeles/run_e0_smoke_nl_v2.py` — E0-v2 smoke harness (RSS, 8 checks, E0_V2_PASS)
- `tests/test_graph_temporal_v2.py` — 24 schema 2.0 tests (T19–T42)
- `data/processed/graph_temporal_v2/` — 3 NL + 5 FR fold NPZs + manifest_v2.json
- `reports/HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md` — E0_V2_PASS audit
- `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` — FR_ADJACENCY_READY (280 ZE, 5 eval years)
- `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md` — FROZEN A1 spec
- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — DEC-028 appended
- `reports/HERALD_EVIDENCE_MATRIX.md` — MET-06 added; 32 claims; SUPPORTED=12

## Documents créés/révisés 2026-06-10
- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — DEC-001 to DEC-027
- `reports/HERALD_EVIDENCE_MATRIX.md` — 31 claims (G-10: L2 SUPPORTED; G-11: community NOT_SUPPORTED), all classified
- `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` — G0→G6→Bloco 3; dashboard section added
- `reports/HERALD_RESEARCH_GANTT.md` — Gantt with DATE_LIMITE_A_CONFIRMER; task 4.4 updated
- `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md` — ≥30 works
- `reports/bibliography/HERALD_REFERENCES_MASTER.md` — 25 master refs, 9 axes; EconoGNN verified
- `reports/bibliography/herald_graph_temporal_references.bib` — 22 architecture/evaluation sources
- `reports/bibliography/herald_references.bib` — BibTeX; Friedman 2008 VERIFIED_PRIMARY
- `reports/bibliography/HERALD_REFERENCE_AUDIT.csv` — audit table; Friedman 2008 VERIFIED_PRIMARY

**Dashboard (DEC-014):**
`reports/dashboards/herald_france_final_dashboard.html` = base visuelle officielle.
Pas de nouveau dashboard from scratch. Adaptation incrémentale uniquement
après validation de L3, L2 (et L1 si récupéré). L3 PASS + L2 PASS sont maintenant validés.
Ne pas modifier ce fichier ni générer un nouveau HTML avant autorisation explicite.

## Claims gate
Permitted: persistence best baseline PT/IT/AT LOCO; Italian residual spatial autocorrelation robust; geographic lags rejected; FR/NL/BE/PT targets heterogeneous.
Prohibited: recommendation, geographic graph improves forecast, cold-start LOCO, universal generalization, attention = explanation, Granger = structural causality.

## HPC Taxonomy (2026-06-12)

Index: `hpc/HPC_PHASE_INDEX.md`. Registry: `hpc/hpc_phase_registry.json`.

| Phase | Dir | Status |
|---|---|---|
| P2P3_REGIME_FRANCE | `hpc/regime/` | frozen |
| P4_GEO_GRAPH (4P/4Q FAIL, closed) | `hpc/phase4/` | frozen |
| P5_FIXED_GRAPH_CORRECTOR | `hpc/phase5/` | NOT_SUPPORTED |
| **P6_DDEG_S1 (frozen/FAIL)** | **`hpc/phase6_dynamic_dual_graph/`** | **frozen/FAIL** |

**P6_DDEG_S1:** Dynamic dual economic graph, France NUTS3, 5 folds × 11 controls × 5 seeds = 275 HPC jobs.
Full study complete — job 7453691, 275/275 COMPLETED, 0 FAILED.
Gate: **DUAL_GRAPH_S1_FAIL** — all 7 criteria fail. Predictive dual-graph branch CLOSED. Do not relaunch.
C5_dual MAE 0.1424 vs C1_ridge 0.1242 (+14.6%) and C2_no_graph 0.1329 (+7.2%). Seed Jaccard 0.3353 (threshold 0.50).
Descriptive: named-edge artefact INVALID_FOR_INTERPRETATION (sector label mapping unverifiable); index-based stability not predictively validated.
Key artifacts: `data/processed/dual_graph_s1/gate_result.json`, `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md`,
`reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md`. Status in registry: frozen/FAIL (DEC-029).

## HPC Connection
SSH alias `meso`: host `hpc2.mesocentre.uca.fr`, user `jpmartinsd`, ProxyJump
`mesoext`. Remote:
`~/project_recomm_herald_v6_2025_20260430/dataset`.

Manual sync:
```bash
rtk proxy rsync -av hpc/phase4/ meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc/phase4/
rtk proxy ssh meso 'cd ~/project_recomm_herald_v6_2025_20260430/dataset && squeue -u jpmartinsd'
rtk proxy rsync -av meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/OUT_ROOT/ hpc_results/OUT_ROOT/
```

Parallel Slurm jobs require `#SBATCH --constraint="mpi"` to avoid affected
`nompi` nodes. Next Italy diagnostic is cheap: local smoke/audit first; HPC only
if justified.

## New research entry
- Added DEC‑057 research report for real relation learning improvements.

## DEC-060 — France Relation Signal Recovery Audit (2026-06-16)
COMPLETE | AUDIT_COMPLETE 10/10 PASS | 63/63 tests
- FR has 1 Phase 7 label (RU→MN FR_COVID_SENSITIVE). Binding constraint: |β| ≥ 0.10.
- 8 near-miss-beta pairs (pass FDR but |β|=0.076–0.097), 3 near-miss-fdr pairs
- MN→BE: most consistent (6 windows, bss=1.000) but beta-FDR anti-correlation
- FR ZE2020 small zones → small absolute effect sizes; no FR pair passes all 4 criteria simultaneously outside COVID window
- `data/processed/france_relation_audit/`, `reports/HERALD_DEC060_FRANCE_RELATION_SIGNAL_AUDIT.md`

## DEC-062 — PT Municipal Panel + NL Gemeente Source Search (2026-06-16)
COMPLETE | PT_PANEL_READY_NL_OPEN_DATA_BLOCKED | 10/10 PASS | 89/89 tests
- PT panel: 278 continental municipalities × 16 years = 4,448 rows; 8 sectors; KZ structural_absent
- INE geocod structure: 1=continental (278), 2=Açores (19), 3=Madeira (11)
- DEC-061 had 297→278 discrepancy: wrong filter included Açores (prefix 2)
- NUTS2013→2024 transition: 176/278 geocods changed; harmonised via municipality name
- NL gemeente: CBS Open Data has no table with gemeente × births × SBI × ≥6 years
  - 83631NED=COROP_ONLY, 81575NED=STOCK_ONLY, 81841NED=COROP_ONLY, 80234ned=STOCK_ONLY
  - Path: CBS Microdata (ABR) via Research Data Center — requires application
- Granularity: FR 280 ZE2020 ≈ PT 278 municipalities; NL COROP 40 (fallback)
- `data/processed/european_panel/pt_municipal_sector_panel.csv`, `data/processed/granular_phase7_preflight/`
- Next: DEC-063 = Phase 7 at PT municipal level

## DEC-063 — Granular FR/PT/NL Evidence Model (2026-06-16)
COMPLETE | GRANULAR_FR_PT_NL_PREFLIGHT_READY | 10/10 PASS | 66/66 tests
- NL gemeente stock (81575NED): 483 GMs × 19 SBI sections × 19 years → 9,177 wide rows (evidence_type=observed_stock)
- NL gemeente birth proxy: 83631NED COROP births disaggregated by gemeente stock share (82,593 rows; 73% proxy_computed)
  - Method: share_gm = stock_gm/corop_total; proxy = corop_births × share; reaggregation to COROP exact (max_abs=0.0)
  - evidence_type=proxy_disaggregated_by_stock_share; NEVER treat as observed_births
- Crosswalk 84721NED: 355 current GM→CR mappings; 128 historical GMs unmatched (pre-merger)
- CBS API 10k-row limit: combine year+SBI filter → 9,177 rows/call (year loop, 19 calls)
- PT KZ structural_absent (Finance excluded from INE); NL KZ present (Finance sector included)
- Training matrix: 4 rows — FR/PT/NL_COROP (observed), NL_GEMEENTE (proxy)
- Evaluation must report separately: observed-only, proxy-included, proxy-excluded sensitivity
- `data/processed/european_panel/nl_gemeente_*`, `reports/HERALD_DEC063_*`, `reports/HERALD_GRANULAR_FR_PT_NL_TRAINING_CONTRACT.md`
- Next: DEC-064 = Phase 7 at PT municipal level; DEC-065 = NL gemeente Phase 7 (proxy-labelled)

## DEC-064 — PT Municipal Phase 7 Sector Precedence (2026-06-16)
SMOKE COMPLETE | PT_MUNICIPAL_PHASE7_READY_FOR_HPC | 10/10 PASS (smoke) | 52/52 tests (+ 8 skip-full)
- Panel: 278 continental municipalities × 16 years × 8 observable sectors (KZ structural_absent)
  Long format (build_pt_municipal_phase7_panel.py): 40,032 rows; velocity = sector[t]/sector[t-1]-1
- Smoke (2018-2023, n_perm=9): 56/56 pares válidos, n_samples 1055–1668 (11× NUTS3)
  - Max |β|=0.078 (MN→GI, bss=1.0); todos abaixo do threshold |β|≥0.10 pré-registado
  - p_perm floor = 0.10 com n_perm=9 — n_perm=999 (HPC) necessário para p_perm real
- Comparação PT NUTS3: 25 territórios, 0 promovidos, n_samples max 150 → municipal tem 11× mais poder
  ACHADO: efeitos fragmentam com granularidade (NUTS3→municipal reduz |β|, ecological correlation)
- RU→MN: β=+0.075, bss=1.0 — consistente com FR (único label FR promovido)
- Threshold |β|≥0.10 pode ser demasiado restritivo para PT/NL — possível DEC-066 threshold calibration
- HPC preparado: 208 tasks, 30 min/task, sbatch pronto; NÃO lançar sem autorização explícita
- Medium run (n_perm=99, todas janelas) a correr localmente em background — resultado em ~6h
- `data/processed/phase7_pt_municipal/`, `reports/HERALD_DEC064_PT_MUNICIPAL_PHASE7_AUDIT.md`
- DEC-065 DRAFT: `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_DRAFT.md` (não autorizado)
- Next: autorizar HPC OU aguardar medium run para decidir; DEC-065 requer DEC-064 completo
