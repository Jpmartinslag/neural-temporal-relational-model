# HERALD — Prévision Économique Territoriale · France

**HERALD** (*Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*)
est un Spatio-Temporal Graph Neural Network (STGNN) pour la **prévision annuelle des créations
d'établissements par zone d'emploi** en France, à partir des données SIDE/INSEE.

---

## Phase actuelle — stabilisation méthodologique France

Le projet entre maintenant dans la phase **HERALD-France robuste**, avant toute extension à d'autres
pays ou transformation en application. L'objectif est de fermer proprement la validation scientifique
sur la France, puis de construire des indicateurs économiques exploitables dans un dashboard/app.

Priorités immédiates :

1. **Leak audit final** — confirmer l'absence de fuite de données et séparer strictement forecast, nowcast et backtest rétrospectif.
2. **Calendrier réel de disponibilité** — vérifier quelles variables sont réellement disponibles au moment opérationnel de la prévision.
3. **Batterie finale de comparaison** — comparer HERALD aux baselines Ridge AR, ARIMA, LSTM, STGNN/DCRNN et variantes internes sur le même panel.
4. **Forecast 2026/2027** — produire des prévisions prospectives France avec protocole ex-ante explicite.
5. **Dashboard propre + indicateurs économiques dérivés** — cartes, erreurs territoriales, secteurs A10, accélération/décélération et zones d'incertitude.

Les tests internationaux (Portugal, Espagne, Suisse, UE) viendront ensuite comme validation externe,
pas comme étape de correction du modèle France.

---

## Résultat principal (bateria geo2025 — 2026-05-02)

| Modèle | WMAPE moyen | Vs Ridge AR |
|---|---|---|
| **HERALD V6 h64** ← meilleur | **0.0313 ± 0.0046** | −47% |
| HERALD V3 | 0.0336 ± 0.0066 | −43% |
| DCRNN résiduel | 0.0537 | −9% |
| Ridge AR | 0.0592 | référence |
| LSTM local | 0.0910 | +54% |

**Semi-supervision par masquage :** résultat négatif. Le masquage dégrade la performance (+9%)
par rapport à V6 h64. Le grafo dinâmico tem forte valor interpretativo (adj_delta COVID ×10–20),
mas seu ganho preditivo isolado exige ablação `fixed_adj` ainda não rodada.

→ Dashboard interactif complet :
`hpc_results/herald_semi_total_253_geo2025/reports/figures/herald_geo2025_final_dashboard.html`

---

## Structure du projet

```
dataset/
├── data/
│   ├── raw/           # Données brutes INSEE (non versionnées)
│   ├── interim/       # Tables intermédiaires (versionnées)
│   └── processed/     # Panneaux modèle, graphes, cibles
├── docs/              # PDFs de référence méthodologique
├── hpc/               # Scripts SLURM (.sbatch) et d'exécution (.sh)
├── hpc_results/       # Sorties des runs HPC par batterie
│   └── herald_semi_total_253_geo2025/   # Batterie principale (253 runs)
│       ├── baselines_v3_v6_stgnn/       # V3, V6 h32/h64, STGNNs, baselines
│       ├── semi_seeds_0_1/              # HERALD Semi seeds 0–1
│       ├── semi_seeds_7_13/             # seeds 7–13
│       ├── semi_seeds_17_42/            # seeds 17–42
│       ├── semi_seeds_77_99/            # seeds 77–99
│       ├── semi_seeds_123_2025/         # seeds 123–2025
│       └── reports/figures/            # Dashboard HTML final
├── metadata/          # Catalogues INSEE, manifests
├── old/               # Archive héritage pré-HERALD
├── reports/
│   ├── herald_v3/     # Métriques V3
│   ├── herald_v6/     # Métriques V6
│   ├── dynamic_stgnn/ # Métriques STGNNs
│   ├── archive/       # V4, V5, historiques
│   └── figures/       # Dashboards antérieurs
├── src/
│   ├── modeles/       # Scripts d'entraînement (train_herald_v6.py, …)
│   ├── analyse/       # Analyse statistique et évaluation
│   └── visualisation/ # Génération de dashboards HTML
└── tools/             # Outils externes
```

---

## Données

| Jeu de données | Source | Couverture |
|---|---|---|
| Créations d'établissements | SIDE/INSEE | 2012–2025, annuel, 280 ZE, 9 secteurs A10 |
| Graphe de mobilité | Flux domicile-travail INSEE | ZE→ZE, annuel |
| Graphe géographique | Contiguïté ZE + distance | Statique geo2025 |
| Covariables | BPE, Filosofi, population, stocks, SITADEL | par ZE, annuel |

**Protocole d'évaluation :** rolling-origin walk-forward — folds 2021, 2022, 2023, 2024, 2025.

---

## Architecture HERALD V6 h64

- Graphe **dynamique** appris année par année (adjacence adaptative)
- **Gate de mobilité** : pondère mobilité vs géographie (γ_mob/γ_geo ≈ 3.5×)
- Encodeur **GRU** + propagation de graphe (type Chebyshev)
- Tête de prévision **totale** + tête **sectorielle A10** (9 secteurs NAF)
- Hidden dim = 64, top_k = 10, gate_bias = 2.0

---

## Utilisation

```bash
# Environnement
source .venv/bin/activate

# Entraînement HERALD V6
python3 src/modeles/train_herald_v6.py

# Générer le dashboard
python3 src/visualisation/generate_herald_geo2025_dashboard.py

# Ouvrir le dashboard
xdg-open hpc_results/herald_semi_total_253_geo2025/reports/figures/herald_geo2025_final_dashboard.html
```

---

## Observations méthodologiques pendantes

1. Ablation `fixed_adj` — isoler la valeur prédictive du graphe dynamique vs statique
2. Précovid pour V6 h64 et V3 — comparer la robustesse hors COVID
3. `spatial_block` catastrophique (+40% WMAPE) — vérifier l'implémentation
4. Valider les 117 nouvelles connexions Semi avec les données de mobilité INSEE

---

*Fichiers hérités archivés dans `old/legacy_before_herald_focus_2026_04_27/`*
