# HERALD France — audit final de fuite de donnees

Date: 2026-05-07

## Verdict court

Les tests disponibles ne detectent pas de fuite directe du target 2025.

Formulation scientifique recommandee:

> Aucun indice de fuite directe du target n'a ete trouve. Quand le target 2025 est melange entre zones, la WMAPE 2025 explose dans tous les modeles, ce qui indique que les bonnes performances originales ne proviennent pas d'une copie directe du target.

## Integrite des batteries

- Strict ex-ante original: `120/120` runs lus.
- Target-shuffle stress: `120/120` JSONs presents.
- Comparaison exacte des predictions: `120` fichiers compares.
- Differences exactes observees: `90`.
- Note: cette comparaison exacte est trop stricte pour des entrainements GPU repetes; les predictions 2024 changent aussi legerement, alors que le target 2024 n'a pas ete modifie. Le critere principal est donc l'effet sur la WMAPE 2025 apres melange du target.

## Resultats strict ex-ante originaux

### strict_lag_only

| Modele | N | Mean | 2024 | 2025 | Sector |
|---|---:|---:|---:|---:|---:|
| V7 graph_only | 10 | 0.017482 | 0.027109 | 0.007854 | 0.092891 |
| V6 self_only | 10 | 0.019315 | 0.030733 | 0.007898 | 0.197873 |
| Semi noSSL | 10 | 0.017695 | 0.027374 | 0.008015 | 0.094046 |
| V6 full | 10 | 0.018546 | 0.028717 | 0.008374 | 0.192869 |
| Semi SSL | 10 | 0.019719 | 0.028349 | 0.011089 | 0.158495 |
| Ridge only | 10 | 0.032304 | 0.030697 | 0.033911 | 0.108274 |

### strict_no_source_flags

| Modele | N | Mean | 2024 | 2025 | Sector |
|---|---:|---:|---:|---:|---:|
| Semi SSL | 10 | 0.023222 | 0.028135 | 0.018309 | 0.166971 |
| V6 self_only | 10 | 0.026383 | 0.031705 | 0.021062 | 0.199003 |
| Semi noSSL | 10 | 0.024352 | 0.024514 | 0.024190 | 0.102220 |
| V6 full | 10 | 0.026564 | 0.028500 | 0.024628 | 0.200565 |
| V7 graph_only | 10 | 0.025004 | 0.024141 | 0.025867 | 0.102255 |
| Ridge only | 10 | 0.032304 | 0.030697 | 0.033911 | 0.131351 |

## Comparaisons 2025 clefs

| Panel | Comparaison | Wins | Diff WMAPE 2025 | Lecture |
|---|---|---:|---:|---|
| strict_lag_only | Semi SSL vs Ridge | 10/10 | 0.022822 | fort |
| strict_lag_only | Semi SSL vs V6 full | 1/10 | -0.002715 | faible/negatif |
| strict_lag_only | Semi SSL vs V7 graph | 2/10 | -0.003234 | faible/negatif |
| strict_lag_only | Semi SSL vs Semi noSSL | 1/10 | -0.003074 | faible/negatif |
| strict_no_source_flags | Semi SSL vs Ridge | 10/10 | 0.015602 | fort |
| strict_no_source_flags | Semi SSL vs V6 full | 10/10 | 0.006319 | fort |
| strict_no_source_flags | Semi SSL vs V7 graph | 7/10 | 0.007558 | directionnel |
| strict_no_source_flags | Semi SSL vs Semi noSSL | 7/10 | 0.005881 | directionnel |

## Test target-shuffle

Principe: le target 2025 est melange entre zones, mais toutes les features restent identiques.
Si le modele copiait le target, la performance resterait artificiellement bonne sur le target melange. Si la performance s'effondre, la bonne performance originale ne vient pas d'une copie directe du target.

- Fichiers originaux: `120`
- Fichiers stress: `120`
- Fichiers communs: `120`
- Differences exactes de prediction: `90` fichiers. Interpretation: non-determinisme GPU/retraining, car 2024 change aussi legerement.
- Plus grande derive moyenne 2024 apres stress: `0.001798` WMAPE.
- Ratio minimal de degradation WMAPE 2025: `36.8x`.

| Panel | Modele | 2024 orig | 2024 stress | 2025 orig | 2025 stress | Ratio 2025 |
|---|---|---:|---:|---:|---:|---:|
| strict_lag_only | Semi SSL | 0.028349 | 0.028139 | 0.011089 | 1.243531 | 112.1x |
| strict_lag_only | Semi noSSL | 0.027374 | 0.026657 | 0.008015 | 1.242263 | 155.0x |
| strict_lag_only | V6 full | 0.028717 | 0.029294 | 0.008374 | 1.240338 | 148.1x |
| strict_lag_only | V6 self_only | 0.030733 | 0.031084 | 0.007898 | 1.243073 | 157.4x |
| strict_lag_only | V7 graph_only | 0.027109 | 0.027561 | 0.007854 | 1.243641 | 158.3x |
| strict_lag_only | Ridge only | 0.030697 | 0.030697 | 0.033911 | 1.246719 | 36.8x |
| strict_no_source_flags | Semi SSL | 0.028135 | 0.029030 | 0.018309 | 1.247107 | 68.1x |
| strict_no_source_flags | Semi noSSL | 0.024514 | 0.026312 | 0.024190 | 1.241028 | 51.3x |
| strict_no_source_flags | V6 full | 0.028500 | 0.028529 | 0.024628 | 1.242828 | 50.5x |
| strict_no_source_flags | V6 self_only | 0.031705 | 0.031987 | 0.021062 | 1.248605 | 59.3x |
| strict_no_source_flags | V7 graph_only | 0.024141 | 0.024413 | 0.025867 | 1.243266 | 48.1x |
| strict_no_source_flags | Ridge only | 0.030697 | 0.030697 | 0.033911 | 1.246719 | 36.8x |

## Forecast prospectif 2026/2027

Pas de WMAPE ici: les annees futures n'ont pas encore de `y_true`.

- Semi SSL no_source_flags 2026: prediction nationale moyenne `1336856`, delta vs ridge `-29070` (-2.13%).
- Semi SSL no_source_flags 2027: prediction nationale moyenne `1398013`, delta vs ridge `-30672` (-2.15%).

## Risque residuel

Le risque residuel n'est plus principalement un leak direct du target. Il concerne le calendrier de disponibilite des variables:

- calendrier detaille: `reports/HERALD_DATA_AVAILABILITY_CALENDAR.md`
- SIDE 2025 doit etre date par rapport a la date de forecast 2026;
- FLORES 2025, SIDE stocks apres 2023 et URSSAF 2025 doivent etre verifies;
- le panel complet avec `has_*source` doit rester une ablation.

## Conclusion

Le protocole strict + target-shuffle permet une conclusion forte mais non absolue: aucune fuite directe du target 2025 n'est detectee. Pour transformer cela en forecast operationnel publiable, il faut figer une date de prediction et exclure toute variable non publiee a cette date.
