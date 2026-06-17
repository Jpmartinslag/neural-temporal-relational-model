# HERALD Observatory v0.4 — Granular FR/PT/NL Contract

**Status:** DATA_READY (contract + exports complete; dashboard build not yet authorised)
**Date:** 2026-06-17
**Follows:** DEC-063, DEC-064, DEC-065 (`NL_GEMEENTE_PROXY_PHASE7_BLOCKED`), DEC-066,
`reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`
**Scope:** Defines the four layers of the granular Observatory and the evidence
boundaries each layer must respect, in particular the DEC-065 prohibition on NL
gemeente proxy relation labels.

---

## Layer 1 — Territory State

**Sources (all permitted, each tagged with its own `evidence_type`):**
- FR ZE2020 observed (280 zones)
- PT Municipality observed (278 municipalities)
- NL COROP observed (40 regions)
- NL gemeente proxy/context (355 gemeenten) — **must carry a visible "proxy/context" badge**

**Content:** growth / decline / stagnation state per sector × territory × year,
derived from causal lag-1 velocity (`value[t]/value[t-1] - 1`), thresholded at ±2%.

**Display rule:** any NL gemeente-level tile/region MUST show a "proxy/context" badge
(or equivalent visual marker) distinguishing it from observed sources at first glance.
No exception — this is the layer where proxy data is legitimately allowed, but it must
never be visually indistinguishable from observed data.

**Export:** `data/processed/herald_observatory_v04_granular/granular_territory_state_panel.csv`

---

## Layer 2 — Relation Graph

**Sources (ONLY):**
- FR ZE2020 observed labels (DEC-066 tiers)
- PT Municipal observed labels (DEC-066 tiers)
- NL COROP observed labels (DEC-066 tiers)

**Explicitly excluded:** NL gemeente proxy labels, under any tier, for any pair, in any
window. This is a hard rule from DEC-065 — no edge with `region_system=GEMEENTE_PROXY`
or `evidence_type=proxy_disaggregated_by_stock_share` may appear in this layer.

**Edge schema (per edge):**
| Field | Description |
|---|---|
| `source_sector` | A10 sector code, origin |
| `target_sector` | A10 sector code, destination |
| `sign` | `+` or `-` |
| `window` | `YYYY-YYYY` rolling window |
| `label_class` | `ROBUST_ORIGINAL` / `FINE_GRAIN_SUPPORTED` / `EXPLORATORY_FINE_GRAIN` |
| `evidence_type` | `observed_births` (only) |
| `region_system` | `ZE2020` / `MUNICIPALITY` / `COROP` |
| `country` | `FR` / `PT` / `NL` |

**Export:** `data/processed/herald_observatory_v04_granular/granular_relation_edges.csv`
(20 rows: FR=9, NL COROP=8, PT Municipal=3, per current DEC-066 labelling)

**Blocked evidence (preserved, not deleted, never rendered as a relation edge):**
`data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv` (121 rows,
`label_class=BLOCKED_PROXY_ARTIFACT`, `allowed_for_training_label=false`)

---

## Layer 3 — Comparison

**Sources:**
- FR observed fine-grain (ZE2020)
- PT observed fine-grain (Municipal)
- NL observed COROP

**NL gemeente proxy** appears in this layer **only as a contextual map** (territorial
distribution visual), never overlaid as a relation graph or compared on equal footing
with the three observed sources for relation-strength claims. Any side-by-side
comparison table must label the NL gemeente column "proxy — context only, not a
relation source."

---

## Layer 4 — Recommendation Readiness

**Status:** NOT a recommendation layer. No automatic recommendation is produced at
this stage (per Bloco 3 status in `HERALD_CURRENT_STATE.md`: NOT STARTED).

**Permitted output:** "candidate opportunity signal" — a flagged territory/sector cell,
shown ONLY when ALL of the following hold simultaneously:
1. A relation label from Layer 2 is `observed` and `supportable`
   (`label_class` in `{ROBUST_ORIGINAL, FINE_GRAIN_SUPPORTED}`, i.e.
   `allowed_for_training_label=true`).
2. The Layer 1 territory state for the target sector/territory/window matches the
   direction implied by the relation's sign (e.g. source sector in `GROWTH` + positive
   sign → target sector flagged).
3. An explicit uncertainty/evidence badge is shown alongside the signal
   (label_class, q_fdr, bss, window — not just a binary "recommended" flag).

**Forbidden:** any "recommended" or "should invest" language; any signal sourced from
`BLOCKED_PROXY_ARTIFACT` or `EXPLORATORY_FINE_GRAIN` edges; any structural-causal
phrasing implying sector X is responsible for growth in sector Y — see the
language rules in `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`.

---

## Data Readiness Checklist

| Item | Status |
|---|---|
| Layer 1 export (territory state, all 4 sources, proxy badge field present) | DONE — `granular_territory_state_panel.csv` |
| Layer 2 export (relation edges, observed-only, NL gemeente excluded) | DONE — `granular_relation_edges.csv` |
| Blocked proxy edges preserved separately | DONE — `blocked_proxy_edges.csv` |
| Manifest with checksums/sources/DEC refs | DONE — `manifest.json` |
| Tests verifying evidence separation | DONE — `tests/test_observatory_v04_granular_evidence_policy.py` |
| Dashboard HTML build | NOT STARTED — requires explicit authorisation (per DEC-014 dashboard-change policy) |

**Decision:** `GRANULAR_OBSERVATORY_V04_DATA_READY` — data layer complete and tested;
dashboard construction is a separate, larger task requiring its own authorisation.

---

*HERALD Observatory v0.4 Granular Contract | DATA_READY | 2026-06-17*
