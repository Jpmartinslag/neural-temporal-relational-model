# HERALD 60 -- France ZE2020 Graph-First Dashboard (specification)

**Date:** 2026-07-28
**Status:** `SPECIFICATION_ONLY_NO_CODE_WRITTEN`
**Stage:** E5 of the sequence fixed in HERALD_56 section 5.
**Decision entry:** DEC-087 will register this specification before implementation.

## 0. Scope

Specification only. No builder, no export, no test and no HTML has been written. Nothing
here is a result.

The dashboard is the most visible artifact this project will produce and the easiest one to
over-claim from, because a colour is read as a verdict long before a caption is read. This
document therefore fixes what each visual element is allowed to assert **before** any of it
exists.

## 1. The governing principle

Fixed by the project owner, and every rule below follows from it:

> **The node shows what was observed. The panel reports the predicted level. The edge shows
> an audited association.**

Three consequences, each of which is a prohibition somewhere later in this document:

- observation and prediction never share a visual channel;
- prediction never becomes a colour, a state or a direction;
- an edge never appears without the evidence scale of its own layer.

## 2. What the dashboard inherits, and what that forbids

| Delivered | Consequence for E5 |
|---|---|
| DEC-084: engine is sectoral persistence at ZE x sector | the panel may report a predicted **level**, nothing more |
| **DEC-085: no forecast-derived state layer** | **no predicted GROWTH / STAGNATION / DECLINE anywhere** -- not as colour, badge, arrow, word or tooltip |
| DEC-082: relational availability mask | a layer may render for a year **only** where the mask says the relation exists |
| DEC-086: ranking metrics recomputed, nothing promoted | no ranking output is displayed as a recommendation |
| E6 not started | **IAT / NAF / NACE structure is absent from this dashboard entirely** |

## 3. Node encoding, fixed

### 3.1 Macro graph -- ZE to ZE

| Channel | Meaning | Source |
|---|---|---|
| **Colour** | recent **observed** trajectory of the zone, labelled descriptive | `fr_ze2020_sector_panel.csv`, observed totals |
| **Size** | observed economic volume of the zone | same |
| Edges | ZE-to-ZE relations, subject to per-year availability | `fr_ze2020_temporal_relation_signals.csv.gz` |

### 3.2 Micro graph -- sectors inside one ZE

| Channel | Meaning | Source |
|---|---|---|
| **Colour** | recent **observed** trajectory of the sector in that zone | `fr_ze2020_sector_panel.csv` |
| **Size** | current observed share of the sector in that zone | same |
| Side panel | last observed value **and** the persistence-predicted level | panel plus DEC-084 |

### 3.3 Why persistence never colours anything

Recorded so a future iteration does not undo it by accident. The persistence forecast
repeats the last observed level and carries **no direction**. Used as a colour it would be
read as a prediction of growth or decline, which is precisely the claim DEC-085 refused. It
is therefore confined to a numeric field, where a reader sees a level rather than a verdict.

### 3.4 The trajectory colour must not become a state by another name

The colour encodes an **observed change**, and it is rendered on a **continuous diverging
scale with no bins and no category labels**. No "growth", "stagnation" or "decline" wording
appears in the legend, the tooltip or the DOM.

This is deliberate: binning the observed change would create a three-state vocabulary
visually identical to the forecast-derived states DEC-085 refused, and a reader cannot be
expected to hold the distinction from a colour alone. **If discrete bins are ever wanted,
their thresholds are reserved for the project owner under HERALD_56 section 8 and require a
new decision.**

The window used for "recent" is fixed in section 8.1 and is stated on the page.

## 4. Layer separation, and the evidence scale of each

**Hard rule, carried from HERALD_56 section 5:** each species of edge is a separate layer,
with its own legend, its own grain statement and its own evidence scale. Layers are never
summed, averaged, overlaid or drawn in one another's style.

| Layer | Grain | Source | Evidence scale |
|---|---|---|---|
| ZE to ZE, trajectory similarity | ZE x year | `ze_similarity` family | **its own**, to be defined in section 8.2. **DEC-066 tiers do not apply** -- they govern sector-to-sector relations |
| sector to sector, observed precedence | **country**, not ZE | Phase 7 promoted edges | DEC-066 tiers, with the grain stated on the layer |
| sector to sector, structural NAF/NACE | nomenclature | **absent until E6 passes** | not applicable |

