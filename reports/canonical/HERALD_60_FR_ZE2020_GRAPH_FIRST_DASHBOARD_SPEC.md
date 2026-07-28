# HERALD 60 -- France ZE2020 Graph-First Dashboard (specification)

**Date:** 2026-07-28
**Status:** `SPECIFICATION_ONLY_NO_CODE_WRITTEN`
**Stage:** E5 of the sequence fixed in HERALD_56 section 5.
**Decision entry:** registered by DEC-087, with the corrections of this revision recorded
in its first correction addendum.

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

The window used for "recent" is fixed in section 8.1 and its legend is stated on the page.

## 4. Layer separation, and the evidence scale of each

**Hard rule, carried from HERALD_56 section 5:** each species of edge is a separate layer,
with its own legend, its own grain statement and its own evidence scale. Layers are never
summed, averaged, overlaid or drawn in one another's style.

| Layer | Grain | Source | Evidence scale |
|---|---|---|---|
| ZE to ZE, trajectory similarity | ZE x year | `ze_similarity` family | `EXPLORATORY_DERIVED`, single status -- see section 8.2. **DEC-066 tiers do not apply** -- they govern sector-to-sector relations |
| **ZE to ZE, functional mobility (commuting)** | **ZE x snapshot** | `fr_ze2020_commuting_strict_ex_ante_edges.csv.gz` | `carried_forward_from_snapshot`, **with the observation year and the snapshot age visible on every edge** |
| sector to sector, observed precedence | **country**, not ZE | Phase 7 promoted edges | DEC-066 tiers, with the grain stated on the layer |
| sector to sector, structural NAF/NACE | nomenclature | **absent until E6 passes** | not applicable |

**Commuting and trajectory similarity are never merged, never overlaid and never share an
encoding.** They are different objects: one is an observed flow of workers carried forward
from a snapshot four to eight years old, the other is a correlation computed from the same
births panel that the rest of the page displays. A reader who cannot tell them apart would
be reading an official statistic and a derived correlation as one thing. The commuting layer
carries its snapshot year and age on the edge itself, not only in a legend, because an edge
drawn in 2025 from a 2017 observation is eight years stale and that must be visible where
the edge is.

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
- No causal language. The interface is French, so the prohibition is enforced in **both
  languages**: English `influence`, `drives`, `causes`, `leads to`, `should`, `recommend`;
  French **`croissance`, `stagnation`, `déclin`, `recul`, `cause`, `influence`, `entraîne`,
  `provoque`, `devrait`, `recommande`**. The state words are forbidden in French for the
  same reason as in English -- `croissance` beside a coloured node is a predicted state to a
  reader, whatever the caption says.
- No recommendation, no "should", no ranked action list.
- No IAT, NAF or NACE structure until E6 passes.
- No NL gemeente proxy edges (DEC-065).
- `fr_ze2020_exploratory_relation_signals.csv` is **never** an input: it is retrospective
  (HERALD_38). The leakage-safe `fr_ze2020_temporal_relation_signals.csv.gz` is.
- No France Q7 figure (`PENDING_REAUDIT`).
- No layer without its grain and evidence scale visible.
- No number on the page that is not traceable to a delivered artifact.

## 7. Validation

Structural testing alone is **not sufficient**, and this specification does not accept it as
a permanent contract. The dashboard is a visual artifact: a chart that renders empty, a
legend that overlaps its plot, or a slider that moves nothing all pass every DOM assertion
ever written. Previous dashboards in this project were validated structurally because no
browser was available, and that expedient must not harden into a standard.

### 7.1 Structural layer, necessary but not sufficient

| Check | Requirement |
|---|---|
| Forbidden vocabulary | the rendered DOM contains no predicted-state, causal or recommendation wording, **in English or French** (section 6) |
| Availability | no layer renders for a year the mask marks `unavailable`; every such year carries its reason |
| Layer isolation | each layer's edges appear only in their own layer, verified by parsing the embedded data |
| Grain labels | every layer states its grain; the country-grain layer says so explicitly |
| Snapshot age | every commuting edge carries its observation year and age |
| Persistence confinement | the persistence value appears in panel or tooltip text only, never in a colour or class attribute |
| Provenance | every embedded figure traces to a delivered artifact, by checksum |
| Determinism | two builds produce byte-identical output |

### 7.2 Visual layer, required before the dashboard may be called complete

A real browser run must be **attempted** -- Playwright or an equivalent -- and must cover:

