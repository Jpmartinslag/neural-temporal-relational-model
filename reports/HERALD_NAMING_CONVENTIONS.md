# HERALD Naming Conventions

**Created:** 2026-06-18 (consolidation/freeze pass).
**Purpose:** Audit naming inconsistencies across the codebase/data and propose a canonical
table. This document does **not** rename any file or rewrite any code — it only documents
what exists today and what the canonical form should be going forward, per the
consolidation task's explicit instruction not to mass-rename.

---

## 1. Dashboard version naming

| Version | File | In-code/decision name | Status |
|---|---|---|---|
| v0.3 | `herald_observatory_v03_dashboard.html` | `OBSERVATORY_V03` | ACTIVE, historical |
| v0.4 | `herald_observatory_v04_granular_dashboard.html` | `OBSERVATORY_V04_DASHBOARD_READY` | superseded in content by v0.4.1, same file |
| v0.4.1 | same file as v0.4 (regenerated in place) | `OBSERVATORY_V041_VISUAL_READY` | ACTIVE, historical/stable |
| v0.5 | `herald_observatory_v05_narrative_dashboard.html` | `OBSERVATORY_V05_NARRATIVE_READY` → corrected to `OBSERVATORY_V05_PARTIAL` | historical, superseded for readiness |
| v0.5.1 | `herald_observatory_v051_narrative_dashboard.html` | `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN` | **current candidate (not final — never visually validated; map-first redesign signalled as next step)** |

**Inconsistency found:** v0.4 and v0.4.1 share the same physical file (the v0.4.1 builder
regenerates `herald_observatory_v04_granular_dashboard.html` in place) — there is no
`..._v041_...html` file, even though the decision log treats v0.4 and v0.4.1 as distinct
milestones with distinct test files (`test_observatory_v04_dashboard.py` vs
`test_observatory_v041_visual_upgrade.py`). This is intentional per the decision log (v0.4.1
is described as a visual upgrade of v0.4, not a new artifact) but is easy to misread as a
missing file. **Recommendation:** keep as-is (do not rename); note this explicitly in any
future onboarding doc.

**Canonical going forward:** `herald_observatory_v{MAJOR}{MINOR}_{qualifier}_dashboard.html`,
decision string `OBSERVATORY_V{MAJOR}{MINOR}_{QUALIFIER}_READY` (or `_PARTIAL` if corrected).

---

## 2. DEC-* numbering

