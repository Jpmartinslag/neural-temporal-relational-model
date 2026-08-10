# HERALD 63 -- Learned sector-affinity graph over a fixed commuting prior

**Date:** 2026-08-10
**Sections 1-8 status:** `PRE_REGISTERED` (DEC-093) -- written before any code ran and before
any metric from it existed.
**Section 10 status:** `SECTOR_GRAPH_REJECTED_MAIN_DOES_NOT_BEAT_PLACEBO` (DEC-094) --
executed; all five gates failed. See 10a: an earlier status string read
`..._PLACEBO_BEATS_MAIN`, which overstated overlapping seed distributions.

---

## 1. Why this is opened, and why it is not a re-tune

`HERALD_62` Part C closed the ZE-level neural line with four measured findings: no forecast
gain (C1, C6), no learning signal distinguishable from a refitted linear model (C2), zero
weight in ex-ante blends (C3), and a graph containing no measurable learned content
(C7c, r = 0.9994 with the learned term zeroed).

The diagnosis is arithmetic, not a hyperparameter. 280 zones give 78,120 possible directed
edges against ~3,900 ZE-year observations. Arm D of C6 measured the consequence directly:
weakening the prior does free the graph, and the five seeds then converge on *different*
structures (seed r = 0.695).

This specification does not change the model to chase the same target. **It changes the size
of the structure-learning problem by three orders of magnitude**, which is the only thing
that was ever binding.

| | free parameters | observations |
|---|---|---|
| ZE x ZE graph (closed by C6/C7) | 78,120 | ~3,900 |
| **sector affinity `S_t`, 14 years** | **1,134** | **35,280** |

Under DEC-081 Q3 this qualifies as an exogenous **sectoral** structure, which is the one
category Q3 permits to authorise another model experiment -- conditional on surviving a
matched placebo. That placebo is G1 below and is the gate this specification is built around.

`HERALD_60`/DEC-087 excluded `cross_ze_same_sector` as a free edge family by written
decision. This specification **reopens cross-ZE sector coupling in a different form** -- not
as free edges, but as the product `C[i,j] x S_t[s,r]` where `C` is fixed and official. The
reopening is recorded here rather than left implicit.

## 2. The question

> Does a sector-affinity matrix learned per year, carried between zones by a fixed official
> commuting prior, encode sector-specific structure that a sector-shuffled placebo does not?

Forecast performance is a **secondary** question here, reported in full but not the basis of
designation. C1, C3 and C6 have already established that the ZE-total target is dominated by
the previous year; nothing in this design is expected to overturn that, and this expectation
is written down now so that a null forecast result cannot later be presented as a surprise.

## 3. Design

### 3.1 Grain and data

`y[i,s,t]`: establishment creations, 280 ZE2020 x 9 A10 sectors x 2012-2025 = 35,280 cells.
Source `side_creations_a10_ze2020_through_2025_v1.csv` (3,920 rows x 9 sector columns).
`HERALD_57`/DEC-082 established this population has 0 unavailable cells and one observed zero
(`5218/2016/JZ`), so no availability mask construction is required.

### 3.2 Features -- causal by construction

Per cell, computed **only** from years `<= t-1`:

```text
lag1 = y[i,s,t-1]      lag2 = y[i,s,t-2]      lag3 = y[i,s,t-3]
g1   = log1p(lag1) - log1p(lag2)                   <- causal, NOT the DEC-088 definition
g2   = log1p(lag2) - log1p(lag3)                   <- see section 9, defect 1
share_lag1 = lag1 / total[i,t-1]
log1p(lag1), log1p(total[i,t-1])
```

`g1` and `g2` are the **causally recomputed** forms. The DEC-088 leak
(`g1 = (y[t]-y[t-1])/y[t-1]`) is structurally impossible here: no feature reads year `t`.

### 3.3 Target

```text
r[i,s,t] = log1p(y[i,s,t]) - log1p(lag1)
```

Persistence is exactly `r = 0`. The model must earn every deviation from the null, and the
null is not a separate model that could be tuned.

### 3.4 The graph

```text
A[(i,s) -> (j,q)]  =  C_t[i,j]  x  S_t[s,q]
```

- **`C_t`** -- official commuting, **fixed, never learned**, from
  `fr_ze2020_commuting_strict_ex_ante_edges.csv.gz` (DEC-073), release-aware: decision year
  `t` uses only the snapshot whose strict ex-ante interval contains `t`. Decision years
  2016-2025 are available, covering all seven origins. Cross-ZE directed edges, row
  normalised. Within-zone weight is supplied by a single learned scalar
  `C_t <- sigmoid(a)*I + (1-sigmoid(a))*C_cross`, so within-zone against cross-zone mixing is
  learned rather than assumed.
