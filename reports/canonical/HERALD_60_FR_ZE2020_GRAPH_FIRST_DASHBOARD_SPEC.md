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
| **Size** | observed economic volume of the zone, **see the summation rule below** | same |
| Edges | ZE-to-ZE relations, subject to per-year availability | `fr_ze2020_temporal_relation_signals.csv.gz` |

**Summation rule, pre-registered.** `total_establishment_creations` is stored **repeated
across the nine sector rows of each ZE-year**. Summing the column directly inflates every
volume by exactly **9.0x** -- verified: the naive column sum is 110,358,018 against a correct
12,262,002.

- exactly **one distinct value per ZE-year** is required, and a build that finds more aborts;
- that single value is the one used;
- it is checked equal to the **sum of the nine sector values**, which holds in every ZE-year
  of the current panel;
- **the repeated column is never summed.**

This is a silent-error class, not a rounding concern: a nine-fold volume would look
plausible and change every node size on the macro graph.

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

## 3.5 The map, as secondary context

Section 7 requires the map to be validated, so it must be specified.

| Property | Fixed |
|---|---|
| Source | `data/external/ze2020_geometry.geojson` |
| Coverage | **280/280 canonical ZEs**, verified by join at build time; a build that covers fewer aborts |
| Out-of-scope geometry | the file holds **306** features; the **26** outside the canonical 280 are **explicitly excluded and counted**, never silently dropped |
| Colour | the **same** macro observed change `tau(z, t)` as the macro graph nodes, on the same scale |
| Interaction | clicking a zone selects it, synchronised with the graph |
| Role | **secondary context**: no edges are drawn on the map, and no prediction ever colours it |

The map and the macro graph must never disagree: one scale, one quantity, one legend.

## 3.6 Edge density, bounded

The corpus is far too large to draw at once: up to **12,600** derived relations and
**27,683** commuting edges per year. Rendering everything would produce an unreadable mat
that no visual check could pass, and silently sampling it would be worse -- the reader could
not tell a thinned graph from a sparse one.

| Rule | Fixed |
|---|---|
| Initial view | **all nodes**, no territory hidden |
| Edges | drawn **only for the selected ZE**, on the incidence rule of 3.6.1 |
| Counter | every layer shows **`X relations affichées sur Y disponibles`** |
| Sampling | **none**. **E5 applies no cap of any kind**; any future cap requires a new DEC and must appear in the counter and the legend |
| Layers | **toggled, never overlaid** |

Hiding a territory would misrepresent coverage; hiding edges until a zone is selected only
defers detail. The distinction is deliberate: nodes are the population, edges are the
detail.

#### 3.6.1 What "edges of the selected ZE" means

`ze_similarity` and commuting are **directed**, so "the edges of a zone" is ambiguous until
fixed. It is fixed here:

| Rule | Fixed |
|---|---|
| Selection | **all incident edges**: `source == selected_ZE` **OR** `target == selected_ZE` |
| Direction | the **stored direction is preserved and drawn with an arrow** -- incidence decides visibility, never orientation |
| Tooltip | names **origin and destination explicitly**, so an arrow is never the only cue |
| Reciprocal pairs | where both directions exist they are **two edges on separate deterministic curves**, never merged into one line |
| Non-incident edges | **never drawn** |
| Counter | counts **directed records**, so a reciprocal pair counts as **two**, never collapsed into one relation |

Merging two directions into one line would turn an asymmetric commuting flow into a symmetric
one, which is a different economic statement about the territory.

Section 7.1 tests incidence, direction preservation and reciprocal-pair separation.

## 4. Layer separation, and the evidence scale of each

**Hard rule, carried from HERALD_56 section 5:** each species of edge is a separate layer,
with its own legend, its own grain statement and its own evidence scale. Layers are never
summed, averaged, overlaid or drawn in one another's style.

| Layer | Grain | Source | Evidence scale |
|---|---|---|---|
| ZE to ZE, trajectory similarity | **stored at ZE-sector x year, rendered at ZE x year after deduplication** -- see 4.1 | `ze_similarity` family | `EXPLORATORY_DERIVED`, single status -- see section 8.2. **DEC-066 tiers do not apply** -- they govern sector-to-sector relations |
| **ZE to ZE, functional mobility (commuting)** | **ZE x snapshot** | `fr_ze2020_commuting_strict_ex_ante_edges.csv.gz` | `carried_forward_from_snapshot`; snapshot year and age **attached to every edge**, surfaced as described below |
| sector to sector, observed precedence | **country**, not ZE -- a **separate national view**, see below | Phase 7 **records** (not "promoted edges": 5 of 9 are exploratory) | DEC-066 tiers, with the grain stated on the layer |
| sector to sector, structural NAF/NACE | nomenclature | **absent until E6 passes** | not applicable |

