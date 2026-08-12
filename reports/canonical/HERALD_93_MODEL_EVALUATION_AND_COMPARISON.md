# HERALD 93 — The model, its benchmark, and what four families recover

*Material for the final report. Figures are medians over the five final seeds, 280 zones,
twelve rolling origins, unless stated otherwise.*

---

## 1. The territorial problem

France is divided into 305 *zones d'emploi* (ZE2020), of which 280 mainland zones are used
here; Corsica is excluded from this round. A zone is a labour-market area: the unit within
which most people both live and work. Public policy asks a question about these zones that
their own statistics answer poorly. When employment moves in one zone, does it move in
another, and can that be anticipated?

The intuition behind the project is that zones are not independent. They are connected by
commuting, and a shock that arrives in one should be visible, later, in the zones that send
it workers. If that is true and measurable, a territorial recommendation system becomes
possible: a zone can be told which other zones its own trajectory depends on.

The whole study is a test of whether that intuition survives measurement.

## 2. The French data

Five economic signals, all published by French statistical bodies at zone level, all with a
single release vintage per source and therefore analysed under a declared
`RETROSPECTIVE_FINAL_VINTAGE_ANALYSIS` policy rather than as an ex-ante exercise.

| signal | source | frequency | median per zone | dispersion | log AR(1) |
|---|---|---|---|---|---|
| salaried headcount | Urssaf | quarterly | ~28 000 | NB, φ ≈ 7 600 | 0.916 |
| payroll | Urssaf | quarterly | ~166 M€ | Gamma, φ ≈ 40 | 0.906 |
| employer establishments | FLORES | annual | ~3 200 | NB, φ ≈ 12 300 | 0.984 |
| unemployment rate | Insee | quarterly | ~8 % | logit | 0.952 |
| enterprise creations | Sirene | annual | ~1 300 | NB, φ ≈ 315 | 0.983 |

The commuting matrix (Insee mobilités professionnelles) supplies the candidate support: the
forty strongest commuting destinations per zone. It is a **prior**, never a label. No method
is ever scored against it, and no loss contains it.

## 3. What was established before the model was built

Two results constrain everything that follows, and both are negative.

**No single French signal carries direction-stable relational information along observed
commuting.** The corrected signal tournament (HERALD 91, array 7864487) fitted each signal
with its own likelihood, froze one graph-free dispersion per rolling origin across all arms,
and compared the true commuting graph against derangement and degree-matched placebos with a
family-wise maxT correction over forty draws. Establishments remained a weak candidate;
creations were reclassified as COVID-sensitive and exploratory. Nothing survived as
relation-informative.

**Signals that are individually weak are not jointly strong for the reason the project
assumed.** The complementarity hypothesis was that each signal measures the same latent
state with *independent* error, so averaging five of them divides the error by √5 while the
relational part adds coherently. Tested on a matched pair — two synthetic worlds identical
in every audited quantity except whether the five measurement errors are independent or
shared — the hypothesis failed:

```
S0_NULL     paired  -0.0024%    (null envelope q97.5 = +0.0857%)
S3F         paired  +0.8634%    own +8.98% -> pooled +9.86%
S4F         paired  +1.0145%
S3F - S4F   median  -0.0736%    positive in 8 of 20 seeds
```

Pooling does help, in nineteen seeds of twenty. It does not help *because the errors are
independent*: making them identical does not remove the gain. Verdict
`COMPLEMENTARITY_NOT_SUPPORTED` (DEC-137). The claim is dropped; the model evaluation
continues on `S0_NULL` and `S1_SHARED`, the latter identifiable by the oracle in twenty
seeds of twenty.

## 4. The HERALD architecture

```
per-signal temporal encoder      dilated causal convolution over (growth, mask)
        |                        two channels: the observation and whether it exists
        v
masked multisignal fusion        learned gate x observed share, normalised over signals
        |                        no signal removed by construction
        v
shared relational scorer         f(z_i, z_j, z_i*z_j, prior_ij) -> logit
        |                        ONE function for every pair
        |                        no per-pair parameter, no zone identity embedding
        v
softmax over incoming candidates competition within each target's candidate set
        |
   straight-through top-k        forward: k neighbours; backward: every candidate
        |
        v
   messages from other zones     diagonal masked; a zone's own state never enters
        |                        its own message
        v
 relational head + node head     added, never merged; the ablation is meaningful
        |
        v
   prediction + abstention       per-signal Gaussian NLL with a learned per-signal scale
```

Design commitments that are enforced by guards rather than by intention:

- the latent state, the true adjacency, the relational component and the typed events exist
  only inside the evaluator and are unreachable from model inputs;
- no observation from after the decision period, and no observation not yet released,
  enters any design;
- absence is a mask channel, never a zero;
- there is no self-loop and no node-only path inside the relational arm;
- top-k selects which neighbours propagate but does not block the gradient;
- width 256 is refused by the model constructor itself.

