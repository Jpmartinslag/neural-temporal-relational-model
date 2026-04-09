# Phase 1 Graph Roadmap

Data: 2026-04-08

Objetivo da Fase 1:

- construir a fundacao de dados necessaria para gerar o primeiro grafo territorial em `zones d'emploi 2020`

Entregavel final da fase:

- um grafo inicial onde:
  - cada no representa uma `zone d'emploi`
  - cada aresta representa adjacencia geografica
  - os nos possuem features anuais limpas derivadas do `zones_master`

## Regra de foco

Durante a Fase 1, qualquer tarefa deve responder a uma destas perguntas:

1. ajuda a limpar a base analitica?
2. ajuda a montar o painel minimo por zona?
3. ajuda a construir a adjacencia espacial?
4. ajuda a validar o grafo final?

Se a resposta for nao, a tarefa sai do caminho critico.

## Sequencia oficial da Fase 1

### Bloco A - Fundacao analitica

1. congelar o `zones_master` canonico
2. enriquecer o dicionario de variaveis
3. formalizar flags de cobertura e anomalia
4. isolar Mayotte como anomalia estrutural

## Criterio de pronto do Bloco A

- `zones_master` com schema estavel
- colunas documentadas
- missingness explicita
- anomalias identificadas

### Bloco B - Painel minimo

5. definir janela temporal inicial
6. construir `panel_zones`
7. alinhar anos entre features
8. documentar defasagens temporais

## Criterio de pronto do Bloco B

- um arquivo `panel_zones` com `zone_id`, `year` e features
- sem mistura temporal silenciosa

### Bloco C - Grafo espacial inicial

9. extrair geometrias de `ZE2020`
10. gerar lista de adjacencia entre zonas
11. produzir tabela de arestas
12. validar conectividade e componentes isolados

## Criterio de pronto do Bloco C

- `nodes` definidos
- `edges` definidos
- relatorio de qualidade do grafo

### Bloco D - Dataset pre-STGNN

13. selecionar features iniciais do no
14. normalizar features
15. gerar mascaras de missingness
16. preparar tensors ou matrizes base

## Criterio de pronto do Bloco D

- dataset pronto para baseline espacial-temporal
- ainda sem entrar na modelagem final

## Fora da Fase 1

- STGNN final
- tuning
- decisao multicriterio
- agentes
- orquestracao completa

## Proximo passo objetivo

O proximo passo no caminho critico e:

1. revisar o `panel_zones_v0`
2. extrair geometrias de `ZE2020`
3. gerar a adjacencia espacial inicial
4. produzir a primeira tabela de arestas