**Commuting and trajectory similarity are never merged, never overlaid and never share an
encoding.** They are different objects: one is an observed flow of workers carried forward
from a snapshot four to eight years old, the other is a correlation computed from the same
births panel that the rest of the page displays. A reader who cannot tell them apart would
be reading an official statistic and a derived correlation as one thing. The commuting layer therefore
carries its snapshot year and age as **data on every edge**, surfaced three ways:

- in the **tooltip** of any edge;
- as **persistent text on the selected edge**;
- in the **layer header**, which states the snapshot year and age governing the current view.

**Never as permanent text over every line.** Thousands of labels would collide, which would
contradict the no-overlap requirement of section 7.2. The metadata is attached to all edges
and shown where a reader is actually looking.

**The national layer is a separate retrospective view, outside the ZE2020 mask.**

Section 5 requires every layer to consult the availability mask before rendering. The
national Phase 7 relations **cannot** satisfy that: the mask marks
`sector_to_sector_comovement` and `temporal_precedence_signal` as `unavailable /
not_constructed` in **all fourteen years**. Subordinating this layer to the mask would
therefore hide it permanently; subordinating it to the year slider would be worse, since its
windows are not the slider's years.

| Property | Fixed |
|---|---|
| Placement | its **own national view**, not a layer of the ZE2020 graph |
| Mask | **outside** the ZE2020 availability mask, which governs ZE-grain relations only |
| Slider | **not subordinate to the year slider**; the view carries its own window labels |
| Source | exactly `data/processed/herald_observatory_v04_granular/granular_relation_edges.csv`, filtered to France, with path and grain in the header |
| Caveat | the windows are **retrospective estimation windows and do not represent ex-ante availability**, stated in the view |

**They are not called "promoted edges".** Verified content: **9 French rows**, of which
**1** is `ROBUST_ORIGINAL`, **3** `FINE_GRAIN_SUPPORTED` and **5** `EXPLORATORY_FINE_GRAIN`.
Five are exploratory, so "promoted" would overstate the majority of the layer. The neutral
term used throughout is **records**.

**Nine records, four directed pairs.** The nine rows are four ordered sector pairs repeated
across different estimation windows:

| Pair | Records | Windows |
|---|---|---|
| RU -> MN | 2 | 2020-2025 (`ROBUST_ORIGINAL`), 2019-2024 (`FINE_GRAIN_SUPPORTED`) |
| MN -> BE | 3 | 2020-2025 and 2018-2023 (`FINE_GRAIN_SUPPORTED`), 2019-2024 (exploratory) |
| OQ -> MN | 3 | 2018-2023, 2019-2024, 2020-2025 (all exploratory) |
| KZ -> FZ | 1 | 2020-2025 (exploratory) |

Drawn as nine straight lines they would coincide in four places, hiding both tier and window.
Therefore:

- **curved multi-edges with a deterministic offset** per record;
- each line keeps its **own window, beta, q_fdr, tier and provenance**, visible on selection;
- **never collapse to the highest tier, and never average across windows** -- a pair present
  in three windows at three strengths is three findings, not one.

**RU->MN is never presented as a relation measured in the selected ZE.** It was pooled across
all 280 zones at country grain, so the national view never inherits a ZE selection.

### 4.1 ZE-to-ZE similarity is stored nine times per pair

The artifact carries **ZE-sector** nodes, so each ZE-to-ZE relation appears **once per
sector**. Verified for decision year 2020: **12,600 rows = 1,400 distinct ZE pairs x 9
replicas**, and across the nine replicas `signal_strength`, `stability_score` and
`relation_direction` are **identical**.

| Rule | Fixed |
|---|---|
| Rendering | **one edge per ZE pair** |
| Precondition | **exactly nine replicas** per pair, else the build **aborts** |
| Value agreement | direction, `signal_strength`, `stability_score`, evidence source and status **identical** across the nine, else the build **aborts** |
| Counter | the macro layer reports **1,400 available**, never 12,600 |

**This is deduplication of identical replicas, not aggregation.** Nothing is averaged,
summed or selected: the nine rows carry one value, and one edge carries it. Recording the
distinction matters because an aggregation would be a modelling choice, and this is not one.

### 4.2 Micro layer -- sector to sector inside one ZE

The micro graph defines nine sector nodes but had no edges. Added:

| Property | Fixed |
|---|---|
| Grain | **ZE x sector pair x year** |
| Source | `fr_ze2020_temporal_relation_signals.csv.gz`, family `intra_ze_sector` -- leakage-safe (HERALD_38) |
| Availability | **2017-2025 only**, per the DEC-082 mask |
| Direction | undirected, as stored |
| Evidence status | **`EXPLORATORY_DERIVED`**, single status |
| Style | dashed, width `abs(signal_strength)`, **signed value in the tooltip** |

