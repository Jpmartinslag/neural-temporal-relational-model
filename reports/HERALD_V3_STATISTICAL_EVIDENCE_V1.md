# HERALD V3 Statistical Evidence

## Overall

- Ridge AR WMAPE: `0.066080`
- HERALD WMAPE: `0.022495`
- Relative gain: `65.96%`
- DM p-value (absolute error, normal approximation): `2.742e-33`

## Diebold-Mariano Tests

| comparison | loss | n | mean_loss_diff | dm_stat | p_value_normal_approx |
| --- | --- | --- | --- | --- | --- |
| HERALD_full_mean_vs_Ridge_AR | absolute_error | 1120 | -177.022 | -12.0214 | 2.742e-33 |
| HERALD_full_mean_vs_Ridge_AR_2021 | absolute_error | 280 | -158.122 | -9.54052 | 1.42123e-21 |
| HERALD_full_mean_vs_Ridge_AR_2022 | absolute_error | 280 | -284.275 | -8.38376 | 5.12619e-17 |
| HERALD_full_mean_vs_Ridge_AR_2023 | absolute_error | 280 | -234.109 | -5.85959 | 4.64012e-09 |
| HERALD_full_mean_vs_Ridge_AR_2024 | absolute_error | 280 | -31.5824 | -1.74356 | 0.0812361 |
| HERALD_full_mean_vs_Ridge_AR | absolute_percentage_error | 1120 | -0.0638401 | -27.0985 | 1.02568e-161 |
| HERALD_full_mean_vs_Ridge_AR_2021 | absolute_percentage_error | 280 | -0.0890053 | -19.6146 | 1.16015e-85 |
| HERALD_full_mean_vs_Ridge_AR_2022 | absolute_percentage_error | 280 | -0.0936573 | -18.3267 | 5.07087e-75 |
| HERALD_full_mean_vs_Ridge_AR_2023 | absolute_percentage_error | 280 | -0.027771 | -6.90601 | 4.9846e-12 |
| HERALD_full_mean_vs_Ridge_AR_2024 | absolute_percentage_error | 280 | -0.0449268 | -11.694 | 1.36743e-31 |
| HERALD_full_mean_vs_Ridge_AR | wmape_numerator | 1120 | -177.022 | -12.0214 | 2.742e-33 |
| HERALD_full_mean_vs_Ridge_AR_2021 | wmape_numerator | 280 | -158.122 | -9.54052 | 1.42123e-21 |
| HERALD_full_mean_vs_Ridge_AR_2022 | wmape_numerator | 280 | -284.275 | -8.38376 | 5.12619e-17 |
| HERALD_full_mean_vs_Ridge_AR_2023 | wmape_numerator | 280 | -234.109 | -5.85959 | 4.64012e-09 |
| HERALD_full_mean_vs_Ridge_AR_2024 | wmape_numerator | 280 | -31.5824 | -1.74356 | 0.0812361 |

## Zone Strata

| stratification | stratum | n | zones | ridge_wmape | herald_wmape | delta_wmape | relative_gain_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| size_stratum | small | 280 | 70 | 0.202393 | 0.0989564 | -0.103437 | 51.1069 |
| size_stratum | medium_low | 280 | 70 | 0.0975327 | 0.0370715 | -0.0604612 | 61.9907 |
| size_stratum | medium_high | 280 | 70 | 0.0555421 | 0.0125803 | -0.0429618 | 77.35 |
| size_stratum | large | 280 | 70 | 0.05553 | 0.0177536 | -0.0377764 | 68.0288 |
| commune_stratum | few_communes | 280 | 70 | 0.08814 | 0.0294685 | -0.0586714 | 66.5662 |
| commune_stratum | midlow_communes | 288 | 72 | 0.0760134 | 0.0268176 | -0.0491958 | 64.7199 |
| commune_stratum | midhigh_communes | 276 | 69 | 0.0503985 | 0.021005 | -0.0293935 | 58.3222 |
| commune_stratum | many_communes | 276 | 69 | 0.0695728 | 0.0182454 | -0.0513274 | 73.775 |

## Gamma Stability

| seed | gamma_geo | gamma_mob | gamma_mob_minus_geo |
| --- | --- | --- | --- |
| 0 | 0.00462098 | 1.1003 | 1.09568 |
| 7 | 0.0529713 | 1.07966 | 1.02669 |
| 42 | 0.109549 | 1.08016 | 0.97061 |

## Top Adaptive Neighbors

