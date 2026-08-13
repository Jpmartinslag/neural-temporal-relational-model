# HERALD 97 — Closure of the broad experimental stage

**Character:** an audit and a freeze. Nothing was trained, fitted, submitted or re-run to
produce this document. Every number in it is read from a committed artefact.

**Scope:** HERALD 93, 94, 95 and 96 — the synthetic benchmark stage.
**Artefacts:** `hpc_results/herald93|94|95|96`, now mirrored into the repository.
**Audit:** `reports/final_visual_evidence/provenance/stage_audit.json`, reproducible by
`reports/final_visual_evidence/scripts/audit_stage.py`.
**Decision:** DEC-146.

---

## 1. What is being frozen, and why now

Four experiments asked four versions of one question and answered it. The answer is stable
across all four, the controls that produced it held, and continuing to run variants would be a
search rather than a study. The stage closes here so that the report can be written against a
fixed set of numbers.

The immediate next step is **writing**, not computing. The final model comparison is specified
in HERALD 98 and has not been run.

---

## 2. The stage in one paragraph each

**HERALD 93 — the benchmark and four families.** 280 synthetic zones calibrated on French
marginals, five signals, twelve rolling origins, five seeds, two scenarios. Six methods:
persistence, graphical Granger by Lasso, MTGNN, NRI, and HERALD at widths 32, 64 and 128. No
method beats persistence — the best is +0.0001 skill, which is persistence to four decimal
places, because log-growth at horizon one is close to measurement noise in this panel. No
method recovers the graph: every one fails edge F1 and dense correlation, and HERALD's
apparent advantage is the one the null scenario disqualifies most clearly, since it scores the
same in `S0_NULL` — which has no mechanism — as in `S1_SHARED`. Decision
`CASE_C_DO_NOT_APPLY_RELATIONS`; no width was promoted.

**HERALD 94 — temporal representation and composites.** The causal temporal representation
removes **11 % to 24 %** of out-of-sample squared error against the best single feature, in
every scenario including the one with no mechanism — a property of how a trajectory is
described, not evidence of a territorial relation. None of the six declared composites adds
anything: all six are negative, between −0.003 and −0.008. The non-linear arm does not beat a
well-regularised linear model in enough seeds, its gain is as large in the null scenario as in
the scenarios built to reward it, and that gain survives the destruction of the very alignment
it was supposed to depend on. `layer2_authorised = False`.

**HERALD 95 — the relational scale ladder.** One quantity was varied, `relational_scale`, with
the noise paired cell by cell. The mechanism **is** observable: an oracle that knows it is
exactly zero without it and rises monotonically with it, in three scenarios and every seed. The
network does neither. Edge recovery is inert — multiplying the mechanism fourfold moves the
learned graph by about 1e−8. HERALD 94's failure was therefore the model's, not the benchmark's.
The qualification that matters: the ceiling is only about **2 %** of squared error, because the
relational term moves the latent path and the latent path is what the signal's own history
already records.

**HERALD 96 — a multirelational universe and a Neural Granger arm.** Three relation families,
two thirds of the true edges outside the commuting support, a frozen local baseline, a residual
target, and an additive per-source arm with no local path. The oracle passes cleanly: exactly
zero in the null and **10 % of the residual** at nominal scale, five times HERALD 95's ceiling.
The arm recovers nothing, in any of four supports, three intensities and five seeds. `all_pairs`
contains every true edge and recovers nothing either, which locates the bottleneck in
**identification**, not in candidate generation. France not authorised.

---

## 3. What the stage established

| claim | status | basis |
|---|---|---|
| a causal temporal representation reduces forecast error | **demonstrated** (synthetic) | 11–24 % against the best single feature, six scenarios |
| the six declared composites add information | **refuted** | negative in all six |
| the network's non-linear gain is relational | **refuted** | as large in the null; survives destruction of its own interaction |
| the relational mechanism is observable in published data | **demonstrated** | oracle exactly 0 without it, monotone with it, in two protocols |
| some model recovers the true edges above chance | **not demonstrated** | six methods in HERALD 93, one arm in HERALD 96, four supports, three intensities |
| the bottleneck is candidate generation | **refuted** | `all_pairs` contains every true edge and recovers nothing |
| a method beats persistence | **not demonstrated** | best skill +0.0001 |
| learned edges describe French economic relations | **not authorised** | `CASE_C_DO_NOT_APPLY_RELATIONS` |
| multirelational attention fusion improves identification | **future work** | neither implemented nor validated |

"Not demonstrated" means the experiment ran and did not support the claim. It does not mean the
claim is false, and it is not a licence to assert its negation.

---

## 4. The freeze

1. **The broad experimental stage is closed.** HERALD 93–96 stand as they are.
2. **No reliable relational recovery has been demonstrated** by any method, in any support, at
   any intensity tested.
3. **Applying learned edges to France is not authorised.** No learned structure from this stage
   may be presented as an association, a precedence, a candidate relation or a recommendation
   for France.
4. **French analysis remains permitted** for temporal results, observed data and exploratory
   candidate relations — the last explicitly marked as constructed, never as discovered.
5. **No new hyperparameter search is authorised** at this stage. Regularisation selected per
   task on training folds by a documented rule is not a search; trying alternatives until one
   succeeds is.
6. **The immediate next step is writing**: the report and the presentation.
7. **Multirelational attention fusion is registered as FUTURE_WORK.** It is not implemented, not
   validated, and must never appear beside a performance number.
8. **The final comparison is specified and not run** (HERALD 98). It requires explicit
   authorisation.
