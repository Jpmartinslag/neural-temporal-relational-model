# HERALD Intelligence Layer — Spécification Méthodologique

**Version** : 1.1 — 2026-05-07 (corrigé post-audit)  
**Statut** : **Prototype / Esqueleto** — à régénérer après finalisation de la batterie HPC  
**Périmètre** : France — 280 zones d'emploi (ZE2020)  
**Données source** : HERALD prédictions 2021–2025, observé INSEE SIDE 2012–2025, forecast 2026–2027

---

## 1. Contexte et Objectif

La couche HERALD Intelligence transforme les prédictions brutes de créations d'établissements en **indicateurs économiques auditables** : rankings, alertes, scores d'opportunité et de risque, et explications territoriales en français.

**Principe fondamental** : aucun indicateur n'est un score isolé. Tout est comparé à des paramètres réels observables.

---

## 2. Nomenclature Publique

Les noms internes de version n'apparaissent **jamais** dans les narratifs, CSVs publics ou présentations. Ils peuvent apparaître uniquement dans les chemins de fichiers techniques.

| Nom interne (usage fichiers uniquement) | Nom public |
|---|---|
| herald_v6, herald_v3, herald_v7 | HERALD |
| semiv2_graph_nossl / semiv2_graph_ssl | contrôle sans semi-supervision |
| self_only / fixed_geo_mob_only | contrôle sans graphe (contrôle local) |
| Ridge_AR | baseline Ridge AR (contrôle linéaire) |
| ARIMA | baseline ARIMA |
| LSTM | baseline LSTM |
| DCRNN / STGNN externe | baseline DCRNN/STGNN (modèles comparatifs) |

---

## 3. Sources de Données

### 3.1 Données disponibles

| Fichier | Contenu | Années | Niveau | Usage | Risque méthodologique |
|---|---|---|---|---|---|
| `v6_results_.../herald_v6_predictions_total_*_seed_*_v1.csv` | Prédictions HERALD totales, 7 seeds | 2021–2025 | ZE2020 | Indicateurs prédits, erreur, incertitude | Aucune fuite confirmée (audit 20260507) |
| `v6_results_.../herald_v6_predictions_sector_*_seed_*_v1.csv` | Prédictions HERALD par secteur A10, 7 seeds | 2021–2025 | ZE2020 × secteur | Signal sectoriel prédit | Proportions dérivées du total |
| `target_side_establishments_annual_core_through_2025_v1.csv` | Créations d'établissements observées (SIDE) | 2012–2025 | ZE2020 | Base observée, historique, benchmark | Révisions INSEE possibles |
| `side_creations_a10_ze2020_through_2025_v1.csv` | Créations observées par secteur A10 | 2012–2025 | ZE2020 × secteur A10 | Spécialisation sectorielle, croissance nationale | Couverture sectorielle partielle |
| `dynamic_feature_panel_baseline_predictions_v1.csv` | Prédictions baseline Ridge AR | 2021–2024 | ZE2020 | Comparaison performance HERALD | Pas de 2025 pour baselines |
| `graph_edges_ze2020_core_v0.csv` | Arêtes du graphe (adjacence géo + mobilité) | Statique | ZE2020 | Dépendance territoriale | Mobilité pendulaire 2016–2019 (Recensement) |
| `graph_adjacency_mobility_v0.csv` | Matrice de poids de mobilité 280×280 | Statique | ZE2020 | Force des liens inter-zones | Mobilité pré-COVID, peut sous-représenter télétravail |
| `graph_nodes_ze2020_core_v0.csv` | Métadonnées zones (code, nom, communes) | Statique | ZE2020 | Labellisation | — |
| `dynamic_stgnn_feature_panel_through_2025_v1.csv` | Panel complet de features (lag, stocks, URSSAF, FLORES) | 2012–2025 | ZE2020 | Feature engineering | Features prospectives non disponibles après 2025 |
| `herald_forecast_total_lag_only_v6_full_forecast_2026_2027_seed_*_v1.csv` | Forecast 2026–2027 par zone (HERALD, panel lag_only) | 2026–2027 | ZE2020 | Forecast prospectif | **Prospectif — aucune vérité terrain disponible** |
| `herald_forecast_sector_lag_only_v6_full_forecast_2026_2027_seed_*_v1.csv` | Forecast 2026–2027 secteurs A10 par zone | 2026–2027 | ZE2020 × secteur | Signal sectoriel prospectif | Proportions dérivées |
| `03_zone_level_analysis_2025.csv` | Analyse de performance par zone (comparaison models) | 2025 | ZE2020 | Validation croisée variantes | Millésime 2025 (observé) |