**Two absences that must never look alike.** The family emits **20 relations per year across
the whole panel**, so in 2020 only **20 of 280 zones** carry one at all. Therefore:

- *layer unavailable* -- the year is before 2017: the page states `insufficient_history`;
- *layer available, no relation for this ZE* -- the normal case for 260 zones: the page says
  so explicitly, in the counter and in words.

Conflating them would let a reader read "no measured relation here" as "relations not
computed yet", or the reverse.

### 4.3 `cross_ze_same_sector` is out of scope for E5, by decision

**`cross_ze_same_sector` contains sector-specific ZE-sector relations. Unlike
`ze_similarity`, its sector rows are not interchangeable replicas and must never be
deduplicated across sectors.**

An earlier revision of this section claimed it had "the same nine-replica structure as
`ze_similarity`". That was false, and verification shows the two families are not comparable
at all:

| Decision year 2020 | `ze_similarity` | `cross_ze_same_sector` |
|---|---:|---:|
| Rows | 12,600 | 12,600 |
| Distinct ZE pairs | **1,400** | **11,675** |
| Rows per pair | exactly 9 | **1 to 4** |
| Pairs whose sectors differ in strength | **0** | **881** |

Deduplicating this family the way section 4.1 deduplicates `ze_similarity` would collapse
12,600 sector-specific relations onto 11,675 pairs and destroy genuine variation in 881 of
them. The rule of 4.1 applies to `ze_similarity` **only**, and this table is recorded so no
future pass generalizes it.

The family is **deliberately not rendered in E5**, and that exclusion is written rather than
left to silence: it would need its own layer, its own grain statement and its own counter,
and E5 already carries four layers. **Adding it later requires a new DEC**, and that DEC must
carry its own deduplication rule -- or the explicit decision that none applies.

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
| **Geographic coverage** | **280 canonical ZEs included and 26 out-of-scope features excluded**, both counted |
| **Macro volume reconciliation** | one distinct `total_establishment_creations` per ZE-year, equal to the sum of its nine sectors; the repeated column never summed |
| **Similarity deduplication** | exactly **nine identical replicas collapse to one edge per ZE pair**; a differing replica aborts |
| **National view temporality** | the national records are **outside the ZE2020 mask and independent of the year slider**, and their windows are labelled retrospective |
| **Micro layer present** | the `intra_ze_sector` layer renders, and **"no relation for this ZE" is visibly distinct from "layer unavailable"** |
| **National record counts** | **9 records, 4 distinct directed pairs, tiers 1 / 3 / 5**, each record keeping its own window |
| **MAE source** | the historical error reads **only** the DEC-084 artifact; the `NOT_COMPARABLE` supplement is never opened |
| **Counters reconcile** | every `X relations affichées sur Y disponibles` matches the underlying data, with `Y` = 1,400 for the macro similarity layer, counted as **directed records** |
| **Edge incidence** | only edges with `source == selected_ZE` or `target == selected_ZE` render; **stored direction is preserved**; a reciprocal pair renders as **two separate curves** and counts as two |
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

With the slider on year `t`, the forecast shown is **for `t+1`**, and the label says so.

| Field | Content |
|---|---|
| **Dernière observation** | last observed value, year `t` |
| **`Prévision pour [t+1] par persistance`** | the same value, **with the reason it repeats stated in the panel**. The horizon is written into the label, never left implicit |
| **Erreur absolue moyenne historique** | MAE of persistence for that ZE-sector, over realized years only |

The second field prints the same number as the first by construction. That is not a defect
to hide: the panel says why, which is more honest than omitting a field the engine genuinely
produces.

The third field is defined **causally with respect to the selected year `t`**:

```text
MAE(z, s, t) = (1 / n) * sum over tau <= t of | y(z, s, tau) - yhat(z, s, tau) |
```

- the **only** admissible source is the official DEC-084 artifact,
  `fr_ze2020_sectoral_persistence_predictions_v1.csv`, over its realized years **2019 to
  `t`**;
- the **`NOT_COMPARABLE` persistence-only supplement is never read here**, silently or
  otherwise. It covers 2013-2025 on a different population and would quietly widen the
  history behind a number the reader believes comes from the audited window;
- only forecasts **already realized at or before `t`** enter the sum;
- **no year after the slider position is ever read** -- moving the slider back must lower the
  number of years, never keep them;
- **`n`, the number of realized forecasts, is displayed** beside the value;
- if fewer than **two** realized forecasts exist at `t`, the field shows
  **`historique insuffisant`** instead of a figure. With the window starting at 2019, this is
  the normal state for `t = 2019`;
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
- Sector-to-sector tiers and their scope: DEC-066; **one robust record among nine French
  records** across four directed pairs: DEC-060, DEC-066.
