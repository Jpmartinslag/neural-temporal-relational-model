# HERALD — Final visual evidence archive

Everything needed to write the report and build the presentation, in one place, each item
reproducible by a script and each item labelled with what it is allowed to claim.

**Nothing in this archive was produced by a new training run.** The audit reads committed
result artefacts; the figures read those artefacts or redraw the synthetic world from its
deterministic generator. The heaviest operation is a `numpy` draw.

---

## How to rebuild

```bash
python -m venv .venv && .venv/bin/pip install numpy matplotlib   # the only dependencies
cd reports/final_visual_evidence/scripts

.venv/bin/python make_all.py                        # audit, tables, figures -> figures/report
HERALD_FIG_TARGET=slides .venv/bin/python make_all.py   # the same figures -> figures/slides
```

Individual stages: `audit_stage.py`, `make_tables.py`, `fig_france.py`, `fig_synthetic.py`,
`fig_architecture.py`, `fig_results.py`. The whole rebuild takes about a minute.

The French geometry is parsed from GeoJSON with the standard library and drawn as polygons, so
`geopandas`, `shapely` and `pyproj` are **not** required.

---

## Layout

```
figures/report/    27 figures, PDF (vector) + PNG (140 dpi)
figures/slides/    the same 27 at larger typography
tables/            7 tables, CSV + Markdown
captions/          ready-to-paste captions, French
provenance/        the audit, and one JSON per figure family recording what each drew
scripts/           everything that produced the above
comparison_protocol/   the specification for the final comparison, NOT YET RUN
```

---

## Categories

Every figure carries one of these as a stamp, and the distinction is load-bearing:

| category | meaning | what may be claimed |
|---|---|---|
| `REAL_FRANCE` | measured on published French series | association, coverage, description |
| `EXPLORATORY` | constructed by this study from published series | candidate, hypothesis |
| `SYNTHETIC_KNOWN_TRUTH` | artificial world whose truth is known | recovery, ceiling, control |
| `FUTURE_WORK` | a proposal | nothing — it has no results |

**Vocabulary.** Authorised: *association*, *précédence temporelle*, *information
incrémentale*, *utilité prédictive*, *stabilité*, *abstention*. Forbidden throughout:
*causalité*, *influence économique prouvée*, *dépendance structurelle*, *recommandation
territoriale définitive*, and any presentation of a learned score as an economic relation.

---

## Fixed colours

| role | hex | role | hex |
|---|---|---|---|
| commuting | `#0072B2` | HERALD | `#D55E00` |
| similarity | `#E69F00` | classical methods | `#56B4E9` |
| complementarity | `#009E73` | other neural methods | `#7B5EA7` |
| true graph / oracle | `#111111` | null scenario | `#9A9A9A` |
| learned graph | `#CC79A7` | multirelational union | `#56B4E9` |

Okabe–Ito, distinguishable under deuteranopia, protanopia and tritanopia. The palette lives in
`scripts/herald_evidence.py` and every figure imports it, so a colour means the same thing in
the report and on the slides.

---

## The figures

`R?` = suggested for the report. `S?` = short presentation. `T?` = technical presentation.

