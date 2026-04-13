# Target Proxy vs Official SIDE Audit Decision v0

Data: 2026-04-13

## Objetivo

Registrar a decisao metodologica apos comparar o target proxy atual com as criacoes oficiais `SIDE` comunais agregadas para `ZE2020`.

## Resultado Da Auditoria

Fonte oficial inspecionada:

- `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip`
- `DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip`

Cobertura confirmada:

- anos: `2012-2024`
- nivel original: `COM`
- nivel agregado no projeto: `ZE2020`
- zonas sobrepostas com o target proxy: `280`
- observacoes sobrepostas: `3640`

Comparacao com o target proxy atual:

- correlacao proxy vs `SIDE` empresas: `0.9546`
- correlacao proxy vs `SIDE` estabelecimentos: `0.9559`
- mediana proxy / `SIDE` empresas: `1.9510`
- mediana proxy / `SIDE` estabelecimentos: `1.7363`

## Leitura

O proxy atual preserva bem a ordenacao e a dinamica espacial do fenomeno, mas esta sistematicamente acima da fonte oficial em nivel.

Isso significa que o proxy atual nao deve ser tratado como ground truth final. Ele pode continuar util como serie auxiliar, sanity check ou variavel de auditoria, mas a fonte oficial `SIDE` deve assumir prioridade para o target formal.

## Decisao

Decisao atual:

- promover `SIDE` estabelecimentos oficiais agregados por `ZE2020` como candidato principal de target
- manter `SIDE` empresas como target alternativo para sensibilidade
- manter o proxy atual como comparacao auxiliar, nao como alvo principal definitivo
- nao usar a mesma serie `SIDE` como feature para prever ela mesma sem defasagem temporal clara

## Racional

Para uma aplicacao de recomendacao economica auditavel, o target principal deve ser o mais proximo possivel de uma fonte oficial e reprodutivel.

O `SIDE` comunal atende melhor a esse criterio que o proxy derivado. O proxy continua importante porque mostrou alta correlacao com o oficial, mas sua diferenca de escala criaria risco de interpretacao em politicas publicas.

## Proximo Passo Tecnico

Reconstruir, em uma etapa posterior, um pacote alternativo usando:

- `y_main = side_establishment_creations_official`
- `y_sensitivity = side_enterprise_creations_official`
- `y_proxy_audit = target_proxy_establishment_creations_year`

Esse rebuild deve gerar novos artefatos com nome explicito, por exemplo:

- `target_side_establishments_annual_core_v0.csv`
- `graph_model_target_side_panel_core_v0.csv`
- `stgnn_tensor_package_side_target_core_v0.npz`

## Restricao

Ainda nao avancar para arquitetura complexa antes de reexecutar os baselines com o target oficial `SIDE`.
