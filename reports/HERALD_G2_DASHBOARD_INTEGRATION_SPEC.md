# Spécification d'intégration au Dashboard (G2 Dynamics)

## Objectif
Ce document définit les spécifications pour l'intégration future des résultats du graphe dynamique (G2) au tableau de bord visuel existant (`reports/dashboards/herald_france_final_dashboard.html`), sans en modifier le code à ce stade.

## Composants à intégrer

### 1. Sélecteurs globaux
- **Sélecteur de pays :** Permettre le choix entre la France (FR), les Pays-Bas (NL) et le Portugal (PT). Lors de la sélection de NL ou PT, un avertissement explicite de "sensibilité COVID" (COVID_SENSITIVE) doit apparaître.
- **Sélecteur de secteur :** Liste déroulante des secteurs analysés (ex: BE, FZ, GI, etc.).
- **Sélecteur d'année :** Curseur temporel (slider) pour choisir l'année d'évaluation. Il doit être clairement indiqué qu'une année "T" représente une fenêtre glissante de 5 ans se terminant en "T-1".

### 2. Éléments visuels principaux
- **Carte territoriale :** Carte géographique interactive (basée sur les zones d'emploi ou NUTS3/COROP) colorée selon le volume observé de créations d'entreprises ou un autre indicateur de base.
- **Relations territoriales (Année sélectionnée) :** Superposition des arêtes du graphe L2 (top-k) sur la carte pour l'année sélectionnée, illustrant les paires de territoires ayant les co-croissances statistiques les plus fortes.
- **Séries temporelles au clic :** Un clic sur une région spécifique doit ouvrir un panneau latéral affichant l'historique des créations d'entreprises pour cette région dans le secteur sélectionné.

### 3. Panneau des métriques agrégées (G2)
- **Densité et poids moyen :** Affichage numérique et graphique (ligne de tendance) de la densité globale et du poids moyen des arêtes pour le secteur sélectionné au fil du temps.
- **Turnover annuel :** Jauge ou indicateur chiffré illustrant le taux de renouvellement des arêtes par rapport à l'année précédente (ex: ~79% pour FR).
- **Comparaison de périodes :** Un tableau ou diagramme à barres comparant la densité et le poids moyen entre trois périodes :
  - **Pré-2020 :** Fenêtres glissantes se terminant avant 2020.
  - **Fenêtre se terminant en 2020 :** Les données évaluées en 2021.
  - **Post-2020 :** Fenêtres glissantes se terminant après 2020.

### 4. Avertissements et distinctions visuelles (Garde-fous scientifiques)
- **Avertissement d'instabilité des arêtes :** Une bannière persistante doit indiquer : *"Attention : Les relations individuelles affichées entre territoires sont très volatiles (turnover élevé) et ne constituent pas des liens stables ou causaux."*
- **Distinction visuelle des données :**
  - *Données observées :* Couleurs unies (par exemple pour la carte territoriale).
  - *Relations statistiques (Graphe L2) :* Lignes en pointillés ou avec transparence, soulignant leur nature d'association statistique.
  - *Prévisions :* Si affichées à l'avenir, elles devront utiliser des hachures ou des couleurs distinctes avec des intervalles affichés visuellement de manière différente des données historiques.

### 5. Évolutions futures envisagées
- **Relations secteur-territoire :** L'architecture visuelle devra prévoir un espace (ex: diagramme de Sankey ou matrice adjacente) pour visualiser plus tard les relations croisées entre un secteur spécifique et un profil territorial.