### 3.2 Données manquantes

| Donnée manquante | Où elle devrait être | Comment la générer | Impact méthodologique |
|---|---|---|---|
| Baseline ARIMA par zone | `data/processed/arima_predictions_ze2020_v1.csv` | Réentraîner ARIMA(1,1,1) ou auto-ARIMA par zone sur 2012-2020, évaluer 2021-2025 | Comparaison HERALD vs ARIMA impossible — comparaison limitée à Ridge AR |
| Baseline LSTM par zone | `data/processed/lstm_predictions_ze2020_v1.csv` | Modèle LSTM univarié par zone, walk-forward | Impossible d'évaluer avantage HERALD sur deep learning univarié |
| Baseline DCRNN/STGNN externe | `data/processed/stgnn_ext_predictions_ze2020_v1.csv` | Implémenter DCRNN ou comparaison avec STGNN public | Impossible d'isoler apport du graphe appris HERALD vs graphe standard |
| Baseline naive lag-1 (walk-forward) | `data/processed/naive_lag1_predictions_ze2020_v1.csv` | Simple `y_pred = y_{t-1}` par zone | Disponible indirectement dans feature panel (`side_lag_1`) |
| Forecast 2026–2027 par zone avec baseline ARIMA | Même dossier forecast | Idem ARIMA ci-dessus | Incertitude sur les zones où HERALD diverge fortement de Ridge AR |
| Régions administratives (REG) par ZE2020 | `data/interim/mappings/ze2020_to_region.csv` | Jointure avec référentiel INSEE | Rankings régionaux impossibles |
| `hpc_results/herald_strict_exante_20260507_142538/` | `dataset/hpc_results/` | Run HPC non encore synchronisé | Utiliser `herald_strict_exante_20260506_night_final/` comme substitut |

---

## 4. Indicateurs — Définitions et Formules

### 4.1 Indicateurs de croissance

| # | Indicateur | Formule | Données nécessaires | Comparaison | Interprétation | Limite |
|---|---|---|---|---|---|---|
| 1 | **Croissance observée 2024→2025** | `(obs_2025 - obs_2024) / obs_2024 × 100` | obs. SIDE 2024, 2025 | Moyenne nationale, historique zone | Trajectoire réelle récente | Révisions INSEE possibles |
| 2 | **Prédiction HERALD 2025 vs historique** | `(pred_2025_mean - hist_mean) / hist_mean × 100` | HERALD preds, hist 2012–2020 | Historique de la zone | Positionnement HERALD sur la zone | Dépend qualité modèle |
| 3 | **Croissance forecast 2025→2026** | `(fc_2026_mean - obs_2025) / obs_2025 × 100` | Forecast HERALD, obs 2025 | Médiane nationale, hist zone | Signal de dynamisme 2026 | **Prospectif, non validé** |
| 4 | **Accélération vs historique (2026)** | `(fc_2026_mean - hist_mean) / hist_mean × 100` | Forecast HERALD, hist 2012–2020 | hist_mean zone, nationale | Écart structurel à la moyenne | Mélange historique + forecast |
| 5 | **Décélération 2026→2027** | `(fc_2027_mean - fc_2026_mean) / fc_2026_mean × 100` | Forecast HERALD, 2026+2027 | Percentile national de décélération | Signal de ralentissement | Double prospectif |

### 4.2 Indicateurs d'incertitude et d'erreur

| # | Indicateur | Formule | Données | Comparaison | Limite |
|---|---|---|---|---|---|
| 6 | **WMAPE historique HERALD** | `mean(|pred - obs| / obs) × 100` sur 2021–2025 | HERALD preds (seed mean), obs SIDE | Ridge AR WMAPE | 5 points seulement |
| 7 | **Incertitude inter-seeds (CV)** | `std_seeds / mean_seeds` | V6 ou forecast, multi-seeds | Distribution nationale des CV | Proxy d'incertitude, pas IC bayésien |
| 8 | **Avantage HERALD vs Ridge AR** | `(herald_wmape - ridge_wmape) / ridge_wmape × 100` | HERALD preds, baselines | 0 = parité | Négatif = HERALD meilleur |

### 4.3 Indicateurs structurels