## 5. The three comparison families and why each was chosen

| family | method | question it answers | why this one |
|---|---|---|---|
| classical frugal | Graphical Granger by Lasso | does a frugal classical method recover the graph? | PCMCI+ was the alternative; `tigramite` is absent from the cluster environment and adding an unaudited dependency to obtain a second classical method is worse than running one that can be read end to end |
| predictive graph | MTGNN | does a graph help forecasting, and is the graph it learns the true one? | learns its adjacency from a forecasting objective alone, which is precisely the confusion the study must avoid |
| relational neural | NRI | does an architecture built for relational recovery recover it? | static posterior, stable, and restricted to the same support so the comparison is between methods and not between supports |
| proposal | HERALD | does temporal dynamics + multiple signals + territorial prior + abstention recover relations frugally? | — |

Every method receives the same released observations, masks, candidate support, folds,
origins and seeds, no edge labels, and all three neural arms minimise the same masked
Gaussian likelihood with a per-signal learned scale. Giving one arm a better-specified
likelihood would be a capacity difference disguised as a result.

## 6. Results — forecasting

Log-growth at horizon one, twelve rolling origins, five final seeds, scenario `S1_SHARED`.

| method | skill vs persistence | interpretation |
|---|---:|---|
| persistence | 0.0000 | the floor |
| Graphical Granger (Lasso) | +0.0001 | persistence to four decimals |
| HERALD @128 | −0.0046 | |
| HERALD @32 | −0.0087 | |
| HERALD @64 | −0.0170 | |
| NRI @64 | −0.0494 | |
| MTGNN @64 | −0.1977 | |

**No method beats persistence.** The best is the classical arm at +0.0001 skill, which is
persistence to four decimal places. Log-growth in this panel is dominated by measurement
noise: the autocorrelation lives in the *level*, and differencing it leaves little for any
method to predict. This is a property of the target, not a failure of any one architecture,
and it applies equally to all four.

## 7. Results — relational recovery

The candidate support contains 11 200 ordered pairs; the true propagation graph is drawn
inside it, so the prevalence of true edges within the support is 0.70. An edge F1 of 0.70 is
therefore what random selection achieves, and the criterion is prevalence plus a margin.

| method | edge F1 | dense corr. | AUPRC (S1) | AUPRC (S0) | prevalence | stability |
|---|---:|---:|---:|---:|---:|---:|
| HERALD @128 | 0.717 | +0.116 | 0.7294 | 0.7269 | 0.700 | 0.918 |
| HERALD @32 | 0.715 | +0.116 | 0.7257 | 0.7216 | 0.700 | 0.997 |
| HERALD @64 | 0.715 | +0.112 | 0.7228 | 0.7254 | 0.700 | 0.997 |
| MTGNN @64 | 0.705 | +0.043 | 0.7147 | 0.7079 | 0.700 | 0.997 |
| Granger @— | 0.702 | +0.003 | 0.6983 | 0.7009 | 0.700 | 0.995 |
| NRI @64 | 0.701 | −0.005 | 0.7005 | 0.7027 | 0.700 | 0.995 |

Required: edge F1 ≥ 0.80 (prevalence + 0.10), dense correlation ≥ 0.30, stability ≥ 0.90,
AUPRC above prevalence in S1, and no structure found in S0. Every method fails the first
two. HERALD is the only family whose dense correlation is materially non-zero, and it is
also the family the S0 control disqualifies most clearly.

**The decisive observation is the S0 control.** HERALD's recovery is statistically identical
in the scenario with a relational mechanism and in the scenario without one:

```
herald@64   S0_NULL    AUPRC 0.7254   dense +0.1160   edge F1 0.7152
herald@64   S1_SHARED  AUPRC 0.7228   dense +0.1118   edge F1 0.7149
```

`S0_NULL` has zero relational loading. There is nothing in it to find. A method that scores
the same there as in `S1_SHARED` has not recovered a relation; it has reproduced something
it was given. In HERALD's case that something is the commuting prior, which the scorer
receives as a pair feature. Because the true propagation graph is itself drawn from the
prior, ranking edges by prior weight lifts the average precision slightly above the
prevalence — in both scenarios equally.

This is the single most important result of the study, and it exists only because the
benchmark contained a scenario with no mechanism at all.

## 8. Frugality

| method | parameters | epochs | seconds | peak MB | abstention |
|---|---:|---:|---:|---:|---:|
| persistence | 0 | 0 | 1.4 | 607 | — |
| Graphical Granger | 50 400 | — | 5.5 | 608 | — |
| MTGNN @64 | 90 506 | 30 | 110 | 665 | — |
| NRI @64 | 89 228 | 30 | 326 | 700 | — |
| HERALD @32 | 24 596 | 30 | 348 | 686 | 0.734 |
| HERALD @64 | 94 228 | 30 | 323 | 725 | 0.009 |
| HERALD @128 | 368 660 | 30 | 1 367 | 822 | 0.000 |

