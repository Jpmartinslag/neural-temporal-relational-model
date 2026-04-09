# Pre-Graph Readiness v0

Data: 2026-04-09

Objetivo:

- verificar se realmente faz sentido abrir o grafo agora
- explicitar o impacto da ausencia de `ground truth`
- evitar que o projeto avance para estrutura espacial sem criterio de validacao

## Pergunta central

Estamos prontos para construir o primeiro grafo?

Resposta curta:

- sim, para um **grafo estrutural inicial**
- nao, ainda nao para inferir qualidade de recomendacao ou desempenho final do sistema

## Ponto critico do projeto

Hoje o projeto **nao tem ground truth final de recomendacao**.

Isso muda a interpretacao do proximo passo:

- o grafo nao vai validar se a recomendacao esta “certa”
- o grafo vai apenas estruturar o espaco territorial para modelagem posterior

Em outras palavras:

- grafo = estrutura
- nao = prova de qualidade da recomendacao

## O que ja esta suficientemente pronto

### 1. Unidade territorial

- `ZE2020` esta estabilizada como no do sistema

### 2. Features iniciais por no

- `zones_master_annual_v0` ja fornece um snapshot util
- `population_history_ze2020_v0` ja adiciona eixo temporal demografico
- `zan_consumption_ze2020_v0` ja adiciona uma camada territorial quantitativa

### 3. Painel minimo

- `panel_zones_v0` ja existe
- o formato `zone-year` esta consistente

### 4. Anomalia principal conhecida

- `Mayotte` ja esta isolada e nao esta mascarando erro de merge

## O que ainda nao esta pronto para inferencia forte

### 1. Nao ha target final definido

Sem target:

- nao ha supervisao real
- nao ha avaliacao preditiva real
- nao ha comparacao de desempenho de modelo

### 2. Nao ha ground truth de recomendacao

Sem ground truth final:

- nao podemos dizer ainda se uma recomendacao e “boa” ou “ruim”
- so podemos validar consistencia interna, coerencia territorial e estabilidade metodologica

### 3. `policy_layers` ainda nao estao operacionalizadas

- `QPV` multi-comuna ainda incompleto
- `ZAN` ainda nao virou regra ou sinal de agente
- `FRR/FRR+` ainda nao esta consolidada nacionalmente

## O que isso implica para o grafo

O primeiro grafo deve ser entendido como:

- grafo de suporte ao projeto
- grafo estrutural e auditavel
- base para pre-STGNN

Nao deve ser entendido como:

- validacao do sistema final
- demonstracao de qualidade de recomendacao
- prova de desempenho do modelo

## Criterio de prontidao que considero suficiente

Podemos abrir o grafo agora se aceitarmos explicitamente estas regras:

1. o grafo inicial representa apenas adjacencia geografica entre `ZE2020`
2. ele nao depende ainda de target final
3. ele sera validado por coerencia estrutural, nao por acuracia final
4. qualquer leitura “inteligente” do grafo vira depois, no bloco pre-STGNN

## Como validar sem ground truth

Nesta fase, a validacao correta e:

### Validacao estrutural

- numero de nos esperado
- numero de arestas
- componentes conectados
- nos isolados
- coerencia com o fundo territorial oficial

### Validacao analitica

- possibilidade de anexar features por no
- possibilidade de alinhar o painel ao conjunto de nos
- capacidade de excluir anomalias estruturais como `Mayotte`

### Validacao metodologica

- o grafo nao introduz suposicoes indevidas
- a adjacencia geografica e defensavel como primeiro passo
- o desenho continua compativel com extensoes futuras por mobilidade

## Conclusao

Se a pergunta for:

- “temos base para o primeiro grafo?”  
  sim

- “temos base para avaliar o sistema final?”  
  nao ainda

## Decisao recomendada

- continuar para o primeiro grafo
- mas registrar explicitamente que ele e **infraestrutura metodologica**
- nao resultado final
- nao substituto de `ground truth`

## Proximo passo seguro

1. construir o primeiro grafo `ZE2020` por adjacencia geografica
2. validar sua estrutura
3. so depois discutir como definir target, proxy de avaliacao e futuro treino
