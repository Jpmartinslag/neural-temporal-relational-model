# ZRR Tables Inspection v0

Data: 2026-04-08

Arquivos de origem:

- [diffusion-zonages-historique-zrr-2019.xls](/home/jpdark/Downloads/project_recomm/dataset/diffusion-zonages-historique-zrr-2019.xls)
- [diffusion-zonages-zrr-cog2021.xls](/home/jpdark/Downloads/project_recomm/dataset/diffusion-zonages-zrr-cog2021.xls)

## Resultado principal

As planilhas `ZRR` sao muito uteis para o projeto.
Elas trazem classificacao comunal e historico institucional com qualidade suficiente para virar camada de politica territorial no pipeline.

## Tabelas extraidas

- [zrr_historique_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/zrr_historique_communes_v0.csv)
- [zrr_cog2021_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/zrr_cog2021_communes_v0.csv)
- [zrr_tables_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/zrr_tables_quality_v0.json)

## Cobertura historica encontrada

Anos presentes no workbook historico:

- `1995`
- `2005`
- `2006`
- `2007`
- `2009`
- `2010`
- `2012`
- `2013`
- `2014`
- `2017`
- `2018`

Linhas historicas extraidas:

- `400866`

## Cobertura comunal COG 2021

Linhas extraidas:

- `34965`

Campos:

- `codgeo`
- `libgeo`
- `zrr_simp`
- `zonage_zrr`

Distribuicao observada de `zrr_simp`:

- `C - Classée en ZRR`: `17694`
- `NC - Commune non classée`: `17235`
- `P - Commune partiellement classée en ZRR`: `36`

## Leitura metodologica

Estas tabelas sao valiosas por quatro motivos:

1. usam chave comunal direta
2. trazem historico institucional da politica `ZRR`
3. trazem alinhamento recente em `COG 2021`
4. podem ser agregadas futuramente para `ZE2020`

## Uso recomendado no projeto

Usar como:

- camada de contexto institucional
- futura variavel de politica territorial
- possivel label ou regime indicator
- referencia para transicao `ZRR -> FRR`

Nao usar ainda como:

- target principal
- unico criterio de recomendacao

## Proxima acao recomendada

1. manter `ZRR` como camada ativa de politica no acervo
2. procurar a cobertura nacional equivalente para `FRR`
3. depois construir uma tabela harmonizada `policy_commune_status`
