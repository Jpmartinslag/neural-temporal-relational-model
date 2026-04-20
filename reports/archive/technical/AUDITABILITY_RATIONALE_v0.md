# Auditability Rationale v0

Data: 2026-04-09

Objetivo:

- registrar por que a separacao entre `STGNN`, decisao, agentes e orquestrador e central no projeto

## Principio

O projeto nao foi desenhado como um sistema monolitico.
Ele foi desenhado como uma arquitetura separada, em que:

- o `STGNN` gera sinais preditivos
- a camada de decisao transforma sinais em candidatas/ranking inicial
- os agentes validam criterios especificos
- o orquestrador resolve conflitos e emite a decisao final

## Por que isso e importante

Essa separacao permite auditar o sistema em partes.

Sem isso, seria dificil responder:

- o erro veio do modelo preditivo?
- veio da formulacao multicriterio?
- veio de uma restricao normativa?
- veio da arbitragem final?

## O que a separacao torna auditavel

### 1. Auditabilidade do STGNN

Permite avaliar:

- capacidade preditiva
- robustez temporal
- ganho sobre baseline
- sensibilidade a features e ao grafo

Pergunta auditavel:

- o modulo preditivo realmente agrega valor?

### 2. Auditabilidade da camada de decisao

Permite avaliar:

- formacao das candidatas
- calculo de objetivos
- impacto das restricoes
- formacao do ranking inicial

Pergunta auditavel:

- a traducao de sinais em recomendacao inicial esta coerente?

### 3. Auditabilidade dos agentes

Permite avaliar:

- qual agente aprovou
- qual agente rejeitou
- qual agente marcou incerteza
- qual criterio foi responsavel por alterar a decisao

Pergunta auditavel:

- a mudanca de decisao veio de qual criterio e por qual razao?

### 4. Auditabilidade do orquestrador

Permite avaliar:

- quais regras foram aplicadas
- como conflitos foram resolvidos
- quais restricoes duras bloquearam candidatas
- como a decisao final emergiu dos sinais anteriores

Pergunta auditavel:

- a arbitragem final foi consistente com as regras do sistema?

## Consequencia metodologica

A arquitetura nao foi separada apenas por organizacao de codigo.
Ela foi separada para permitir:

- validacao modular
- rastreabilidade causal do processo decisorio
- explicacao auditavel em politica publica
- adaptacao de restricoes sem retrainar o modelo preditivo

## Relacao com as hipoteses do projeto

Essa escolha sustenta diretamente:

- `H1`: separacao entre predicao e decisao melhora rastreabilidade
- `H2`: conflitos resolvidos por regras deterministicas melhoram coerencia
- `H3`: a camada decisional pode ser reconfigurada sem reentrenar o backbone preditivo

## Conclusao

No projeto, a separacao entre `STGNN`, decisao, agentes e orquestrador nao e opcional.
Ela e uma condicao para:

- auditar o sistema
- validar cada modulo
- defender metodologicamente a recomendacao final
