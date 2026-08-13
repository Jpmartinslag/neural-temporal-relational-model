# Légendes prêtes à coller

Une légende par figure, rédigée pour être copiée telle quelle dans le rapport ou sous une
diapositive. Chaque légende dit ce que la figure montre, sur quoi elle repose, et — quand la
distinction compte — ce qu'elle ne dit pas.

Les catégories sont celles de l'archive : **REAL_FRANCE** (observé sur données publiées),
**EXPLORATORY** (construit par cette étude à partir de données observées),
**SYNTHETIC_KNOWN_TRUTH** (monde artificiel dont la vérité est connue), **FUTURE_WORK**
(proposition, non implémentée).

---

## Données et géographie françaises

**F01 — Les 280 zones d'emploi.** *(REAL_FRANCE)*
> Les 280 zones d'emploi de France métropolitaine (découpage ZE2020) qui constituent la
> population de l'étude. Une zone d'emploi est l'aire à l'intérieur de laquelle la plupart des
> actifs résident et travaillent. La Corse et les départements d'outre-mer sont exclus de ce
> tour. *Source : Insee, géographie ZE2020.*

**F02 — Le réseau de navettes domicile-travail.** *(REAL_FRANCE)*
> Les trois destinations de navettes les plus fortes de chaque zone, soit 840 arêtes tracées
> sur les flux inter-zones observés en 2012 ; l'épaisseur suit le nombre de navetteurs. Ce
> graphe est utilisé comme **prior de candidature** : il propose quelles paires un modèle a le
> droit d'examiner. Il n'est jamais une étiquette, aucune méthode n'est notée contre lui et
> aucune perte ne le contient. *Source : Insee, mobilités professionnelles.*

**F03 — Similarité économique construite.** *(EXPLORATORY)*
> Support candidat obtenu en corrélant les croissances annuelles standardisées des effectifs
> salariés privés entre 1999 et 2019, puis en retenant les cinq voisins les plus proches de
> chaque zone. Le panneau de gauche montre un échantillon aléatoire déclaré de 180 paires sur
> 1 400, les paires distantes tracées plus épais ; celui de droite montre, à densité complète,
> toutes les paires partant d'une seule région. **Cette similarité est construite, pas
> découverte** : aucun modèle ne l'a apprise et aucune de ces arêtes ne porte de sens
> économique établi. *Source : Urssaf, effectifs salariés privés.*

**F04 — Complémentarité économique construite.** *(EXPLORATORY)*
> Même définition que F03, mais avec les cinq corrélations les plus **négatives** par zone.
> Une trajectoire de forme opposée n'est pas une complémentarité économique : c'est une
> hypothèse candidate, à tester, et non un résultat. *Source : Urssaf.*

**F05 — Quatre supports candidats côte à côte.** *(REAL_FRANCE / EXPLORATORY)*
> Navettes observées, similarité construite, complémentarité construite, et leur union. Chaque
> panneau montre un échantillon aléatoire déclaré de 200 paires, tiré avec une graine fixe,
> pour que la densité tracée soit comparable entre panneaux ; les effectifs réels figurent
> dans les titres. Les familles se recouvrent peu — 54 paires communes entre navettes et
> similarité sur 1 400 — ce qui est précisément la raison d'être d'un support multirelationnel.

**F06 — Cinq signaux, trois zones représentatives.** *(REAL_FRANCE)*
> Effectifs salariés privés, masse salariale, établissements employeurs, taux de chômage
> localisé et créations d'établissements, pour les zones situées aux déciles 10, 50 et 90 de
> taille. Les fenêtres temporelles diffèrent d'une source à l'autre : c'est la disponibilité
> réelle des publications et non un choix de cadrage. Une cellule non publiée reste absente.
> *Sources : Urssaf, Insee, Sirene/SIDE.*

**F07 — La représentation temporelle causale d'une zone.** *(REAL_FRANCE, dérivé)*
> Les neuf dérivations qui composent la représentation d'une trajectoire — niveau, croissance,
> accélération, tendance, momentum, volatilité, composante nationale, croissance relative et
> les quatre indicatrices de régime — sur une zone médiane. Chaque colonne n'utilise que des
> données disponibles à la date de décision. La fenêtre est réduite à cinq ans pour la
> lisibilité ; le modèle en utilise douze pour la tendance et huit pour le momentum et la
> volatilité. *Source : Urssaf, effectifs salariés privés.*

---

## Le monde synthétique

**S01 — Territoires, volumes et signaux publiés.** *(SYNTHETIC_KNOWN_TRUTH)*
> Quatre-vingts territoires artificiels avec des volumes réalistes, dont vingt à faible
> information, et deux de leurs cinq signaux. Les marginales, autocorrélations, dispersions,
> masques de publication, retards de diffusion et ruptures sont calibrés sur le panel français
> — mais ce n'est pas la France, et un résultat obtenu ici contraint ce qu'on peut affirmer
> sans jamais décrire l'économie française.