| # | Indicateur | Formule | Données | Interprétation | Limite |
|---|---|---|---|---|---|
| 9a | **Dépendance au pôle principal (prior mobilité)** | Poids mobilité vers top-3 zones voisines / total sortant | Matrice mobilité 280×280 (prior statique, INSEE ~2016–2019) | High = zone satellite d'un pôle | **Ce n'est PAS le graphe appris par HERALD** — c'est le prior de mobilité. Données 2016–2019. |
| 9b | **Poids du lien appris par HERALD (graphe dynamique)** | `dynamic_adj[-1, i, j]` extrait des fichiers NPZ internals | NPZ `dynamic_adj`, forme (T, 280, 280) | Poids final après apprentissage du modèle | **Statut: pending** — extraction NPZ non encore implémentée |
| 10 | **Concentration sectorielle (Herfindahl)** | `Σ (share_secteur_i)²` sur A10 | A10 obs 2017–2020 | >0.25 = forte spécialisation | Statique |
| 11 | **Spécialisation relative par secteur** | `share_zone_secteur / share_national_secteur` | A10 obs, total national | >1 = surreprésenté vs France | Données 2017-2020 |
| 12 | **Signal sectoriel forecast (prop_pred)** | `y_pred_secteur / y_pred_total` par secteur | Forecast secteurs HERALD | Secteurs moteurs du signal HERALD | Proportions dérivées |

### 4.4 Scores composites

#### Score d'opportunité

```
opportunity_score = percentile_rank(
    0.30 × c_local_trend          # fc_2026 vs hist_mean (percentile rank croissant)
  + 0.20 × c_national_diff        # fc_2026 vs moyenne nationale
  + 0.15 × c_vs_baseline          # fc_2026 vs Ridge AR (HERALD signal additionnel)
  + 0.20 × c_reliability          # (1 - WMAPE_percentile) → faible erreur = bon
  + 0.15 × c_low_uncertainty      # (1 - CV_percentile) → faible incertitude = bon
)
```

#### Score de risque

```
risk_score = percentile_rank(
    0.30 × c_deceleration         # décroissance fc_2025→2026 (percentile décroissant)
  + 0.15 × c_volatility           # std historique (percentile croissant)
  + 0.15 × c_concentration        # Herfindahl A10 (percentile croissant)
  + 0.10 × c_graph_dep            # top3 mobilité concentration
  + 0.20 × c_uncertainty          # CV seeds (percentile croissant)
  + 0.10 × c_herald_error         # WMAPE historique (percentile croissant)
)
```

**Justification des poids initiaux** : poids simples, basés sur importance relative des signaux dans la littérature de prévision économique territoriale. La composante principale (décélération / tendance locale) reçoit 0.30 ; les composantes d'incertitude reçoivent un poids cumulé de 0.35 dans le score de risque. Ces poids sont une **proposition initiale** : une régression ou calibration sur des événements de décrochage observés permettrait de les optimiser.

**Alternative percentile pure** : remplacer les poids fixes par un vote majoritaire sur les 5 composantes (chaque zone au-dessus du p75 sur ≥ 3 composantes = "opportunité élevée"). Cette approche est plus robuste aux outliers.

---

## 5. Paramètres de Comparaison Réels

Chaque indicateur doit être accompagné des éléments suivants :

| Contexte | Source | Disponibilité |
|---|---|---|
| Moyenne nationale France (tous secteurs) | Agrégat obs SIDE 2012–2025 | ✓ Disponible |
| Moyenne historique de la zone (2012–2020) | obs SIDE par zone | ✓ Disponible |
| Percentiles nationaux p10/p25/p50/p75/p90 | Distribution obs ou forecast | ✓ Calculés |
| Baseline Ridge AR | `dynamic_feature_panel_baseline_predictions_v1.csv` | ✓ 2021–2024 |
| Croissance nationale par secteur A10 | Agrégat `side_creations_a10_ze2020_*` | ✓ Disponible |
| Zones voisines géographiques | `graph_edges_ze2020_core_v0.csv` (edge_type = geographic_adjacency) | ✓ Disponible |
| Zones connectées par mobilité | `graph_adjacency_mobility_v0.csv` | ✓ Disponible |
| Baseline ARIMA | En attente batterie HPC | ⏳ Pending (pas définitivement absent) |
| Baseline LSTM | En attente batterie HPC | ⏳ Pending |
| Baseline DCRNN/STGNN (modèles comparatifs) | En attente batterie HPC | ⏳ Pending |
| Régions administratives (REG) | Jointure référentiel INSEE | ✗ À générer (jointure simple) |
| Grafo appris HERALD (poids dynamiques) | NPZ internals `dynamic_adj[-1]` | ⏳ Pending extraction NPZ |

**Format exigé pour tout ranking** :

