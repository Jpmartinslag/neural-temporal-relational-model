# HERALD Regime Discovery Battery

Objectif: tester si HERALD peut apprendre les changements de régime économique
sans recevoir des indicateurs manuels `COVID` / `rebound`.

Cette batterie est expérimentale. Elle n'écrase pas les sorties utilisées par le
dashboard HERALD France actuel.

## Hypothèses testées

| Mode | Description | Flags manuelles dans les features annuelles ? |
|---|---|---:|
| `manual_flags` | Contrôle actuel: COVID/rebound + croissance globale | oui |
| `no_regime` | Aucun signal de régime | non |
| `change_point` | Rupture statistique dérivée des lags observables | non |
| `no_regime + learned_regime_both` | HERALD crée un régime latent interne pour le graphe et l'arbitrage | non |

## Décision Phase 2A: LatentGate conservateur

La première batterie a montré que les flags manuelles restent le contrôle le plus solide en WMAPE moyen
et en A10, tandis que les régimes non manuels améliorent surtout 2025. La conclusion n'est donc pas de
basculer directement vers une architecture plus complexe, mais de tester une étape plus parcimonieuse:

```text
HERALD doit apprendre un état latent minimal qui module l'arbitrage local/graphe,
sans recevoir de label manuel d'événement.
```

La Phase 2A ne teste pas encore de mixture-of-experts lourd. Avec seulement 2012-2025, le panel temporel
est court; la priorité est l'auditabilité et la stabilité entre seeds.

| Configuration | Régime explicite | Variante interne | Raison |
|---|---|---|---|
| `manual_flags` | flags manuelles | `full` | contrôle à battre |
| `no_regime` | zéro | `full` | test sans régime |
| `latent_gate` | zéro | `learned_regime_gate` | état latent interne module alpha local/graphe |
| `latent_gate_cp_aux` | rupture statistique | `learned_regime_gate` | rupture ex-ante auxiliaire + alpha latent |

Chaque configuration doit être lancée avec et sans `has_*_source`. Ces flags de disponibilité sont
légitimes pour documenter le panel, mais peuvent agir comme proxy temporel indirect. La Phase 2A les
teste donc explicitement au lieu de supposer qu'elles sont neutres.

Critère de victoire opérationnel:

- pas de `is_covid_year` ni `is_post_covid_rebound`;
- différence absolue de WMAPE moyen <= 0.001 face au contrôle, ou meilleure;
- pas de dégradation notable en 2025;
- pas de dégradation A10;
- trajectoire latente et alpha stables entre seeds.

Les variantes `Small-RegimeMoE-3E` et `A10-aware expert` restent en seconde étape. Elles ne seront
justifiées que si `latent_gate` ou `latent_gate_cp_aux` montrent un signal robuste.

## Décision Phase 2B: garde A10 avant MoE

La Phase 2A a identifié un candidat prometteur:

```text
no_regime + learned_regime_gate + no_source_flags
```

Ce candidat améliore surtout les années récentes, mais il dégrade la tête A10. La Phase 2B ne lance
donc pas encore un `Mixture-of-Experts` complet. Elle teste d'abord si le signal latent peut être
conservé tout en protégeant les secteurs.

| Label | Mode | Variante | Source flags | sector lambda | But |
|---|---|---|---|---:|---|
| `ctrl` | `manual_flags` | `full` | non | 0.1 | contrôle opérationnel comparable |
| `candidate` | `no_regime` | `learned_regime_gate` | non | 0.1 | candidat Phase 2A |
| `sec02` | `no_regime` | `learned_regime_gate` | non | 0.2 | augmenter légèrement la garde A10 |
| `sec03` | `no_regime` | `learned_regime_gate` | non | 0.3 | tester la frontière total/A10 |
| `sec05` | `no_regime` | `learned_regime_gate` | non | 0.5 | stress test A10 |
| `secenh` | `no_regime` | `learned_regime_gate_sector_enhanced` | non | 0.2 | combiner gate latent et tête A10 adaptative |
| `alpha005` | `no_regime` | `learned_regime_gate` | non | 0.2 | lisser davantage alpha local/graphe |
| `smooth003` | `no_regime` | `learned_regime_gate` | non | 0.2 | lisser davantage le graphe |
| `cp_sec02` | `change_point` | `learned_regime_gate` | non | 0.2 | rupture ex-ante + garde A10 |
| `both_sec02` | `no_regime` | `learned_regime_both` | non | 0.2 | état latent sur graphe et gate |

