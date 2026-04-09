# Versioning Policy

Data: 2026-04-08

Objetivo:

- manter rastreabilidade metodologica
- controlar mudancas em datasets analiticos
- evitar perda de contexto tecnico

## O que deve entrar no git

- `src/`
- `metadata/`
- `reports/`
- `data/interim/mappings/`
- `data/interim/tables/`
- `data/processed/`
- arquivos de configuracao do projeto

## O que nao deve entrar no git

- arquivos brutos pesados `.zip`
- downloads temporarios
- planilhas binarias nao essenciais para reproducao
- caches e arquivos descartaveis

## Regra de versionamento de artefatos

Para datasets processados:

- iniciar o estado canonico do repositorio em `v0`
- avancar para `v1`, `v2` e seguintes apenas quando houver mudanca metodologica real
- nao sobrescrever versoes anteriores quando houver necessidade de comparacao metodologica
- cada nova versao deve ter justificativa no journal
- depois que uma versao se tornar canonica e as anteriores perderem utilidade operacional, manter no repositorio apenas a versao ativa
- o historico metodologico fica registrado no `git` e no journal, nao em multiplos arquivos redundantes no diretorio

Para scripts:

- todo artefato processado deve ter script reprodutivel quando a logica deixar de ser trivial
- mudancas de regra analitica devem acompanhar mudanca no script
- nomes novos devem seguir [NAMING_CONVENTIONS_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/NAMING_CONVENTIONS_v0.md)

## Regra de commit

Cada commit deve refletir uma unica unidade de decisao ou entrega.

Exemplos:

- `build initial commune to ze2020 mapping`
- `add zones master annual v0`
- `replace unemployment proxy with estimated unemployment rate`
- `isolate mayotte as structural anomaly`
- `add phase 1 roadmap and versioning policy`

## Regra de rastreabilidade

Toda mudanca relevante precisa aparecer em tres niveis:

1. no `git`
2. no [PROJECT_JOURNEY.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_JOURNEY.md)
3. no artefato de qualidade ou roadmap correspondente

## Regra de fase

Enquanto estivermos na Fase 1:

- o objetivo principal e construir o grafo territorial inicial
- decisoes que nao contribuirem para esse objetivo devem ser adiadas
- complexidade de modelagem fica fora do caminho critico
