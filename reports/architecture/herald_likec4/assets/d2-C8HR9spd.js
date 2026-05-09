var e=e=>{switch(e){case`index`:return`direction: down

France: {
  label: "HERALD France"
}
`;case`view_14htaoj`:return`direction: down

France: {
  label: "HERALD France"

  Data: {
    label: "Donnees observees"
  }
  Priors: {
    label: "Priors territoriaux"
  }
  Ridge: {
    label: "Ridge AR"
  }
  Herald: {
    label: "HERALD"
  }
  Intelligence: {
    label: "HERALD Intelligence v0"
  }
  Dashboard: {
    label: "Dashboard HERALD France"
  }
}

France.Data -> France.Ridge: "[...]"
France.Data -> France.Herald: "garantit train passe seulement"
France.Ridge -> France.Herald: "composante mathematique"
France.Ridge -> France.Dashboard
France.Herald -> France.Ridge: "reutilise la base Ridge"
France.Herald -> France.Intelligence
France.Herald -> France.Dashboard
France.Priors -> France.Herald
France.Intelligence -> France.Dashboard
`;case`view_1yuis9v`:return`direction: down

FranceData: {
  label: "Donnees observees"
}
FranceHerald: {
  label: "HERALD"
}
FranceRidge: {
  label: "Ridge AR"

  Features: {
    label: "Features locales"
  }
  Preprocessing: {
    label: "Imputation + standardisation"
  }
  Linear: {
    label: "Regression Ridge(alpha=1)"
  }
  RidgePred: {
    label: "Prediction Ridge"
  }
}
FranceDashboard: {
  label: "Dashboard HERALD France"
}

FranceData -> FranceRidge.Features: "fournit l historique local"
FranceHerald -> FranceRidge.Linear: "reutilise la base Ridge"
FranceRidge.Features -> FranceRidge.Preprocessing
FranceRidge.Preprocessing -> FranceRidge.Linear
FranceRidge.Linear -> FranceRidge.RidgePred
FranceRidge.RidgePred -> FranceHerald: "composante mathematique"
FranceRidge.RidgePred -> FranceDashboard
`;case`view_1mz8h1l`:return`direction: down

FranceData: {
  label: "Donnees observees"
}
FranceRidge: {
  label: "Ridge AR"
}
FrancePriors: {
  label: "Priors territoriaux"
}
FranceHerald: {
  label: "HERALD"

  Sequences: {
    label: "Sequences forecast-safe"
  }
  Local: {
    label: "Encodeur local"
  }
  DynamicGraph: {
    label: "Graphe dynamique"
  }
  GraphMessages: {
    label: "Messages territoriaux"
  }
  Internals: {
    label: "Internals graphe"
  }
  Mix: {
    label: "Gate / Alpha"
  }
  Residual: {
    label: "Tete residuelle"
  }
  Sector: {
    label: "Tete A10"
  }
  HeraldPred: {
    label: "Prediction HERALD"
  }
  SectorPred: {
    label: "Predictions A10"
  }
}
FranceIntelligence: {
  label: "HERALD Intelligence v0"
}
FranceDashboard: {
  label: "Dashboard HERALD France"
}

FranceData -> FranceHerald.Sequences: "garantit train passe seulement"
FranceRidge -> FranceHerald.HeraldPred: "composante mathematique"
FrancePriors -> FranceHerald.DynamicGraph
FranceHerald.Sequences -> FranceHerald.Local
FranceHerald.Local -> FranceHerald.DynamicGraph
FranceHerald.Local -> FranceHerald.Mix
FranceHerald.DynamicGraph -> FranceHerald.GraphMessages
FranceHerald.DynamicGraph -> FranceHerald.Internals
FranceHerald.GraphMessages -> FranceHerald.Mix
FranceHerald.Mix -> FranceHerald.Residual
FranceHerald.Mix -> FranceHerald.Sector
FranceHerald.Residual -> FranceHerald.HeraldPred: "Ridge + residual * zone_std"
FranceHerald.Sector -> FranceHerald.SectorPred
FranceHerald.Sequences -> FranceRidge: "reutilise la base Ridge"
FranceHerald.Internals -> FranceIntelligence
FranceHerald.HeraldPred -> FranceIntelligence
FranceHerald.HeraldPred -> FranceDashboard
FranceHerald.SectorPred -> FranceIntelligence
FranceHerald.SectorPred -> FranceDashboard
`;case`view_1py4btl`:return`direction: down

FrancePriors: {
  label: "Priors territoriaux"
}
FranceHeraldLocal: {
  label: "Encodeur local"
}
FranceHeraldDynamicGraph: {
  label: "Graphe dynamique"
}
FranceHeraldGraphMessages: {
  label: "Messages territoriaux"
}
FranceHeraldInternals: {
  label: "Internals graphe"
}

FrancePriors -> FranceHeraldDynamicGraph
FranceHeraldLocal -> FranceHeraldDynamicGraph
FranceHeraldDynamicGraph -> FranceHeraldGraphMessages
FranceHeraldDynamicGraph -> FranceHeraldInternals
`;case`view_1dglhfw`:return`direction: down

FranceHerald: {
  label: "HERALD"
}
FranceIntelligence: {
  label: "HERALD Intelligence v0"

  Scores: {
    label: "Scores opportunite/risque"
  }
  Maps: {
    label: "Cartes interpretatives"
  }
  Alerts: {
    label: "Alertes territoriales"
  }
}
FranceDashboard: {
  label: "Dashboard HERALD France"
}

FranceHerald -> FranceIntelligence.Scores
FranceHerald -> FranceIntelligence.Maps
FranceIntelligence.Scores -> FranceIntelligence.Alerts
FranceIntelligence.Maps -> FranceDashboard
`;default:throw Error(`Unknown viewId: `+e)}};export{e as d2Source};