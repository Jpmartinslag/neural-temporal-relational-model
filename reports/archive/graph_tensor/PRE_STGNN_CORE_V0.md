# Pre-STGNN Core v0

Data: 2026-04-09

Objetivo:

- consolidar o pacote estrutural minimo antes do congelamento do target

Artefatos:

- [graph_node_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_node_index_core_v0.csv)
- [graph_edge_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edge_index_core_v0.csv)
- [pre_stgnn_dataset_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/pre_stgnn_dataset_core_v0.csv)
- [pre_stgnn_feature_masks_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/pre_stgnn_feature_masks_core_v0.csv)
- [pre_stgnn_feature_registry_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/pre_stgnn_feature_registry_core_v0.csv)
- [pre_stgnn_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/pre_stgnn_core_quality_v0.json)

## Estrutura

- grafo: `280` nos no `core_v0`
- arestas: lista direcionada pronta para uso
- painel: uma linha por `year` e `node_idx`
- masks: uma coluna binaria por feature

## Importante

- este pacote ainda **nao** define target
- ele prepara a base estrutural para baseline e STGNN
- o proximo congelamento necessario e o target inicial do forecasting
