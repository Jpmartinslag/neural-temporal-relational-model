# HERALD 95 — Relational scale ladder: is the relation too small, or is the model unable?

**Character:** strictly exploratory. Not applied to France.
**Jobs:** 7865295 (validation + smoke), 7865298 (grid, 60 tasks, all `COMPLETED`).
**Seeds:** 9901–9903, never generated before; every calibration decision was taken on
9891–9892. **Commits:** `b52ffeb`, `3a4aaef`, `185202a`. Environment `herald-v5`.

---

## 1. Answer

The mechanism **is** observable at nominal scale. The failure reported in HERALD 94 was a
limitation of the model, not of the benchmark — but the ceiling that limitation is measured
against is itself low.

At `1×` the relational effect carries a signal-to-noise ratio of 0.47–0.58 in the published
growth of the primary signal. An oracle that knows the true relational term removes 1.8 % to
2.5 % of the out-of-sample squared error. The network removes nothing attributable to the
mechanism: it gains as much in the scenario that has none, and its gain does not respond
monotonically to the scale.

Edge recovery does not respond to the scale **at all**, at any scale, in any scenario.

## 2. What varied, and what had to be fixed before it could

One number varied: `relational_scale`. The review the design required found three reasons it
did not mean what its name says, and two of them would have made the ladder unreadable.

**It multiplied `gamma` as well as the loading.** `gamma` is the loading on the common state,
which is not relational. At `scale = 0` the world lost its common state along with its
relation, so the intended control did not exist. Every earlier stage ran at `scale = 1`,
where the two are indistinguishable, so nothing already reported changes.

**The worlds were not paired.** `rng.poisson` at these rates uses rejection sampling and
consumes a variable number of uniforms depending on its mean. Changing the latent path — which
is exactly what changing the scale does — put the generator out of step: masks differed
between scales, and every signal after the first negative-binomial one received a different
stream. Separating the generators per signal fixed the leak *between* signals and left the
one *inside* each signal untouched. The Gamma deviate is now drawn as
`standard_gamma(dispersion)` and scaled afterwards, since its consumption depends on the
shape and not on the mean; the Poisson layer gets its own generator per
`(signal, period, zone)`. Measured at 120 zones, sharing the streams inflated the observable
signal-to-noise ratio by **94 % at half scale** and 34 % at unit scale — worst exactly where a
sensitivity threshold is read.

**Two mechanisms damp the parameter and were measured rather than removed**, both being part
of the model of a bounded growth rate: the latent path is clipped, and the observation model
normalises the integrated drift by its own standard deviation. The consequence is that the
scale is *not* a multiplier on what the model sees, and the guard on the observable effect
demands monotonicity while explicitly refusing to demand linearity.

## 3. The ladder

Median over three seeds. `N0_NULL` has no loading to scale and is flat by construction, which
the grid confirms: at scales 0, 0.5, 1, 2 and 4 it returns identical numbers.

| scenario | scale | observable SNR | clipped | **oracle** | network | destroyed | edge AUPRC | dense |
|---|---|---|---|---|---|---|---|---|
| `N0_NULL` | any | 0.0000 | 0.008 | **+0.0000** | +0.1343 | +0.1141 | 0.7268 | 0.1210 |
| `N2_NONLINEAR` | 0.5 | 0.3175 | 0.010 | **+0.0081** | −0.4509 | +0.1344 | 0.7249 | 0.1210 |
| | 1 | 0.5773 | 0.022 | **+0.0254** | +0.1334 | +0.1229 | 0.7258 | 0.1210 |
| | 2 | 0.8956 | 0.079 | **+0.0489** | +0.1007 | −0.4023 | 0.7274 | 0.1210 |
| | 4 \* | 1.1755 | 0.229 | +0.0723 | +0.1014 | +0.0559 | 0.7253 | 0.1210 |
| `N3_REGIME` | 0.5 | 0.2998 | 0.011 | **+0.0063** | +0.1493 | +0.1348 | 0.7252 | 0.1196 |
| | 1 | 0.5467 | 0.021 | **+0.0177** | −0.4630 | +0.1261 | 0.7254 | 0.1210 |
| | 2 | 0.8459 | 0.062 | **+0.0322** | +0.1392 | +0.0743 | 0.7261 | 0.1171 |
| | 4 \* | 1.0535 | 0.175 | +0.0503 | −0.9560 | −0.3469 | 0.7270 | 0.1210 |
| `N4_INTERACTION` | 0.5 | 0.2597 | 0.009 | **+0.0085** | +0.1665 | +0.0897 | 0.7252 | 0.1210 |
| | 1 | 0.4704 | 0.018 | **+0.0194** | +0.1439 | +0.1067 | 0.7237 | 0.1210 |
| | 2 | 0.7540 | 0.057 | **+0.0370** | −0.1764 | +0.0466 | 0.7236 | 0.1210 |
| | 4 \* | 1.1315 | 0.171 | +0.0761 | −0.2742 | −0.0448 | 0.7275 | 0.1210 |

\* stress scale: the clip saturates 17–23 % of cells, so that world is not the same one with
more mechanism. Excluded from every threshold and every verdict.

## 4. Reading it against the declared rules

**The oracle is monotone in the scale, in all three scenarios, and exactly zero without a
mechanism.** Per seed in `N4_INTERACTION`:

