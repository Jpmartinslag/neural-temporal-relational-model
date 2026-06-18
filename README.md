# HERALD — Système européen d'intelligence économique territoriale

**HERALD** (*Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*) est un **système européen d'intelligence économique territoriale**. Il combine prévision quantitative, détection d'états économiques, graphe territorial, graphe sectoriel, explication et (à terme) recommandation.

La naissance d'entreprises (`enterprise_birth` / `establishment_creation` / `local_unit_opening` selon le pays) est **le premier indicateur opérationnel**, choisi parce qu'il est mesurable et harmonisable entre pays — ce n'est pas l'objectif unique du système. La direction officielle, le périmètre et les claims autorisés/interdits sont définis dans `reports/HERALD_PROJECT_CHARTER.md`, qui prévaut sur toute description informelle.

**Pour reprendre ce dépôt :** lire d'abord `CODEX_MEMORY.md` (point d'entrée concis), puis `reports/HERALD_CURRENT_STATE.md` (état détaillé par couche), puis `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (toutes les décisions DEC-001→DEC-068) et `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` (quel document lire/ignorer).

---

## 1. Qu'est-ce que HERALD ?

Un système qui, pour chaque **territoire × secteur × année** d'un ensemble de pays européens :

1. **Prévoit** l'activité d'entreprise attendue (naissances/ouvertures par secteur).
2. **Détecte un état économique** (croissance, stagnation, déclin, reprise, etc.) à partir de la série observée.
3. **Cartographie des relations secteur→secteur** validées statistiquement (précédence temporelle).
4. **Explique** quelles variables/secteurs/territoires sont associés aux changements observés.
5. **Visualise** tout cela dans l'« Observatory », un tableau de bord interactif.
6. **Recommandera** (futur, non encore validé) des opportunités territoriales/sectorielles.

---

## 2. Architecture actuelle

| Couche | Méthode actuelle | Statut |
|---|---|---|
| Données | Panel pays × territoire × secteur × année | FR/PT/NL observés ; IT/AT harmonisés (Path H) ; BE hétérogène |
| Prévision de base | Persistance + Ridge/AR(1), causal (rolling-origin) | Validé comme meilleure baseline (PT/IT/AT LOCO ; FR pending re-audit) |
| États économiques | Labels déterministes dérivés de la série observée : growth / stability / decline / recovery (+ acceleration/deceleration/stagnation) | Exportés (Observatory v0.1.1→v0.4) |
| Relations secteur→secteur | Précédence temporelle signée, lag-1, validation bootstrap/permutation/FDR (Phase 7) | Validée pour des paires spécifiques FR/NL COROP/PT Municipal (20 arêtes observées) |
| Niveaux d'évidence | `observed` / `proxy` / `robust` / `supported` (fine-grain) / `exploratory` (fine-grain) / `blocked` | Taxonomie figée (DEC-066, DEC-065) — voir §5 |
| Visualisation | « Observatory » — tableaux de bord HTML autonomes (Plotly embarqué) | v0.4.1 et v0.3 stables/historiques ; v0.5.1 actuel (voir §4) |
| Recommandation | — | **Travail futur, non implémenté, non validé** |

**Permis / interdit dans les publications :** voir `reports/HERALD_PROJECT_CHARTER.md` §4-5. En résumé : jamais de langage causal structurel pour les relations sectorielles ("précédence prédictive" / "association", pas "cause"), jamais de claim de généralisation universelle, jamais de recommandation présentée comme opérationnelle.

---

## 3. État actuel par composant (vérifié contre le decision log au 2026-06-18)

| Élément | Statut | Référence |
|---|---|---|
| FR ZE2020 | **Observé** (établissements créés, SIDE/SIRENE) | DEC-013, sector panel |
| PT Municipal (278 communes continentales) | **Observé** (INE 0009703/0014099) | DEC-062, Phase 7 DEC-064 |
| NL COROP (40 régions) | **Observé** (CBS 83631NED) | DEC-034/064, `NL_COROP_PHASE7` |
| NL Gemeente proxy (355 communes) | **Contexte uniquement** — jamais une relation/label d'entraînement | DEC-063 (construction), DEC-065 (BLOCKED pour relations) |
| NL Gemeente proxy pour labels de relation | **BLOQUÉ** — défaut de validité structurelle (le terme de pondération par part de stock injecte une corrélation inter-sectorielle non liée à la précédence des naissances) | DEC-065 |
| PT Municipal — Phase 7 (précédence sectorielle) | **Complet** — 2 paires COVID-robustes promues (GI→OQ, MN→JZ) | DEC-064 |
| DEC-066 — politique de seuil fine-grain | **Prête** (`FINE_GRAIN_THRESHOLD_POLICY_READY`) — seuil original 0.10 inchangé + palier supplémentaire 0.09 + palier exploratoire non-entraînable 0.07-0.09 | DEC-066 |
| Observatory v0.5.1 | **Tableau de bord actuel** (`herald_observatory_v051_narrative_dashboard.html`) — décision `OBSERVATORY_V051_NARRATIVE_READY` si les 103/103 tests passent (vérifié : ils passent). **Non encore committé en git**, validation visuelle Playwright toujours indisponible (validation structurelle JS/DOM uniquement) | DEC-068 |
| Observatory v0.5 | **Superseded** pour le statut "prêt" — rejeté par le product owner comme MVP poli (UI anglaise, architecture en bas de page, prédiction PT non fermée, pas de vraie carte de chaleur géographique). Conservé comme artefact historique, ses 65/65 tests passent toujours | DEC-067 (corrigé par DEC-068) |
| Observatory v0.4 / v0.4.1 | **Stables, historiques** — toujours corrects scientifiquement, dashboard v0.4.1 avec carte municipale PT réelle + graphe dynamique | DEC-065 addenda |

**Aucun de ces statuts n'a été modifié dans cette tâche de consolidation** — ils sont rapportés ici tels que trouvés dans le decision log et les rapports correspondants.

---

## 4. Tableaux de bord ("Observatory")

| Fichier | Statut | Notes |
|---|---|---|
| `reports/dashboards/herald_france_final_dashboard.html` | ACTIF — ne pas modifier sans décision explicite | Base France originale (DEC-014) |
| `reports/dashboards/herald_observatory_v03_dashboard.html` | ACTIF | Carte + graphe sectoriel + états + couche territoriale Phase 8 |
| `reports/dashboards/herald_observatory_v04_granular_dashboard.html` | ACTIF, stable/historique | FR ZE2020 + NL COROP + **PT Municipal choropleth réelle (278/278)** + graphe dynamique (slider, 3 modes, marqueurs) + panneau d'arêtes bloquées |
| `reports/dashboards/herald_observatory_v05_narrative_dashboard.html` | Historique — superseded pour le statut "prêt" (UI anglaise, MVP poli) | Conservé pour traçabilité ; ses tests passent toujours |
| `reports/dashboards/herald_observatory_v051_narrative_dashboard.html` | **ACTUEL** | Français ; architecture HERALD en tête de page ; prédiction FR+NL+PT (PT municipal fermée sans proxy ni HPC) ; carte = "Bassins économiques" (heatmap géographique réelle) ; graphe→carte connecté ; vocabulaire technique confiné à un panneau repliable. **Pas encore committé en git, pas encore validé visuellement (pas de Playwright disponible dans cet environnement)** |

Toutes les arêtes NL gemeente proxy et les 121 arêtes bloquées (`BLOCKED_PROXY_ARTIFACT`) sont vérifiées absentes du graphe de relations dans tous les dashboards — confirmé par tests automatisés, pas par inspection visuelle.

---

## 5. Niveaux d'évidence et vocabulaire de label

| Concept | Valeurs canoniques | Référence |
|---|---|---|
| `evidence_type` | `observed_births`, `observed_stock`, `proxy_disaggregated_by_stock_share` | DEC-063 |
| `label_class` (Phase 7 / fine-grain) | `ROBUST_ORIGINAL` (\|β\|≥0.10), `FINE_GRAIN_SUPPORTED` (\|β\|≥0.09 + critère additionnel), `EXPLORATORY_FINE_GRAIN` (0.07-0.09, jamais un label d'entraînement), `BLOCKED_PROXY_ARTIFACT`, `INSUFFICIENT_EVIDENCE` | DEC-066, DEC-065 |
| `region_system` | `ZE2020` (FR), `MUNICIPALITY_CONTINENTE` (PT), `COROP` (NL observé), `GEMEENTE_PROXY` (NL, contexte seulement) | adapters `src/data/european_panel/` |
| Statuts d'artefact | `VALID_OBSERVED`, `BLOCKED`, `INVALID_FOR_TRAINING_LABELS`, `INVALID_FOR_RELATION_LABELS`, `STRUCTURAL_ABSENT` (ex. KZ pour le PT) | `reports/herald_artifact_registry.json` |

Voir `reports/HERALD_NAMING_CONVENTIONS.md` pour l'audit complet des incohérences de nommage (versions de dashboard, numérotation DEC, etc.) et la table canonique.

---

## 6. Comment lancer les tests

Pas de suite de tests racine unique recommandée (la racine collecte aussi des paquets vendored sans rapport — voir note dans `CODEX_MEMORY.md`). Lancer les suites ciblées :

```bash
# Suite complète du dépôt (collecte des collisions non liées en root — connu, ignorer)
python3 -m pytest -q tests

