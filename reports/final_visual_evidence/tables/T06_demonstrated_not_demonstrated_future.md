# T06 — Demonstrated, not demonstrated, future work

'DÉMONTRÉ' and 'RÉFUTÉ' are claims about synthetic worlds whose truth is known. None of them is a claim about the French economy. 'NON DÉMONTRÉ' means the experiment was run and did not support the claim; it does not mean the claim is false.

| affirmation | statut | catégorie | sur quoi le statut repose | source |
|---|---|---|---|---|
| La représentation temporelle causale réduit l'erreur | DÉMONTRÉ | SYNTHETIC_KNOWN_TRUTH | gain médian de 0.106 à 0.245 de l'erreur quadratique hors échantillon contre le meilleur signal isolé, dans les six scénarios | HERALD 94 §3.1 |
| Les six composites déclarés ajoutent de l'information | RÉFUTÉ | SYNTHETIC_KNOWN_TRUTH | l'effet médian est négatif dans les six scénarios (−0,003 à −0,008) | HERALD 94 §3.2 |
| Le gain non linéaire du réseau est relationnel | RÉFUTÉ | SYNTHETIC_KNOWN_TRUTH | le gain est aussi grand dans le scénario sans mécanisme et survit à la destruction de sa propre interaction | HERALD 94 §3.3–3.4, HERALD 95 §4 |
| Le mécanisme relationnel est observable dans les données publiées | DÉMONTRÉ | SYNTHETIC_KNOWN_TRUTH | l'oracle vaut exactement 0 sans mécanisme et croît de façon monotone ; +0.0194 de l'erreur à l'échelle nominale sur la croissance brute, +0.1006 du résidu après un baseline local gelé | HERALD 95 §4, HERALD 96 §2 |
| Un modèle récupère les arêtes vraies au-dessus du hasard | NON DÉMONTRÉ | SYNTHETIC_KNOWN_TRUTH | aucune des six méthodes de HERALD 93, ni le bras Neural Granger de HERALD 96, dans aucun des quatre supports ni aucune des trois intensités | HERALD 93 §7, HERALD 96 §3 |
| Le goulot est la génération de candidats | RÉFUTÉ | SYNTHETIC_KNOWN_TRUTH | le support « toutes les paires » contient toutes les arêtes vraies et ne récupère rien ; le goulot est l'identification | HERALD 96 §6 |
| Une méthode bat la persistance en prévision | NON DÉMONTRÉ | SYNTHETIC_KNOWN_TRUTH | le meilleur skill est +0,0001 (Granger), c'est-à-dire la persistance à quatre décimales ; la croissance logarithmique à l'horizon 1 est proche du bruit de mesure | HERALD 93 §6 |
| Les arêtes apprises décrivent des relations économiques françaises | NON AUTORISÉ | EXPLORATORY | aucune arête apprise n'est appliquée, visualisée ou interprétée pour la France ; décision CASE_C_DO_NOT_APPLY_RELATIONS | HERALD 93 §9, HERALD 96 §7 |
| La fusion multirelationnelle par attention améliore l'identification | TRAVAIL FUTUR | FUTURE_WORK | ni implémentée ni validée à cette étape ; aucune donnée ne la soutient ni ne la réfute | HERALD 97 |
| Un objectif d'entraînement qui note les arêtes plutôt que de seulement prévoir | TRAVAIL FUTUR | FUTURE_WORK | proposé par HERALD 96 §8 comme la cible directe du goulot identifié | HERALD 96 §8 |
