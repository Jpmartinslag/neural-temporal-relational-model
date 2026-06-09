# HERALD — Prévision économique territoriale

**HERALD** (*Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*) est un modèle hybride de prévision territoriale. Il estime les créations d'établissements par zone d'emploi, produit des cartes de dynamisme, ralentissement et structure sectorielle, et apprend les régimes économiques (choc, rebond, tendance) sans flags manuelles.

---

## Trajectoire du projet

```mermaid
gantt
    title HERALD — Trajectoire de développement
    dateFormat  YYYY-MM-DD
    axisFormat  %b %Y

    section Fondation
    Données & graphe France          :done, found1, 2026-04-08, 2026-04-20
    Architecture de base V6/V7       :done, found2, 2026-04-13, 2026-04-22

    section Phase 2 — Régimes & Robustesse France
    2A-2C Régime learner + flags     :done, p2a, 2026-04-20, 2026-05-05
    2D-2J Stabilité + fair flag      :done, p2d, 2026-05-05, 2026-05-18
    2K-2R Latent dim + confirmatoire :done, p2k, 2026-05-18, 2026-05-26

    section Phase 3 — q_tensor URSSAF
    3A-3C Labor tutor signals        :done, p3a, 2026-05-24, 2026-05-26
    3D q_tensor présence             :done, p3d, 2026-05-27, 2026-05-27
    3E Architecture selection → Q7   :done, p3e, 2026-05-27, 2026-05-27

    section Dashboard & Consolidation
    Dashboard France finalisé        :done, dash, 2026-05-27, 2026-05-28
    Commit + push Phase 3E           :done, commit, 2026-05-28, 2026-05-28

    section Phase 4 — Généralisation Internationale
    Pipelines données NL+BE+PT       :done, p4data, 2026-05-28, 2026-05-28
    Batterie HPC NL+BE               :p4hpc_nb, 2026-05-28, 2026-06-04
    Batterie HPC PT                  :p4hpc_pt, 2026-06-04, 2026-06-08
    Rapport comparatif 4 pays        :p4rep, 2026-06-08, 2026-06-12

    section Phase 5 — Données Synthétiques
    DGP contrôlé + génération        :p5gen, 2026-06-12, 2026-06-20
    Validation régime learner        :p5val, 2026-06-20, 2026-06-27

    section Publication
    Rédaction paper (conf/revue)     :paper, 2026-06-27, 2026-09-01
```

---

## État scientifique actuel

**Candidat France:** `Q7_effectifs_lag1` — sélectionné en Phase 3E (240 runs, 12 configs × 20 seeds).

| Métrique | Valeur |
|----------|--------|
| Mean WMAPE 2021-2025 | 0.020398 |
| Std WMAPE | 0.001498 (le plus stable) |
| WMAPE 2025 | 0.011415 |
| Sector WMAPE (A10) | 0.15612 |

**Comparaison principale dashboard:**

| Modèle | Mean WMAPE | WMAPE 2025 |
|--------|-----------|------------|
| **HERALD no flags Q7** ← candidat | 0.0204 | 0.0114 |
| HERALD no flags clean (Phase 2J) | 0.0209 | 0.0122 |
| HERALD flags clean (Phase 2J) | 0.0282 | 0.0129 |
| Ridge AR | 0.0361 | 0.0361 |

**Verdicts clés Phase 3E:**
- q_tensor réel vs zéro: Δ = 0.0001, p = 0.52 — **non indispensable globalement**
- effectifs > masse salariale: Δ = 0.0004, direction consistante
- lag1 > contemporain: Δ = 0.0003, 13/20 seeds gagnantes
- Sinal local ZE (spatial falsification): modéré — non robuste sur Q7 vs permutation spatiale

---

## Architecture

HERALD combine:

1. **Graphe territorial** — zones d'emploi connectées par mobilité domicile-travail et adjacence géographique (`gamma_geo`, `gamma_mob` appris)
2. **Régime learner** — état latent continu qui module l'arbitrage local/graphe sans flags manuelles (`alpha_by_year` appris)
3. **q_tensor URSSAF** — structure locale du marché du travail (effectifs × secteur × lag temporel)
4. **Semi-supervision sectorielle** — objectif A10 auxiliaire pour régulariser la structure sectorielle

**Entrées candidat Q7:**
- `side_lag_1` — créations d'établissements année précédente
- `growth_1y` — taux de croissance YoY
- `effectifs_lag1` — employés URSSAF avec lag 1 an, par secteur A10 × ZE