# Suites Observatory (rapides, ~30-40s pour la plus lourde)
python3 -m pytest tests/test_observatory_v04_dashboard.py -q
python3 -m pytest tests/test_observatory_v041_visual_upgrade.py -q
python3 -m pytest tests/test_observatory_v04_granular_evidence_policy.py -q
python3 -m pytest tests/test_observatory_v05_narrative_dashboard.py -q
python3 -m pytest tests/test_observatory_v051_narrative_dashboard.py -q   # ~38s, 103 tests

# Suites de décisions récentes (DEC-060→DEC-066)
python3 -m pytest tests/test_dec060_france_relation_audit.py tests/test_dec061_municipal_granularity.py \
  tests/test_dec062_granular_preflight.py tests/test_dec064_pt_municipal_phase7.py \
  tests/test_dec065_nl_gemeente_proxy_phase7.py tests/test_dec066_threshold_calibration.py -q

# Registre d'artefacts (note : 6 tests historiquement en échec — schéma incomplet
# sur les entrées ajoutées depuis DEC-038 ; voir reports/HERALD_CURRENT_STATE.md)
python3 -m pytest tests/test_herald_artifact_registry.py -q
```

---

## 7. Où se trouvent les données et les décisions

- **Décisions :** `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-068) — jamais renuméroté ni supprimé, seulement corrigé/superseded explicitement.
- **Index de documents actifs :** `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` — classe chaque rapport (actif / historique / bloqué / régénérable).
- **Registre d'artefacts :** `reports/herald_artifact_registry.json` — chemin, statut, usage permis/interdit par artefact.
- **Panels principaux :**
  - `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv` — PT/IT/AT harmonisé (Path H, LOCO)
  - `data/processed/economic_graph/sector_panel_fr_nl_pt.csv` — panel sectoriel FR/NL/PT canonique
  - `data/processed/european_panel/pt_municipal_sector_panel.csv` — PT au niveau municipal
  - `data/processed/herald_observatory_v04_granular/` — exports propres Observatory v0.4 (territory_state, relation_edges observées uniquement, blocked_proxy_edges)
  - `data/processed/herald_observatory_v051_narrative/` — exports français v0.5.1 (non committés, volumineux — voir `.gitignore`)