| ID | title | category | source | message | limitation | R | S | T | status |
|---|---|---|---|---|---|:-:|:-:|:-:|---|
| F01 | Les 280 zones d'emploi | REAL_FRANCE | Insee ZE2020 | la population de l'étude | aucune donnée économique dessus | ● | ● | ● | INCLUDE |
| F02 | Réseau de navettes | REAL_FRANCE | Insee mobilités, 2012 | le prior de candidature, observé | échantillon top-3 ; jamais une étiquette | ● | ● | ● | INCLUDE |
| F03 | Similarité construite | EXPLORATORY | Urssaf 1999–2019 | des relations candidates existent hors du voisinage | construite, non découverte | ● | | ● | INCLUDE |
| F04 | Complémentarité construite | EXPLORATORY | Urssaf 1999–2019 | une famille de candidats de forme opposée | une corrélation négative n'est pas une complémentarité | ● | | ● | OPTIONAL |
| F05 | Quatre supports côte à côte | REAL_FRANCE / EXPLORATORY | Insee, Urssaf | les familles se recouvrent peu | échantillon déclaré de 200 paires par panneau | ● | ● | ● | INCLUDE |
| F06 | Cinq signaux, trois zones | REAL_FRANCE | Urssaf, Insee, SIDE | ce que le panel contient réellement | fenêtres inégales — c'est la disponibilité réelle | ● | ● | ● | INCLUDE |
| F07 | Représentation temporelle | REAL_FRANCE dérivé | Urssaf | ce que « représenter une trajectoire » veut dire | fenêtre d'illustration réduite à 5 ans | ● | | ● | INCLUDE |
| S01 | Territoires synthétiques | SYNTHETIC | générateur v96, graine 9961 | le monde artificiel imite le panel français | ce n'est pas la France | ● | ● | ● | INCLUDE |
| S02 | Le graphe vrai | SYNTHETIC | générateur v96 | 80 des 120 arêtes sont hors navettes | n'atteint jamais le modèle | ● | ● | ● | INCLUDE |
| S03 | Support candidat et plafond | SYNTHETIC | générateur + artefacts | ce que le support des navettes ne peut pas contenir | 400 paires tracées sur 2 762 | ● | | ● | INCLUDE |
| S04 | Les scores appris | SYNTHETIC mesuré | `herald96/tasks` | les scores ne séparent pas les vraies arêtes | moyennes par famille, pas de dump par arête | ● | | ● | INCLUDE |
| S05 | Scénario sans mécanisme | SYNTHETIC | générateur v96 | le contrôle : rien ne circule | — | ● | ● | ● | INCLUDE |
| S06 | Scénario avec mécanisme | SYNTHETIC | générateur v96 | même monde, une seule différence | — | ● | ● | ● | INCLUDE |
| S07 | Échelles 0× à 2× | SYNTHETIC | générateur v96 | une seule quantité varie, appariée cellule par cellule | 4× exclu : saturation | ● | ● | ● | INCLUDE |
| S08/S09 | Oracle contre modèles | SYNTHETIC mesuré | `herald95` + `herald96` | **la figure centrale** : l'oracle répond, les modèles non | deux protocoles, niveaux non comparables | ● | ● | ● | INCLUDE |
| S10 | Graphe vrai contre appris | SYNTHETIC schéma | `herald96/tasks` | 1 arête retrouvée sur 70 dans le support | l'arête surlignée est illustrative, le nombre est mesuré | ● | ● | ● | INCLUDE |
| S11 | AUPRC contre prévalence | SYNTHETIC mesuré | `herald96/tasks` | le hasard obtient déjà ce score | lire chaque barre contre SA prévalence | ● | ● | ● | INCLUDE |
| S12 | Prévision contre récupération | SYNTHETIC mesuré | `herald96/tasks` | deux questions distinctes | un point par support, une seule intensité | ● | | ● | INCLUDE |
| A01 | Flux global du projet | diagramme | — | où chaque étape se situe | schéma, pas un résultat | ● | ● | ● | INCLUDE |
| A02 | Architecture actuelle | diagramme | HERALD 96 | baseline gelé, résidu, pas de chemin local | schéma de ce qui a tourné | ● | ● | ● | INCLUDE |
| A03 | Architecture future | FUTURE_WORK | — | la direction proposée | **NOT IMPLEMENTED — aucun résultat** | ● | ● | ● | INCLUDE |
| R01 | Performance temporelle | SYNTHETIC — H94 | `herald94/tasks` | 11–24 % de l'erreur retirée | aussi vrai dans le scénario nul | ● | ● | ● | INCLUDE |
| R02 | Skill contre persistance | SYNTHETIC — H93 | `herald93` | aucune méthode ne bat la persistance | propriété de la cible, pas d'une architecture | ● | ● | ● | INCLUDE |
| R03 | AUPRC contre prévalence, deux protocoles | SYNTHETIC — H93 + H96 | `herald93`, `herald96` | nulle des deux côtés | les deux panneaux ne se comparent pas | ● | | ● | INCLUDE |
| R04 | Diagnostic d'échelle | SYNTHETIC — H95 | `herald95/tasks` | « le modèle », pas « trop petit » | plafond ≈ 2 % sur cette cible | ● | ● | ● | INCLUDE |
| R05 | Coût et paramètres | SYNTHETIC — H93 | `herald93` | la frugalité n'est pas favorable à la proposition | coûts d'un seul protocole | ● | | ● | INCLUDE |
| R06 | Évolution scientifique | trajectoire | — | chaque étape ouverte par un manque | schéma narratif | ● | ● | ● | INCLUDE |