---

## Généralisation internationale (Phase 4E — painel européen causal)

> **⚠️ Note critique — leakage temporel Phase 4A/4D (2026-06-03)**
>
> Les batteries Phase 4A et Phase 4D calculaient `growth_1y[t] = (y[t] − y[t-1]) / y[t-1]`,
> ce qui utilise l'objectif courant `y[t]`. Les WMAPE correspondants sont **invalides comme
> baseline scientifique**. Phase 4E corrige cela avec `growth_1y[t] = (y[t-1] − y[t-2]) / y[t-2]`
> (données passées uniquement). Voir `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md`.
>
> **Baseline causal actuel : Phase 4E-B (par pays — feature-policy ablation 180 runs).**

### Résultats Phase 4E-B (baseline causal final, 10 seeds par pays)

| Pays | Baseline limpo | WMAPE | Config | Interprétation |
|------|---------------|-------|--------|---------------|
| FR | `b2_side2_zero` | 0.1031 ± 0.0084 | lag1 + causal growth1, zero tensor | modèle simple gagne |
| NL | `b0_baseline_annual` | 0.1017 ± 0.0075 | historique complet 5 features | historique complet gagne; side2 dégrade (+25%) |
| BE | `b3_current_clean_zero` | 0.1488 ± 0.0063 | current_clean, zero tensor | current_clean gagne; side2 dégrade |
| PT | `b5_side2_emp_lag1` | 0.2286 ± 0.0148 | lag1 + growth1 + tensor emploi | tensor Eurostat/ARDECO gagne |

Phase 4E-C doit comparer contre ces vencedores par pays — pas contre Phase 4E-A.  
Phase 4A/4D : référence historique uniquement — **affectées par fuite temporelle sur `growth_1y`**.

<details>
<summary>Résultats intermédiaires Phase 4E-A/A2 (historique)</summary>

| Pays | Phase 4E-A (n=10) | Phase 4E-A2 (n=10) | Config A2 |
|------|-------------------|---------------------|-----------|
| FR | 0.117044 ± 0.004437 | 0.103189 ± 0.008034 | fr_side2 |
| NL | 0.103570 ± 0.008227 | 0.102759 ± 0.006983 | current_clean + zero |
| BE | 0.154536 ± 0.008184 | 0.162253 ± 0.008524 | side5_lag1_growth1y + zero |
| PT | 0.246521 ± 0.013689 | 0.234945 ± 0.009427 | side5_lag1_growth1y + effectifs_lag1 |

</details>

### Sources de données internationales

| Composant | France | Belgique | Pays-Bas | Portugal |
|-----------|--------|---------|---------|---------|
| Créations entreprises | SIDE/SIRENE | Statbel TVA primo-assujettissements | CBS 83631NED | INE 0009702 |
| Effectifs (Q-tensor) | URSSAF effectifs | ONSS localunit Q4 | CBS 83582NED | Eurostat `nama_10r_3empers` + ARDECO SNETZ 2024 |
| Stock entreprises | SIDE | Statbel TVA | CBS 81578NED | INE 0009819 |
| Territoire | 306 ZE | **42** arrondissements | 40 COROP | **25 NUTS3** |
| Secteur | NAF Rev.2 | NACE-BEL → A10 | SBI 2008 → A10 | CAE Rev.3 → A10 |
| Fenêtre Phase 4E | 2012–2024 | 2007–2024 | 2015–2025 | 2008–2024 |
| Preflight | ✅ | ✅ | ✅ | ✅ (tensor framing ⚠️) |

Voir `reports/HERALD_PHASE4_INTERNATIONAL_PLAN.md` et `reports/HERALD_EUROPEAN_PANEL_STANDARD_PLAN.md`.

---

## État scientifique actuel — Phase 4 (généralisation LOCO 4 pays)

> Phase 4G/4H/4I étend le painel européen à un protocole **leave-one-country-out**
> (FR, NL, BE, PT). Cette section reflète l'état validé après les audits 4H-B et
> 4I-A et l'audit indépendant du prochain pas. **Elle supersède, pour le claim de
> généralisation, les chiffres antérieurs des phases 4A/4D (affectées par fuite).**

### Protocole (à énoncer précisément)

Le protocole est un **LOCO « parameter zero-shot avec historique du pays-cible
disponible »** : le pays exclu ne participe pas à l'ajustement (Ridge, préproc,
loss neuronale), mais ses **lags historiques** et ses écarts-types par zone
proviennent de son propre passé à l'inférence. **Ce n'est pas un cold-start
complet** — distinction établie dans `HERALD_PHASE4H_CODE_CONCEPT_AUDIT_2026.md`.

