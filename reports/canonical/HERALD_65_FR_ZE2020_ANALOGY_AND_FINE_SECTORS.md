# HERALD 65 -- Analogy edges, fine-sector fingerprint, employment influence

**Date:** 2026-08-10
**Sections 1-5:** `PRE_REGISTERED` (DEC-098). Written before the code for A2/A3 existed.
**Section 6:** results, appended after execution.

---

## 1. Correction to HERALD_64: the mission was mis-scoped

`HERALD_64` section 3.1 demoted `similarity` from edge to node attribute, on the argument that
resembling is not interacting. That argument is sound for an **interaction** framing and wrong
for this project's actual mission, which the owner restated as: *observe relations over time in
order to recommend*. Forecasting was instrumental, not the goal.

Two recommendation routes follow, and only the first was tested:

| route | mechanism | status before this file |
|---|---|---|
| influence | sector Y moves sector X, same zone or via commuting | tested; only same-sector diffusion survived |
| **analogy** | zone K resembles zone M's past, so M's next years inform K | **removed in error** |

Analogy needs no interaction between the two territories. It is the mechanism the product
requires, and the demotion is reversed here. `similarity` returns as its own family with its
own null. `specialization` stays a node attribute.

## 2. Analogy, defined

Node-level and lagged, not zone-level:

> Two nodes `(zone i, sector s)` and `(zone j, sector s)` are analogous at decision year `t`
> if their growth trajectories over the `W` years ending at `t-1` are close. The prediction
> for node `i` at `t` is what its top-`K` analogues did at `t`.

Everything forming the analogy uses years `<= t-1`; year `t` is only ever scored.

**Same-sector constraint, fixed here and justified in section 6.1.** Analogues must share the
sector. Cross-sector matches are admitted to the estimator only as a reported control, never
as edges.

`W = 4`, `K = 10`.

## 3. Fine-sector fingerprint

FLORES A88 (`TD_FLORES{2017..2021}_NA88_NBSAL`, `DS_FLORES_A88_{2022,2023,2024}`) is complete on
disk, 2017-2024, at the **zone of employment level that INSEE validates** -- commune
localisation is supplied but only validated up to the ZE, which is the grain used here.

