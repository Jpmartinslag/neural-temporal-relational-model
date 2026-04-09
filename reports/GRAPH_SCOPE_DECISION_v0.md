# Graph Scope Decision v0

Data: 2026-04-09

Objetivo:

- formalizar o recorte espacial do MVP do grafo

## Decisao

O `core_v0` do grafo vai manter apenas a maior componente conectada do grafo geografico `ZE2020`.

Interpretacao pratica:

- manter Francia continental
- excluir Corse neste ciclo
- excluir componentes ultramarinos
- excluir ilhas e componentes desconectados do bloco principal

## Justificativa

- reduzir anomalias territoriais no MVP
- evitar que cobertura desigual do governo degrade o primeiro ciclo
- manter o recorte mais coerente para pre-STGNN

## Consequencia

O projeto nao abandona esses territorios.
Eles ficam apenas fora do `core_v0` e poderao ser reintroduzidos depois, com tratamento metodologico proprio.