### Résultats valides (4 pays, horizon 1 an, métrique WMAPE annuelle balancée par pays)

| Modèle | WMAPE balancé 4 pays | Statut |
|--------|----------------------|--------|
| Persistance (last value) | **~0.0939** | meilleur baseline balancé |
| Ridge non pondéré | ~0.0969 | meilleur modèle entraînable |
| Graphe réel / résiduel neuronal / sélection par compatibilité | ≥ Ridge | ne transfère pas robustement |

- Le **graphe réel ne dépasse pas consistamment** l'identité ni le graphe permuté
  (BE : petit gain, non significatif).
- Le **résiduel neuronal** et la **sélection par compatibilité de descripteurs**
  ne transfèrent pas robustement dans ce protocole (compat. améliore NL/PT mais
  dégrade FR +113 % et BE +27 %).

### Limites du claim (à respecter)

- Claim **conditionnel valide** : « la méthode actuelle ne transfère pas
  robustement sur **ces 4 pays et ce protocole** ».
- Claim **universel interdit** : ceci **ne prouve pas** que graphes ou résiduels
  ne fonctionnent **jamais** sur d'autres pays ou protocoles (n=4 domaines, pas de
  puissance statistique ; les seeds ne sont pas des pays indépendants).
- L'**avantage de la persistance est dépendant de l'horizon d'un an** — non
  testé au-delà.

### Géométries et targets hétérogènes (fait confirmé par les adapters)

| Pays | Géométrie | Target (concept national) |
|------|-----------|---------------------------|
| FR | ZE2020 | créations d'établissements (SIDE/SIRENE) |
| NL | COROP | oprichtingen van vestigingen (CBS 83631NED, unité locale) |
| BE | arrondissements | primo-assujettissements TVA (StatBel) |
| PT | NUTS3 | naissances d'entreprises INE (0009702/0014098) |

Le painel **mélange 4 systèmes spatiaux** (pas du NUTS3 homogène → exposé au
*Modifiable Areal Unit Problem*) et **plusieurs concepts de target dont l'équivalence
sémantique n'est pas établie documentalement**. Ne pas présenter ces targets
comme équivalents.

### Décision méthodologique actuelle

**Ne pas étendre les pays ni augmenter l'architecture.** Phase 4J a exécuté les
deux gates :

1. **Gate sémantique : FAIL pour un target unique harmonisé.** FR/NL mesurent des
   unités locales avec des règles différentes, BE une première inscription TVA,
   PT des naissances d'entreprises INE. Le panneau actuel reste utilisable comme
   benchmark de transfert entre tâches hétérogènes, pas comme preuve de
   généralisation d'un target identique.
2. **Gate combinaison agrégé : PASS, promotion finale : en attente.** La moyenne
   fixe `0.5 × persistance + 0.5 × Ridge` réduit le WMAPE balancé de `0.093912` à
   `0.087067` (-7.29 %) et améliore la moyenne dans les 4 pays. Mais elle dégrade
   fortement certaines pires années; les poids appris sur pays-source ne
   transfèrent pas de façon sûre.

Les intervalles conformes rolling restent exploratoires: couverture raisonnable,
mais largeur élevée en FR/PT. Prochaine décision: construire un nouveau target
européen harmonisé, ou formaliser le problème comme transfert multi-tâche à
targets explicitement hétérogènes.

### Rapports principaux

- `reports/HERALD_PHASE4_NEXT_STEP_INDEPENDENT_AUDIT.md` — audit indépendant, matrice de décision, gates
- `reports/HERALD_PHASE4J_A_FORECAST_COMBINATION_AUDIT.md` — combinaison, stabilité et incertitude
- `reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` — audit officiel des concepts de target
- `reports/HERALD_PHASE4H_B_RESULTS_AUDIT.md` — résultats LOCO corrigés (graphe réel, contrôle permutation)
- `reports/HERALD_PHASE4I_A_RESULTS_AUDIT.md` — benchmark de transfert sélectif (persistance vs Ridge vs graphe)
- `reports/HERALD_PHASE4H_CODE_CONCEPT_AUDIT_2026.md` — audit code/concept, définition du protocole

---

## Structure du dépôt