> "La zone X est au p90 national de croissance prévue, 18% au-dessus de sa moyenne historique, avec une incertitude inter-seeds faible et une meilleure performance que la baseline Ridge AR. Le signal est porté par les secteurs MN et GI."

**Format interdit** :

> ~~"La zone X est dynamique."~~

---

## 6. Fichiers de Sortie

Tous les fichiers sont dans `reports/metrics/herald_intelligence/`.

| Fichier | Contenu | Lignes | Usage recommandé |
|---|---|---|---|
| `zone_growth_ranking.csv` | Ranking zones par croissance prévue 2026, avec contexte historique et national | 280 | Dashboard principal, carte choroplèthe |
| `zone_deceleration_ranking.csv` | Zones avec fc_growth_2025_2026 < 0, triées par décélération | 39 | Monitoring, alertes risque |
| `zone_uncertainty_ranking.csv` | Ranking par CV inter-seeds, avec WMAPE historique | 280 | Filtre de confiance avant recommandation |
| `zone_sector_opportunity_a10.csv` | Herfindahl, parts sectorielles hist., croissance sectorielle, signal forecast | 280 | Analyse sectorielle, ciblage politique |
| `zone_graph_dependency.csv` | Top-3 pôles de mobilité, concentration, poids de self-loop | 280 | Compréhension structure territoriale |
| `zone_alerts.csv` | Alertes typées (deceleration, high_uncertainty, high_error, opportunity) | 157 | Notifications, tableau de bord alertes |
| `zone_recommendation_scores.csv` | Scores finaux opportunité/risque, composantes, explication en français | 280 | Recommandation, rapport export |

---

## 7. Explications Automatiques en Français — Templates

### Opportunité élevée, faible incertitude
```
Cette zone est classée en opportunité élevée car la croissance prévue dépasse 
la médiane nationale (p{X}), l'incertitude entre seeds est faible (CV = {Y}) 
et les secteurs {S1}/{S2} contribuent fortement au signal. HERALD est {Z}% 
au-dessus de la baseline Ridge AR.
```

### Décélération prévue
```
Cette zone doit être surveillée : HERALD prévoit une décélération de {X}% 
(2025→2026), supérieure au p75 national de décélération. 
La concentration sectorielle ({S1} représente {Y}% des créations) amplifie 
le signal de risque.
```

### Signal exploratoire (forte incertitude)
```
Le signal est exploratoire : la prévision est élevée mais l'incertitude 
inter-seeds est forte (CV = {X} > 0.10). Interpréter avec prudence ; 
toute recommandation sur cette zone doit signaler ce niveau d'incertitude.
```

### Erreur historique élevée
```
L'erreur historique HERALD sur cette zone est élevée (WMAPE = {X}%). 
Toute prévision doit être considérée comme indicative uniquement.
```

---

## 8. Règles Méthodologiques

1. **Ne pas inférer de causalité** : HERALD prédit des corrélations spatiotemporelles, pas des mécanismes causaux.
2. **Ne pas affirmer qu'une zone "va croître avec certitude"** : toujours indiquer l'incertitude inter-seeds et l'erreur historique.
3. **Séparer observé / prédit / forecast** :
   - Observé = SIDE INSEE 2012–2025
   - Prédit = HERALD sur la période de validation 2021–2025
   - Forecast = HERALD 2026–2027 (aucune vérité terrain disponible)
4. **Ne pas mélanger WMAPE validé avec performance forecast** : le WMAPE 2021–2025 caractérise le modèle sur données observées ; il ne garantit pas la précision 2026–2027.
5. **Tout score doit être décomposable** : les 5 composantes du score d'opportunité et les 6 composantes du score de risque sont toutes exportées dans `zone_recommendation_scores.csv`.
6. **Toute recommandation doit pointer vers une évidence** : format "Zone X est en opportunité car [composante dominante]".
7. **Si baselines ARIMA/LSTM manquantes, marquer comme exploratoire** : le champ `arima_lstm_available = False` est propagé dans tous les CSVs.
8. **Ne pas utiliser les noms internes de version dans la narration publique** (voir table section 2).

---

## 9. Tiers d'Opportunité et de Risque

Les scores sont des percentiles nationaux sur les 280 zones.

| Tier | Score | Interprétation |
|---|---|---|
| Très élevée/Très élevé | p75–p100 | Signal fort, mais vérifier composantes |
| Élevée/Élevé | p50–p75 | Signal modéré, exploitable |
| Modérée/Modéré | p25–p50 | Signal faible, surveillance |
| Faible | p0–p25 | Pas de signal particulier |

