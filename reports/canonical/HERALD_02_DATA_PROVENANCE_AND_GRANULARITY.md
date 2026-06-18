# HERALD 02 — Data Provenance and Granularity

**Created:** 2026-06-18 (canonical consolidation pass).
**Status:** Documentation only — restates `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`,
`reports/HERALD_NAMING_CONVENTIONS.md`, `reports/herald_artifact_registry.json`, and the
DEC-060→DEC-066 decision-log entries. If this document disagrees with any of those, they
win.
**Represents:** `HERALD_DEC063_GRANULAR_FR_PT_NL_EVIDENCE_MODEL.md`,
`HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md`,
`HERALD_GRANULAR_FR_PT_NL_TRAINING_CONTRACT.md`, `HERALD_GRANULAR_EVIDENCE_POLICY.md`. None
deleted — see `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md`.

---

## 1. Evidence-level vocabulary (canonical, verified against code/data)

| Level | Meaning | Can it be a relation/training label? |
|---|---|---|
| `observed` | Direct measurement from a national statistical source | Yes |
| `proxy` | Derived/disaggregated from an observed source by a non-trivial method | Only if the proxy method itself passes a structural validity check — **NL gemeente proxy fails this** (see §3) |
| `robust` / `supported` | A relation that passed bootstrap/permutation/FDR validation at a given threshold tier | Yes, per its tier |
| `exploratory` | Passed only the loosest threshold tier | Documented, **never** promoted as a training label |
| `blocked` | Structurally invalid for the stated use, regardless of apparent statistical significance | No |

Full source: `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`.

---

## 2. Data sources, by country/grain

| Source | Grain | N territories | Target concept | Status | Processed path |
|---|---|---|---|---|---|
| FR ZE2020 | Employment zone | 280 (306 historically cited in Q7 scope) | `establishment_creation` (SIDE/SIRENE) | **observed**, VALID | `data/processed/herald_observatory_v04_granular/granular_territory_state_panel.csv` |
| PT Municipal (`PT_MUNICIPALITY_CONTINENTE`) | Municipality (continental) | 278 | `enterprise_birth` (INE 0009703/0014099) | **observed**, VALID | same file; also `data/processed/phase7_pt_municipal/` |
| NL COROP | COROP region | 40 | `local_unit_opening` (CBS 83631NED) | **observed**, VALID — the NL relation baseline | same file; `data/processed/phase7_sector_precedence_results/` (original Phase 7) |
| NL Gemeente (proxy) | Municipality | 355 | `estimated_births_gemeente = corop_births × stock_share` | **proxy**, **BLOCKED for relation labels** (DEC-065) | `data/processed/phase7_nl_gemeente_proxy/results/`; tagged `allowed_use=territory_state_context_only` in the v0.4 granular export |
| PT/IT/AT Path H | NUTS3 | ~151 (3-country panel) | Eurostat `bd_size_r3` (`enterprise_birth`, harmonized demographic concept) | **observed**, VALID for LOCO forecasting only — **no sector graph at this grain** | `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv` |
| BE | NUTS3 | — | `vat_first_registration` (StatBel) | **observed** but semantically heterogeneous vs FR/NL/PT (DEC-003) | Path M (heterogeneous multitask), not Path H |

**Target heterogeneity (DEC-003, Charter §5 forbidden claim):** FR = établissement
creations, NL = local unit openings, BE = first VAT registrations, PT = enterprise births.
These are **not** the same concept. Any claim that treats them as interchangeable beyond
the explicitly harmonized Path H subpanel (PT/IT/AT, Eurostat `bd_size_r3`) is forbidden.

---

## 3. The NL gemeente proxy — why it is blocked, in one place

This is the most consequential negative finding in the granular-evidence work and is
restated here in full because it is easy to mis-cite as "121 promoted edges" without the
correction.

- **Construction (DEC-063):** `estimated_births_gemeente = corop_births × stock_share`,
  where `stock_share` is each gemeente's share of its parent COROP region's
  establishment stock.
- **Automated gate-count verdict, if taken at face value:** `SUPPORTED` — 121 promoted
  edges, 97 nominally COVID-robust, 7/8 COROP pairs preserved.
- **What DEC-065's structural diagnostic actually found:** the `share_velocity`
  coefficient (13.0) is ~10x larger than the `corop_velocity` coefficient (1.33),
  R²=0.635, and `share_velocity` correlates 0.34–0.82 across sectors — i.e. the apparent
  relations are driven by **general local stock co-movement** (e.g. gentrification), not
  by births dynamics. This also explains the implausible 15x jump in promoted edges going
  from 8 (COROP, observed) to 121 (gemeente, proxy) — the opposite of the expected
  ecological-fragmentation pattern (finer units → fewer detectable effects, confirmed
  elsewhere in DEC-064/066).
- **Decision:** `NL_GEMEENTE_PROXY_PHASE7_BLOCKED` — a **manual override** of the
  automated gate count. None of the 121 promoted/97 COVID-robust gemeente edges may be
  used as a training label under any DEC-066 tier.
- **What remains valid:** NL COROP (8 promoted, 3 COVID-robust, **observed**) is the only
  valid NL relation baseline. The gemeente proxy may still be shown in a dashboard as
  **context only** (`allowed_use=territory_state_context_only`), never as a relation edge
  or training label.

Source: `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md`.

---