```
dataset/
├── data/           données brutes, intermédiaires et panels canoniques
├── hpc/            batteries SLURM, scripts de soumission et audits
├── hpc_results/    sorties HPC (non versionnées, régénérables)
├── reports/        rapports méthodologiques, audits et dashboards
│   └── dashboards/ herald_france_dashboard.html
├── src/            code modèle, baselines, visualisation
└── metadata/       splits walk-forward, datasets, politiques de données
```

---

## Commandes principales

```bash
# Régénérer le dashboard France
python3 src/visualisation/generate_herald_semi_v2_dashboard.py

# Vérifier les panneaux Phase 4 (NL/BE/PT)
python3 src/data/phase4_preflight.py

# Lancer batterie Phase 4 (après préparation des scripts)
bash hpc/phase4/submit_herald_phase4_nl.sh
bash hpc/phase4/submit_herald_phase4_be.sh
bash hpc/phase4/submit_herald_phase4_pt.sh

# Agréger résultats France
python3 hpc/regime/aggregate_herald_regime_results.py --root hpc_results/<run_root>

# Auditer Phase 3E
python3 hpc/regime/audit_herald_phase3e_qtensor_arch_results.py \
  --root hpc_results/herald_regime_phase3e_qtensor_arch_20260527_173259_r1
```

---

## Documents clés

**Phase 3E (sélection architecture q_tensor):**
- `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md` — verdict Q7

**Phase 2R (confirmatoire France):**
- `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md`
- `reports/HERALD_CURRENT_MODEL_DECISION_20260527.md`

**Phase 4E (généralisation internationale — painel européen causal):**
- `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md` — **baseline causal final par pays (Phase 4E-B)**
- `reports/HERALD_PHASE4E_B_FEATURE_POLICY_PLAN.md` — design de la feature-policy ablation
- `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md` — audit leakage Phase 4A + historique 4E-A/A2
- `reports/HERALD_EUROPEAN_PANEL_STANDARD_PLAN.md` — architecture du painel européen standardisé
- `src/data/european_panel/build_european_panel.py` — pipeline causal (enforce_causal_growth)
- `src/data/european_panel/validation.py` — garde causale automatique sur growth_1y/2y
- `hpc/phase4/` — batteries HPC Phase 4E-A/A2/B complètes

**Phase 4G/4H/4I/4J (généralisation LOCO 4 pays — état scientifique actuel):**
- `reports/HERALD_PHASE4_NEXT_STEP_INDEPENDENT_AUDIT.md` — audit indépendant + gates de décision
- `reports/HERALD_PHASE4J_A_FORECAST_COMBINATION_AUDIT.md` — combinaison 50/50 (candidate), stabilité, conformal exploratoire
- `reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` — audit officiel des targets (gate sémantique : FAIL, Path H/M)
- `reports/HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md` — table canonique des 4 targets (PT gate fermé : Eurostat total enterprise births)
- `reports/HERALD_PHASE4J_PATH_M_PROTOCOL.md` — protocole transfert multi-tâche à targets hétérogènes
- `reports/HERALD_PHASE4J_TARGET_AWARE_RESULTS.md` — résultats par concept + tail-risk (50/50 : FAIL, non promu)
- `reports/HERALD_PHASE4H_B_RESULTS_AUDIT.md` — résultats LOCO corrigés
- `reports/HERALD_PHASE4I_A_RESULTS_AUDIT.md` — benchmark de transfert sélectif
- `reports/HERALD_PHASE4H_CODE_CONCEPT_AUDIT_2026.md` — audit code/concept + protocole

**Phase 4A/4D (legacy — leakage-affected, ne pas utiliser comme baseline):**
- `data/external/PHASE4_DATA_STATUS.md` — statut panneaux NL/BE/PT (pipelines anciens)
- `src/data/ingest_belgium_panel.py` — pipeline Belgique ancien (growth_1y leaky)
- `src/data/ingest_netherlands_panel.py` — pipeline Pays-Bas ancien (growth_1y leaky)
- `src/data/ingest_portugal_panel_nuts3.py` — pipeline Portugal ancien (growth_1y leaky)

**Audit intégrité:**
- `reports/HERALD_LEAK_AUDIT_FINAL_20260507.md`

**Dashboard:**
- `reports/dashboards/herald_france_dashboard.html`

---

## Règle de présentation

Pour le papier, l'application et le dashboard: **HERALD**. Les variantes internes (Q7, L5, Phase 2J, etc.) sont des configurations expérimentales qui prouvent la robustesse — pas une histoire de versions successives.
