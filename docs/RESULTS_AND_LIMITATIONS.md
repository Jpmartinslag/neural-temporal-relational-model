# Results and limitations

This document states only audited results, each tied to its **protocol** (French application,
280-territory main benchmark, or 80-territory residual diagnostic) and its evidence type
(synthetic known-truth vs. observed French data). It is derived from the project's most recent
closure record and the frozen figure/table archive (`reports/final_visual_evidence/`), which are
the most recent and most audited statements in the repository. Where this document and an older
document in `reports/canonical/` disagree, this document wins — see `EXPERIMENT_PROVENANCE.md`
for why older documents in that folder can be stale on this point.

**Read this section before any figure or number below:**

1. Synthetic-protocol results measure *recovery of a known graph in an artificial world*. French
   results are *observed data or constructed hypotheses with no known ground truth*. The two are
   never comparable and must never be presented together as if they answered the same question.
2. **There are two synthetic protocols, and they are not comparable to each other either** —
   different territory counts, targets, candidate supports, and prevalence. A number from one
   must never be ranked, plotted, or averaged against a number from the other.

## 0. The two synthetic protocols, side by side

| | Main benchmark | Residual diagnostic |
|---|---|---|
| Population | 280 synthetic territories | 80 synthetic territories |
| Target | Growth of the 5 signals at the next period | Residual after a frozen local temporal baseline, at 3 horizons |
| Purpose | Compare forecasting methods (persistence, graphical Granger, 2 neural relational baselines, proposed model) and measure relation recovery | Test a single additive relational arm across candidate supports, including one that contains every possible connection |
| Candidate support | Commuting, 40 outgoing flows per zone (11,200 ordered pairs); true graph drawn inside it | Commuting and economic similarity by incoming source, their union, and all ordered pairs (6,320 pairs, 120 true connections) |
| Main metric | Forecast skill vs. persistence; edge F1 / AUPRC vs. the support's own prevalence (0.70) | Out-of-sample residual gain; AUPRC vs. each support's own prevalence (as low as 0.019 for all-pairs) |
| Permitted interpretation | Comparison between the 5 methods under one shared protocol | Whether out-of-sample pair contributions remain measurable once the local baseline is frozen — **not** a comparison between methods |