| Check | Why |
|---|---|
| Desktop **and** mobile viewports | a legend that fits at 1920px may cover the graph at 390px |
| Map and graph render **non-empty** | the commonest silent failure, and invisible to the DOM |
| No overlapping elements | legends over plots, tooltips clipped at the viewport edge |
| Legends present and readable | an unreadable evidence scale is the same as none, and this page depends on its scales |
| Year slider moves the layers | including that an `unavailable` year shows its reason rather than a blank canvas |
| Interaction | node selection opens the panel; layer toggles isolate rather than overlay |

### 7.3 The only two admissible end states

| State | Meaning |
|---|---|
| `DASHBOARD_VISUALLY_VALIDATED` | 7.1 and 7.2 both executed and passed, on both viewports |
| **`PENDING_VISUAL_VALIDATION`** | 7.1 passed and no browser was available. The dashboard is a **candidate**, and the page and every citation say so |

**There is no third state.** A structurally tested dashboard is never described as validated,
finished, or ready, in this document, in the decision log, in the page itself or in any
report that cites it. The v0.5.1 precedent is explicit about the cost of blurring this
(DEC-068): passing structural tests was mistaken for being accepted, and the correction had
to be written afterwards.

## 8. The three product decisions, now fixed

Answered by the project owner. No further reservation blocks implementation.

### 8.1 Recent trajectory: one-year observed change, log scale

```text
tau(z, s, t) = log(1 + y(z, s, t)) - log(1 + y(z, s, t - 1))
```

Chosen because it moves with the year slider, stays finite when the previous value is zero,
creates no categories, and dampens the visual dominance of the largest territories. The
macro graph applies the same form to the zone total.

- Legend, verbatim: **"Variation observée sur un an, échelle logarithmique."**
- The first year of the panel has no predecessor: the node renders **`indisponible`**. **A
  zero is never invented**, and an absent value is never drawn as the neutral midpoint of the
  scale, which would read as "no change".
- Continuous diverging scale, no bins, no category labels (section 3.4).

### 8.2 ZE-to-ZE evidence: one status, numeric channels only

No strong / medium / weak levels are created, because nothing in the record defines them for
a trajectory-similarity edge.

| Element | Rule |
|---|---|
| Evidence status | **`EXPLORATORY_DERIVED`**, a single status for every edge in the layer |
| Line style | **identical dashed stroke** for all edges -- style carries no ranking |
| Width | magnitude of `signal_strength`, numerically |
| Opacity | recurrence of `stability_score`, numerically |
| Tooltip | the exact values of both |

**Neither width nor opacity means causality, validation or quality.** They are the two
numbers the artifact carries, shown as themselves. The commuting layer keeps its own scale
(section 4) and never uses this one.

### 8.3 Side panel: three fields, with a causal error

| Field | Content |
|---|---|
| **Dernière observation** | last observed value |
| **Prévision par persistance** | the same value, **with the reason it repeats stated in the panel** |
| **Erreur absolue moyenne historique** | MAE of persistence for that ZE-sector |

The second field prints the same number as the first by construction. That is not a defect
to hide: the panel says why, which is more honest than omitting a field the engine genuinely
produces.

The third field is defined **causally with respect to the selected year `t`**:

```text
MAE(z, s, t) = (1 / n) * sum over tau <= t of | y(z, s, tau) - yhat(z, s, tau) |
```

- only forecasts **already realized at or before `t`** enter the sum;
- **no year after the slider position is ever read** -- moving the slider back must lower the
  number of years, never keep them;
- **`n`, the number of evaluated years, is displayed** beside the value;
- if `n < 2`, the field shows **`historique insuffisant`** instead of a figure;
- the MAE is **never converted into high / medium / low confidence**. A confidence label is a
  three-state vocabulary, and section 3.4 forbids exactly that.

This field is the only place on the page where the reliability of "next year resembles this
year" is visible in the specific cell the reader is looking at.

## 9. Cross-reference

- Contract and layer rules: `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`.
- Availability mask: `reports/canonical/HERALD_57_FR_ZE2020_AVAILABILITY_MASKS.md`, DEC-082.
- Engine and the absence of forecast states: `reports/canonical/HERALD_58_...`, DEC-084, DEC-085.
- Ranking coverage: `reports/canonical/HERALD_59_FR_ZE2020_RANKING_GAP_AUDIT.md`, DEC-086.
- Leakage-safe relation input: `reports/canonical/HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md`.
- Sector-to-sector tiers and their scope: DEC-066; France's single edge: DEC-060.
