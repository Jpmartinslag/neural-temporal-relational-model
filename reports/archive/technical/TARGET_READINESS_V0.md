# Target Readiness v0

Data: 2026-04-09

Objetivo:

- verificar se o target inicial do forecasting ja pode ser operacionalizado com o acervo local atual

## Target previsto no projeto

Target recomendado pelos documentos do projeto:

- criacao de empresas por `zone d'emploi`
- em frequencia mensal
- com horizonte inicial `t+1`

## O que foi verificado no acervo local

Arquivos inspecionados:

- [DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip](/home/jpdark/Downloads/project_recomm/dataset/DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip)
- [DS_SIDE_CREA_ENT_COM_2024_CSV.zip](/home/jpdark/Downloads/project_recomm/dataset/DS_SIDE_CREA_ENT_COM_2024_CSV.zip)
- [DS_SIDE_CREA_ETAB_COM_2024_CSV.zip](/home/jpdark/Downloads/project_recomm/dataset/DS_SIDE_CREA_ETAB_COM_2024_CSV.zip)

## Resultado

### 1. `DS_SIDE_CREA_ENT_SERIES`

- possui frequencia mensal e trimestral
- cobre `FRANCE`, `REG` e `DEP`
- nao entrega `ZE2020`

Conclusao:

- bom para contexto macro
- insuficiente para target no nivel do projeto

### 2. `DS_SIDE_CREA_ENT_COM_2024`

- nao apareceu `ZE2020`
- na inspecao direta, apareceram linhas em `EPCI`
- frequencia observada no sample: anual

Conclusao:

- nao sustenta diretamente o target mensal por `zone d'emploi`

### 3. `DS_SIDE_CREA_ETAB_COM_2024`

- nao apareceu `ZE2020`
- na inspecao direta, apareceram linhas em `EPCI`
- frequencia observada no sample: anual

Conclusao:

- nao sustenta diretamente o target mensal por `zone d'emploi`

## Diagnostico

O target do projeto esta:

- **conceitualmente congelado**
- mas **operacionalmente pendente**

Isto significa:

- ja sabemos qual target queremos
- ainda nao temos, no acervo atual, uma fonte pronta que o entregue exatamente em `ZE2020` mensal

## Decisao metodologica

Nao vamos inventar o target.

O estado correto do projeto agora e:

- infraestrutura pre-STGNN pronta
- target inicial definido no plano
- integracao do target ainda dependente de fonte adequada

## Proximos caminhos possiveis

1. buscar fonte mensal mais adequada para criacao por territorio e depois agregar a `ZE2020`
2. derivar o target a partir de registros administrativos mais finos, como `SIRENE`, se a cobertura temporal e a qualidade permitirem
3. usar temporariamente um proxy mais fraco apenas para validar pipeline, mas sem confundi-lo com o target oficial do projeto

## Recomendacao

- manter como target oficial: criacao de empresas por `zone d'emploi` e por mes
- nao congelar ainda uma implementacao fraca desse target
- abrir uma rodada propria de busca/derivacao do target antes de entrar em baseline e STGNN
