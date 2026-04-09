# Consistency Review v0

Data: 2026-04-09

Objetivo:

- revisar coerencia territorial, temporal e estrutural do pipeline atual
- identificar incoerencias que poderiam custar caro mais tarde
- registrar o estado real antes de avancar para visualizacao e grafo

## Escopo revisado

- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)
- [panel_zones_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/panel_zones_v0.csv)
- [population_history_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/population_history_ze2020_v0.csv)
- [zan_consumption_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zan_consumption_ze2020_v0.csv)
- [policy_commune_status_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/policy_commune_status_v0.csv)

## O que foi corrigido nesta revisao

- a extração `QPV` foi corrigida para usar parser CSV real com `;`
- a correspondencia `QPV 2024 -> 2015` voltou a carregar corretamente
- linhas multi-comuna de `QPV` foram excluidas temporariamente da camada comunal canônica
- o historico `ZRR` foi sanitizado para remover linhas de legenda que tinham entrado como pseudo-comunas
- a reconstrucao de `policy_commune_status_v0.csv` foi refeita em sequencia, evitando corrupcao por execucao paralela

## Estado consistente hoje

### Cobertura `ZE2020`

- `zones_master`: `306` zonas
- `panel_zones`: `306` zonas
- `population_history_ze2020`: `306` zonas
- `zan_consumption_ze2020`: `305` zonas

Leitura:

- a unica zona ausente em `ZAN` agregado e `0601 / Mayotte`
- isso esta coerente com a anomalia estrutural ja conhecida

### Painel temporal

- anos presentes: `2021`, `2022`, `2023`, `2024`
- `306` linhas por ano
- `1220` linhas elegiveis para treino no recorte atual

Leitura:

- o formato `zone-year` esta consistente
- o painel ainda e minimo, mas estruturalmente valido

### `policy_layers`

- `policy_commune_status_v0.csv`: `433235` linhas
- `ZRR`: `431862`
- `QPV`: `1373`
- `0` linhas com `codgeo` invalido apos a correcao

Leitura:

- a camada canônica de politica voltou a um estado estrutural limpo
- `QPV` agora esta consistente como camada comunal simples

## Incoerencias residuais que continuam abertas

### 1. `QPV` multi-comuna ainda nao foi explodido

Situacao:

- o arquivo bruto tem `1584` linhas de correspondencia
- a camada comunal `QPV` canônica ficou com `1373` linhas
- a diferenca vem de linhas em que um mesmo `QPV` referencia varias comunas no mesmo campo bruto

Impacto:

- a camada `QPV` atual esta limpa
- mas ainda nao representa todos os casos multi-comuna

Decisao:

- manter fora da camada canônica por enquanto
- tratar depois com uma regra explicita de explode comunal

### 2. `ZAN` ainda nao virou sinal de agente

Situacao:

- `ZAN` ja existe em comuna e em `ZE2020`
- mas ainda nao foi traduzida em regra de conformidade, score ou alerta

Impacto:

- a camada ja e utilizavel analiticamente
- mas ainda nao esta operacional para o modulo de agentes

### 3. `ZRR` ainda tem fragilidade de reprodutibilidade na extracao bruta

Situacao:

- o script [extract_zrr_tables_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_zrr_tables_v0.py) ainda depende de `xlsx` temporario em `/tmp`
- a camada atual foi saneada e esta boa
- mas a reproducao completa a partir do bruto ainda nao esta fechada em caminho 100% local do repositorio

Impacto:

- o dado atual esta limpo
- a reproducao bruta ainda precisa ser endurecida

## Diagnostico final

Estado geral:

- bom para continuar
- sem incoerencia estrutural critica aberta nos datasets canônicos principais

Risco residual real:

- `QPV` multi-comuna incompleto
- reproducao bruta `ZRR` ainda nao totalmente fechada
- `ZAN` ainda sem traducao para regras/sinais de agente

## Proximo passo coerente

1. abrir visualizacao diagnostica do que ja temos
2. usar `zones_master`, `population_history_ze2020` e `zan_consumption_ze2020` como base principal
3. manter `policy_layers` como contexto institucional limpo
4. depois construir o primeiro grafo espacial `ZE2020`
