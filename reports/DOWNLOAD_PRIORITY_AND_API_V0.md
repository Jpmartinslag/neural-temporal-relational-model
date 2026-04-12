# Download Priority and API v0

Data: 2026-04-09

Objetivo:

- listar o que deve ser buscado primeiro para aprofundar a profundidade temporal
- distinguir claramente o que tem API confirmada do que ainda nao tem API confirmada

## Prioridade de coleta

### 1. RP 2021

- buscar primeiro:
  - `DS_RP_POPULATION_PRINC_2021`
  - `DS_RP_EMPLOI_LR_COMP_2021`
  - `DS_RP_EMPLOI_LT_PRINC_2021`
  - `DS_RP_NAVETTES_PRINC_2021`

API:

- **nao confirmada nesta rodada**

Base oficial confirmada:

- `RP 2021` esta oficialmente difundido e cobre tambem `zones d'emploi`
- fonte:
  - https://www.insee.fr/fr/metadonnees/source/operation/s2150/bases-donnees-ligne
  - https://www.insee.fr/fr/metadonnees/source/operation/s2150/coherence-comparabilite

### 2. SIDE 2020-2021

- buscar primeiro:
  - `DS_SIDE_STOCKS_ET_COM_2021`
  - `DS_SIDE_STOCKS_UL_COM_2021`
  - se existir:
    - `DS_SIDE_STOCKS_ET_COM_2020`
    - `DS_SIDE_STOCKS_UL_COM_2020`

API:

- **provavel via Melodi, mas nao confirmada nesta rodada**

Base oficial:

- a familia `DS_SIDE_*` continua sendo o bloco central para aprofundar a dinamica economica territorial

### 3. BPE 2023

- buscar:
  - `DS_BPE_2023`
  - e, se necessario, a evolucao associada

API:

- **confirmada em fonte oficial**

Base oficial:

- a pagina oficial da `BPE 2023` diz explicitamente que os jogos podem ser baixados em `csv`, `par API` e consultados em explorador
- fonte:
  - https://www.insee.fr/fr/metadonnees/source/operation/s2155/bases-donnees-ligne

API candidata:

- endpoint Melodi esperado: `https://api.insee.fr/melodi/data/DS_BPE_2023`

### 4. BPE 2021 e BPE 2020

- buscar:
  - `DS_BPE_2021`
  - `DS_BPE_2020`

API:

- **alta plausibilidade, mas nao confirmada nesta rodada**

Base oficial:

- as bases anuais anteriores da BPE possuem paginas oficiais de diffusion
- fontes:
  - https://www.insee.fr/fr/metadonnees/source/operation/s2077/bases-donnees-ligne
  - https://www.insee.fr/fr/metadonnees/source/operation/s2027/bases-donnees-ligne

### 5. Filosofi 2020

- buscar:
  - `DS_FILOSOFI_CC_2020`

API:

- **nao confirmada nesta rodada**

Base oficial:

- `Filosofi 2020` esta oficialmente documentado e difundido
- fonte:
  - https://www.insee.fr/fr/metadonnees/source/operation/s2105/processus-statistique

### 6. Flores 2023

- buscar:
  - `DS_FLORES_A17_2023`
  - ou a tabela equivalente oficialmente difundida ate a comuna

API:

- **nao confirmada nesta rodada**

Base oficial:

- a pagina oficial `Flores 2023` confirma a disponibilizacao de jogos de dados e tabelas Excel em download ate a comuna
- fonte:
  - https://www.insee.fr/fr/metadonnees/source/operation/s2220/publications

## Regra operacional

Na proxima rodada de coleta:

1. quando a pagina oficial confirmar `par API`, priorizar tentativa via Melodi
2. quando a API nao estiver confirmada, baixar via jogo de dados oficial do Insee
3. manter no journal a diferenca entre:
   - `api confirmed`
   - `api inferred`
   - `download only confirmed`