| scale | seed 9901 | 9902 | 9903 |
|---|---|---|---|
| 0 | 0.0000 | 0.0000 | 0.0000 |
| 0.5 | 0.0085 | 0.0119 | 0.0072 |
| 1 | 0.0187 | 0.0194 | 0.0252 |
| 2 | 0.0509 | 0.0370 | 0.0335 |

Every seed rises, none dips, and the null is exactly nil rather than nearly nil. This is the
instrument working: it does not invent an advantage where there is no mechanism to know.

**The network is not monotone, and it gains where there is nothing to gain.** In
`N4_INTERACTION` its median gain runs +0.1665 → +0.1439 → −0.1764 as the mechanism grows,
the wrong direction. Per seed at scale 0 — no mechanism whatever — it is +0.202, −1.0121,
−0.5937. Both declared disqualifying conditions hold: it gains in `N0_NULL`, and it does not
respond monotonically. **Verdict: `NETWORK_GAIN_IS_NOT_RELATIONAL`**, in all three scenarios.

**The gain survives the destruction of its own interaction**, as in HERALD 94: +0.1141 in the
null against an original +0.1343.

**Edge recovery is inert.** AUPRC sits at 0.723–0.731 against a prevalence of 0.70 at every
scale including zero, and the dense correlation agrees to six decimal places between a world
with no mechanism and one with four times the nominal amount. The metric is not the culprit:
fed random scores it returns −0.03, fed the truth it returns 1.00. The scores' own
correlation with the true propagation is 0.096 at every scale, and with the commuting prior
0.124. Multiplying the mechanism by four moves the learned graph by about `1e−8`. This is not
weak recovery; it is insensitivity.

## 5. Why a strong observable signal buys so little

At `1×` the relational effect is not small in the observations — an SNR near 0.5 means its
root-mean-square is half the residual's. Yet perfect knowledge of it removes only about 2 %
of the squared error. The two facts are consistent, and the reason matters more than either.

The oracle adds **one column** to a design that already carries 120. The relational term moves
the latent path, and the latent path is what the signal's own history records, so most of its
information is already present in the growth, trend and momentum features. What the oracle
adds is the *increment* over what the history already reveals, and that increment is small.

So the ceiling at nominal scale is real but low: roughly 2 % of squared error, against a
target that HERALD 93 established is close to measurement noise at horizon one. A model that
recovered the mechanism perfectly would win by two per cent.

## 6. Answers

1. **At which scale does the oracle begin to recover?** Between 0 and 0.5. It is already
   positive and consistent across all three seeds at `0.5×` (+0.006 to +0.0085); against the
   declared 0.01 floor it clears at `1×`. The true onset is below the smallest scale tested.
2. **At which scale does the network begin to recover?** At none. It exceeds the floor at some
   scales, but not monotonically and equally in the scenario with no mechanism, so those
   crossings are not recovery.
3. **The sensitivity threshold.** Not estimable for the network: a threshold presumes a
   monotone response and there is none. For the oracle it lies below `0.5×`.
4. **Is `1×` observable?** Yes. SNR 0.47–0.58 in the published growth, and an oracle gain of
   +1.8 % to +2.5 % — small, but positive in every seed and every scenario.
5. **Was HERALD 94 a limitation of scale or of the model?** **Of the model.** The mechanism is
   present and detectable at nominal scale by an estimator that knows it. The network does not
   find it at any scale, and what it does find appears identically without a mechanism. The
   qualification that matters: the ceiling it failed to reach is about 2 % of squared error.
6. **Jobs and tests.** 7865295 (validation and smoke), 7865298 (grid, 60/60 `COMPLETED`).
   Twelve HERALD 95 guards, twelve mutants killed, twenty-five HERALD 94 guards intact, all
   run on the cluster. All 60 tasks report `worlds_are_paired = True`; `N0_NULL` is flat
   across all five scales.

## 7. Limits

Three seeds, one primary signal, one horizon. The stress scale is reported and interpreted
nowhere. The oracle measures the ceiling for a model of this shape — one extra regressor in a
linear design — and a different architecture could in principle extract more from the same
mechanism; what the ladder establishes is that the mechanism is there to be extracted, not
how much any particular architecture could get.

The clip and the drift normalisation mean the scale is not a multiplier on the observable
effect. Every number in the ladder is reported at the observable level for that reason.

## 8. Lay summary

The previous stage found that the model could not detect economic relations between
territories. Two explanations were possible: the relation was too faint to see, or the model
was not good enough. This stage settles it by turning the relation up and down like a dial
and watching who notices.

Two instruments watched. One is a cheat that is told the right answer — it exists only to
measure how much there is to be found. The other is the real model.

The cheat responds cleanly: nothing at zero, a little at half strength, more at full, more
still at double. So the relation **is** there and **is** visible in the published numbers.

The real model does not. It sometimes appears to do better, but it does so just as much in a
world built with no relation at all, and it does not improve as the relation grows stronger —
sometimes it gets worse. That pattern means its apparent gains come from somewhere else.

The part that looks for the map of connections between territories is the most striking: turn
the relation up fourfold and the map it draws changes in the eighth decimal place. It is not
looking.

One caveat keeps this from being a simple "fix the model" conclusion. Even the cheat, knowing
the answer perfectly, only improves the forecast by about two per cent — because most of what
the relation does to a territory is already written in that territory's own recent history.
The prize for solving this is small.