France holds **one** promoted sector-to-sector edge (RU->MN, COVID-sensitive, DEC-060). The
layer will look sparse. That is the evidence, and the page states it rather than padding it.

## 5. Availability governs rendering

For every layer and every year the dashboard consults
`fr_ze2020_relation_availability_mask.csv` before drawing anything:

| Mask status | Rendering |
|---|---|
| `derived_available` | layer renders, labelled **derived from causal lag features, not observed** |
| `carried_forward_from_snapshot` | layer renders, labelled with the snapshot year and its age |
| `unavailable` | **layer does not render**, and the page states the reason -- `source_not_released`, `insufficient_history` or `not_constructed` |

A year with no relation must look **different from** a year with weak relations. An empty
canvas with no explanation is the failure this mask was built to prevent (DEC-082), so
absence is always narrated, never blank.

Concretely: the ZE-to-ZE layer cannot render before 2017, and no commuting layer can render
before 2016.

## 6. Prohibitions

- No predicted state, in any channel, in any wording.
- No causal language, and no "influence", "drives", "causes", "leads to".
- No recommendation, no "should", no ranked action list.
- No IAT, NAF or NACE structure until E6 passes.
- No NL gemeente proxy edges (DEC-065).
- `fr_ze2020_exploratory_relation_signals.csv` is **never** an input: it is retrospective
  (HERALD_38). The leakage-safe `fr_ze2020_temporal_relation_signals.csv.gz` is.
- No France Q7 figure (`PENDING_REAUDIT`).
- No layer without its grain and evidence scale visible.
- No number on the page that is not traceable to a delivered artifact.

## 7. Validation

Playwright has never been available in this environment, and prior dashboards were validated
structurally. The same applies, and the limitation is stated on the page rather than
implied: the dashboard is **structurally tested, not visually validated**.

| Check | Requirement |
|---|---|
| Forbidden vocabulary | the rendered DOM contains no predicted-state, causal or recommendation wording |
| Availability | no layer renders for a year the mask marks `unavailable`; every such year carries its reason |
| Layer isolation | each layer's edges appear only in their own layer, verified by parsing the embedded data |
| Grain labels | every layer states its grain; the country-grain layer says so explicitly |
| Persistence confinement | the persistence value appears in panel or tooltip text only, never in a colour or class attribute |
| Provenance | every embedded figure traces to a delivered artifact, by checksum |
| Determinism | two builds produce byte-identical output |

## 8. Reserved for the project owner, before implementation

1. **The "recent trajectory" window.** One year against the previous, or a multi-year slope.
   This changes what the dominant visual channel means and is not a technical detail.
2. **The ZE-to-ZE evidence scale.** DEC-066 does not apply to this layer, and nothing yet
   defines what "strong" means for a trajectory-similarity edge. Until it is defined, the
   layer renders edge strength as a continuous width with no qualitative label.
3. **The side panel's third field.** The persistence-predicted level for the next year
   **equals the last observed value by construction**, so showing both would print the same
   number twice. Options: show it anyway with that stated; or replace it with the observed
   historical error of persistence for that ZE-sector, available from
   `fr_ze2020_sectoral_persistence_predictions_v1.csv`, which tells the reader how reliable
   "next year resembles this year" has been in that specific cell. The second is more
   informative and uses only delivered evidence, but it is a product decision.

No implementation begins until these three are answered.

## 9. Cross-reference

- Contract and layer rules: `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`.
- Availability mask: `reports/canonical/HERALD_57_FR_ZE2020_AVAILABILITY_MASKS.md`, DEC-082.
- Engine and the absence of forecast states: `reports/canonical/HERALD_58_...`, DEC-084, DEC-085.
- Ranking coverage: `reports/canonical/HERALD_59_FR_ZE2020_RANKING_GAP_AUDIT.md`, DEC-086.
- Leakage-safe relation input: `reports/canonical/HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md`.
- Sector-to-sector tiers and their scope: DEC-066; France's single edge: DEC-060.