- **`S_t`** -- 9x9, **learned, one per year**, `S_t = softmax(L[t], dim=-1)`, `L` initialised
  at zero (uniform affinity). **No temporal smoothness penalty of any kind.** C4b established
  that such a penalty is what froze the previous graph; imposing one here would prejudge the
  dynamism question this experiment exists to answer.

Message passing, factorised so the product is never materialised:

```text
z[i,q] = sum_j C_t[i,j] e[j,q]        # 280x280 over zones
m[i,s] = sum_q S_t[s,q] z[i,q]        # 9x9 over sectors
```

### 3.5 Causal serving rule for `S_t`

For evaluation year `t`, training uses target years `<= t-1` only. `S_t` for the evaluation
year is therefore never trained, and **the model is served with `S_{t-1}`**. This is stated
now because the alternative -- fitting `S_t` on the year being scored -- would be a leak of
exactly the class DEC-088 documented.

## 4. Arms

| arm | description |
|---|---|
| `main` | learned `S_t`, fixed `C_t` |
| `placebo_sector` | sector labels permuted **per zone, held fixed across all years** (seed 20260810, independent of the model seed). Every sector time series and every zone-year total stay intact, so persistence scores identically; only the correspondence between a sector's identity and its slot *across zones* is destroyed -- the one thing a zone-shared `S_t` can exploit. **Corrected from an earlier draft** that permuted per (zone, year): that scrambles each cell's own history, hands the placebo a strictly harder target, and would make beating it meaningless. |
| `no_graph` | `m = 0`; identical encoder and features, no message passing |

Baselines on identical populations: `persistence` (`r = 0`) and `ridge` on the same causal
features.

Protocol: 7 rolling origins 2019-2025, 5 seeds per arm, train on `target_year <= t-1`.

## 5. Gates, pre-registered

**G1 -- placebo (the designating gate).** `main` must beat `placebo_sector` on aggregate
ZE x sector WMAPE **and** in at least **5 of 7** years. Failure means `S_t` carries no
sector-specific information, and no interpretation of `S_t` is permitted -- not as a figure,
not as an appendix, not as "suggestive".

**G2 -- does the graph add anything.** `main` must beat `no_graph` on aggregate WMAPE.
Failure means the features alone explain the result and the relational layer is decorative.

**G3 -- forecast, reported but not designating.** `main` against persistence and Ridge at
ZE x sector, aggregate and per year, plus NDCG@3 / Precision@3 for the within-zone sector
ranking. **Expected to fail against persistence**, per section 2.

**G4 -- dynamism.** `S_t` counts as dynamic only if `corr(S_2019, S_2025) < 0.95`
**and** seed-pairwise correlation of `S_t` is `>= 0.90`. Both conditions are required: C6
arm D produced movement with seed r = 0.695, and that was reported as noise, not dynamism.

**G5 -- artifact control, mandatory before any interpretation of `S_t`.** C7 established
that a structure can be reproduced with the learned term zeroed. The same control runs here:
rebuild predictions with `S_t` replaced by the uniform matrix `1/9`. If the difference in
WMAPE is below 1% relative, `S_t` is decorative regardless of G1-G4.

## 6. Reporting rule

`HERALD_62` B7 applies unchanged: if the gates fail, `S_t` and the predictions may be
presented as a direction for future work, and the failure must be stated in the same place.

Additionally fixed now: **G1 failure forbids publishing the sector affinity matrix in any
form.** A 9x9 table of named sectors is readable and persuasive, which is precisely why it
must not be shown if a shuffled placebo produces one just as good.

## 7. What a pass would and would not authorise

A pass authorises: describing a per-year learned sector-affinity structure that survives a
matched placebo, carried across zones by an official commuting prior, on France ZE2020 x A10.

A pass does **not** authorise: any causal claim, automatic recommendation, extension beyond
France, or the claim that the ZE-level graph is dynamic. `C_t` is fixed by construction; any
dynamism in the ZE x ZE product comes from `S_t` and must be attributed to it.

## 8. Cross-reference

