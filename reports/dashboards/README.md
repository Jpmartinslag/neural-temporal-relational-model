# Dashboards HERALD

Ce dossier contient les dashboards HTML offline présentables.

## Dashboard principal

```text
herald_france_dashboard_offline.html
```

Statut:

- base stable issue du dashboard Semi V2 strict ex-ante;
- fonctionne sans connexion internet;
- doit devenir la base du dashboard final HERALD-France;
- ne doit pas être remplacé par un dashboard expérimental non validé.

## Règle

Le dashboard final doit lire des fichiers légers dans `reports/metrics/`, pas directement les milliers
de fichiers par seed dans `hpc_results/`.