The classical arm is two orders of magnitude cheaper than any neural one and forecasts as
well as the best of them. That is the frugality result, and it is not favourable to the
proposal.

The abstention rate is worth reading alongside the recovery table rather than on its own:
HERALD at width 32 abstains on 73 % of cells while wider models abstain on almost none, and
all three recover the same amount, which is nothing. Abstention is behaving as a capacity
valve here, not as a confidence signal.

## 9. Decision on France

`CASE_C_DO_NOT_APPLY_RELATIONS`. No HERALD width was promoted: the selection rule requires
control of false positives in `S0` first, and no width achieved it. Promoting "the best of
the failures" is not permitted and was not done.

No method passed the recovery gate, and no method beat persistence on forecasting. Relations
are not applied to the French panel, no learned edge is visualised or interpreted as an
economic finding, and no territorial recommendation is issued on this basis. The synthetic
comparison, the failure analysis, the frugality accounting and the limits below are the
deliverable.

Authorised statements: association, temporal precedence, predictive impact, stability,
agreement, abstention. Forbidden: structural causality, any claim that a learned edge is an
economic relation, and any application of relations to France.

## 10. Limitations

1. **The prior can be echoed.** HERALD's scorer receives the commuting weight as a pair
   feature, and the true graph is drawn from that prior, so a model can score above
   prevalence without learning anything. Future work should score the *residual* after the
   prior is projected out, so that echoing it earns nothing.
2. **The target may be the wrong one.** Log-growth at horizon one is close to noise in this
   panel. A recoverable relational signal may exist at longer horizons, or in levels with an
   explicit trend model, and this study does not test that.
3. **Typed events were not exercised.** The truth graph did not move inside the twelve
   scoring origins, so the typed birth/death criterion was skipped rather than passed. The
   metric is implemented and guarded, but the benchmark's calendar did not put it to work.
4. **One classical method, not two.** PCMCI+ was not run.
5. **Support prevalence is high.** With the truth drawn inside the support, 0.70 of the
   candidate pairs are true edges. A harder benchmark would draw part of the truth outside
   the commuting support and measure recovery inside and outside separately.
6. **Complementarity is closed only for the mechanism tested.** Independent measurement
   error was the declared mechanism and it failed. Other forms of complementarity — signals
   sensitive at different horizons, or to different sectors — are untested.

## 11. Future work

Project the prior out of the scorer's input and require the residual to carry the ranking.
Test longer horizons and level-based targets. Draw part of the synthetic truth outside the
commuting support. Build a benchmark whose graph moves inside the scoring window, so the
typed-event criterion is exercised rather than skipped.

---

## Methodological validity and controls against spurious conclusions

*This subsection is deliberately short and deliberately last. The trajectory of defects and
repairs is evidence that the controls worked, not the subject of the study.*

Every claim in this report rests on a benchmark whose truth is known and whose null
scenario contains no mechanism. Across the study, the controls caught the following, each
before it could become a result:

- an oracle target that was a latent generator variable rather than an observable one;
- an ill-conditioned IRLS design that made one arm score 1739× its own null;
- a negative-binomial score that silently re-estimated a design-specific dispersion;
- a pooled channel that *replaced* the signal's own driver instead of joining it, which made
  pooling appear harmful in every scenario;
- a redundancy scenario that raised its own signal strength by 14 %, making it incomparable
  to the complementary one;
- a complementarity gate that compared absolute gains between worlds differing threefold in
  amplitude, and could not have been satisfied by any amount of redundancy control;
- a relational scorer whose gradient fell to exactly zero after thirty epochs while the head
  consuming its output measured 7.86, so the graph froze while the model went on training
  against it;
- a false-positive control that was unsatisfiable by construction, pinned at 0.30 for every
  method including a perfect one;
- a typed-event metric that credited a frozen score with an F1 of 0.062 for predicting
  nothing;
- a rectifier that saturated at initialisation for the two signals whose mask is nearly
  constant, silently removing them from training;
- a benchmark that did not reproduce itself, because `index_add` has no fixed summation
  order across CPU threads.

Guard and mutation coverage: 20 guards / 18 mutants on the generator and oracle, 11/11 on
the matched pair, 23/22 on the benchmark. Every mutant reinstates a concrete defect; none
stubs a function with a constant. All run inside the first task of every array, under
`set -e`, before any arithmetic is written.

Thresholds were declared before submission and were not moved after results were seen. Two
criteria were replaced *before interpretation*, both because they were unsatisfiable by
construction rather than because they failed, and both are recorded with their reasoning in
DEC-136 and DEC-138.
