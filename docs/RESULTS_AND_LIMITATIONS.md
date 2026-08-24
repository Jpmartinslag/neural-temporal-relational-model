# Results and limitations

This document states only audited results, each tied to its evidence type (synthetic
known-truth vs. observed French data) and its artefact. It is derived from the project's
closure record (`reports/canonical/HERALD_97_STAGE_CLOSURE_AND_VISUAL_EVIDENCE.md`, DEC-146)
and the frozen figure/table archive (`reports/final_visual_evidence/`), which are the most
recent and most audited statements in the repository. Where this document and an older
`reports/canonical/HERALD_0X` document disagree, this document and `HERALD_97` win — see
`EXPERIMENT_PROVENANCE.md` for why older canonical documents can be stale on this point.

**Read this section before any figure or number below:** synthetic-benchmark results measure
*recovery of a known graph in an artificial world*. French results are *observed data or
constructed hypotheses with no known ground truth*. The two are never comparable and must
never be presented together as if they answered the same question. See "French application vs.
synthetic known-truth benchmark" in `PROJECT_OVERVIEW.md`.

## 1. Forecasting

**Demonstrated (synthetic).** A causal temporal representation of a territory's own trajectory
reduces out-of-sample squared error by **11% to 24%** against the best single attribute, in
every tested synthetic scenario — including the scenario with no relational mechanism at all.
This is a property of *how the trajectory is described*, not evidence of a territorial
relation.

**Not demonstrated.** No evaluated method — persistence, graphical Granger with Lasso, Neural
Relational Inference, MTGNN, or the proposed model at any width — clearly beats a persistence
baseline on one-step-ahead forecasting in the main synthetic benchmark. The best observed skill
is **+0.0001**, effectively equal to persistence. See `reports/final_visual_evidence/tables/T04_models_compared.md`
and `T05_prediction_versus_recovery.md` for the full per-method table.

**French annual comparison.** The audited French comparison designates persistence as the
reference, and a fitted alternative reaches a lower aggregate error while failing a
pre-registered stability condition and a per-sector safety condition. This is a decision under
a pre-registered rule, not a measurement of relational value, and it must not be read as
"persistence is more accurate" or as "the alternative wins" — both are prohibited framings
(see §6).

## 2. Observability of the relational mechanism

**Demonstrated (synthetic).** The relational mechanism is observable in the published-style
observations: an **oracle** — an estimator that receives the true relational term directly,
rather than having to find it — returns exactly zero without the mechanism and rises
monotonically with its intensity, in every tested scenario and seed, across two protocols. At
nominal strength it recovers about **2%** of squared error on raw growth and about **10%** of
the residual left by a frozen local baseline.

This matters because it separates two different failures that are easy to conflate: the
mechanism being *undetectable in the data* versus the *evaluated models failing to find it*.
The oracle result rules out the first explanation.

## 3. Relation recovery / identification

**Not demonstrated.** No evaluated method — classical or neural — recovers the true
connections above the random baseline of its own candidate set, under any of the tested
protocols, four candidate supports, and three relational intensities. Every method's recovery
metric sits at its support's own prevalence once judged against the correct baseline (never
against another support's prevalence — see §6). Full comparison:
`reports/final_visual_evidence/tables/T05_prediction_versus_recovery.md`.

**The proposed model's apparent margin is disqualified by its own no-relation control**: in a
paired synthetic world with the propagation mechanism switched off, the proposed model shows
the same apparent "recovery" as in the world with the mechanism present, because its scorer
reproduces the commuting prior it is given rather than finding structure. This is the single
most important negative result in the project, and the honest reason it is stated so plainly:
the study's own architecture is the one arm its own control disqualifies.

## 4. Is the bottleneck the candidate set?

**Refuted.** Widening the candidate set to `all_pairs` — every ordered pair of distinct
territories, guaranteed to contain every true edge — does not produce recovery. This locates
the limitation in **identification** (the scoring/learning objective), not in candidate
generation. See `reports/final_visual_evidence/tables/T06_demonstrated_not_demonstrated_future.md`.

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
  best single attribute, across every tested synthetic scenario including the no-mechanism one.
- Forecast improvement and relation recovery are distinct outcomes, measured separately.
- The relational mechanism is observable in the data and exploitable by an estimator that
  receives it directly (the oracle); no evaluated model that must find it does so reliably.
- Widening the candidate set to every pair does not produce recovery — the bottleneck is
  identification, not candidate generation.
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
- That this study demonstrates frugal learning (no frugality claim is authorised; the cost/
  parameter comparison exists as an optional appendix figure only and was explicitly withdrawn
  as a headline claim).
- That attention-based relational fusion, or relation-family-specific representations, are
  implemented, validated, or expected to succeed — both are future work only (§7).
- That any French territorial recommendation follows from any result in this repository.
- Comparing the 280-zone synthetic benchmark and the 80-zone residual/multirelational
  diagnostic on the same numeric scale (different targets, different prevalence — see
  `reports/final_visual_evidence/README.md`, "forbidden comparisons").

## 7. Future work (not implemented)

- **A relation-scoring training objective** that directly targets identification, motivated
  precisely by the bottleneck found in §4.
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

The framework is designed for territorial economic intelligence, integrates temporal and
territorial information, admits relations of different natures, separates the local baseline
from the relational contribution, and carries audit/abstention/null-control mechanisms
stricter than a plain comparison of forecast errors. It has **not yet recovered relations
reliably**, has **not consistently outperformed** simpler competitors, and its present value is
methodological and architectural rather than a demonstrated empirical advantage. That is
reported as a scientific delimitation of the current prototype, not as evidence that
territorial economic relations do not exist.