**S02 — Le graphe vrai.** *(SYNTHETIC_KNOWN_TRUTH)*
> Cent vingt arêtes réparties en trois familles : navettes, similarité économique et
> complémentarité conditionnée au régime. **Quatre-vingts d'entre elles relient des zones sans
> aucune navette entre elles**, ce qui est exactement ce que les étapes précédentes ne
> pouvaient pas tester. Ce graphe n'atteint jamais le modèle : ni comme entrée, ni comme
> étiquette, ni dans une fonction de perte. Il n'existe qu'à l'intérieur de l'évaluateur.

**S03 — Le support candidat et son plafond.** *(SYNTHETIC_KNOWN_TRUTH)*
> À gauche, le support des navettes. À droite, les arêtes vraies qu'il contient (en noir) et
> celles qu'il ne peut pas contenir (en rouge). Un modèle restreint aux navettes ne peut pas
> retrouver les arêtes rouges, quelle que soit sa qualité — c'est pourquoi HERALD 96 compare
> quatre supports, dont « toutes les paires », qui les contient toutes.

**S04 — Les scores appris ne séparent rien.** *(SYNTHETIC_KNOWN_TRUTH, mesuré)*
> Contribution moyenne que le bras attribue aux paires qui sont de vraies arêtes, contre
> toutes les autres, par famille et par intensité. Un classificateur utile donnerait des
> barres colorées nettement plus hautes que les grises. Elles sont au même niveau, et à
> l'intensité nominale les vraies arêtes reçoivent une contribution très légèrement **plus
> faible**. *Union typée, médiane sur cinq graines finales.*

**S05 — Scénario sans mécanisme.** *(SYNTHETIC_KNOWN_TRUTH)*
> Les arêtes existent et rien n'y circule. C'est le contrôle : une méthode qui trouve une
> structure ici a reproduit quelque chose qu'on lui a donné, et non découvert une relation.

**S06 — Scénario avec mécanisme.** *(SYNTHETIC_KNOWN_TRUTH)*
> La même géographie, la même graine, les mêmes paires tirées depuis le même flux aléatoire.
> Les deux mondes ne diffèrent que par le fait que quelque chose voyage, ou non, le long des
> arêtes. C'est cet appariement qui rend le scénario nul interprétable.

**S07 — La même relation, du silence au double du nominal.** *(SYNTHETIC_KNOWN_TRUTH)*
> Une seule quantité varie entre ces quatre mondes : `relational_scale`. Territoires, graphe,
> états latents, bruit et masques sont identiques **cellule par cellule** — l'appariement a dû
> être réparé avant que l'échelle ne veuille dire quelque chose, parce que
> l'échantillonnage par rejet de la loi de Poisson consomme un nombre variable de tirages et
> désynchronisait tout ce qui suivait. Le rayon est à échelle commune : la composante
> relationnelle reçue double exactement à chaque palier.

**S08/S09 — L'oracle répond à l'intensité ; les modèles n'y répondent pas.**
*(SYNTHETIC_KNOWN_TRUTH, mesuré)*
> **La figure centrale de l'étude.** À gauche, un estimateur qui connaît le mécanisme : il vaut
> exactement zéro sans mécanisme et croît de façon monotone avec lui, dans tous les scénarios
> et toutes les graines. À droite, les modèles réels : leur gain ne suit pas l'intensité, il
> change de signe, et il est aussi grand dans le monde construit **sans aucune relation**. Un
> gain qui ne répond pas à l'intensité du mécanisme n'est pas un gain relationnel. Les deux
> protocoles sont tracés ensemble parce qu'ils partagent la question, et non parce que leurs
> niveaux se comparent : les cibles diffèrent.

**S10 — Graphe vrai contre graphe appris.** *(SYNTHETIC_KNOWN_TRUTH, schéma quantitatif)*
> Le monde compte 120 arêtes vraies, dont 70 tombent dans l'union typée. Le bras dispose d'un
> budget égal à ce nombre : il désigne ses 70 meilleures paires, et **une seule** d'entre elles
> est vraie. Les scores par arête ne sont pas conservés dans les artefacts, donc l'arête
> surlignée à droite est tirée au hasard parmi les arêtes vraies : c'est le **nombre** qui est
> mesuré, pas la position.

**S11 — AUPRC contre prévalence.** *(SYNTHETIC_KNOWN_TRUTH, mesuré)*
> La prévalence est la part d'arêtes vraies dans le support, c'est-à-dire le score qu'obtient
> déjà un classement aléatoire. Aucune barre ne s'en écarte. Le support « similarité seule »
> dépasse sa prévalence d'environ un quart, mais il le fait **autant dans le scénario sans
> mécanisme** : c'est une propriété du support, pas une récupération.

