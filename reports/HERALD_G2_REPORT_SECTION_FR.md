# Résultats obtenus et analyse : Dynamique du graphe économique (G2)

## 1. Objectif scientifique
L'objectif de cette étape de recherche est de caractériser la dynamique temporelle du graphe économique territorial (couche L2) pour chaque pays et secteur. Cette analyse s'inscrit dans le développement d'outils descriptifs pour comprendre les associations économiques territoriales, sans formuler d'hypothèses causales ni viser l'amélioration des prévisions temporelles.

## 2. Construction du graphe économique dynamique
Le graphe L2 représente des associations statistiques de co-croissance territoriale par secteur. Il n'est pas un graphe causal, ni un graphe de causalité au sens de Granger, et ne repose pas sur un apprentissage de type GNN (Graph Neural Network). La construction du graphe s'appuie sur une corrélation de Pearson calculée sur des fenêtres temporelles glissantes. Une filtration par le critère top-k (avec k=5) est appliquée, ce qui a pour effet structurel de ne retenir que les corrélations positives les plus fortes entre les territoires.

## 3. Protocole temporel sans fuite
Pour éviter toute fuite d'information future (data leakage), l'analyse s'appuie sur un protocole d'évaluation glissant (rolling window) de cinq ans. La période désignée par « 2020 » dans nos résultats fait référence à une fenêtre glissante de cinq années qui se termine par l'année d'observation 2020, dont les données ne sont disponibles et utilisables qu'en 2021. Les métriques sont calculées sur un total de 321 observations annuelles réparties comme suit : 90 pour la France, 127 pour les Pays-Bas et 104 pour le Portugal.

## 4. Résultats agrégés pour la France, les Pays-Bas et le Portugal
Les résultats descriptifs agrégés mettent en évidence une variation modeste de la structure du graphe.
Les différences observées entre les périodes postérieures à 2020 et antérieures à 2020 (post-minus-pre) sont les suivantes :
- **France (FR) :** Évolution de la densité de +0.0006 et du poids moyen de −0.0047.
- **Pays-Bas (NL) :** Évolution de la densité de +0.0061. Pour le poids moyen, la moyenne des différences sectorielles est de +0.0064, tandis que la différence entre les moyennes globales des périodes est de +0.011.
- **Portugal (PT) :** Évolution de la densité de +0.0013 et du poids moyen de +0.0480.
Afin d'évaluer la dispersion de ces métriques, des intervalles de reéchantillonnage par paires ont été calculés. Il est important de préciser que ces intervalles ont une vocation purement descriptive et ne constituent en aucun cas des intervalles de confiance inférentiels, les paires de territoires n'étant pas statistiquement indépendantes.

## 5. Sensibilité à l’année 2020
Une analyse de sensibilité a été menée en incluant ou en excluant l'année d'observation 2020 des fenêtres de calcul. Seul le signal agrégé de la France s'est révélé robuste à cette sensibilité. Pour les Pays-Bas et le Portugal, les résultats agrégés sont sensibles à la présence de l'année 2020, ce qui empêche toute généralisation robuste du signal temporel au niveau inter-pays (réplication robuste inter-pays non supportée).

## 6. Stabilité des relations
L'analyse montre un renouvellement (turnover) moyen très élevé des arêtes du graphe d'une année sur l'autre : environ 79% pour la France (0.7903), 59% pour les Pays-Bas (0.5899) et 51% pour le Portugal (0.5070). Cette forte volatilité démontre que les relations individuelles entre deux territoires spécifiques ne sont pas stables dans le temps, même si la densité globale et la distribution des poids du graphe restent relativement cohérentes. De même, la détection de communautés stables (par exemple avec l'algorithme de Louvain) n'est pas supportée par ces données.

## 7. Limites méthodologiques
L'approche présente plusieurs limites structurelles :
- Les graphes captent une association statistique (co-mouvement) qui peut simplement refléter des tendances macroéconomiques partagées, sans lien direct ou causal entre les territoires.
- Le problème de l'unité spatiale modifiable (MAUP) s'applique, les territoires étant basés sur des découpages administratifs.
- Le petit nombre d'années disponibles par période réduit la portée de la comparaison temporelle.
- L'utilisation d'un correcteur basé sur le graphe (fixed-L2) n'apporte aucune amélioration prédictive des créations d'entreprises par rapport à un modèle autorégressif de référence (AR-Ridge).

## 8. Ce que les résultats permettent d’affirmer
- Sur le plan descriptif, les métriques calculées montrent que les distributions agrégées (densité et poids) du graphe L2 positif varient de manière modérée entre les différentes périodes analysées (avant, pendant et après la fenêtre 2020).
- Le signal temporel agrégé pour la France présente une robustesse face à l'inclusion ou l'exclusion de l'année 2020. Cette consistance de sa structure macroscopique globale découle de l'analyse par permutations avec l'année 2020 retenue (contrôle G-13), au-delà des résultats purement descriptifs (G-14).

## 9. Ce qu’ils ne permettent pas d’affirmer
- Ces résultats ne permettent pas d'affirmer que les relations individuelles d'arêtes entre les territoires sont stables, car leur volatilité est très élevée.
- Ils ne permettent pas d'affirmer que le graphe L2 améliore les capacités de prévision des créations d'entreprises.
- Ils n'autorisent pas l'identification de communautés territoriales robustes.
- Ils ne peuvent servir de support à une explication causale des chocs économiques tels que le COVID-19.

## 10. Transition vers la visualisation et la recommandation future
La prochaine étape du projet se concentre sur l'exploitation visuelle de ces associations statistiques territoriales. Un système de recommandation économique de territoires n'existe pas à l'heure actuelle, ni n'est directement dérivable en tant que solution prédictive. Néanmoins, la représentation visuelle interactive du graphe dynamique, intégrant un avertissement sur l'instabilité des arêtes individuelles, servira d'outil descriptif. Elle permettra de visualiser les évolutions de densité et de poids moyens, préparant ainsi le terrain pour la formulation future d'hypothèses de recommandations de politiques publiques basées sur le suivi des associations territoriales sectorielles.
