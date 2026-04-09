# Evaluation Without Ground Truth v0

Data: 2026-04-09

Objetivo:

- registrar como pensar avaliacao enquanto o projeto ainda nao tem verdade-terreno final

## Principio

Sem `ground truth`, nao ha como avaliar recomendacao final de maneira supervisionada.

Entao, por enquanto, o projeto deve separar tres niveis de avaliacao:

## 1. Avaliacao de dados

- cobertura
- coerencia territorial
- coerencia temporal
- missingness
- rastreabilidade de anomalias

## 2. Avaliacao estrutural

- consistencia do painel
- consistencia do grafo
- capacidade de anexar features e mascaras

## 3. Avaliacao futura de modelagem

So podera existir de forma mais forte quando houver:

- target definido
- proxy de sucesso territorial
- ou criterio institucional/observacional para comparacao

## O que nao fazer agora

- nao tratar o grafo como prova de qualidade do sistema
- nao interpretar clusters ou centralidade como recomendacao final
- nao confundir coerencia estrutural com validacao substantiva

## O que fazer agora

- usar o grafo como base tecnica
- manter a documentacao explicita sobre essa limitacao
- adiar qualquer pretensao de avaliacao final ate a definicao do target