Critère de lecture:

- ne pas choisir uniquement la meilleure moyenne WMAPE;
- comparer la frontière de Pareto entre WMAPE moyen, WMAPE 2025 et A10;
- rejeter toute variante qui gagne en 2025 mais dégrade A10 de façon persistante;
- n'envisager MoE qu'après une variante latente stable sans flags manuelles.

## Critère scientifique

La version intéressante n'est pas forcément celle qui gagne de quelques points de
WMAPE. Le test central est:

```text
un régime non manuel égale ou dépasse le contrôle manual_flags
```

Si oui, le claim devient plus fort:

```text
HERALD détecte des régimes économiques latents à partir des signaux passés,
sans que le chercheur impose explicitement les années COVID/rebound.
```

Le test le plus strict est `no_regime + learned_regime_both`: aucune flag
manuelle n'entre dans les features annuelles, et HERALD apprend lui-même un
vecteur de régime latent à partir de sa représentation interne.

## Commande HPC

Depuis la racine du projet:

```bash
bash hpc/regime/submit_herald_regime_discovery.sh
```

Pour la Phase 2A conservatrice:

```bash
REGIME_PLAN=latent_gate_phase2a bash hpc/regime/submit_herald_regime_discovery.sh
```

Pour la Phase 2B A10 guard:

```bash
REGIME_PLAN=phase2b_a10_guard bash hpc/regime/submit_herald_regime_discovery.sh
```

Ne pas lancer directement `run_herald_regime_array.sbatch` sauf si `OUT_ROOT`
est explicitement fourni. Le script `submit_herald_regime_discovery.sh` crée un
répertoire unique et audite les chemins avant le `sbatch`.

Paramètres utiles:

```bash
EPOCHS=800 MAX_PARALLEL=10 bash hpc/regime/submit_herald_regime_discovery.sh
```

Après la fin:

```bash
python3 hpc/regime/aggregate_herald_regime_results.py \
  --root hpc_results/herald_regime_discovery_<STAMP_OR_JOBID>
```

## Sorties

```text
hpc_results/herald_regime_discovery_*/
  reports/per_run/
  reports/herald_regime_discovery_runs.csv
  reports/herald_regime_discovery_summary.csv
  reports/HERALD_REGIME_DISCOVERY_SUMMARY.md
  data_processed/
  metadata/
```

## Garde-fous méthodologiques

- Les modes non manuels retirent `is_covid_year` et
  `is_post_covid_rebound` des features annuelles.
- La normalisation des régimes utilise seulement les années du train du fold.
- Les signaux sont dérivés de lags forecast-safe, pas du target observé du fold.
- Le régime latent appris peut conditionner le graphe et l'arbitrage
  local/graphe, mais il ne réduit pas directement la pénalité de lissage du
  graphe. Cela évite une solution dégénérée où le modèle inventerait des sauts
  de régime uniquement pour autoriser un graphe instable.
- Les sorties ont un `OUT_ROOT` dédié et ne contaminent pas le dashboard actuel.
- Les fichiers NPZ sauvegardent `latent_regime_values` pour vérifier si le
  régime appris présente des ruptures temporelles interprétables.
- La Phase 2A peut retirer `has_flores_source`, `has_side_stock_source` et
  `has_urssaf_source` des features annuelles via `--drop-source-flags`.

## Variantes optionnelles non lancées par défaut

Le code contient aussi `growth_only`, `shock_zscore`, `latent_quantile` et
`latent_change`, mais elles ne sont pas dans la batterie par défaut. Elles sont
gardées uniquement pour exploration ultérieure si le résultat principal justifie
une analyse plus fine.