9. **Positive, negative and limiting results are all preserved**, including the defects the
   controls caught and the two selection errors that reversed a reported answer.

---

## 5. The audit, and what it found

Fourteen findings. **None changes a verdict, and none was repaired by altering a model, a seed,
a threshold or a result.** They are recorded as found.

**Substantive enough to state in the report.**

1. **HERALD 95 §3** says the null scenario "returns identical numbers" at all five scales. That
   is true of every forecasting arm and every control, which are bit-identical, and **false of
   the edge scorer**: at scale 0.0 two of three seeds differ (AUPRC 0.7214 and 0.7309 against
   0.7249 and 0.7268 elsewhere). The differences are an order of magnitude below the
   seed-to-seed spread, and no verdict depends on them, because edge recovery is inert at every
   scale in every scenario. What it indicates is that something in the scorer's own stochastic
   path is scale-conditioned at exactly zero — worth knowing before that scorer is trusted with
   a finer measurement.
2. **HERALD 96 §3** summarises as "AUPRC equals prevalence" what its own table states more
   precisely. The `similarity_only` support sits about 25 % above its prevalence (0.0780 against
   0.0612) — and does so **equally in the null scenario** (0.0471 against 0.0375), where nothing
   propagates. Equal ratios in both scenarios make it a property of the support, not a recovery.
   The table is right; the sentence is looser than the table, and the report should carry the
   table's version.

**Transcription, no verdict attached.**

3. **HERALD 96 §5** quotes 109–218 s per task and 977–6 320 candidate pairs. The artefacts span
   43.1–447.6 s and 800–6 320 pairs. `977` is HERALD 94's network parameter count, not a support
   size; the smallest support, `similarity_only`, holds 800 pairs.
4. **HERALD 96 §4** quotes smoke gains of +0.0414 and +0.0210; the artefacts hold +0.0419 and
   +0.0238. The paragraph's point — that the smoke was wrong — is unaffected by either figure.
5. **HERALD 96 header** cites commit `4f4f00e`, which does not exist. The stage's commits are
   `3a9e434`, `3e692a1`, `0946d8a` and `3ab599b`.

**Artefact metadata.**

6. `hpc_results/herald93/benchmark_summary_v2.json` carries a stale `thresholds.edge_f1 = 0.5`
   and a check key named `edge_f1_at_least_0_50`, while the rule actually applied is
   prevalence + 0.10 = 0.80 — which is what HERALD 93 §7 states, and which `herald@128`
   correctly fails at 0.717.

**Provenance, now fixed.**

7. The HERALD 94, 95 and 96 task artefacts existed only on the cluster. They are mirrored into
   `hpc_results/` by this stage, so that every figure and every audit line is reproducible from
   the repository alone.

**Confirming, not correcting.** The audit re-derived every headline number of HERALD 93, 94, 95
and 96 from the task artefacts and found them correct: the 11–24 % temporal gain and its
per-seed values, the six negative composites, the oracle ladders in both protocols, the network's
gain in the null, the AUPRC-equals-prevalence result in every support and family, the frozen
baseline in all 120 tasks, and the cost and parameter counts of all seven HERALD 93 arms.

---

## 6. Protocol separation, stated once

HERALD 93 and HERALD 96 **must never appear in the same numeric ranking.**

| | HERALD 93 | HERALD 96 |
|---|---|---|
| zones | 280 | 80 |
| target | log-growth at horizon 1 | residual after a frozen local baseline |
| scenarios | `S0_NULL`, `S1_SHARED` | `M0_NULL`, `M1_MULTIRELATIONAL` |
| support | commuting top-40, truth drawn **inside** it | four supports, two thirds of the truth **outside** commuting |
| prevalence | 0.70 | 0.011–0.061 depending on support |

An AUPRC of 0.73 and an AUPRC of 0.02 are not comparable quantities. What is comparable is each
one's distance from **its own** prevalence, which is zero in both.

---

## 7. Deliverables of this stage

- `reports/final_visual_evidence/` — 27 figures (vector PDF and PNG), 7 tables (CSV and
  Markdown), ready-to-paste captions, provenance for every item, and the scripts that rebuild
  all of it from `numpy` and `matplotlib` alone.
- `reports/canonical/HERALD_98_FINAL_MODEL_COMPARISON_SPECIFICATION.md` — the three-axis
  comparison, its fairness conditions, its gates and its estimated cost. **Not run.**
- `hpc_results/herald94|95|96` — the task artefacts, mirrored from the cluster.

---

## 8. Positioning, honestly

The framework may be presented as: designed for territorial economic intelligence; integrating
temporal and territorial information; admitting relations of different natures; separating the
local baseline from the relational contribution; carrying audit and abstention mechanisms;
extensible to an attention-based fusion; and submitted to controls stricter than a comparison of
errors.

It must equally be stated that it has **not yet recovered relations reliably**, has **not
consistently outperformed** its competitors, that its present advantage is **methodological and
architectural**, and that its empirical superiority remains a **future hypothesis**.

> The proposed framework is not yet the most accurate relational estimator, but it provides an
> auditable architecture in which temporal prediction, relational contribution, graph recovery
> and future territorial interpretation can be evaluated separately.

---

## 9. Vocabulary

**Authorised:** association, précédence temporelle, information incrémentale, utilité
prédictive, impact prédictif, stabilité, accord, abstention.

**Forbidden:** causalité, influence économique prouvée, dépendance structurelle, recommandation
territoriale définitive, and any presentation of a learned score as an economic relation.