## 4. Granularity comparison — do not treat as equivalent

| Country | Territories (relation-eligible) | Max \|β\| observed | Interpretation |
|---|---|---|---|
| PT NUTS3 | ~23 | 0.362 | Larger units → larger detectable effect sizes |
| NL COROP | 40 | 0.285 | Mid-size units, mid-size effects |
| FR ZE2020 / PT Municipal | 280 / 278 | ~0.10–0.13 | Many small units → systematically smaller effects (DEC-060) |

This is the **ecological fragmentation pattern**: finer territorial grain mechanically
shrinks effect sizes for a fixed underlying relation, because each unit captures less of
the total variance. **It is a scale property of the statistical method, not evidence that
France or PT-municipal has a "weaker" economy or fewer real relations.** Comparing
promoted-edge counts across countries without controlling for this is explicitly
discouraged (DEC-060, DEC-064, DEC-066).

This is also why the fine-grain threshold policy (DEC-066) exists: a flat |β|≥0.10
threshold systematically penalizes finer-grain countries, so a second, evidence-gated tier
(`FINE_GRAIN_SUPPORTED`, |β|≥0.09 + extra robustness check) was added rather than just
lowering the threshold uniformly (which would have let weaker effects through everywhere).

---

## 5. What can be used for what

| Use | Allowed sources | Forbidden sources |
|---|---|---|
| Relation/training labels | FR ZE2020, NL COROP, PT Municipal — all **observed**, per DEC-066 tier | NL gemeente proxy (DEC-065, blocked) |
| LOCO forecasting | PT/IT/AT harmonized Path H panel | Pooling FR/NL/BE/PT targets as if equivalent (DEC-003) |
| Dashboard territorial context (visual only, never a label) | NL gemeente proxy, with `allowed_use=territory_state_context_only` tag preserved | — |
| Cross-country pooled relation claims | None yet — explicitly forbidden until NL gemeente proxy is corrected and re-validated, and target heterogeneity is resolved | Any current pooled claim |

---

## 5b. European sector-coverage preflight (DEC-038) — eligibility beyond FR/NL/PT

A 27-country eligibility audit (`reports/HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md`)
classified every EU country's territory×year×sector enterprise-birth data, ahead of any
future expansion beyond FR/NL/PT:

| Status | Countries |
|---|---|
| `IN_OBSERVATORY` | FR (280 ZE2020), NL (40 COROP), PT (25 NUTS3) |
| `ELIGIBLE_WITH_MAPPING` | FI (19 NUTS3, Eurostat BD_HGNACE_R, 2013–2021, K_L sectors combined) |
| `ELIGIBLE_WITH_DOWNLOAD` | AT, CZ, DE, DK, ES, IT, PL, RO, SE (national source download + mapping required) |
| `PARTIAL_DESCRIPTIVE_ONLY` | BG, CY, EE, EL, HR, HU, IE, LT, LU, LV, MT, SI, SK (Eurostat BD_SIZE_R3, only 3 years, total births only) |
| `BLOCKED_SEMANTICS` | BE (`vat_first_registration` ≠ `enterprise_birth`, permanent semantic blocker) |

**Key structural limitation found:** Eurostat's `BD_HGNACE_R` combines KZ (financial) and
LZ (real estate) into one `K_L` sector for every country — Phase 7 relations involving KZ
or LZ individually cannot be tested from this Eurostat source alone, for any country.
This audit did not integrate any new country — it is eligibility classification only.

---

## 6. File index (clean exports)

- `data/processed/herald_observatory_v04_granular/granular_territory_state_panel.csv` —
  142,650 rows: FR ZE2020 + PT Municipal + NL COROP observed + NL gemeente proxy
  (context-only tag).
- `data/processed/herald_observatory_v04_granular/granular_relation_edges.csv` — 20 rows
  (FR=9, NL COROP=8, PT Municipal=3), NL gemeente proxy structurally excluded.
- `data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv` — 121 rows,
  `BLOCKED_PROXY_ARTIFACT`, `allowed_for_training_label=false`.
- `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json` — DEC-066
  policy artefact.
- `reports/herald_artifact_registry.json` — authoritative per-artefact status; vocabulary:
  `ACTIVE`, `FROZEN`, `SUPERSEDED`, `INVALID_FOR_CLAIMS`, `INVALID_FOR_INTERPRETATION`,
  `INVALID_FOR_TRAINING_LABELS`, `INVALID_FOR_RELATION_LABELS`, `VALID_OBSERVED`,
  `BLOCKED`, `REGENERABLE`, `ARCHIVED`.

**Naming note (code-level inconsistency not fixed, documentation-level rule defined —
see `reports/HERALD_NAMING_CONVENTIONS.md` §5):** PT's `region_system` field is written
in code as both `"MUNICIPALITY"` and `"MUNICIPALITY_CONTINENTE"` across different active
builders; both refer to the same 278-municipality continental-only panel. The official
documentation identifier for this grain, used throughout the canonicals, is
**`PT_MUNICIPALITY_CONTINENTE`** — "PT Municipal" remains an acceptable readable name,
but a precise technical reference should say `PT_MUNICIPALITY_CONTINENTE`, not bare
`MUNICIPALITY` (ambiguous vs Açores/Madeira).

---

## Cross-reference

- Phase-by-phase narrative: `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`
- Methods/architecture: `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md`
- Full claim/evidence table: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
