# Official Source Search v1

Data: 2026-04-10

Objetivo:

- ampliar a busca para fontes oficiais confiaveis alem do `data.gouv`
- distinguir entre existencia institucional da base, link bruto de download e adequacao real ao pipeline

## Fontes oficiais verificadas

- `insee.fr`
- `data.gouv.fr`
- `catalogue-donnees.insee.fr`

## Achados principais

### BPE 2021

Pagina oficial:

- https://www.insee.fr/fr/metadonnees/source/operation/s2077/bases-donnees-ligne

O HTML oficial confirma que a diffusion publica inclui:

- comptages por `REG`
- comptages por `DEP`
- comptages por `BV2012`
- comptages por `AAV2020`
- comptages por `UU2020`
- comptages por `EPCI`
- presence/absence por `commune`

Leitura:

- a base oficial de `BPE 2021` existe e esta documentada pelo Insee
- a pagina officielle du `Insee` indique explicitement que, dans la rubrique `Téléchargement de la base`, `les fichiers sont disponibles au format csv`
- a forma publica visivel nesta pagina nao aparece como um `ensemble csv` bruto facilmente fechavel por link direto
- para o nosso pipeline, isso e importante porque talvez a camada util seja a presenca por comuna, nao um fichier point complet

Instrucoes operacionais para download manual:

- abrir: https://www.insee.fr/fr/metadonnees/source/operation/s2077/bases-donnees-ligne
- na rubrica `Téléchargement de la base`, procurar por:
  - `BPE 2021 Ensemble`
  - `BPE 2021 Ensemble_xy`
  - `BPE en évolution 2016-2021 : BPE1621_pres_equip_DEPCOM`

Observacao:

- a propria pagina oficial informa que os arquivos dessa rubrica existem em `csv`
- se a interface do navegador renderizar a tabela corretamente, esses sao os nomes certos para procurar

### BPE 2020

Pagina oficial:

- https://www.insee.fr/fr/metadonnees/source/operation/s2027/bases-donnees-ligne

O HTML oficial confirma documentacao especifica de:

- `BPE 2020 Ensemble`
- `BPE 2020 Ensemble_xy`
- `BPE 2020 Enseignement`
- `BPE 2020 Enseignement_xy`
- `BPE 2020 - Table de passage`

Leitura:

- a familia `BPE 2020` existe com difusao oficial
- a documentacao oficial de `BPE 2020` mostra a existencia de `Ensemble` e `Ensemble_xy`, o que reforca a existencia de uma camada de dados publica estruturada para esse milésime
- nesta rodada, o link bruto exato de dados nao foi isolado a partir da pagina publica
- o status correto e `existencia oficial confirmada, download bruto ainda nao fechado`

Instrucoes operacionais para download manual:

- abrir: https://www.insee.fr/fr/metadonnees/source/operation/s2027/bases-donnees-ligne
- na rubrica `Téléchargement de la base`, procurar por:
  - `BPE 2020 Ensemble`
  - `BPE 2020 Ensemble_xy`

Observacao:

- a propria pagina oficial informa que os arquivos dessa rubrica existem em `dbf` e `csv`
- isso indica que o bloco de dados deve estar acessivel no navegador, mesmo que o endpoint bruto nao tenha sido isolado nesta rodada

### BPE 2023

Fonte oficial observada:

- https://www.data.gouv.fr/datasets/base-permanente-des-equipements-2

Recursos associados:

- csv: https://www.data.gouv.fr/api/1/datasets/r/dcdcf8fb-acaf-4260-b455-b25e0c7ee003
- zip: https://www.data.gouv.fr/api/1/datasets/r/abfc35ff-8305-43f0-a553-3b549673c002

Leitura:

- o acesso oficial foi fechado
- mas a inspecao do conteudo aponta `Millésime = 2024`
- por isso o recurso nao pode ser integrado como `BPE 2023` sem risco metodologico

### SIDE stocks

Paginas oficiais:

- https://www.data.gouv.fr/datasets/stocks-detablissements-par-activite-a10/
- https://www.data.gouv.fr/datasets/stocks-dunites-legales-par-activite-a10

Leitura via API do `data.gouv`:

- cobertura temporal declarada: `2014 -> 2023`
- recurso exposto hoje para etablissements aponta para `DS_SIDE_STOCKS_ET_COM_2022_CSV_FR`
- recurso exposto hoje para unites legales aponta para `DS_SIDE_STOCKS_UL_COM_2022_CSV_FR`

Conclusao:

- a familia oficial esta confirmada
- o ano exato `2021` ainda nao foi fechado por recurso bruto

### FLORES A17

Pagina oficial:

- https://www.data.gouv.fr/datasets/nombre-detablissements-et-effectifs-salaries-en-17-grands-secteurs

Leitura via API do `data.gouv`:

- familia `DS_FLORES_A17` confirmada
- o recurso bruto hoje exposto aponta para `DS_FLORES_A17_2024_CSV_FR`

Conclusao:

- a familia oficial esta confirmada
- `FLORES 2023` ainda nao foi fechado por link bruto exato

## Estado metodologico atual

O problema restante nao e uniforme:

- `BPE 2021` e `BPE 2020`: existencia oficial confirmada, mas link bruto ainda nao isolado
- `BPE 2023`: link bruto fechado, mas conteudo temporalmente incoerente
- `SIDE 2021`: familia confirmada, mas recurso publicado hoje aponta para 2022
- `FLORES 2023`: familia confirmada, mas recurso publicado hoje aponta para 2024

## Conclusao pratica

As lacunas continuam abertas, mas agora em categorias mais precisas:

1. `download nao fechado`
2. `download fechado com ano errado`
3. `familia confirmada, recurso publico insuficiente para o ano desejado`

Isso melhora a estrategia de coleta porque evita insistir no lugar errado ou integrar um arquivo formalmente oficial, mas temporalmente incorreto.