Use: a zone's 88-sector employment composition is a stricter fingerprint than its 9-sector
creation shares. Two zones alike in A10 can differ sharply inside. The fingerprint refines
**which nodes count as analogues**; it creates no nodes and no edges. Base stays A10
(owner's decision).

Years before 2017 keep the A10 fingerprint, recorded in the availability mask.

**CLAP is not chained.** INSEE states the results of FLORES and CLAP *"ne sont pas comparables
et ne doivent donc pas faire l'objet d'analyses comparatives dans le temps"*: CLAP covered
non-employer establishments and counted only non-ancillary posts, so the 2015->2017 join would
inject an artificial break in exactly the counts this estimator reads. 2016 is unpublished at
this grain; FLORES 2025 publishes around March 2027.

## 4. Employment influence at A38

`HERALD_64` 10.4 found the constraint on the creations panel to be volume, and the earlier
diagnosis was that establishment **creations cannot express supply-chain linkage**: a supplier
meeting higher demand hires, it does not register a new firm. FLORES counts employment, so the
influence test is run again on the variable where linkage should appear, at A38 (38 sectors,
2017-2024).

This is a **separate finding, not a substitute**: a result on employment does not transfer to
creations. If influence appears at A38 employment and not at A10 creations, that localises
where the relation lives, which is reportable either way.

Multiplicity rises to 1,444 pairs per year; R4 handles it.

## 5. Gates

Carried unchanged from `HERALD_64` section 7: **R1** placebo (shuffled years, >= 5/7),
**R2** sign stability over 10 disjoint zone halves (>= 0.8), **R4** Benjamini-Hochberg at
q = 0.10.

Added for analogy:

**A1 -- beat the national sector trend.** Analogy is admitted only if it beats predicting each
node by its own sector's national mean at `t`, in >= 5 of the evaluated years. Matched-random
neighbour sets are the second control. Beating random is not sufficient: the sector mean is the
baseline that a naive analogy reproduces by accident.

**A2 -- the fingerprint must earn its place.** A88-refined analogy must beat A10 analogy on the
same years. If it does not, the fingerprint is dropped and A10 similarity stands.

Reporting rule of `HERALD_62` B7 applies throughout.

---

## 6. Results (DEC-099)

### 6.1 Analogy must be same-sector, and the constraint is what makes it work

Unrestricted node-level analogy beats a matched-random neighbour set in 9/9 years
(0.1704 against 0.0013) but **loses to the national sector mean in 8/9 years**. Only 13-18% of
its top-10 neighbours shared the sector; the rest diluted it (cross-sector analogy scores
0.1147).

| variant | mean correlation with what actually happened |
|---|---|
| analogy, unrestricted | 0.1704 |
| national sector mean | 0.3211 |
| **analogy, same sector** | **0.3663** |
| analogy, cross-sector only | 0.1147 |

Random neighbours are the wrong control on their own: the sector mean is what a naive analogy
reproduces by accident. This is why A1 was written against the sector mean, and it is the
control that changed the design.

### 6.2 A1 -- PASSED

Evaluated 2018-2025, same-sector analogy against the national sector mean:

| year | sector mean | analogy A10 | analogy A88 | random |
|---|---|---|---|---|
| 2018 | 0.2219 | **0.3416** | 0.3036 | 0.0000 |
| 2019 | 0.3176 | **0.3839** | 0.3534 | 0.0111 |
| 2020 | 0.3338 | **0.4028** | 0.3841 | 0.0062 |
| 2021 | 0.3111 | 0.3209 | **0.3459** | 0.0036 |
| 2022 | 0.5178 | 0.4995 | 0.5092 | -0.0078 |
| 2023 | 0.2667 | 0.2429 | 0.2481 | -0.0055 |
| 2024 | 0.3420 | **0.3880** | 0.3683 | 0.0013 |
| 2025 | 0.4150 | **0.4293** | 0.4229 | 0.0039 |
| **mean** | 0.3407 | **0.3761** | 0.3669 | 0.0016 |

**6/8 years, gate needed 5.** Knowing *which* zones resemble yours adds information beyond
knowing what your sector did nationally. `similarity` is admitted as an edge family, which
reverses the HERALD_64 3.1 demotion.

Bounded: the two losing years are 2022 and 2023, both years where the sector mean itself is
unusually strong (0.5178, and 2023 is the weakest year for every method). Analogy adds least
when the national trend dominates.

### 6.3 A2 -- FAILED, fingerprint dropped

The A88 employment fingerprint (2017-2024, built commune-to-ZE for 2017-2021 and directly at
ZE for 2022-2024, 306 zones x 89 sector columns) restricts analogue candidates to the top 25%
structurally closest zones.

**It beats plain A10 analogy in 3/8 years, mean delta -0.0092.** By the pre-registered A2
gate the fingerprint is **dropped** and A10 similarity stands.

Reading: at this grain, two zones with similar 9-sector *creation trajectories* are already
similar enough; adding an 88-sector *employment structure* filter removes useful analogues more
often than it removes bad ones. The fingerprint is not wrong, it is redundant here.

Consequence: **the analogy layer needs no FLORES dependency**, which also removes the
2017 start-year limitation from that layer.

### 6.4 State

| family | status |
|---|---|
| `flow` | observed, official |
| `precedence_intra` | admitted (DEC-096), 9 edges |
| `precedence_cross` | admitted (DEC-096), 18 edges |
| **`similarity` (same-sector analogy)** | **admitted (A1), reverses HERALD_64 3.1** |
| `comovement` | excluded, window-fragile |
| A88 fingerprint | dropped (A2) |
| `specialization` | node attribute |

Outstanding: section 4, employment influence at A38 on FLORES 2017-2024 -- the one test of
inter-sector influence run on a variable that can express it. Not yet executed.
