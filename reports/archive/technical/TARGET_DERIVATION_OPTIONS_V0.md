# Target Derivation Options v0

Data: 2026-04-09

Objetivo:

- esclarecer como o target inicial do forecasting pode ou nao ser derivado com o acervo local atual

## Pergunta

Queremos um target que respeite o projeto:

- criacao economica
- frequencia temporal suficiente para forecasting
- agregacao final em `zone d'emploi`

## O que foi verificado

Arquivos analisados:

- [StockEtablissement_utf8.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/business_registry/sirene/StockEtablissement_utf8.zip)
- [StockEtablissementHistorique_utf8.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/business_registry/sirene/StockEtablissementHistorique_utf8.zip)
- [StockUniteLegale_utf8.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/business_registry/sirene/StockUniteLegale_utf8.zip)
- [TARGET_READINESS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/archive/technical/TARGET_READINESS_V0.md)

## Resultado da inspeção

### 1. `StockEtablissement_utf8`

O estoque atual de estabelecimentos contem colunas centrais para um target de criacao:

- `dateCreationEtablissement`
- `codeCommuneEtablissement`
- `etatAdministratifEtablissement`
- `siret`

Amostra de `300000` linhas:

- `dateCreationEtablissement`: `228740` preenchidas
- `codeCommuneEtablissement`: `296353` preenchidas
- `292812` comunas validas de 5 digitos
- `etatAdministratifEtablissement`: `300000` preenchidas

Leitura:

- existe material suficiente para derivar um agregado territorial por data de criacao
- mas a comuna disponivel aqui e a comuna observada no estoque atual

### 2. `StockEtablissementHistorique_utf8`

O historico contem:

- `dateDebut`
- `dateFin`
- `etatAdministratifEtablissement`
- `siret`

Mas **nao** contem:

- `codeCommuneEtablissement`

Amostra de `300000` linhas:

- `dateDebut`: `294018` preenchidas
- `dateFin`: `153277` preenchidas
- `siret`: `300000`
- `codeCommuneEtablissement`: inexistente

Leitura:

- o historico ajuda a reconstruir estados e periodos
- mas nao resolve sozinho a localizacao comunal ao longo do tempo

## Opcoes metodologicas

### Opcao A - Target oficial ideal

Definicao:

- criacao de empresas por `zone d'emploi`
- mensal
- com observacao territorial coerente no momento da criacao

Estado:

- ainda nao operacional com o acervo atual

Problema:

- as bases locais `DS_SIDE_CREA_*` inspecionadas nao entregam isso diretamente no nivel do projeto

### Opcao B - Target derivado de `SIRENE` por estabelecimento

Definicao:

- contar criacoes de estabelecimentos por mes e por comuna
- usando `dateCreationEtablissement`
- agregar comuna -> `ZE2020`

Vantagens:

- usa fonte administrativa fina
- tem granularidade potencialmente mensal
- e territorialmente agregavel

Limite forte:

- a comuna observada no estoque atual pode nao ser a comuna exata do momento de criacao
- sem historico de endereco comunal, isso gera risco de deslocamento territorial

Conclusao:

- forte como **proxy operacional de pesquisa**
- ainda nao deve ser confundido com target oficial sem caveat

### Opcao C - Target por unidade legal

Definicao:

- usar `dateCreationUniteLegale`

Problema:

- a unidade legal nao coincide necessariamente com atividade territorial efetiva
- o projeto trabalha melhor com dinamica territorial observavel de estabelecimentos

Conclusao:

- util como comparacao
- inferior a `Etablissement` para o problema territorial

### Opcao D - Proxy apenas para validar pipeline

Definicao:

- usar qualquer serie mais fraca apenas para testar treino

Risco:

- contaminar a interpretacao cientifica do projeto

Conclusao:

- aceitavel so para teste tecnico
- inadequado para virar target de pesquisa sem rotulo explicito de proxy

## Decisao recomendada

Manter duas camadas explicitas:

1. `target_oficial_alvo`
- criacao economica mensal por `zone d'emploi`
- ainda pendente de derivacao/confirmacao mais forte

2. `target_proxy_candidato_v0`
- criacoes de estabelecimentos agregadas para `ZE2020`
- derivadas de `SIRENE StockEtablissement`
- com caveat de localizacao observada no estoque atual

## O que isso significa para o projeto

- ja existe um caminho realista para sair do bloqueio do target
- mas esse caminho precisa nascer com nome correto de `proxy`
- isso preserva a honestidade metodologica do projeto

## Proximo passo recomendado

1. construir um `target_proxy_candidate_core_v0`
2. documentar formalmente o caveat territorial
3. usar esse target para baseline tecnico inicial
4. manter aberta a busca por uma implementacao mais forte do target oficial
