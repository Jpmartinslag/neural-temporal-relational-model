# HERALD 96 — Neural Granger / NAVAR on a multirelational universe: results

**Character:** strictly exploratory, synthetic only. "Relation" means a directed, temporal,
predictive association. **Not applied to France.**
**Jobs:** 7867595 (validation: 16 guards, 16 mutants, smoke), 7867596 (grid, 120 tasks, all
`COMPLETED`). **Seeds:** 9961–9965, never generated before; all calibration on 9951.
**Commits:** `3a9e434`, `3e692a1`, `4f4f00e`. Environment `herald-v5`.

---

## 1. Answer

The oracle works. No model recovers anything. By the interpretation matrix fixed before the
run, this is the row **"oracle passes and no model recovers: identification remains the
bottleneck."**

The formulation is not shown to be a valid future direction on this evidence. It is also not
refuted as an idea — what is refuted is that this implementation, at this scale, identifies
relations. The distinction is carried through §6.

## 2. The oracle: the instrument is sound

Median over five seeds, share of residual variance explained by the true arriving
contribution:

| scenario | scale | commuting-only | similarity-only | typed union | all pairs |
|---|---|---|---|---|---|
| `M0_NULL` | any | **+0.0000** | **+0.0000** | **+0.0000** | **+0.0000** |
| `M1` | 0 | +0.0108 | +0.0160 | +0.0160 | +0.0108 |
| `M1` | 1 | +0.1006 | +0.0799 | +0.1006 | +0.0799 |
| `M1` | 2 | +0.1105 | +0.1341 | +0.1105 | +0.1105 |

Exactly zero without a mechanism, monotone in the scale, and reaching **10 %** of the
residual at nominal scale — five times the ceiling HERALD 95 measured on raw growth, because
the target here is what a frozen local baseline could not explain.

The floor at scale 0 is worth stating: the edges exist and nothing propagates along them, yet
the oracle still marks 1.1–1.6 %. Economically similar zones co-move by construction. Any
gain below that figure is co-movement, not mechanism.

## 3. The arm: no recovery, anywhere

**Edge recovery is nil in every support, every scale and every family.** AUPRC against
prevalence at `M1`, scale 1:

| support | AUPRC | prevalence |
|---|---|---|
| commuting_only | 0.0112 | 0.0119 |
| similarity_only | 0.0780 | 0.0612 |
| typed_union | 0.0200 | 0.0221 |
| all_pairs | 0.0190 | 0.0190 |

Per family inside the typed union: commuting 0.0115 against 0.0109, similarity 0.0057 against
0.0053, complementarity 0.0054 against 0.0060. Every one of them is its own prevalence. The
arm ranks candidates no better than chance.

The out-of-commuting figure looks more promising and is not. In the typed union it reads
0.0838 at scale 1 against an out-of-commuting prevalence of about 0.084 — the prevalence
again — and in `M0_NULL`, where nothing propagates at all, it reads 0.0713 against 0.0596,
*above* its own prevalence by more than the mechanism scenario is. It is not tracking the
mechanism.

**The residual gain is negative and unstable.** Median at `M1`, scale 1: commuting_only
−0.0114, typed_union −0.0281, similarity_only −0.0093, all_pairs −0.1567. Per seed in the
typed union: `+0.0724, −2.6853, −0.0533, +0.0764, −0.0281`. One fit in five diverges
catastrophically, and the median is carried by that instability rather than by any signal.

**The gain does not respond to the scale.** The oracle rises from +0.016 to +0.101 to +0.111
across scales 0, 1 and 2; the arm's gain does not follow it in any support. Multiplying the
mechanism does not make the arm find it.

**`M0_NULL` stays clean.** AUPRC equals prevalence there too, so the arm invents nothing. It
is a valid method in the sense of not fabricating relations; it simply finds none.

## 4. The smoke was wrong, and that is why the final seeds exist

On seed 9951 the typed union returned a residual gain of **+0.0414** against commuting-only's
+0.0210 — an apparent near-doubling that looked like support for the multirelational
direction. On the five seeds that had never been generated, the same comparison is −0.0281
against −0.0114. The smoke result was noise, and reading it as a finding would have produced
a positive claim from a single draw.

## 5. Cost

Between 109 and 218 seconds per task, 977 to 6320 candidate pairs, a shared function of
identical size throughout. The arm is frugal; frugality is not the constraint.

## 6. What this does and does not establish

**Established.** With a frozen local baseline, a residual target, no local path, a support
containing the true out-of-commuting edges, and a mechanism the oracle confirms is worth 10 %
of that residual, this additive per-source arm identifies none of it, at any of three scales,
in any of four supports, in five seeds.

**Not established.** That the family of methods cannot work. Three specific limitations of
this implementation are visible in the results and none was addressed, because addressing
them would have been the architecture search the instruction forbids:

1. one fit in five diverges, so the optimisation is not reliable and the median is partly a
   measure of that;
2. the arm reads one signal's twelve features per zone, chosen for cost, where the
   mechanism's identifiability may need more;
3. the group penalty was calibrated on one smoke seed to a single value, not selected per
   task on training folds as HERALD 94's arms were.

A fair test of the formulation would fix all three first. What this stage establishes is that
the direction is **not supported by the present evidence**, not that it is closed.

**The bottleneck is identification, not candidate generation.** All-pairs contains every true
edge and recovers nothing; the typed union contains most of them and recovers nothing; the
commuting-only support recovers nothing among the edges it does contain. Widening the
candidate set does not help when the scorer cannot rank inside it.

## 7. France

**Not authorised.** The synthetic did not recover relations outside commuting, so the
precondition fixed in the specification is not met. No learned structure from this stage may
be presented as an association, a precedence or a candidate relation for France.

## 8. Text for "future work"

> A relational mechanism worth about a tenth of the residual left by a strong local baseline
> is present in the synthetic panel and is confirmed observable by an oracle that responds
> monotonically to its intensity and returns exactly zero in its absence. Neither the existing
> attention-based scorer nor an additive per-source Neural Granger arm identifies it, at any
> of three intensities or four candidate supports. Widening candidate generation to all pairs
> does not help, which locates the bottleneck in identification rather than in candidate
> proposal. Future work should target the identification step directly — a training objective
> that scores edges rather than only forecasts, a reliable optimisation for the additive form,
> and richer per-pair evidence — and should measure any proposal against the oracle ceiling
> rather than against a local baseline.

## 9. Lay summary

Earlier stages showed the model could not find economic relations between territories, and
that this was the model's fault rather than the data's. Two suspicions remained: perhaps it
was only ever allowed to look at neighbouring zones, and perhaps its way of looking was
wrong.

This stage removed both excuses. It built a world where some real relations connect zones far
apart with no commuting between them, and it let the model consider every possible pair. It
also changed the method: the model now has to explain only what a good local forecast could
not, and it cannot cheat by looking at the zone itself.

A "cheat" instrument confirms the relations are there and are worth about a tenth of what
remains to be explained.

The model still finds nothing. Not less than before — nothing: its ranking of which pairs are
connected is indistinguishable from chance, in every configuration tried. Giving it every
pair to choose from does not help, which says the difficulty is not in *where* it is allowed
to look but in *how* it decides.

One honest caveat. One fit in five collapsed, and a fairer test would repair that first. So
the conclusion is that this approach is not supported by what was measured here — not that it
could never work.
