# data.gouv Link Search v0

Data: 2026-04-10

Objetivo:

- localizar links baixaveis exatos em `data.gouv.fr` para as lacunas temporais restantes

## Links confirmados em data.gouv

### SIDE / stocks

#### Stocks d'etablissements par activite (A10)

Pagina do dataset:

- https://www.data.gouv.fr/datasets/stocks-detablissements-par-activite-a10/

Link direto do recurso:

- https://www.data.gouv.fr/api/1/datasets/r/225ce88b-d1c5-4ed8-aac8-ba5aa0a1d20f

Leitura:

- a API do `data.gouv` confirma a familia `DS_SIDE_STOCKS_ET_COM`
- a cobertura temporal declarada no dataset e `2014 -> 2023`
- mas o recurso bruto atualmente exposto aponta para `DS_SIDE_STOCKS_ET_COM_2022_CSV_FR`
- conclusao: o dataset foi confirmado, mas o link exato de `2021` ainda nao foi fechado nesta rodada

#### Stocks d'unites legales par activite (A10)

Pagina do dataset:

- https://www.data.gouv.fr/datasets/stocks-dunites-legales-par-activite-a10

Link direto do recurso:

- https://www.data.gouv.fr/api/1/datasets/r/701c4331-7e1c-491e-a983-4d21337f1826

Leitura:

- a API do `data.gouv` confirma a familia `DS_SIDE_STOCKS_UL_COM`
- a cobertura temporal declarada no dataset e `2014 -> 2023`
- mas o recurso bruto atualmente exposto aponta para `DS_SIDE_STOCKS_UL_COM_2022_CSV_FR`
- conclusao: o dataset foi confirmado, mas o link exato de `2021` ainda nao foi fechado nesta rodada

### FLORES 2023

#### Nombre d'etablissements et effectifs salaries en 17 grands secteurs

Pagina do dataset:

- https://www.data.gouv.fr/datasets/nombre-detablissements-et-effectifs-salaries-en-17-grands-secteurs/

Link direto confirmado pela API do `data.gouv`:

- https://www.data.gouv.fr/api/1/datasets/r/d9283b53-69ce-41c6-ad65-c9dfe697fb83

Leitura:

- a API do `data.gouv` confirma a familia `DS_FLORES_A17`
- o recurso bruto atualmente exposto aponta para `DS_FLORES_A17_2024_CSV_FR`
- conclusao: a familia esta confirmada, mas `FLORES 2023` ainda nao foi fechado com link bruto exato nesta rodada

### BPE 2023

#### Base permanente des equipements

Pagina do dataset:

- https://www.data.gouv.fr/datasets/base-permanente-des-equipements-2

Links diretos dos recursos observados:

- csv: https://www.data.gouv.fr/api/1/datasets/r/dcdcf8fb-acaf-4260-b455-b25e0c7ee003
- zip: https://www.data.gouv.fr/api/1/datasets/r/abfc35ff-8305-43f0-a553-3b549673c002

Leitura:

- a pagina observada informa explicitamente que os dados estao difundidos em geografia ao `1er janvier 2023`
- os recursos sao baixaveis e validos tecnicamente
- porem, a inspecao do conteudo mostrou `Millésime = 2024` e `an = 2024`
- conclusao: o caminho de download foi fechado, mas a integracao como `BPE 2023` fica suspensa por mismatch temporal

## Links uteis, mas secundarios

### FLORES 2023 em 88 grands secteurs

Pagina do dataset:

- https://www.data.gouv.fr/datasets/nombre-detablissements-et-effectifs-salaries-en-88-grands-secteurs

Link direto do recurso:

- https://www.data.gouv.fr/api/1/datasets/r/78cbf92d-4594-4037-a356-06b3cb42d7a3

Leitura:

- util como alternativa ou enriquecimento
- nao substitui o foco principal em `A17`

## O que ainda nao foi fechado nesta rodada

- `SIDE 2021`
- `FLORES 2023`
- `BPE 2023` permanece em observacao por mismatch entre pagina/recurso e conteudo
- `BPE 2021`
- `BPE 2020`

Leitura:

- `data.gouv` confirmou com seguranca as familias `SIDE`, `FLORES` e `BPE`
- porem, para `SIDE` e `FLORES`, os recursos brutos hoje publicados em `data.gouv` apontam respectivamente para `2022` e `2024`
- `BPE 2023` teve o download fechado, mas o conteudo observado aponta para `2024`
- para `BPE 2021` e `BPE 2020`, nao apareceu um recurso nacional equivalente em `data.gouv`

## Conclusao pratica

Com esta rodada, `data.gouv` passa a oferecer caminhos concretos de acesso para:

- a familia `BPE`, ainda com ambiguidade temporal no recurso hoje exposto

E passa a oferecer confirmacao institucional adicional para:

- a familia `SIDE stocks` em `A10`, mas sem fechar o ano `2021`
- a familia `FLORES A17`, mas com recurso bruto hoje apontando para `2024`