| target_year | source_city | source_ze2020 | source_name | rank | neighbor_ze2020 | neighbor_name | weight |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | Paris | 1109 | Paris | 1 | 1112 | Roissy | 0.268645 |
| 2021 | Paris | 1109 | Paris | 2 | 1115 | Versailles-Saint-Quentin | 0.18751 |
| 2021 | Paris | 1109 | Paris | 3 | 1113 | Saclay | 0.177385 |
| 2021 | Paris | 1109 | Paris | 4 | 1106 | Marne-la-Vallée | 0.137176 |
| 2021 | Paris | 1109 | Paris | 5 | 1114 | Seine-Yvelinoise | 0.081719 |
| 2021 | Paris | 1109 | Paris | 6 | 1104 | Évry-Courcouronnes | 0.0815994 |
| 2021 | Paris | 1109 | Paris | 7 | 1101 | Cergy-Vexin | 0.0554097 |
| 2021 | Paris | 1109 | Paris | 8 | 1108 | Melun | 0.00473674 |
| 2021 | Paris | 1109 | Paris | 9 | 1107 | Meaux | 0.00378452 |
| 2021 | Paris | 1109 | Paris | 10 | 1103 | Étampes | 0.00203419 |
| 2021 | Lyon | 8421 | Lyon | 1 | 8406 | Bourgoin-Jallieu | 0.281167 |
| 2021 | Lyon | 8421 | Lyon | 2 | 8434 | Villefranche-sur-Saône | 0.193466 |
| 2021 | Lyon | 8421 | Lyon | 3 | 8433 | Vienne-Annonay | 0.172882 |
| 2021 | Lyon | 8421 | Lyon | 4 | 8405 | Bourg-en-Bresse | 0.146524 |
| 2021 | Lyon | 8421 | Lyon | 5 | 8428 | Saint-Étienne | 0.118459 |
| 2021 | Lyon | 8421 | Lyon | 6 | 8430 | Tarare | 0.0410468 |
| 2021 | Lyon | 8421 | Lyon | 7 | 1109 | Paris | 0.0194789 |
| 2021 | Lyon | 8421 | Lyon | 8 | 8409 | Grenoble | 0.0145951 |
| 2021 | Lyon | 8421 | Lyon | 9 | 59 | Mâcon | 0.00670993 |
| 2021 | Lyon | 8421 | Lyon | 10 | 8412 | La Plaine du Forez | 0.00331352 |
| 2021 | Marseille | 9312 | Marseille | 1 | 9301 | Aix-en-Provence | 0.631102 |
| 2021 | Marseille | 9312 | Marseille | 2 | 9313 | Martigues-Salon | 0.220535 |
| 2021 | Marseille | 9312 | Marseille | 3 | 9318 | Toulon | 0.114716 |
| 2021 | Marseille | 9312 | Marseille | 4 | 9303 | Brignoles | 0.0120226 |
| 2021 | Marseille | 9312 | Marseille | 5 | 1109 | Paris | 0.00581414 |
| 2021 | Marseille | 9312 | Marseille | 6 | 9311 | Manosque | 0.00477289 |
| 2021 | Marseille | 9312 | Marseille | 7 | 53 | Avignon | 0.00369395 |
| 2021 | Marseille | 9312 | Marseille | 8 | 52 | Arles | 0.0033706 |
| 2021 | Marseille | 9312 | Marseille | 9 | 9306 | Cavaillon | 0.00204673 |
| 2021 | Marseille | 9312 | Marseille | 10 | 9315 | Nice | 0.00100647 |
| 2021 | Toulouse | 7625 | Toulouse | 1 | 7615 | Montauban | 0.269516 |
| 2021 | Toulouse | 7625 | Toulouse | 2 | 7602 | Albi | 0.163448 |
| 2021 | Toulouse | 7625 | Toulouse | 3 | 7612 | Foix-Pamiers | 0.129984 |
| 2021 | Toulouse | 7625 | Toulouse | 4 | 7604 | Auch | 0.115388 |
| 2021 | Toulouse | 7625 | Toulouse | 5 | 7622 | Saint-Gaudens | 0.112243 |
| 2021 | Toulouse | 7625 | Toulouse | 6 | 7610 | Castres-Mazamet | 0.0817806 |
| 2021 | Toulouse | 7625 | Toulouse | 7 | 7608 | Carcassonne-Limoux | 0.0564376 |
| 2021 | Toulouse | 7625 | Toulouse | 8 | 7609 | Castelsarrasin-Moissac | 0.0279585 |
| 2021 | Toulouse | 7625 | Toulouse | 9 | 1109 | Paris | 0.0272528 |
| 2021 | Toulouse | 7625 | Toulouse | 10 | 7505 | Bordeaux | 0.0159912 |
| 2022 | Paris | 1109 | Paris | 1 | 1112 | Roissy | 0.267684 |
| 2022 | Paris | 1109 | Paris | 2 | 1115 | Versailles-Saint-Quentin | 0.187392 |
| 2022 | Paris | 1109 | Paris | 3 | 1113 | Saclay | 0.177585 |
| 2022 | Paris | 1109 | Paris | 4 | 1106 | Marne-la-Vallée | 0.136395 |
| 2022 | Paris | 1109 | Paris | 5 | 1104 | Évry-Courcouronnes | 0.0823461 |
| 2022 | Paris | 1109 | Paris | 6 | 1114 | Seine-Yvelinoise | 0.0820101 |
| 2022 | Paris | 1109 | Paris | 7 | 1101 | Cergy-Vexin | 0.055845 |
| 2022 | Paris | 1109 | Paris | 8 | 1108 | Melun | 0.00482633 |
| 2022 | Paris | 1109 | Paris | 9 | 1107 | Meaux | 0.00382946 |
| 2022 | Paris | 1109 | Paris | 10 | 1103 | Étampes | 0.0020865 |
| 2022 | Lyon | 8421 | Lyon | 1 | 8406 | Bourgoin-Jallieu | 0.279908 |
| 2022 | Lyon | 8421 | Lyon | 2 | 8434 | Villefranche-sur-Saône | 0.193413 |
| 2022 | Lyon | 8421 | Lyon | 3 | 8433 | Vienne-Annonay | 0.17331 |
| 2022 | Lyon | 8421 | Lyon | 4 | 8405 | Bourg-en-Bresse | 0.146479 |
| 2022 | Lyon | 8421 | Lyon | 5 | 8428 | Saint-Étienne | 0.119066 |
| 2022 | Lyon | 8421 | Lyon | 6 | 8430 | Tarare | 0.041188 |
| 2022 | Lyon | 8421 | Lyon | 7 | 1109 | Paris | 0.0195775 |
| 2022 | Lyon | 8421 | Lyon | 8 | 8409 | Grenoble | 0.0146977 |
| 2022 | Lyon | 8421 | Lyon | 9 | 59 | Mâcon | 0.00669485 |
| 2022 | Lyon | 8421 | Lyon | 10 | 8412 | La Plaine du Forez | 0.00329647 |
| 2022 | Marseille | 9312 | Marseille | 1 | 9301 | Aix-en-Provence | 0.632177 |
| 2022 | Marseille | 9312 | Marseille | 2 | 9313 | Martigues-Salon | 0.21965 |
| 2022 | Marseille | 9312 | Marseille | 3 | 9318 | Toulon | 0.114671 |
| 2022 | Marseille | 9312 | Marseille | 4 | 9303 | Brignoles | 0.0119481 |
| 2022 | Marseille | 9312 | Marseille | 5 | 1109 | Paris | 0.00583213 |
| 2022 | Marseille | 9312 | Marseille | 6 | 9311 | Manosque | 0.0047384 |
| 2022 | Marseille | 9312 | Marseille | 7 | 53 | Avignon | 0.00368064 |
| 2022 | Marseille | 9312 | Marseille | 8 | 52 | Arles | 0.00333966 |
| 2022 | Marseille | 9312 | Marseille | 9 | 9306 | Cavaillon | 0.00202771 |
| 2022 | Marseille | 9312 | Marseille | 10 | 9315 | Nice | 0.00162157 |
| 2022 | Toulouse | 7625 | Toulouse | 1 | 7615 | Montauban | 0.269373 |
| 2022 | Toulouse | 7625 | Toulouse | 2 | 7602 | Albi | 0.163103 |
| 2022 | Toulouse | 7625 | Toulouse | 3 | 7612 | Foix-Pamiers | 0.130078 |
| 2022 | Toulouse | 7625 | Toulouse | 4 | 7604 | Auch | 0.115586 |
| 2022 | Toulouse | 7625 | Toulouse | 5 | 7622 | Saint-Gaudens | 0.112195 |
| 2022 | Toulouse | 7625 | Toulouse | 6 | 7610 | Castres-Mazamet | 0.081693 |
| 2022 | Toulouse | 7625 | Toulouse | 7 | 7608 | Carcassonne-Limoux | 0.0564743 |
| 2022 | Toulouse | 7625 | Toulouse | 8 | 7609 | Castelsarrasin-Moissac | 0.0280661 |
| 2022 | Toulouse | 7625 | Toulouse | 9 | 1109 | Paris | 0.0275249 |
| 2022 | Toulouse | 7625 | Toulouse | 10 | 7505 | Bordeaux | 0.015906 |