- **Architecture détaillée :** `reports/HERALD_ARCHITECTURE_OVERVIEW.md`.
- **Calendrier de recherche :** `reports/HERALD_RESEARCH_GANTT.md`.

---

## 8. Structure du dépôt

```
dataset/
├── data/           données brutes, intermédiaires et panels canoniques
├── hpc/            batteries SLURM, scripts de soumission et audits
├── hpc_results/    sorties HPC (partiellement versionnées — JSON/manifest/README; raw npz/csv/logs ignorés)
├── reports/        rapports méthodologiques, audits et dashboards
│   └── dashboards/ herald_observatory_v051_narrative_dashboard.html ← actuel
├── src/            code modèle, baselines, builders d'export, visualisation
└── tests/          suites de tests par phase/décision
```

---

## 9. Règle de présentation

Pour le papier, l'application et le dashboard : **HERALD**. Les variantes internes (Q7, v0.3, v0.4, v0.5, v0.5.1, etc.) sont des étapes de développement qui prouvent la robustesse de la méthode — pas une histoire de versions à présenter telle quelle au lecteur final.

---

## 10. Claims permis (résumé — voir le Charter pour la liste complète et la portée précise)

**Permis :**
- La persistance est le meilleur baseline LOCO balancé pour PT/IT/AT (2008–2020, horizon 1 an).
- Les résidus italiens montrent une autocorrélation spatiale robuste.
- Les lags géographiques linéaires (queen-contiguité) n'améliorent pas les prévisions sous le protocole actuel.
- FR/NL/BE/PT ont des targets sémantiquement hétérogènes — le WMAPE poolé n'est pas une métrique de généralisation valide.
- HERALD Q7 (France) WMAPE 0.0204 — **PENDING_REAUDIT**, pas encore un claim de tête.
- 20 relations sectorielles observées (FR=9, NL COROP=8, PT Municipal=3) validées par précédence temporelle, dont 2 promues récemment en PT municipal (GI→OQ, MN→JZ).

**Interdits :**
- « HERALD fournit des recommandations économiques. »
- « Le graphe géographique améliore les prévisions. »
- « Le système se généralise à tout pays européen. »
- « Le protocole LOCO est un cold-start complet. »
- « Les poids d'attention expliquent les relations économiques. »
- « Granger-prédictabilité = causalité économique structurelle. »
- Traiter une arête NL gemeente proxy comme une relation observée ou un label d'entraînement.