**S12 — Prévoir et retrouver sont deux questions.** *(SYNTHETIC_KNOWN_TRUTH, mesuré)*
> Gain sur le résidu en abscisse, écart à la prévalence en ordonnée, un point par support.
> Aucun n'atteint le quadrant supérieur droit. La valeur de l'oracle indiquée à côté de chaque
> point est ce qu'il restait à gagner : environ un dixième du résidu.

---

## Architecture

**A01 — Le flux global du projet.** *(diagramme)*
> Des données publiées jusqu'à un éventuel appui territorial. La validation synthétique n'est
> pas une étape qui suit les modèles : c'est ce qui **autorise** l'étape suivante. L'analyse
> française n'est ouverte qu'aux résultats que le monde à vérité connue a soutenus, et la
> dernière case est grise parce que rien à cette étape ne l'a atteinte.

**A02 — L'architecture actuelle.** *(diagramme, implémenté et exécuté)*
> Le baseline temporel local est **gelé** pendant l'entraînement relationnel — un checksum
> identique avant et après le vérifie dans les 120 tâches — et le bras relationnel ne peut
> expliquer que le résidu. Il n'a ni chemin local, ni boucle sur soi, ni paramètre par paire.
> Les poids de navettes et de similarité **proposent** des candidats mais n'entrent jamais
> comme valeur dans le scorer. L'évaluation prédictive et l'évaluation relationnelle sont
> séparées, parce qu'une méthode peut prévoir mieux sans rien retrouver.

**A03 — PROPOSED FUTURE ARCHITECTURE — NOT IMPLEMENTED.** *(FUTURE_WORK)*
> Proposition d'évolution : encodeurs temporels par signal, modules par type de relation,
> fusion multirelationnelle par attention, graphe dynamique. **Aucun résultat de ce schéma
> n'existe.** Rien ici n'a été entraîné, mesuré ni validé. Cette figure ne doit jamais être
> présentée à côté d'un tableau de résultats sans sa bannière.

---

## Résultats

**R01 — La représentation temporelle contre le meilleur signal isolé.**
*(SYNTHETIC_KNOWN_TRUTH — HERALD 94)*
> Un modèle linéaire régularisé sur les 120 colonnes temporelles retire entre 11 % et 24 % de
> l'erreur quadratique hors échantillon par rapport à la meilleure colonne unique, dans les six
> scénarios. Le gain est **aussi grand dans le scénario sans mécanisme relationnel** : c'est une
> propriété de la façon de décrire une trajectoire, et cela ne dit rien des voisines d'une zone.

**R02 — Aucune méthode ne bat la persistance.** *(SYNTHETIC_KNOWN_TRUTH — HERALD 93)*
> Le meilleur résultat, +0,0001, est la persistance à quatre décimales. C'est une propriété de
> la **cible** — l'autocorrélation vit dans le niveau, et la différencier laisse peu à prévoir —
> et elle s'applique identiquement aux six méthodes.

**R03 — AUPRC contre prévalence, dans deux protocoles distincts.**
*(SYNTHETIC_KNOWN_TRUTH — HERALD 93 et 96)*
> Les deux panneaux ont des ordonnées et des prévalences différentes et **ne se comparent
> pas** : à gauche la vérité est tirée à l'intérieur du support et 0,70 des candidats sont
> vrais ; à droite deux tiers des arêtes vraies sont hors navettes et la prévalence tombe entre
> 0,011 et 0,061. Ce qui se compare est la distance de chaque barre à sa **propre** prévalence,
> et cette distance est nulle des deux côtés.

**R04 — Diagnostic d'échelle.** *(SYNTHETIC_KNOWN_TRUTH — HERALD 95)*
> « La relation est-elle trop petite pour être vue, ou le modèle est-il incapable de la
> retrouver ? » Réponse : le modèle. Le mécanisme est visible dans les données publiées
> (panneau 1), il est exploitable par un estimateur qui le connaît (panneau 2), et le scorer
> d'arêtes n'y répond pas du tout (panneau 3) — multiplier le mécanisme par quatre déplace le
> graphe appris d'environ 1e−8. La qualification qui compte : le plafond lui-même vaut environ
> 2 % de l'erreur quadratique sur cette cible.

**R05 — Coût, paramètres et performance.** *(SYNTHETIC_KNOWN_TRUTH — HERALD 93)*
> Le résultat de frugalité, et il n'est **pas** favorable à la proposition : le Granger
> graphique par Lasso coûte 5,5 s et 50 400 paramètres, prévoit aussi bien que le meilleur bras
> neuronal, et son contrôle nul est propre. HERALD @128 coûte 1 367 s et 368 660 paramètres
> pour la même récupération, c'est-à-dire aucune.

**R06 — L'évolution scientifique du projet.** *(trajectoire)*
> Chaque étape a été ouverte par ce que la précédente n'avait **pas** montré. La question s'est
> déplacée trois fois : « le modèle récupère-t-il ? » → « y a-t-il quelque chose à
> récupérer ? » → « où est le goulot ? ». Aucune de ces réponses n'a exigé de déplacer un seuil
> après avoir vu un résultat.
