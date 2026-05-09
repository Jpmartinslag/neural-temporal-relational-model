var e=e=>{switch(e){case`index`:return`---
title: "HERALD France - vue generale"
---
graph TB
  France@{ shape: rectangle, label: "HERALD France" }
`;case`view_14htaoj`:return`---
title: "HERALD vs Ridge AR - comparaison globale"
---
graph TB
  subgraph France["\`HERALD France\`"]
    France.Data@{ shape: rectangle, label: "Donnees observees" }
    France.Priors@{ shape: rectangle, label: "Priors territoriaux" }
    France.Ridge@{ shape: rectangle, label: "Ridge AR" }
    France.Herald@{ shape: rectangle, label: "HERALD" }
    France.Intelligence@{ shape: rectangle, label: "HERALD Intelligence v0" }
    France.Dashboard@{ shape: rectangle, label: "Dashboard HERALD France" }
  end
  France.Data -. "\`[...]\`" .-> France.Ridge
  France.Data -. "\`garantit train passe seulement\`" .-> France.Herald
  France.Ridge -. "\`composante mathematique\`" .-> France.Herald
  France.Ridge -.-> France.Dashboard
  France.Herald -. "\`reutilise la base Ridge\`" .-> France.Ridge
  France.Herald -.-> France.Intelligence
  France.Herald -.-> France.Dashboard
  France.Priors -.-> France.Herald
  France.Intelligence -.-> France.Dashboard
`;case`view_1yuis9v`:return`---
title: "Ridge AR - baseline lineaire"
---
graph TB
  FranceData@{ shape: rectangle, label: "Donnees observees" }
  FranceHerald@{ shape: rectangle, label: "HERALD" }
  subgraph FranceRidge["\`Ridge AR\`"]
    FranceRidge.Features@{ shape: rectangle, label: "Features locales" }
    FranceRidge.Preprocessing@{ shape: rectangle, label: "Imputation + standardisation" }
    FranceRidge.Linear@{ shape: rectangle, label: "Regression Ridge(alpha=1)" }
    FranceRidge.RidgePred@{ shape: rectangle, label: "Prediction Ridge" }
  end
  FranceDashboard@{ shape: rectangle, label: "Dashboard HERALD France" }
  FranceData -. "\`fournit l historique local\`" .-> FranceRidge.Features
  FranceHerald -. "\`reutilise la base Ridge\`" .-> FranceRidge.Linear
  FranceRidge.Features -.-> FranceRidge.Preprocessing
  FranceRidge.Preprocessing -.-> FranceRidge.Linear
  FranceRidge.Linear -.-> FranceRidge.RidgePred
  FranceRidge.RidgePred -. "\`composante mathematique\`" .-> FranceHerald
  FranceRidge.RidgePred -.-> FranceDashboard
`;case`view_1mz8h1l`:return`---
title: "HERALD - architecture interne"
---
graph TB
  FranceData@{ shape: rectangle, label: "Donnees observees" }
  FranceRidge@{ shape: rectangle, label: "Ridge AR" }
  FrancePriors@{ shape: rectangle, label: "Priors territoriaux" }
  subgraph FranceHerald["\`HERALD\`"]
    FranceHerald.Sequences@{ shape: rectangle, label: "Sequences forecast-safe" }
    FranceHerald.Local@{ shape: rectangle, label: "Encodeur local" }
    FranceHerald.DynamicGraph@{ shape: rectangle, label: "Graphe dynamique" }
    FranceHerald.GraphMessages@{ shape: rectangle, label: "Messages territoriaux" }
    FranceHerald.Internals@{ shape: rectangle, label: "Internals graphe" }
    FranceHerald.Mix@{ shape: rectangle, label: "Gate / Alpha" }
    FranceHerald.Residual@{ shape: rectangle, label: "Tete residuelle" }
    FranceHerald.Sector@{ shape: rectangle, label: "Tete A10" }
    FranceHerald.HeraldPred@{ shape: rectangle, label: "Prediction HERALD" }
    FranceHerald.SectorPred@{ shape: rectangle, label: "Predictions A10" }
  end
  FranceIntelligence@{ shape: rectangle, label: "HERALD Intelligence v0" }
  FranceDashboard@{ shape: rectangle, label: "Dashboard HERALD France" }
  FranceData -. "\`garantit train passe seulement\`" .-> FranceHerald.Sequences
  FranceRidge -. "\`composante mathematique\`" .-> FranceHerald.HeraldPred
  FrancePriors -.-> FranceHerald.DynamicGraph
  FranceHerald.Sequences -.-> FranceHerald.Local
  FranceHerald.Local -.-> FranceHerald.DynamicGraph
  FranceHerald.Local -.-> FranceHerald.Mix
  FranceHerald.DynamicGraph -.-> FranceHerald.GraphMessages
  FranceHerald.DynamicGraph -.-> FranceHerald.Internals
  FranceHerald.GraphMessages -.-> FranceHerald.Mix
  FranceHerald.Mix -.-> FranceHerald.Residual
  FranceHerald.Mix -.-> FranceHerald.Sector
  FranceHerald.Residual -. "\`Ridge + residual * zone_std\`" .-> FranceHerald.HeraldPred
  FranceHerald.Sector -.-> FranceHerald.SectorPred
  FranceHerald.Sequences -. "\`reutilise la base Ridge\`" .-> FranceRidge
  FranceHerald.Internals -.-> FranceIntelligence
  FranceHerald.HeraldPred -.-> FranceIntelligence
  FranceHerald.HeraldPred -.-> FranceDashboard
  FranceHerald.SectorPred -.-> FranceIntelligence
  FranceHerald.SectorPred -.-> FranceDashboard
`;case`view_1py4btl`:return`---
title: "Graphe dynamique HERALD"
---
graph TB
  FrancePriors@{ shape: rectangle, label: "Priors territoriaux" }
  FranceHeraldLocal@{ shape: rectangle, label: "Encodeur local" }
  FranceHeraldDynamicGraph@{ shape: rectangle, label: "Graphe dynamique" }
  FranceHeraldGraphMessages@{ shape: rectangle, label: "Messages territoriaux" }
  FranceHeraldInternals@{ shape: rectangle, label: "Internals graphe" }
  FrancePriors -.-> FranceHeraldDynamicGraph
  FranceHeraldLocal -.-> FranceHeraldDynamicGraph
  FranceHeraldDynamicGraph -.-> FranceHeraldGraphMessages
  FranceHeraldDynamicGraph -.-> FranceHeraldInternals
`;case`view_1dglhfw`:return`---
title: "HERALD Intelligence v0"
---
graph TB
  FranceHerald@{ shape: rectangle, label: "HERALD" }
  subgraph FranceIntelligence["\`HERALD Intelligence v0\`"]
    FranceIntelligence.Scores@{ shape: rectangle, label: "Scores opportunite/risque" }
    FranceIntelligence.Maps@{ shape: rectangle, label: "Cartes interpretatives" }
    FranceIntelligence.Alerts@{ shape: rectangle, label: "Alertes territoriales" }
  end
  FranceDashboard@{ shape: rectangle, label: "Dashboard HERALD France" }
  FranceHerald -.-> FranceIntelligence.Scores
  FranceHerald -.-> FranceIntelligence.Maps
  FranceIntelligence.Scores -.-> FranceIntelligence.Alerts
  FranceIntelligence.Maps -.-> FranceDashboard
`;default:throw Error(`Unknown viewId: `+e)}};export{e as mmdSource};