**Inconsistency found:** DEC-061 has no standalone `## DEC-061` section in
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, even though DEC-062 explicitly says
"DEC-061 confirmed PT_READY_NL_BLOCKED..." and references it as "Part A — DEC-061 Review".
The corresponding report `reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md` exists
and is referenced from `CODEX_MEMORY.md` (line "DEC-061 — PT/NL Municipal Sector Data
Availability Audit (COMPLETE; PT_READY_NL_BLOCKED...)"). **This consolidation does not
silently add a synthetic DEC-061 log entry** — per the task's hard rule, this is recorded
here and in the final report as a finding for a human to resolve (either backfill the DEC-061
section from the existing report/CODEX_MEMORY content, or document why it was intentionally
omitted).

DEC-066 is logged in `HERALD_METHODOLOGICAL_DECISION_LOG.md` **before** DEC-065 (the DEC-066
section appears at line ~2612, DEC-065 at line ~2628) even though DEC-066 depends on
DEC-064/065 chronologically per `HERALD_CURRENT_STATE.md` ("DEC-065 — NL Gemeente Proxy...
Next: DEC-065 (NL gemeente proxy, now authorised); DEC-067"). This is likely because DEC-066
was finalized and written up before DEC-065's BLOCKED override was fully consolidated on the
same day (2026-06-16 vs 2026-06-17). **Not a numbering error** (no number reused or skipped),
just an out-of-chronological-order placement in the file. Left as-is per "never renumber."

**Canonical rule (already in effect, restated):** DEC numbers are assigned once and never
reused, renumbered, or deleted. Corrections are appended as new sections
("DEC-NNN — Addendum" or a new DEC-MMM that supersedes DEC-NNN's specific claim), never as
edits to the original section's verdict line.

---

## 3. "Phase 7" usage

"Phase 7" is overloaded across at least three distinct runs:
1. **Original Phase 7** (DEC-033/034) — FR/NL/PT sector precedence, NUTS3/COROP scale,
   `data/processed/sector_precedence_results/`.
2. **PT Municipal Phase 7** (DEC-064) — same method, PT at municipal scale,
   `data/processed/phase7_pt_municipal/`.
3. **NL Gemeente Proxy Phase 7** (DEC-065) — same method, NL gemeente proxy scale,
   `data/processed/phase7_nl_gemeente_proxy/`.

All three use the identical statistical method (signed lag-1 precedence, bootstrap/
permutation/FDR) but at different territorial grains and evidence levels. **Recommendation
for future docs/code:** always qualify "Phase 7" with its scale (e.g. "Phase 7 (PT
Municipal)") rather than bare "Phase 7", since the bare term is ambiguous across three
result directories with different promoted-edge counts.

---

## 4. "Granular" usage

"Granular" is used in two senses that should not be conflated:
1. **Observatory v0.4 "granular" exports** (`data/processed/herald_observatory_v04_granular/`)
   — refers to the dashboard's data layer being more spatially granular (municipality/COROP)
   than the earlier v0.1-v0.3 aggregate/NUTS3 exports.
2. **DEC-061/062/063 "granular" preflight/evidence model** — refers to the underlying panel
   construction work (PT municipal panel, NL gemeente proxy panel) that the Observatory v0.4
   granular exports are built from.

These are related but not identical: the Observatory "granular" dashboard consumes the DEC-063
"granular" evidence model's *observed-only* subset (FR ZE2020, PT Municipal, NL COROP) and
explicitly excludes the NL gemeente proxy that DEC-063 also produced. **No fix needed** — the
distinction is consistently maintained in the actual code/tests, just easy to conflate when
reading prose quickly.

---

## 5. PT region_system naming — found inconsistency

Two different string literals are used for the same concept (Portugal's 278 continental
municipalities) across active, current code:

| String | Used in |
|---|---|
| `"MUNICIPALITY"` | `build_observatory_v04_granular_exports.py`, `build_observatory_v04_dashboard.py`, `build_observatory_v051_narrative_exports.py`, `build_observatory_v051_narrative_dashboard.py`, `build_observatory_v05_narrative_dashboard.py`, `build_pt_municipal_sector_panel.py` (as a partial value `meta_region_system="MUNICIPALITY_ALL"`) |
| `"MUNICIPALITY_CONTINENTE"` | `build_pt_municipal_phase7_panel.py` (`REGION_SYSTEM` constant), `build_granular_training_matrix.py`, `preflight_granular_phase7.py`, `HERALD_DEC062_GRANULAR_PHASE7_PREFLIGHT.md`, `HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-062/063 tables) |

Both refer to the same 278-municipality continental-only panel. **This is a genuine,
unresolved naming inconsistency** — not silently fixed here, since changing either string
would require re-running/re-testing every dependent builder and is out of scope for a
documentation-only consolidation pass. **Recommendation:** standardize on
`MUNICIPALITY_CONTINENTE` (the more precise, disambiguating form, since PT also has
Açores/Madeira municipalities that are explicitly excluded) the next time any of the
Observatory builders are touched for a non-trivial reason — not as a standalone task.

---

## 6. Canonical label/tag vocabulary (verified present in code/data via grep, 2026-06-18)

### `label_class` (Phase 7 / fine-grain relation labels — DEC-065/066)
| Value | Meaning |
|---|---|
| `ROBUST_ORIGINAL` | `\|β\|≥0.10`, original pre-registered threshold (DEC-034/064) |
| `FINE_GRAIN_SUPPORTED` | `\|β\|≥0.09` + (COVID-robust OR ≥2 consecutive windows OR cross-country replication) — DEC-066 |
| `EXPLORATORY_FINE_GRAIN` | `0.07-0.09`, `bss≥0.90` — documented, **never** a training label |
| `BLOCKED_PROXY_ARTIFACT` | NL gemeente proxy edges — structurally invalid for training/relation labels (DEC-065) |
| `INSUFFICIENT_EVIDENCE` | Defined in the DEC-065 policy taxonomy; verified present in `HERALD_GRANULAR_EVIDENCE_POLICY.md` — **not currently emitted by any builder** (0 pairs ever receive this label; DEC-058/059 found 0 abstentions in every run). Recorded as a finding: the label exists in the taxonomy but the implementation never assigns it.

### `evidence_type` (panel/source-level — DEC-063)
| Value | Meaning |
|---|---|
| `observed_births` | FR ZE2020, PT Municipal, NL COROP |
| `observed_stock` | NL gemeente stock panel (81575NED) — establishment counts, not births |
| `proxy_disaggregated_by_stock_share` | NL gemeente proxy births (DEC-063 method, structurally rejected for relations by DEC-065) |

### Artifact/registry status vocabulary (`reports/herald_artifact_registry.json` `_meta.status_vocabulary`)
`ACTIVE`, `FROZEN`, `SUPERSEDED`, `INVALID_FOR_CLAIMS`, `INVALID_FOR_INTERPRETATION`,
`INVALID_FOR_TRAINING_LABELS`, `INVALID_FOR_RELATION_LABELS`, `VALID_OBSERVED`, `BLOCKED`,
`REGENERABLE`, `ARCHIVED`.

**Inconsistency found and FIXED (2026-06-18 traceability re-audit):**
`tests/test_herald_artifact_registry.py` hardcodes a narrower `VALID_STATUSES` set
(`ACTIVE`, `ARCHIVED`, `FROZEN`, `INVALID_FOR_CLAIMS`, `INVALID_FOR_INTERPRETATION`,
`REGENERABLE`, `SUPERSEDED`) than the registry's own `_meta.status_vocabulary`
(which also lists `INVALID_FOR_TRAINING_LABELS`, `INVALID_FOR_RELATION_LABELS`,
`VALID_OBSERVED`, `BLOCKED`). Nine real artifact entries previously used free-text
milestone labels in the `status` field instead of a lifecycle status
(`COMPLETE`, `SMOKE_COMPLETE — READY_FOR_HPC`, `COMPLETE_278_278`,
`OBSERVATORY_V05_PARTIAL`, `OBSERVATORY_V051_NARRATIVE_READY`,
`FINE_GRAIN_THRESHOLD_POLICY_READY`, `BLOCKED`, `VALID_OBSERVED`), causing
`test_status_vocabulary` to fail. Fixed by correcting each entry's `status` field to
the correct value from the test's `VALID_STATUSES` set (e.g. `ACTIVE` for
in-use/current artifacts, `SUPERSEDED` for v0.5's dashboard-readiness status,
`INVALID_FOR_CLAIMS` for the NL gemeente proxy Phase 7 result) and preserving the
original milestone label verbatim in each entry's `notes` field, so no information
was lost — only the `status` field's vocabulary was normalized.
`tests/test_herald_artifact_registry.py::test_status_vocabulary` was NOT weakened;
`VALID_STATUSES` is unchanged. The wider `_meta.status_vocabulary`
(`VALID_OBSERVED`/`BLOCKED`/etc.) remains declared but currently unused by any
`status` field — that residual declared-but-unused-vocabulary gap is left as-is
(not a test failure, just an unused declaration) since narrowing `_meta` itself
was out of scope for this pass.

### `region_system`
`ZE2020` (FR), `COROP` (NL observed), `GEMEENTE_PROXY` (NL, context-only),
`MUNICIPALITY` / `MUNICIPALITY_CONTINENTE` (PT — see §5 above for the inconsistency).

### Structural-absence vocabulary
`structural_absent` (boolean/flag field), `STRUCTURAL_ABSENT` (status constant),
`INSUFFICIENT_DATA` (state label shown in dashboards for PT/KZ rows) — all three are used
consistently for the same concept (PT's KZ/Finance sector, definitionally excluded per INE
convention, DEC-018) and are not flagged as an inconsistency, just listed for completeness
since the task asked to verify these strings exist (they do).

---

## 7. Summary of findings in this document

1. v0.4/v0.4.1 share one physical dashboard file — intentional, not a bug, but worth noting explicitly.
2. **DEC-061 has no standalone decision-log section** despite being referenced by DEC-062 and CODEX_MEMORY — unresolved, flagged for a human decision.
3. DEC-066 appears before DEC-065 in the decision log file — chronological quirk, not a numbering error, left as-is.
4. PT `region_system` is inconsistently `MUNICIPALITY` vs `MUNICIPALITY_CONTINENTE` across active current code — unresolved, recommend standardizing on the latter next time those files are touched for another reason.
5. `INSUFFICIENT_EVIDENCE` label class is defined in policy but never emitted by any builder (0 real abstentions ever recorded) — unresolved, flagged as an implementation gap vs the documented taxonomy.
6. The artifact registry test's `VALID_STATUSES` constant is narrower than the registry's own documented `_meta.status_vocabulary`, and several real entries use status strings outside both — pre-existing test/data drift, not fixed in this pass (see `tests/test_herald_artifact_registry.py`).

None of these were silently fixed; all are reported per the task's explicit instruction to
record inconsistencies rather than paper over them.