- Closure of the ZE-level line: `HERALD_62` C1-C7, DEC-088 to DEC-092.
- Contract and Q3: `HERALD_56`, DEC-081.
- A10 population: `HERALD_57`, DEC-082.
- Commuting provenance and release-aware rule: DEC-073, `HERALD_44`.
- Structure learning deferred for short T: DEC-046.
- `cross_ze_same_sector` exclusion being reopened: `HERALD_60`, DEC-087.

---

## 9. Implementation addendum -- two defects found and fixed before any gate was read

Recorded because both were found after code existed, and the distinction between "fixed a
numerical bug" and "tuned until the gates passed" is the whole difference.

**Defect 1 -- division by the observed zero (the material one).** Growth features were first
written as ratios, `g1 = lag1/max(lag2, 1e-9) - 1`. `HERALD_57`/DEC-082 recorded one observed
zero in this population (`5218/2016/JZ`). That cell produced `g1 = 4e9` and a feature
standard deviation of ~4e7, so standardisation annihilated every other feature, and whichever
fold placed the zero on the test side diverged: eval year 2019 scored WMAPE 53.8 against
persistence 0.141.

Fixed by defining growth as a log1p difference, `g1 = log1p(lag1) - log1p(lag2)`, which is
finite at zero and shares the scale of the target. **This is a correctness fix, not a
tuning choice**: the pre-fix run was numerically invalid, not merely worse, and no gate was
computed from it.

**Defect 2 -- no early stopping.** The first fold fits four years. Early stopping on the last
training year was added, with `S` served from the last *fitted* year rather than the last
training year, keeping the causal serving rule of section 3.5 intact. This alone did **not**
fix defect 1 (the 2019 fold still diverged, at 53.8), which is what led to the real diagnosis.

**Disclosure.** A first grid (`7836271`, 15 tasks) ran before defect 1 was found. Its
aggregates were dominated by the diverged fold (`main` 1.73, `placebo_sector` 6.33 against
persistence 0.118) and are **discarded in full, not partially reused**. Gate values printed
from that run are void. The grid was relaunched as `7836288` after the fix.

Git cannot independently prove that the fix preceded reading the corrected gates, since both
happened in one session; what can be checked is that the diverged values above are recorded
here rather than omitted.

---

## 10. Results -- all five gates failed

**Status:** `SECTOR_GRAPH_REJECTED_PLACEBO_BEATS_MAIN` (DEC-094).
Slurm `7836288`, 30/30 tasks COMPLETED, 3 arms x 5 seeds x 7 rolling origins.

### WMAPE at ZE x sector, mean over 5 seeds

| arm | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | mean |
|---|---|---|---|---|---|---|---|---|
| persistence | 0.1409 | 0.1010 | 0.1566 | 0.1546 | 0.0852 | 0.0975 | 0.0868 | **0.1175** |
| `no_graph` | 0.1275 | 0.1227 | 0.1324 | 0.1834 | 0.1291 | 0.0835 | 0.0710 | 0.1214 |
| `placebo_sector` | 0.1133 | 0.1410 | 0.1326 | 0.1805 | 0.1378 | 0.0878 | 0.0743 | 0.1239 |
| **`main`** | 0.1132 | 0.1506 | 0.1325 | 0.1670 | 0.2112 | 0.1010 | 0.0763 | **0.1360** |
| ridge | 0.2096 | 0.1304 | 0.1819 | 0.2077 | 0.1694 | 0.0817 | 0.0718 | 0.1504 |
| `main`, S = uniform | 0.1513 | 0.1504 | 0.1325 | 0.1671 | 0.1743 | 0.1039 | 0.0764 | 0.1366 |

### Gate outcomes

| gate | criterion | measured | verdict |
|---|---|---|---|
| **G1 placebo** | beat `placebo_sector`, aggregate and >= 5/7 | 0.1360 vs **0.1239**, 3/7 | **FAIL** |
| **G2 graph** | beat `no_graph` | 0.1360 vs **0.1214** | **FAIL** |
| **G3 forecast** | beat persistence and Ridge | 0.1360 vs 0.1175 (3/7) / 0.1504 (3/7) | **FAIL** (predicted in section 2) |
| **G4 dynamism** | `corr(S_2019,S_2025) < 0.95` AND seed-corr `>= 0.90` | -0.0871 and **0.7044** | **FAIL** |
| **G5 artifact** | `S = uniform` at least 1% worse | **0.432%** | **FAIL** -- `S_t` decorative |

Ranking, NDCG@3 on within-zone sector growth: persistence **0.4849**, `placebo_sector`
0.4140, `no_graph` 0.4076, `main` 0.4071, ridge 0.3785. Persistence wins that too.