**EXCLUDE — deliberately not produced.** A French map of learned edge scores; a single ranking
table merging HERALD 93 and HERALD 96; any figure of the future attention architecture carrying
a performance number. The first two would be false, the third does not exist.

### The three recommended sets

- **Report (27):** everything above.
- **Short presentation (17):** F01, F02, F05, F06, S01, S02, S05, S06, S07, S08/S09, S10, S11,
  A01, A02, A03, R01, R02, R04, R06 — the narrative arc without the method detail.
- **Technical presentation (25):** everything except F04 and the optional duplicates; add T04,
  T05 and T07 as slides.

---

## The tables

| ID | title | built from | note |
|---|---|---|---|
| T01 | Sources et périodes | `fr_ze2020_multisource_long_panel_v1.csv` | measured coverage, mask included |
| T02 | Représentations temporelles | `HERALD_94_..._SPECIFICATION.md` | a declaration, written before results |
| T03 | Relations candidates | specifications | observed / constructed, and the rule attached to each |
| T04 | Modèles comparés | `herald93/benchmark_summary_v2.json` | one protocol only |
| T05 | Prévision contre récupération | idem | the decisive column is AUPRC in S0 |
| T06 | Démontré / non démontré / futur | all four stages | status, not opinion |
| T07 | Cohérence état de l'art | — | why some methods are foundations and others representatives |

---

## Provenance

- `provenance/stage_audit.json` — the full audit of HERALD 93–96 with every finding.
- `provenance/figures_*.json` — what each figure drew, with counts, seeds and sampling rules.

### What the audit found

Fourteen findings, none of which changes a verdict. The four that matter to a reader:

1. **HERALD 95 §3** claims the null scenario "returns identical numbers" at all five scales.
   True of every forecasting arm and control, which are bit-identical; **false of the edge
   scorer**, which differs at scale 0.0 for two of three seeds (AUPRC 0.7214 / 0.7309 against
   0.7249 / 0.7268). The differences are far below the seed-to-seed spread and no verdict
   depends on them, since edge recovery is inert at every scale in every scenario.
2. **HERALD 96 §3** summarises as "AUPRC equals prevalence" what its own table shows more
   precisely: the `similarity_only` support sits about 25 % above its prevalence — and does so
   **equally in the null scenario**, which makes it a property of the support and not a
   recovery. The table is right; the sentence is looser than the table.
3. **HERALD 96 §5** quotes 109–218 s per task and 977–6 320 candidate pairs. The artefacts span
   43.1–447.6 s and 800–6 320 pairs; 977 is HERALD 94's network parameter count, not a support
   size. A cost sentence, no verdict attached.
4. **HERALD 96 header** cites commit `4f4f00e`, which does not exist in the repository. The
   stage's commits are `3a9e434`, `3e692a1`, `0946d8a` and `3ab599b`.

Also recorded: `herald93/benchmark_summary_v2.json` carries a stale `thresholds.edge_f1 = 0.5`
and a check key named `edge_f1_at_least_0_50`, while the rule actually applied is prevalence +
0.10 = 0.80, as HERALD 93 §7 states. Artefact metadata, not science.

**None of these was corrected by changing a model, a seed, a threshold or a result.** They are
recorded as they were found, which is the whole point of an audit performed after the fact.

---

## What may and may not be said with this archive

**May be said.** That a causal temporal representation of a zone's own trajectory removes 11–24 %
of out-of-sample squared error against the best single signal. That the relational mechanism in
the synthetic panel is observable and worth about 2 % of squared error on raw growth and about
10 % of the residual after a frozen local baseline. That no method tested — persistence, Granger
by Lasso, MTGNN, NRI, HERALD at three widths, and an additive per-source Neural Granger arm —
recovers the true edges above chance, in any support or intensity. That the bottleneck is
identification and not candidate generation.

**May not be said.** That any learned edge is an economic relation. That HERALD outperforms its
competitors. That relations were discovered in France. That the future attention architecture
works. That a smoke result is a finding.

**Not yet said, and pending.** The final comparison in `comparison_protocol/` has not been run.
No number from it exists.
