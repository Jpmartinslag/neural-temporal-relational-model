# Nettoyage du dépôt — 2026-05-19

Objectif: remettre le dépôt HERALD dans un état lisible avant la prochaine batterie de tests, sans
supprimer les éléments nécessaires à la reproductibilité scientifique.

## Ce qui a été supprimé

Artefacts locaux recréables:

- `.venv/`
- `node_modules/`
- caches Python `__pycache__/`
- `logs/`, `hpc/logs/`, `test_dummy/`
- anciens dossiers `hpc_results/*smoke*`
- `old/`
- `reports/figures/`
- prédictions, `.npz`, stress-tests et exports intermédiaires déjà marqués comme régénérables dans
  `.gitignore` sous `data/processed/`, `data/interim/`, `reports/archive/` et `docs/archive/`

Raison: ces dossiers ne sont pas des sources du projet. Ils sont soit des environnements locaux, soit
des sorties générées, soit des archives historiques non suivies par Git.

La taille locale du dépôt est passée d'environ `37G` à environ `31G`. Le volume restant vient surtout
des données brutes (`data/raw`, environ `27G`) et des résultats HPC conservés pour audit
(`hpc_results`, environ `3.8G`).

## Ce qui a été déplacé

Les téléchargements bruts qui étaient à la racine ont été déplacés vers:

```text
data/raw/manual_downloads/20260519/
```

Contenu:

- exports Banque de France Webstat;
- séries ZIP téléchargées manuellement;
- PDF/XLS bruts récupérés pour exploration.

Ces fichiers restent disponibles localement mais ne polluent plus la racine du dépôt. `data/raw/` est
ignoré par Git sauf pour le fichier URSSAF trimestriel canonique.

Le rapport de recherche de données a été déplacé vers:

```text
reports/HERALD_DATA_RESEARCH_REPORT.md
```

## Ce qui a été conservé

Sources et documentation:

- `src/`
- `hpc/`
- `reports/`
- `metadata/`
- `docs/`
- `data/processed/` canoniques déjà suivis;
- `data/interim/atlas_iat/` et tables utiles déjà suivies.

Résultats HPC complets:

- conservés localement pour audit;
- ignorés par défaut quand ils correspondent aux racines `hpc_results/herald_regime_*`;
- à ne pas committer sauf extraction explicite de métriques légères ou rapport final.

## Règle à partir de maintenant

À versionner:

- code source;
- scripts HPC;
- rapports méthodologiques;
- dashboards finaux;
- métriques agrégées légères quand elles soutiennent une décision.

À ne pas versionner:

- environnements locaux;
- caches;
- logs;
- prédictions complètes par seed;
- `.npz`;
- téléchargements bruts;
- résultats HPC complets.

## Point d'attention

Les fichiers `src/modeles/train_herald_semi_v2.py`, `train_herald_v6.py`, `train_herald_v7.py`,
`src/modeles/herald_regime_modes.py` et `src/modeles/train_herald_regime_experiment.py` contiennent
encore des modifications de recherche actives liées aux phases de régime. Ils ne sont pas du bruit:
ils doivent être audités puis commités ou séparés avant la Phase 2K.
