# Policy Layers Design

Data: 2026-04-09

Objetivo:

- formalizar a familia `policy_layers` no projeto

## Papel no sistema

As `policy_layers` nao sao apenas anexos documentais.
Elas servem para:

- alimentar o `policy_agent`
- apoiar o `territorial_agent`
- sustentar regras de conformidade
- fornecer contexto institucional para explicabilidade
- potencialmente gerar sinais estruturados para treino e validacao futura dos agentes

## Camadas previstas

- `ZRR`
- `FRR/FRR+`
- `QPV`
- `ZAN`

## Regra arquitetural

Separacao funcional:

- `predictive_layers`
  - SIDE
  - RP
  - BPE
  - FLORES
  - FILOSOFI
  - demografia historica

- `policy_layers`
  - ZRR
  - FRR/FRR+
  - QPV
  - ZAN

## Schema canônico comunal

Tabela alvo:

- `policy_commune_status_v0.csv`

Campos:

- `codgeo`
- `policy_type`
- `policy_year`
- `policy_status`
- `policy_status_raw`
- `source_layer`
- `policy_scope`
- `policy_reference_geo`
- `notes`

## Regra de evolucao

1. normalizar cada camada no schema comunal
2. depois agregar para `ZE2020`
3. depois ligar ao modulo de agentes

## Estado atual

- `ZRR` ja esta normalizada
- `QPV` ja esta normalizada
- `FRR/FRR+` tem fonte parcial identificada, mas nao cobertura nacional
- `ZAN` ja tem camada quantitativa interim, mas ainda nao status canônico
