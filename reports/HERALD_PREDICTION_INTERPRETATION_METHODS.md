# HERALD — méthodes d'interprétation des prédictions

Date: 2026-05-07

Ce document propose comment transformer les sorties HERALD en informations économiques lisibles dans
un dashboard, un article ou une future application.

## 1. Indicateurs territoriaux dérivés

| Indicateur | Définition | Interprétation |
|---|---|---|
| Dynamisme prévu | prévision HERALD normalisée par la taille historique de la zone | niveau d'activité attendu |
| Accélération | prévision future moins dernière observation, rapportée à la dernière observation | territoire qui chauffe |
| Ralentissement | baisse prévue persistante sur 2026/2027 | territoire en refroidissement |
| Surprise HERALD | HERALD moins Ridge AR | signal non linéaire/spatial détecté par HERALD |
| Incertitude | dispersion entre seeds | robustesse locale de la prévision |
| Risque d'erreur | erreur historique récente + incertitude seed | prudence d'interprétation |
| Spécialisation A10 | secteurs où la zone est prévue en croissance | lecture métier/sectorielle |
| Sensibilité réseau | zones dont la prévision dépend davantage du graphe | dépendance aux connexions territoriales |

## 2. Classes économiques simples pour carte

Pour un utilisateur non technique, utiliser des classes:

- **Chaud**: forte croissance prévue et faible incertitude.
- **En accélération**: croissance prévue supérieure à la tendance locale.
- **Stable**: variation faible, incertitude faible.
- **À surveiller**: croissance positive mais incertitude forte.
- **En ralentissement**: baisse prévue ou sous-performance face à la tendance.
- **Froid**: baisse prévue et faible dynamisme structurel.

Ces classes doivent être calculées par quantiles nationaux et affichées avec explication en français.

## 3. Utilisation du graphe

Le graphe ne doit pas être présenté comme causal. Il doit être présenté comme une structure
d'association territoriale apprise.

Usages défendables:

- identifier les connexions économiques stables;
- détecter les connexions nouvelles après choc;
- comparer mobilité vs géographie;
- repérer les zones centrales dans le réseau économique;
- trouver des groupes de zones qui évoluent ensemble.

Usages à éviter:

- dire qu'une zone cause la croissance d'une autre;
- utiliser une connexion unique comme preuve politique;
- tirer une conclusion sans vérifier les données de mobilité, distance et secteurs.

## 4. Annexes utiles au graphe

Les annexes doivent enrichir l'interprétation, pas être ajoutées au modèle sans test.

| Annexe | Ce qu'elle peut révéler |
|---|---|
| Mobilité domicile-travail | flux fonctionnels entre bassins d'emploi |
| Temps de trajet / rail | accessibilité économique réelle |
| A10/A17 sectoriel | chaînes sectorielles et spécialisation |
| URSSAF emploi/salaire | tension et masse économique locale |
| SITADEL construction | signal avancé immobilier/activité |
| Population active | base de main-d'oeuvre |
| FILOSOFI revenus | pouvoir d'achat local |
| BPE équipements | attractivité et services |
| QPV/ZRR/ZAN | contexte de politique publique |

## 5. Dashboard recommandé

Le dashboard doit permettre trois lectures:

1. **Validation**: le modèle est-il fiable par rapport aux baselines?
2. **Carte économique**: où la France accélère ou ralentit?
3. **Réseau territorial**: quelles zones semblent connectées économiquement?

Ordre conseillé:

1. résumé exécutif;
2. comparaison modèles;
3. audit anti-fuite et calendrier;
4. carte principale unique avec filtres;
5. secteurs A10;
6. graphe territorial;
7. forecast 2026/2027;
8. annexes exploratoires.

## 6. Phrase utilisable dans l'article

> HERALD transforme une prévision de créations d'établissements en diagnostic territorial: il identifie
> les zones en accélération, en ralentissement ou en incertitude, tout en révélant les associations
> économiques apprises entre territoires à partir de la mobilité, de la géographie et des trajectoires
> historiques.

