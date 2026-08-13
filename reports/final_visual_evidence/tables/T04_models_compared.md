# T04 — The models compared under the HERALD 93 protocol

One protocol only: 280 synthetic zones calibrated on French marginals, log-growth at horizon 1, twelve rolling origins, five seeds, scenarios S0_NULL and S1_SHARED, the same commuting support for every method. HERALD 96's Neural Granger arm is NOT in this table: it ran on 80 zones against a residual target, and the two numbers are not comparable.

| méthode | famille | graphe | objectif | paramètres | époques | secondes | mémoire (Mo) | abstention |
|---|---|---|---|---|---|---|---|---|
| Persistance | classique | aucun graphe | none | 0 | 0 | 1.4 | 607 | — |
| Granger graphique (Lasso) | classique | apprend le graphe | lasso | 50400 | 0 | 5.5 | 608 | — |
| HERALD @128 | proposition | apprend le graphe | forecast | 368660 | 30 | 1366.9 | 822 | 0.000 |
| HERALD @32 | proposition | apprend le graphe | forecast | 24596 | 30 | 348.3 | 686 | 0.734 |
| HERALD @64 | proposition | apprend le graphe | forecast | 94228 | 30 | 322.9 | 725 | 0.009 |
| NRI | inférence relationnelle | apprend le graphe | forecast + KL | 89228 | 30 | 325.8 | 700 | — |
| MTGNN | grafo-temporel | apprend le graphe | forecast | 90506 | 30 | 110.3 | 665 | — |