### Reading

The decisive number is G1: **the placebo beats the real model.** This is stronger than "no
signal was found". Learning affinities between true sectors is *worse* than learning them
between shuffled ones, which is the signature of 81 parameters per year fitting noise. G5
agrees independently -- replacing the learned `S_t` with the uniform matrix costs 0.43%.

G4 reproduces C6 arm D exactly one level down: `S_t` does move across years, and the seeds
do not agree on how (0.704). Movement without reproducibility was pre-registered as noise
and is reported as noise.

`main` does win 2019 (0.1132 against persistence 0.1409), which the smoke test had already
shown. That is why the gate required 5 of 7 years rather than a best year.

**Consequence under section 6:** G1 failed, so the sector-affinity matrix must not be
published in any form -- no figure, no appendix, no "suggestive" caption.

### What this closes, and what it does not

Closed: the hypothesis that shrinking the structure-learning problem from ZE x ZE to sector
x sector rescues the relational layer. It does not. The constraint was never only parameter
count; at this grain the target is dominated by the previous year, and `no_graph` -- a plain
MLP on causal features, the best neural arm here -- still loses to persistence.

Not closed, and untouched by this result: the exploratory relational layer
(`fr_ze2020_exploratory_relation_signals.csv`), which is an association catalogue rather
than a forecasting component, and the graph-first dashboard specified in `HERALD_60`. Neither
depends on a forecast gain that now has three independent refutations behind it
(DEC-090, DEC-091, DEC-094).

### 10a. Seed-dispersion check, and a correction to how G1 was first stated

Run after section 10 was written, because the first phrasing asserted more than the data
carries.

Per-seed aggregate WMAPE:

| arm | s1 | s2 | s3 | s4 | s5 | mean | sd |
|---|---|---|---|---|---|---|---|
| `main` | 0.1390 | 0.1264 | 0.1450 | 0.1379 | 0.1315 | 0.1360 | 0.0064 |
| `placebo_sector` | 0.1320 | 0.1220 | 0.1362 | 0.1144 | 0.1148 | 0.1239 | 0.0088 |
| `no_graph` | 0.1249 | 0.1240 | 0.1216 | 0.1191 | 0.1173 | 0.1214 | 0.0029 |

Worst `placebo_sector` seed (0.1362) is **worse** than the best `main` seed (0.1264): the two
distributions **overlap**. Dropping 2023, the outlier year, narrows the gap to 0.1234 against
0.1216.

No seed diverged; 2023 is elevated across all five `main` seeds (0.19-0.25), so it is a year
effect and not a repeat of the defect-1 blow-up.

**Correction.** Section 10 first read "the placebo beats the real model" and called it "the
signature of 81 parameters per year fitting noise". That overstates overlapping
distributions. The defensible statement is narrower:

> `main` **fails to beat** `placebo_sector`, which is what G1 required of it; the point
> estimate favours the placebo but the seeds do not separate. The robust reading is that
> `main`, `placebo_sector` and `no_graph` are **mutually equivalent** (0.121-0.136) and all
> three lose to persistence (0.1175).

The gate verdict is unchanged -- the burden was on `main` to demonstrate superiority, and
overlap does not discharge it. What changes is the strength of the mechanism claim.

G5 is unaffected and remains the cleanest evidence in this experiment: replacing the learned
`S_t` with the uniform matrix costs 0.432%, measured within-arm and free of the seed-variance
problem above.

**Also disclosed:** a single configuration was run -- 400 epochs, hidden 64, lr 0.01, no
hyperparameter search. A failure at one configuration is weaker evidence than an explored
space, and section 10 did not say so.

### 10b. Scope -- what these results do not touch

Recorded because the forecasting negatives in DEC-090/091/094 risk being read as a verdict on
the relational layer, which was not tested by any of them.

Untouched and still standing:

- the eight closed relational gates (DEC-069 to DEC-080) and the exploratory association
  catalogue, which are descriptive artifacts, not forecasting components;
- `HERALD_62` C7a: the mobility prior correlates with audited official commuting at
  **+0.9914**, empirically addressing the `HERALD_09` provenance concern;
- `HERALD_62` C4b: observed inter-ZE relations move **34.9%** over 2019-2025, measured
  outside any model and independent of every gate in this file.

The tested and rejected object is **the graph as a forecasting component**. The graph as a
descriptive relational object has not been evaluated here, and nothing in DEC-090, DEC-091
or DEC-094 licenses a claim about it.
