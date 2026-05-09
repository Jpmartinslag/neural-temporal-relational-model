var e=e=>{switch(e){case`index`:return`@startuml
title "HERALD France - vue generale"
top to bottom direction

hide stereotype
skinparam ranksep 60
skinparam nodesep 30
skinparam {
  arrowFontSize 10
  defaultTextAlignment center
  wrapWidth 200
  maxMessageSize 100
  shadowing false
}

skinparam rectangle<<France>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
rectangle "==HERALD France\\n\\nModele de prevision territoriale des creations d etablissements par zone d emploi." <<France>> as France
@enduml
`;case`view_14htaoj`:return`@startuml
title "HERALD vs Ridge AR - comparaison globale"
top to bottom direction

hide stereotype
skinparam ranksep 60
skinparam nodesep 30
skinparam {
  arrowFontSize 10
  defaultTextAlignment center
  wrapWidth 200
  maxMessageSize 100
  shadowing false
}

skinparam rectangle<<FranceData>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FrancePriors>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceRidge>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHerald>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceIntelligence>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceDashboard>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
rectangle "HERALD France" <<France>> as France {
  skinparam RectangleBorderColor<<France>> #3b82f6
  skinparam RectangleFontColor<<France>> #3b82f6
  skinparam RectangleBorderStyle<<France>> dashed

  rectangle "==Donnees observees" <<FranceData>> as FranceData
  rectangle "==Priors territoriaux" <<FrancePriors>> as FrancePriors
  rectangle "==Ridge AR\\n\\nBaseline mathematique lineaire: lags locaux + regression Ridge." <<FranceRidge>> as FranceRidge
  rectangle "==HERALD\\n\\nModele hybride: Ridge AR + correction neurale territoriale." <<FranceHerald>> as FranceHerald
  rectangle "==HERALD Intelligence v0\\n\\nCouche exploratoire de post-traitement: scores, alertes et contexte." <<FranceIntelligence>> as FranceIntelligence
  rectangle "==Dashboard HERALD France" <<FranceDashboard>> as FranceDashboard
}

FranceData .[#8D8D8D,thickness=2].> FranceRidge : <color:#8D8D8D>[...]
FranceData .[#8D8D8D,thickness=2].> FranceHerald : <color:#8D8D8D>garantit train passe seulement
FranceRidge .[#8D8D8D,thickness=2].> FranceHerald : <color:#8D8D8D>composante mathematique
FranceRidge .[#8D8D8D,thickness=2].> FranceDashboard
FranceHerald .[#8D8D8D,thickness=2].> FranceRidge : <color:#8D8D8D>reutilise la base Ridge
FranceHerald .[#8D8D8D,thickness=2].> FranceIntelligence
FranceHerald .[#8D8D8D,thickness=2].> FranceDashboard
FrancePriors .[#8D8D8D,thickness=2].> FranceHerald
FranceIntelligence .[#8D8D8D,thickness=2].> FranceDashboard
@enduml
`;case`view_1yuis9v`:return`@startuml
title "Ridge AR - baseline lineaire"
top to bottom direction

hide stereotype
skinparam ranksep 60
skinparam nodesep 30
skinparam {
  arrowFontSize 10
  defaultTextAlignment center
  wrapWidth 200
  maxMessageSize 100
  shadowing false
}

skinparam rectangle<<FranceData>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHerald>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceRidgeFeatures>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceRidgePreprocessing>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceRidgeLinear>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceRidgeRidgePred>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceDashboard>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
rectangle "==Donnees observees" <<FranceData>> as FranceData
rectangle "==HERALD\\n\\nModele hybride: Ridge AR + correction neurale territoriale." <<FranceHerald>> as FranceHerald
rectangle "Ridge AR" <<FranceRidge>> as FranceRidge {
  skinparam RectangleBorderColor<<FranceRidge>> #3b82f6
  skinparam RectangleFontColor<<FranceRidge>> #3b82f6
  skinparam RectangleBorderStyle<<FranceRidge>> dashed

  rectangle "==Features locales\\n\\nside_lag_1, side_lag_2, side_lag_3, growth_1y, growth_2y." <<FranceRidgeFeatures>> as FranceRidgeFeatures
  rectangle "==Imputation + standardisation" <<FranceRidgePreprocessing>> as FranceRidgePreprocessing
  rectangle "==Regression Ridge(alpha=1)" <<FranceRidgeLinear>> as FranceRidgeLinear
  rectangle "==Prediction Ridge" <<FranceRidgeRidgePred>> as FranceRidgeRidgePred
}
rectangle "==Dashboard HERALD France" <<FranceDashboard>> as FranceDashboard

FranceData .[#8D8D8D,thickness=2].> FranceRidgeFeatures : <color:#8D8D8D>fournit l historique local
FranceHerald .[#8D8D8D,thickness=2].> FranceRidgeLinear : <color:#8D8D8D>reutilise la base Ridge
FranceRidgeFeatures .[#8D8D8D,thickness=2].> FranceRidgePreprocessing
FranceRidgePreprocessing .[#8D8D8D,thickness=2].> FranceRidgeLinear
FranceRidgeLinear .[#8D8D8D,thickness=2].> FranceRidgeRidgePred
FranceRidgeRidgePred .[#8D8D8D,thickness=2].> FranceHerald : <color:#8D8D8D>composante mathematique
FranceRidgeRidgePred .[#8D8D8D,thickness=2].> FranceDashboard
@enduml
`;case`view_1mz8h1l`:return`@startuml
title "HERALD - architecture interne"
top to bottom direction

hide stereotype
skinparam ranksep 60
skinparam nodesep 30
skinparam {
  arrowFontSize 10
  defaultTextAlignment center
  wrapWidth 200
  maxMessageSize 100
  shadowing false
}

skinparam rectangle<<FranceData>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceRidge>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FrancePriors>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldSequences>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldLocal>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldDynamicGraph>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldGraphMessages>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldInternals>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldMix>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldResidual>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldSector>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldHeraldPred>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldSectorPred>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceIntelligence>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceDashboard>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
rectangle "==Donnees observees" <<FranceData>> as FranceData
rectangle "==Ridge AR\\n\\nBaseline mathematique lineaire: lags locaux + regression Ridge." <<FranceRidge>> as FranceRidge
rectangle "==Priors territoriaux" <<FrancePriors>> as FrancePriors
rectangle "HERALD" <<FranceHerald>> as FranceHerald {
  skinparam RectangleBorderColor<<FranceHerald>> #3b82f6
  skinparam RectangleFontColor<<FranceHerald>> #3b82f6
  skinparam RectangleBorderStyle<<FranceHerald>> dashed

  rectangle "==Sequences forecast-safe" <<FranceHeraldSequences>> as FranceHeraldSequences
  rectangle "==Encodeur local\\n\\nProjection annuelle, encodeur trimestriel et memoire GRU locale." <<FranceHeraldLocal>> as FranceHeraldLocal
  rectangle "==Graphe dynamique\\n\\nAttention QK conditionnee par regime, prior geo et prior mobilite." <<FranceHeraldDynamicGraph>> as FranceHeraldDynamicGraph
  rectangle "==Messages territoriaux\\n\\nAggregation A_t @ embeddings des zones connectees." <<FranceHeraldGraphMessages>> as FranceHeraldGraphMessages
  rectangle "==Internals graphe\\n\\ndynamic_adj, gate, alpha, gamma_geo, gamma_mob." <<FranceHeraldInternals>> as FranceHeraldInternals
  rectangle "==Gate / Alpha\\n\\nArbitrage entre signal local, signal graphe et correction residuelle." <<FranceHeraldMix>> as FranceHeraldMix
  rectangle "==Tete residuelle" <<FranceHeraldResidual>> as FranceHeraldResidual
  rectangle "==Tete A10" <<FranceHeraldSector>> as FranceHeraldSector
  rectangle "==Prediction HERALD" <<FranceHeraldHeraldPred>> as FranceHeraldHeraldPred
  rectangle "==Predictions A10" <<FranceHeraldSectorPred>> as FranceHeraldSectorPred
}
rectangle "==HERALD Intelligence v0\\n\\nCouche exploratoire de post-traitement: scores, alertes et contexte." <<FranceIntelligence>> as FranceIntelligence
rectangle "==Dashboard HERALD France" <<FranceDashboard>> as FranceDashboard

FranceData .[#8D8D8D,thickness=2].> FranceHeraldSequences : <color:#8D8D8D>garantit train passe seulement
FranceRidge .[#8D8D8D,thickness=2].> FranceHeraldHeraldPred : <color:#8D8D8D>composante mathematique
FrancePriors .[#8D8D8D,thickness=2].> FranceHeraldDynamicGraph
FranceHeraldSequences .[#8D8D8D,thickness=2].> FranceHeraldLocal
FranceHeraldLocal .[#8D8D8D,thickness=2].> FranceHeraldDynamicGraph
FranceHeraldLocal .[#8D8D8D,thickness=2].> FranceHeraldMix
FranceHeraldDynamicGraph .[#8D8D8D,thickness=2].> FranceHeraldGraphMessages
FranceHeraldDynamicGraph .[#8D8D8D,thickness=2].> FranceHeraldInternals
FranceHeraldGraphMessages .[#8D8D8D,thickness=2].> FranceHeraldMix
FranceHeraldMix .[#8D8D8D,thickness=2].> FranceHeraldResidual
FranceHeraldMix .[#8D8D8D,thickness=2].> FranceHeraldSector
FranceHeraldResidual .[#8D8D8D,thickness=2].> FranceHeraldHeraldPred : <color:#8D8D8D>Ridge + residual * zone_std
FranceHeraldSector .[#8D8D8D,thickness=2].> FranceHeraldSectorPred
FranceHeraldSequences .[#8D8D8D,thickness=2].> FranceRidge : <color:#8D8D8D>reutilise la base Ridge
FranceHeraldInternals .[#8D8D8D,thickness=2].> FranceIntelligence
FranceHeraldHeraldPred .[#8D8D8D,thickness=2].> FranceIntelligence
FranceHeraldHeraldPred .[#8D8D8D,thickness=2].> FranceDashboard
FranceHeraldSectorPred .[#8D8D8D,thickness=2].> FranceIntelligence
FranceHeraldSectorPred .[#8D8D8D,thickness=2].> FranceDashboard
@enduml
`;case`view_1py4btl`:return`@startuml
title "Graphe dynamique HERALD"
top to bottom direction

hide stereotype
skinparam ranksep 60
skinparam nodesep 30
skinparam {
  arrowFontSize 10
  defaultTextAlignment center
  wrapWidth 200
  maxMessageSize 100
  shadowing false
}

skinparam rectangle<<FrancePriors>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldLocal>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldDynamicGraph>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldGraphMessages>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceHeraldInternals>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
rectangle "==Priors territoriaux" <<FrancePriors>> as FrancePriors
rectangle "==Encodeur local\\n\\nProjection annuelle, encodeur trimestriel et memoire GRU locale." <<FranceHeraldLocal>> as FranceHeraldLocal
rectangle "==Graphe dynamique\\n\\nAttention QK conditionnee par regime, prior geo et prior mobilite." <<FranceHeraldDynamicGraph>> as FranceHeraldDynamicGraph
rectangle "==Messages territoriaux\\n\\nAggregation A_t @ embeddings des zones connectees." <<FranceHeraldGraphMessages>> as FranceHeraldGraphMessages
rectangle "==Internals graphe\\n\\ndynamic_adj, gate, alpha, gamma_geo, gamma_mob." <<FranceHeraldInternals>> as FranceHeraldInternals

FrancePriors .[#8D8D8D,thickness=2].> FranceHeraldDynamicGraph
FranceHeraldLocal .[#8D8D8D,thickness=2].> FranceHeraldDynamicGraph
FranceHeraldDynamicGraph .[#8D8D8D,thickness=2].> FranceHeraldGraphMessages
FranceHeraldDynamicGraph .[#8D8D8D,thickness=2].> FranceHeraldInternals
@enduml
`;case`view_1dglhfw`:return`@startuml
title "HERALD Intelligence v0"
top to bottom direction

hide stereotype
skinparam ranksep 60
skinparam nodesep 30
skinparam {
  arrowFontSize 10
  defaultTextAlignment center
  wrapWidth 200
  maxMessageSize 100
  shadowing false
}

skinparam rectangle<<FranceHerald>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceIntelligenceScores>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceIntelligenceMaps>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceIntelligenceAlerts>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
skinparam rectangle<<FranceDashboard>>{
  BackgroundColor #3b82f6
  FontColor #eff6ff
  BorderColor #2563eb
}
rectangle "==HERALD\\n\\nModele hybride: Ridge AR + correction neurale territoriale." <<FranceHerald>> as FranceHerald
rectangle "HERALD Intelligence v0" <<FranceIntelligence>> as FranceIntelligence {
  skinparam RectangleBorderColor<<FranceIntelligence>> #3b82f6
  skinparam RectangleFontColor<<FranceIntelligence>> #3b82f6
  skinparam RectangleBorderStyle<<FranceIntelligence>> dashed

  rectangle "==Scores opportunite/risque" <<FranceIntelligenceScores>> as FranceIntelligenceScores
  rectangle "==Cartes interpretatives" <<FranceIntelligenceMaps>> as FranceIntelligenceMaps
  rectangle "==Alertes territoriales" <<FranceIntelligenceAlerts>> as FranceIntelligenceAlerts
}
rectangle "==Dashboard HERALD France" <<FranceDashboard>> as FranceDashboard

FranceHerald .[#8D8D8D,thickness=2].> FranceIntelligenceScores
FranceHerald .[#8D8D8D,thickness=2].> FranceIntelligenceMaps
FranceIntelligenceScores .[#8D8D8D,thickness=2].> FranceIntelligenceAlerts
FranceIntelligenceMaps .[#8D8D8D,thickness=2].> FranceDashboard
@enduml
`;default:throw Error(`Unknown viewId: `+e)}};export{e as pumlSource};