Full specification of both protocols: `reports/final_visual_evidence/README.md` ("forbidden
comparisons") and the project's closure record (`EXPERIMENT_PROVENANCE.md` §2–3).

## 1. Forecasting

**Demonstrated (main benchmark).** A causal temporal representation of a territory's own
trajectory reduces out-of-sample squared error by **11% to 24%** against the best single
attribute, in every tested scenario — including the scenario with no relational mechanism at
all. This is a property of *how the trajectory is described*, not evidence of a territorial
relation.

**Not demonstrated (main benchmark).** No evaluated method — persistence, graphical Granger with
Lasso, Neural Relational Inference, MTGNN, or the proposed model at any width — clearly beats a
persistence baseline on forecasting, under the shared protocol described in §0. The best observed
skill is **+0.0001**, effectively equal to persistence. See
`reports/final_visual_evidence/tables/T04_models_compared.md` and
`T05_prediction_versus_recovery.md` for the full per-method table — both restricted to the
280-territory main benchmark; the residual diagnostic does not include these five methods as
comparators (§0).

**French annual comparison.** The audited French comparison designates persistence as the
reference, and a fitted alternative reaches a lower aggregate error while failing a
pre-registered stability condition and a per-sector safety condition. This is a decision under
a pre-registered rule, not a measurement of relational value, and it must not be read as
"persistence is more accurate" or as "the alternative wins" — both are prohibited framings
(see §6).

## 2. Observability of the relational mechanism

**Demonstrated, in both protocols, but at different magnitudes that must not be compared:**

- **Main benchmark (sensitivity extension):** an oracle — an estimator that receives the true
  relational term directly, rather than having to find it — recovers about **1.9%** of squared
  error on raw growth at nominal relational intensity, is exactly zero in the no-mechanism
  scenario, and rises monotonically with intensity.
- **Residual diagnostic:** the same kind of oracle recovers **10.1%** of the residual left by
  the frozen local baseline at nominal intensity (11.1% at double intensity). Unlike the main
  benchmark's oracle, this one is **not exactly zero at zero relational intensity** — it sits at
  a **1.6% floor**, because economically similar territories share observable common factors by
  construction even without propagation. The report treats this floor as a graph-aligned
  co-movement baseline, not as evidence of transmission, and the 10.1% nominal figure should be
  read relative to that floor, not relative to zero.

Because the two figures come from different targets (raw growth vs. a residual) on different
populations (280 vs. 80 territories), **they must not be added, ranked, or described as "the same
oracle result at two scales."** What they jointly show is that the relational mechanism is
observable in the data under both protocols — separating "is the mechanism present and
measurable" from "does the evaluated model find it" (§3).

## 3. Relation recovery / identification

**Not demonstrated, in either protocol.** No evaluated method — classical or neural — recovers
the true connections above the random baseline of its own candidate set. In the main benchmark,
every method's recovery metric sits at approximately its support's prevalence of 0.70. In the
residual diagnostic, the all-pairs support's measured AUPRC is **0.0190 against a prevalence of
0.0190** — i.e., also at chance. Full comparison:
`reports/final_visual_evidence/tables/T05_prediction_versus_recovery.md` (main benchmark).

**In the main benchmark, the proposed model's apparent margin is disqualified by its own
no-relation control**: in a paired synthetic world with the propagation mechanism switched off,
the proposed model shows the same apparent "recovery" as in the world with the mechanism
present, because its scorer reproduces the commuting prior it is given rather than finding
structure. This is the single most important negative result in the project, and the honest
reason it is stated so plainly: the study's own architecture is the one arm its own control
disqualifies.

## 4. Is the bottleneck the candidate set? (residual diagnostic only)

At the widest candidate coverage tested — the all-pairs support of the **80-territory residual
diagnostic**, 6,320 ordered pairs containing all 120 true connections by construction — the
measured AUPRC is 0.0190 against a prevalence of 0.0190. Because no true connection can be
missing from what this arm is allowed to consider there, the correctly scoped conclusion is:

> In the 80-territory residual diagnostic, incomplete candidate coverage was not a sufficient
> explanation for the failure of this implementation, because the all-pairs support contained
> all 120 true connections while its AUPRC remained equal to prevalence.

**This result does not establish that candidate construction is irrelevant to every relational
architecture or to the French application.** It is a single implementation's single arm on an
80-territory diagnostic. Do not use, and treat as prohibited:

- "candidate generation was ruled out" without the qualification above;
- "every possible relation" without naming the 80-territory diagnostic specifically;
- "the bottleneck is definitively identification" as a universal statement about any future
  architecture;
- any claim that this generalises to the 280-territory main benchmark, which was not tested at
  the all-pairs candidate scale.

The same diagnostic also fails predictively at nominal intensity: median out-of-sample residual
gain is −1.14% on commuting, −0.93% on economic similarity, −2.81% on their union, and −15.67% on
all pairs, with one of five union fits diverging to −268.53% (an optimisation-stability issue,
not evidence about a source effect).

## 5. Composite signals and multisignal complementarity

**Refuted.** None of six declared composite economic signals adds information over a properly
regularised linear model; all six are negative (−0.003 to −0.008 in the audited comparison).

**Refuted.** The declared multisignal-complementarity mechanism is not supported: two
synthetic worlds identical except for the independence of five measurement errors differ by a
median of only **−0.07 percentage points** — i.e., combining signals does not recover
relational information that a single signal hides.

## 6. Language and comparison rules (binding)

**Authorised statements**

- A causal temporal representation removes 11–24% of out-of-sample squared error against the
  best single attribute, in the 280-territory main benchmark, across every tested scenario
  including the no-mechanism one.
- Forecast improvement and relation recovery are distinct outcomes, measured separately, and
  under different protocols that are not interchangeable.
- The relational mechanism is observable in both synthetic protocols and exploitable by an
  estimator that receives it directly (the oracle); no evaluated model that must find it does so
  reliably, in either protocol.
- In the 80-territory residual diagnostic, incomplete candidate coverage was not sufficient to
  explain that arm's failure to recover connections — a result scoped to that diagnostic only
  (§4).
- Association, temporal precedence, incremental predictive information, predictive utility,
  stability, agreement, abstention, candidate connection, model-scored connection, exploratory
  hypothesis.

**Prohibited statements**

- That any learned edge is an economic relation, an influence, a dependency, or a causal link.
- That relations were *discovered* in France, or that any learned French structure is a
  validated association or precedence.
- That the proposed model outperforms its competitors, or that any width was promoted.
- That persistence is more accurate than the fitted alternative in the French annual
  comparison (the correct statement is in §1).
- That territorial relations do not exist or cannot be recovered — the honest statement is that
  they were not recovered by the methods and data tested here, not that they are absent.
- That this study demonstrates efficiency, cost savings, or a favourable resource comparison for
  the proposed model. No such claim was established as a final result; an optional appendix
  figure comparing cost and parameters exists but was explicitly withdrawn as a headline claim.
- That attention-based relational fusion, or relation-family-specific representations, are
  implemented, validated, or expected to succeed — both are future work only (§7).
- That any French territorial recommendation follows from any result in this repository.
- Comparing the 280-territory main benchmark and the 80-territory residual diagnostic on the
  same numeric scale, in any table, axis, or sentence that ranks their raw values (§0).
- Describing the two protocols' oracle results (§2) as one number, or implying they measure the
  same quantity.

## 7. Future work (not implemented)

- **A relation-scoring training objective** that directly targets identification, motivated
  precisely by the bottleneck examined in §4.
- **Attention-based relational fusion** across relation families — proposed in the architecture
  diagrams as a future block, not implemented or validated anywhere in the current code.
- **Relation-family-specific representations** — treating commuting, similarity, and
  complementarity edges with dedicated encoders rather than a shared one.
- **A classical spatial panel estimator** (e.g. a spatial lag/error model) as an additional
  comparator — flagged as an unjustified omission by the project's own adversarial review; not
  run, and no pre-registered justification for skipping it was recorded.
- A longer forecast horizon, a level-based (rather than growth-based) target, and a
  changing-topology (birth/death of edges) recovery test — none were in scope of the tests run.

## 8. Applying this to France

French application results are **exploratory and descriptive only**. No French relation has a
known ground truth to be scored against, so no French relation-recovery number exists or can
exist under the current design. French figures showing learned or candidate relations must
carry a visible non-validation warning and must never be captioned as recovered relations,
causal effects, or a basis for territorial recommendation. See
`reports/final_visual_evidence/README.md`, "Interpretation boundary," which is the frozen,
report-facing statement of this boundary and should be treated as authoritative wording.

## 9. One-paragraph honest summary

The architecture integrates temporal and territorial information, admits relations of different
natures, separates the local baseline from the relational contribution, and carries audit/
abstention/null-control mechanisms stricter than a plain comparison of forecast errors. It has
**not yet recovered relations reliably** under either synthetic protocol, has **not consistently
outperformed** simpler competitors, and its present value is methodological and architectural
rather than a demonstrated empirical advantage. That is reported as a scientific delimitation of
the current prototype, not as evidence that territorial economic relations do not exist.
