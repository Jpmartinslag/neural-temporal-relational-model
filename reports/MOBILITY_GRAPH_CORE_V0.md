# Mobility Graph Core v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-13

Objetivo:

- substituir o grafo geografico estatico por um grafo de mobilidade funcional
- fonte: fluxos domicilio-trabalho em nivel comunal (RP 2021), agregados para ZE2020
- hipotese: zonas que trocam trabalhadores tem dinamicas economicas correlacionadas

## Motivacao

O baseline espacial com grafo geografico escolheu `alpha = 1.0` (ignorar vizinhos).
Isso indica que proximidade geografica nao implica correlacao de dinamica economica.
Um grafo de mobilidade captura relacoes funcionais: se trabalhadores de A trabalham em B,
as economias de A e B sao interdependentes, independente de compartilharem fronteira.

## Fonte

- `base-flux-mobilite-domicile-lieu-travail-2021-csv.zip`
- par (CODGEO, DCLT): comuna de residencia, comuna de trabalho
- campo de fluxo: `NBFLUX_C21_ACTOCC15P` (ativos ocupados 15+ anos)
- ano: 2021

## Resultados

- pares ZE2020 inter-zona com fluxo: `27,571`
- arestas nao nulas na matriz `[280, 280]`: `27,571`
- zonas com pelo menos 1 saida: `280` / `280`
- cobertura de fluxo (core/total): `17.1%`
- grau medio de saida: `98.5` arestas por zona
- grau mediano de saida: `88.0`

Comparacao: grafo geografico atual: 1486 arestas em 280 nos.

## Top 5 Pares por Fluxo

| ZE origem | ZE destino | fluxo (trabalhadores) |
|---|---|---|
| `1112` | `1109` | `97,273` |
| `1114` | `1109` | `89,179` |
| `1101` | `1109` | `66,546` |
| `1113` | `1109` | `57,479` |
| `1104` | `1109` | `57,221` |

## Variantes de Adjacencia

- `adjacency_raw`: dirigida, valores brutos de fluxo (trabalhadores por par ZE2020)
- `adjacency_symmetric`: media de (A + A^T), nao dirigida
- `adjacency_row_normalized_self_loop`: simetrica + self-loop + normalizacao por linha
  recomendada para modelos de passagem de mensagem (GCN, GraphSAGE, STGNN)

## Artefatos

- [mobility_graph_edges_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_graph_edges_core_v0.csv)
- [mobility_adjacency_raw_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_raw_core_v0.csv)
- [mobility_adjacency_row_normalized_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_row_normalized_core_v0.csv)
- [mobility_graph_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_graph_core_v0.npz)

## Decisao

- o grafo de mobilidade esta pronto para ser usado no baseline espacial
- proximo passo: repetir o baseline espacial (persistencia vs. media ponderada por mobilidade)
  usando `adjacency_row_normalized_self_loop` no lugar do grafo geografico
- apenas se o grafo de mobilidade mostrar ganho sobre persistencia e que o grafo
  sera tratado como sinal preditivo confirmado

## Proxima Etapa

- avaliar baseline espacial com grafo de mobilidade
- comparar: persistencia, media-vizinhos-geo, media-vizinhos-mobilidade
- registrar decisao sobre qual grafo usar no pacote tensorial final