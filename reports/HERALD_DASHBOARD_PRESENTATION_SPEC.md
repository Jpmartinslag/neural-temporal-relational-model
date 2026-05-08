# HERALD France — specification du dashboard de presentation

Date: 2026-05-07

## Objectif

Le dashboard public doit presenter **HERALD** comme un modele unique. Les anciennes
variantes de laboratoire ne doivent pas apparaitre comme des modeles concurrents.
Elles deviennent des controles methodologiques internes:

- HERALD: modele principal.
- HERALD sans graphe: controle local.
- HERALD sans semi-supervision: controle d'apprentissage.
- HERALD panel conservateur: controle anti-fuite.
- Ridge AR, ARIMA, LSTM, DCRNN, STGNN: modeles externes de comparaison.

## Ordre de lecture

1. Resultat executif: WMAPE 2025, gain vs Ridge, nombre de seeds, verdict anti-fuite.
2. Comparaison modele principal vs baselines externes.
3. Tests methodologiques HERALD, sans vocabulaire de version.
4. Reel vs predit, France entiere et zones.
5. Secteurs A10: toujours montrer le reel a cote du predit.
6. Carte unique de France avec controles annee/metrique.
7. Graphe territorial appris: top connexions, lecture interpretative non causale.
8. Audit anti-fuite et calendrier de disponibilite.
9. Forecast 2026/2027, separe des backtests observes.

## Regles visuelles

- Ne pas multiplier les cartes: une carte principale avec selecteurs.
- Les modes par defaut de la carte sont seulement: reel, predit, erreur absolue,
  erreur relative.
- Croissance, acceleration, incertitude et densite du graphe sont des modes
  avances avec definition visible.
- Ne jamais montrer seulement une erreur relative sans volume reel associe.
- Couleur HERALD: orange.
- Couleur reel: gris clair/neutre.
- Couleurs baselines: vert/violet/rose selon modele.
- Erreur: echelle sequentielle lisible.
- Difference entre modeles: echelle divergente, vert = HERALD meilleur, rouge = HERALD pire.

## Texte

Toutes les interpretations visibles doivent etre en francais. Le dashboard doit etre
comprehensible pour un professeur ou un decideur public sans connaitre l'historique
V3/V6/V7/Semi.

## Donnees a integrer

- Backtests observes et strict ex-ante.
- Predictions territoriales et sectorielles A10.
- Graphe dynamique appris.
- Audit target-shuffle.
- Calendrier de disponibilite.
- Forecast 2026/2027 avec avertissement: prediction prospective conditionnelle aux
  donnees disponibles au 2026-05-07.

## Exigences methodologiques minimales

- Chaque mode de carte doit avoir formule, unite, fenetre temporelle et
  denominateur.
- Toute comparaison en volume doit utiliser un CSV de prediction reel; ne jamais
  reconstruire un volume de baseline a partir d'un WMAPE.
- Le graphe appris doit montrer stabilite entre seeds et ablation avec/sans
  graphe avant tout claim predictif.
- Une arete du graphe doit etre expliquee comme signal predictif, avec mobilite,
  distance, poids appris, stabilite et statut critique. Ne jamais formuler une
  causalite.
- Les secteurs A10 doivent afficher volume reel, volume predit, WMAPE, erreur
  absolue, variance entre seeds et support statistique.
- Le forecast 2026/2027 doit afficher un bandeau permanent: "prevision
  prospective — non encore observee", sans WMAPE.

## Formulations a eviter

- "V3", "V6", "V7", "Semi V2" dans l'interface publique.
- "zero leak".
- "forecast ex-ante 2026-01-01" pour les sorties 2026/2027 actuelles.
- "le graphe cause la croissance economique".

## Formulation recommandee

> HERALD predit les creations d'etablissements par zone d'emploi, compare ses
> predictions aux observations reelles et expose les signaux territoriaux appris
> sous forme de carte, secteurs A10 et graphe dynamique. Les controles strict
> ex-ante et target-shuffle ne detectent pas de fuite directe du target; le risque
> restant concerne le calendrier reel de publication des sources.
