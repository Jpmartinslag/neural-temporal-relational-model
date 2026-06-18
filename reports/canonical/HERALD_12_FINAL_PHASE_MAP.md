# HERALD 12 — Final Phase Map

**Created:** 2026-06-18 (post-consolidation structural mapping, final synthesis layer).
**Status:** Documentation only — restates canonicals #1, #4, #6, and the decision log.
If this map disagrees with `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, the
decision log wins. No DEC-* is changed, renumbered, or reinterpreted here.
**Purpose:** the single table to explain the project's trajectory end to end —
phase/DEC range, period, question, data, technique, validation, result, status, and
where each phase lands relative to the article/dashboard/future recommendation layer.

---

| Phase / DEC range | Period | Scientific question | Data used | Technique/model | Validation/gates | Result | Status | Canonical doc | In article/dashboard/future? |
|---|---|---|---|---|---|---|---|---|---|
| France foundation, ZE2020 | Apr–May 2026 (pre-DEC) | Can France enterprise creation be forecast better than naive baselines? | FR ZE2020, SIDE/SIRENE | Architecture search (Phase 2/3) → Q7 | 240 runs, 12 configs × 20 seeds, rolling-window | WMAPE 0.0204 | **PARTIAL** (`PENDING_REAUDIT`) | #1, #6 | Article: yes-with-caveat. Dashboard: yes (France base). Recommendation: no |
| Leakage audit | DEC-001 (2026-06-03) | Are pre-DEC-001 cross-country WMAPEs valid? | BE/NL/PT `growth_1y` feature | Code audit | Causal recompute | All pre-DEC-001 baselines reclassified LEGACY/LEAKAGE-AFFECTED | **VALID** (as a finding) | #1, #4 | Article: yes (methods discipline). Dashboard: n/a |
| Q7 selection confirmed | Phase 3E/2R (2026-05-27) | Which France architecture to keep as default? | FR ZE2020 | Q-tensor channel/lag ablation | Paired Wilcoxon, p=0.0028 for the confirmatory L5_trainopt comparison | Q7 kept over marginally-better Q12 (noise, not worth complexity) | **PARTIAL** (`PENDING_REAUDIT`) | #1, #6 | Same as France foundation row |
| Internationalization FR/NL/BE/PT | DEC-002/003 (2026-06-04) | What's the per-country causal baseline, and are targets comparable? | FR/NL/BE/PT panels | Causal feature-policy ablation | Per-country WMAPE | FR 0.1031/NL 0.1017/BE 0.1488/PT 0.2286; targets found heterogeneous | **VALID** (per-country) / **SUPERSEDED** (pooled claim) | #4 | Article: yes, per-country only |
| Path H PT/IT/AT, LOCO | DEC-005/006 (2026-06-09) | Is there a transferable harmonized baseline across PT/IT/AT? | Eurostat `bd_size_r3`, 151 NUTS3 | Persistence/Ridge LOCO | Rolling-origin, promotion gate ≥2/3 countries | Persistence best-balanced (0.0874), no model promoted | **VALID** | #1, #4 | Article: yes |
| Transfer attempts (4H/4I) | DEC (2026-06-08/09) | Does a shared neural residual or selective transfer generalize zero-shot? | FR/NL/BE/PT | Shared residual, selective-source Ridge/neural | Compatibility + graph gates | Both gates FAIL; Ridge remains safest zero-shot model | **FAILED** | #4 | Article: yes (negative result) |
| Geographic branch (4P/4Q) | DEC-008/009 (2026-06-09/10) | Does queen-contiguity or Spatial-Durbin improve Italy forecasts? | IT 93 NUTS3 | Spatial lag / Spatial Durbin | 99 permuted controls | p=0.19 / p=0.32, both FAIL | **CLOSED_FAIL** | #4 | Article: yes (negative result). Reopening needs new DEC |
| G1/G2 territorial graph | DEC-017/019/020/021/023/024/025 (2026-06-10/11) | Is there a stable territorial co-growth/community structure? | FR/NL/PT sector panels | Pearson co-growth, top-k=5, Louvain | Temporal/territory permutation nulls, BH/FDR | L2 PASS (FR/NL/PT), L1/communities FAIL, individual edges NOT stable | **PARTIAL** | #4 | Article: yes, scoped |
| Graph-temporal branch | DEC-027/028/031 (2026-06-11/12) | Does GConvGRU/EvolveGCN-H beat AR-Ridge for France? | FR 280 ZE, schema 2.0 | GConvGRU, EvolveGCN-H | Fail-closed 5-criterion gate, 9999-perm nulls | `S1_FR_FAIL`, indistinguishable from nulls | **CLOSED_FAIL** | #1, #4, #6 | Article: yes (negative result) |
| P6 dual graph | DEC-029 (2026-06-12) | Does a learned dual graph (≤10k params) improve prediction/state/recovery? | FR 101 NUTS3, 9 sectors | Territory graph + learned sector graph | 5-fold × 11 controls × 5 seeds, 7-criterion gate | All 7 criteria fail; C5=0.1424 vs C1=0.1242 | **CLOSED_FAIL** | #1, #4, #6 | Article: yes (negative result) |
| Synthetic benchmark | DEC-039/040/042/043/044/045 (2026-06-13) | Can a controlled synthetic benchmark validate imputation/relation architecture? | Synthetic 10T×5S×12Y | B1-B8 baselines, lagged-graph imputer | Frozen gates G1-G8, L1-L8, X1-X9 | `SMOKE PASS`; edge structure transfers OOD (AUC=0.611) but decoder doesn't | **PARTIAL** | #3, #6 | Article: yes, as architecture evidence only |
| Few-shot adaptation | DEC-046/047 (2026-06-13) | Does few-shot decoder adaptation fix the OOD generalization gap? | Synthetic | Frozen attention + adapted decoder | Gates A1-A10 | `FEWSHOT_ADAPTATION_FAILED`, ffill beats all neural | **CLOSED_FAIL** | #3, #6 | Article: yes (negative result) |
| SharedRelationEncoder | DEC-048→055 (2026-06-14/15) | Can masked pretraining + a shared encoder detect relations, on synthetic then real data? | Synthetic; FR/NL/PT real | Masked multitask pretraining, SharedRelationEncoder | Gates C1-C10, U1-U10, S1-S10 | Synthetic: unseen-pair AUC=0.690 (strong) | **VALID** (synthetic only) | #3, #6 | Article: yes (synthetic). Dashboard: no |
| Real weak-label tuning | DEC-056/058/059 (2026-06-16) | Does fine-tuning with Phase 7 weak labels fix real-data sign concordance? | FR/NL/PT real + Phase 7 labels | Confidence-weighted fine-tuning | Gates W1-W10, M1-M10, 7 controls | Sign concordance 0.438→0.500 honest figure (0.667 was inflated by 1 FR label); 4/7 controls indistinguishable | **PARTIAL** (`REAL_WEAK_LABEL_TUNING_PARTIAL`) | #3, #4, #6 | Article: yes, with caveat. Dashboard: no |
| Phase 7 sector precedence | DEC-033/034 (2026-06-12) | Is there a validated sector→sector temporal precedence signal? | FR/NL/PT, 9 sectors | Signed lag-1 regression | 999 permutations, 500 bootstraps, BH/FDR | 20 observed edges (FR=9/NL=8/PT=3 final count) | **VALID** | #1, #4, #6 | Article: yes. Dashboard: yes (v0.3+) |
| France relation signal audit | DEC-060 (2026-06-15) | Why does France have only 1 promoted pair? | FR ZE2020, 280 zones | Threshold sensitivity audit | 8 near-miss-beta, 7 near-miss-fdr documented | Ecological fragmentation — scale effect, not a methodology gap | **VALID** (finding) | #2, #6 | Article: yes |
| PT/NL municipal granularity | DEC-061/062 (2026-06-15/16) | Can PT/NL be raised to municipal grain comparable to FR ZE2020? | PT INE API, NL CBS catalog | 10-gate eligibility audit | G1-G10 | `PT_READY_NL_BLOCKED` — NL has no gemeente×births×sector table | **VALID** (finding) | #2, #6 | Article: yes |
| PT Municipal Phase 7 | DEC-064 (2026-06-16) | Does PT municipal grain yield valid relations? | PT, 278 municipalities | Signed lag-1 regression, full scale | 10/10 gates | 2 COVID-robust pairs (2015-2020 only) | **VALID** | #2, #4, #6 | Article: yes, period-specific |
| NL gemeente proxy | DEC-063/065 (2026-06-16/17) | Can NL gemeente proxy data yield valid relations? | NL, 355 gemeenten (proxy) | Same method on proxy data | Automated gates + structural diagnostic (manual override) | 121 edges nominally promoted, but proxy method injects spurious correlation — BLOCKED | **CLOSED_FAIL** (for relation labels) | #2, #4, #6 | Article: yes (negative methodological finding). Dashboard: context-only, never a label |
| Fine-grain threshold policy | DEC-066 (2026-06-16) | What threshold applies fairly across territorial grains? | All Phase 7 results | Tiered policy (0.10/0.09+/0.07-0.09) | 10/10 gates, 43/43 tests | 4-tier label taxonomy adopted | **VALID** | #2, #6 | Article: yes |
| Observatory v0.3→v0.4.1 | DEC-032/035/036/063/065 (2026-06-12→17) | How to visualize validated results without overclaiming? | All validated exports | Deterministic Python builders | Structural/DOM tests, 48→241 tests across versions | Stable scientific baseline, observed-only relation graph | **VALID** | #5, #6 | Dashboard: yes, stable baseline |
| Observatory v0.5 | DEC-067 (2026-06-17) | Does a layperson narrative layer improve presentation? | v0.4 exports + v0.3 forecast | Narrative dashboard builder | 65/65 tests | Rejected as polished MVP, not complete-method presentation | **SUPERSEDED** | #5, #6 | Dashboard: no (UX superseded) |
| Observatory v0.5.1 | DEC-068 (2026-06-17/18) | Corrected French narrative dashboard with closed PT prediction gap | v0.4 exports + PT municipal forecast | Corrected narrative builder | 103/103 tests, never visually validated | `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN` | **PARTIAL** (current candidate) | #5, #6 | Dashboard: current candidate, not final |
| Future recommendation layer | Not started, no DEC | Can validated forecast + relation evidence support decision support? | Would require Bloco 1+2 complete | Not designed | None run | 0% — not started | **FUTURE** | #1, #3, #6, #7 | No — must never be described as existing |

---

## How to read the Status column

- **VALID** — citable within its stated scope, as-is.
- **PARTIAL** — part of the result is validated, part is not; never cite the unvalidated part as final.
- **FAILED** / **CLOSED_FAIL** — tested under a pre-registered gate and rejected; Charter §8 governs reopening.
- **BLOCKED** — a structural defect was found that prevents promotion regardless of gate counts (used here interchangeably with CLOSED_FAIL for the NL gemeente proxy row, which is the only BLOCKED-type entry).
- **SUPERSEDED** — replaced by a later phase in the same line of work.
- **FUTURE** — not started, no implementation exists.

## Cross-reference

- Narrative version: `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`
- Phase/technique detail matrix: `reports/canonical/HERALD_06_PHASE_TECHNIQUE_MATRIX.md`
- Full claim/evidence table: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
- Article storyline: `reports/canonical/HERALD_07_METHOD_LINEAGE_FOR_ARTICLE.md`
- Data/code/HPC structural maps: `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`, `HERALD_10_CODE_PATH_MAP.md`, `HERALD_11_HPC_AND_RESULTS_MAP.md`
- Decision history: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`