**Note** : la distribution est uniforme par construction (percentiles). Un score "très élevé" signifie "dans le quartile supérieur parmi les 280 zones", pas "fort en valeur absolue".

---

## 10. Ce qu'il Manque pour Intégration Dashboard/App

### Priorité haute
1. **Baseline ARIMA par zone** (2021–2025) : permet de distinguer zones où HERALD apporte un vrai signal vs zones où un simple ARIMA suffit.
2. **Carte géographique ZE2020** (GeoJSON ou Shapefile) : actuellement disponible dans `data/interim/territorial_xlsx/ZE2020_au_01-01-2026.xlsx` — convertir en GeoJSON pour affichage cartographique.
3. **Mapping ZE2020 → Région administrative** : pour agréger les rankings par région.

### Priorité moyenne
4. **Forecast 2026–2027 multi-modèles** : les CSVs actuels n'utilisent que le modèle HERALD principal (panel `lag_only`). Intégrer le contrôle sans semi-supervision comme variante de comparaison.
5. **Séries temporelles par zone** : le dashboard actuel montre des agrégats ; ajouter une vue par zone avec historique + forecast.

### Priorité basse
6. **Baselines LSTM/DCRNN** : utiles pour la narrativité scientifique, peu impactantes pour l'utilisateur final.

---

## 11. Statut des Indicateurs

Trois niveaux : **validé** (comparaison sur données observées, méthodologie stable), **exploratoire** (logique correcte, paramètres non calibrés ou données partielles), **à confirmer** (en attente de données ou run finale).

| Indicateur | Statut | Usage autorisé |
|---|---|---|
| Croissance observée 2024→2025 | **validé** | Recommandation |
| WMAPE HERALD 2021–2024 (aligné Ridge) | **validé** | Filtre de confiance |
| WMAPE HERALD 2025 (HERALD seul, sans baseline) | **exploratoire** | Exploration |
| Prédiction HERALD 2025 vs historique | **validé** | Recommandation |
| Forecast 2026 total, comparé Ridge AR | **exploratoire** | Exploration (prospectif, non validé) |
| Incertitude inter-seeds (CV) | **exploratoire** | Filtre de confiance — pas recommandation seule |
| Signal sectoriel A10 (historique) | **validé** | Recommandation |
| Signal sectoriel forecast 2026 (proportions) | **exploratoire** | Exploration |
| Dépendance mobilité (prior statique) | **exploratoire** | Exploration — ne pas présenter comme "graphe appris HERALD" |
| Dépendance graphe appris HERALD (poids NPZ) | **à confirmer** | En attente extraction NPZ |
| Forecast baseline ARIMA/LSTM/STGNN | **à confirmer** | En attente batterie HPC finale |
| Rankings régionaux | **à confirmer** | En attente jointure région |
| Score opportunité/risque | **exploratoire** | Exploration uniquement — calibration requise pour recommandation |
| Explications en français | **exploratoire** | Prototype — formulaires à valider avant présentation publique |

---

## 12. Corrections Post-Audit (v1.0 → v1.1)

| # | Problème identifié | Correction appliquée |
|---|---|---|
| 1 | Source HERALD = run 2026-04-30, non finale | Chemins paramétrés dans le script — mettre à jour `HERALD_PRED_DIR` après batterie finale |
| 2 | WMAPE comparatif calculé sur années différentes (HERALD 2021–2025 vs Ridge 2021–2024) | **Corrigé** : `herald_wmape_aligned` utilise uniquement les années communes ; 2025 reporté séparément |
| 3 | Graphe présenté sans distinction prior/appris | **Corrigé** : champ `graph_source: mobility_prior` + `learned_adj_status: pending` dans tous les CSVs |
| 4 | Scores sans statut explicite de fiabilité | **Corrigé** : champ `score_status: exploratoire_poids_non_calibres` dans `zone_recommendation_scores.csv` |
| 5 | ARIMA/LSTM marqués `available: False` (absence définitive) | **Corrigé** : `baseline_arima_status: pending_hpc_battery` |
| 6 | Noms V6/V7/Semi dans narratif du spec | **Corrigé** : remplacés par HERALD / contrôle local / contrôle linéaire / modèles comparatifs |

---

*HERALD Intelligence Layer v1.1 — 2026-05-07 (post-audit)*  
*Données : INSEE SIDE 2012–2025, HERALD (run prototype 2026-04-30, 7 seeds, ZE2020)*  
*À régénérer avec batterie HPC finale avant utilisation dashboard public.*
