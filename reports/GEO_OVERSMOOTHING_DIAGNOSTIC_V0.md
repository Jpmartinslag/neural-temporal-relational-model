# Geo Oversmoothing Diagnostic v0

Date : 2026-04-21

## Objectif

Transformer l'intuition d'oversmoothing en diagnostic tabulaire reproductible sur la région 84 pour l'année cible 2023.

## Résumé global

- Zones : `39`
- Improved zones : `13`
- Worsened zones : `26`
- Mean delta (`geo_abs_error - ridge_abs_error`) : `6.365`
- Median delta : `12.373`
- Corr(degree, delta) : `0.467`
- Corr(target, delta) : `0.274`

## Par bande de degré

| degree_band | zones | avg_delta | median_delta | worsened | improved | avg_target | avg_degree |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-2 | 0 | nan | nan | 0 | 0 | nan | nan |
| 3-5 | 4 | -18.658 | -18.876 | 1 | 3 | 1606.0 | 4.00 |
| 6-8 | 14 | -11.653 | -6.111 | 7 | 7 | 1385.6 | 7.29 |
| 9+ | 21 | 23.144 | 24.653 | 18 | 3 | 5258.1 | 11.52 |

## Par bande de taille

| size_band | zones | avg_delta | median_delta | worsened | improved | avg_target | avg_degree |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| small | 13 | -11.747 | -12.329 | 6 | 7 | 846.9 | 8.31 |
| medium | 13 | -2.385 | 3.763 | 7 | 6 | 1764.0 | 7.69 |
| large | 13 | 33.228 | 27.463 | 13 | 0 | 7869.2 | 11.69 |

## Croisement degré × taille

| degree_band | size_band | zones | avg_delta | worsened | improved |
| :--- | :--- | ---: | ---: | ---: | ---: |
| 0-2 | small | 0 | nan | 0 | 0 |
| 0-2 | medium | 0 | nan | 0 | 0 |
| 0-2 | large | 0 | nan | 0 | 0 |
| 3-5 | small | 2 | -33.460 | 0 | 2 |
| 3-5 | medium | 2 | -3.856 | 1 | 1 |
| 3-5 | large | 0 | nan | 0 | 0 |
| 6-8 | small | 5 | -13.791 | 3 | 2 |
| 6-8 | medium | 8 | -13.799 | 3 | 5 |
| 6-8 | large | 1 | 16.211 | 1 | 0 |
| 9+ | small | 6 | -2.805 | 3 | 3 |
| 9+ | medium | 3 | 29.035 | 3 | 0 |
| 9+ | large | 12 | 34.646 | 12 | 0 |

## Plus fortes améliorations

| ze2020 | libze2020 | degree | y_true | delta |
| ---: | :--- | ---: | ---: | ---: |
| 8425 | Oyonnax | 6 | 731.0 | -79.593 |
| 8423 | Montluçon | 8 | 1296.0 | -59.902 |
| 8429 | Saint-Flour | 8 | 376.0 | -48.135 |
| 8420 | Les Sources de la Loire | 10 | 1031.0 | -46.730 |
| 8427 | Romans-sur-Isère | 8 | 1481.0 | -44.021 |
| 8424 | Moulins | 4 | 1085.0 | -40.642 |
| 8422 | Montélimar | 8 | 1710.0 | -26.447 |
| 8403 | Aurillac | 4 | 841.0 | -26.277 |
| 8410 | Issoire | 10 | 980.0 | -19.766 |
| 55 | Bollène-Pierrelatte | 6 | 1246.0 | -17.485 |

## Plus fortes dégradations

| ze2020 | libze2020 | degree | y_true | delta |
| ---: | :--- | ---: | ---: | ---: |
| 8416 | Le Genevois Français | 10 | 5173.0 | 71.095 |
| 8433 | Vienne-Annonay | 14 | 3667.0 | 58.042 |
| 8409 | Grenoble | 10 | 9796.0 | 55.312 |
| 8412 | La Plaine du Forez | 10 | 1144.0 | 50.398 |
| 64 | Valréas | 6 | 942.0 | 44.380 |
| 8402 | Aubenas | 10 | 2059.0 | 39.471 |
| 8405 | Bourg-en-Bresse | 12 | 3563.0 | 39.006 |
| 8401 | Annecy | 12 | 6072.0 | 33.874 |
| 8419 | Le Puy-en-Velay | 12 | 1395.0 | 33.746 |
| 8413 | La Tarentaise | 8 | 2579.0 | 31.691 |
