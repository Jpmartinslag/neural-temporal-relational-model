# FRR Layer Inspection v0

Data: 2026-04-08

Arquivo analisado:

- [dataset-1775678390572.zip](/home/jpdark/Downloads/project_recomm/dataset/dataset-1775678390572.zip)

## Resultado principal

O arquivo contem uma camada vetorial `FRR`, mas ela nao representa a Franca inteira.
Ela parece ser um extrait regional ou departamental.

## Estrutura encontrada

Conteudo do zip:

- `dataset/N_FRR_026.shp`
- `dataset/N_FRR_026.shx`
- `dataset/N_FRR_026.dbf`
- `dataset/N_FRR_026.prj`
- `dataset/N_FRR_026.cpg`
- `dataset/fr-120066022-jdd-0058dc2a-5fee-4826-a8db-b0808c8f97b2.xml`

## Caracteristicas tecnicas

Geometria:

- `Polygon`

Projecao:

- `RGF93 / Lambert-93`

Campos do `dbf`:

- `ID`
- `NOM`
- `NOM_M`
- `INSEE_COM`

Numero de registros:

- `223`

## Interpretacao

A camada esta em nivel comunal:

- o campo chave e `INSEE_COM`

Mas a cobertura nao e nacional:

- todos os codigos observados pertencem ao departamento `26`
- o nome da camada `N_FRR_026` reforca isso

Conclusao:

- este arquivo nao pode ser usado sozinho como camada nacional da `FRR`
- ele e util como prova de formato e de estrutura da fonte
- para o projeto, precisamos localizar a versao nacional ou consolidar extraits equivalentes

## Uso no projeto

Utilidade atual:

- contexto de politica territorial
- prototipo de join `commune -> FRR`
- referencia de schema para coleta nacional futura

Nao usar ainda para:

- label nacional final
- camada nacional unica de politica
- integracao direta no grafo completo

## Proxima acao recomendada

1. localizar a versao nacional da `FRR`
2. se a fonte oficial estiver segmentada por territorio, baixar os extraits equivalentes
3. so depois integrar `FRR` ao pipeline ativo
