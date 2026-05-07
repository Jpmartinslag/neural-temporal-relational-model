# Code source HERALD

Ce dossier contient le code du modèle, des baselines, des analyses et des dashboards.

## Organisation actuelle

```text
src/
├── modeles/        # entraînement HERALD, STGNN et baselines temporelles
├── analyse/        # analyses statistiques, sélection de gate, résumés
└── visualisation/  # génération des dashboards HTML
```

## Règle publique

Les scripts `train_herald_v3.py`, `train_herald_v6.py`, `train_herald_v7.py` et
`train_herald_semi_v2.py` sont des configurations de laboratoire. Ils ne doivent pas apparaître dans
la narration finale comme des modèles séparés.

Nom public:

- **HERALD principal**: configuration strict ex-ante / no-source-flags;
- **HERALD conservateur**: strict lag-only;
- **HERALD références internes**: local-only, dynamic graph, semi-supervised, graph-only;
- **Baselines**: Ridge AR, ARIMA, LSTM, DCRNN, Dynamic STGNN, Graph WaveNet.

## Prochaine étape de nettoyage

Créer ensuite un wrapper public:

```text
src/herald/
├── train.py
├── forecast.py
├── evaluate.py
└── configs/
```

Le wrapper appellera les scripts historiques sans les dupliquer.
