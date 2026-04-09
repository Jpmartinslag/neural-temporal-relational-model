# Environment Setup v0

Data: 2026-04-09

Objetivo:

- registrar a base de dependencias do projeto
- tornar a etapa geoespacial reproduzivel

## Dependencias Python iniciais

- `pandas`
- `matplotlib`
- `openpyxl`
- `geopandas`
- `shapely`
- `fiona`
- `pyogrio`

## Justificativa

- `pandas` e `matplotlib` sustentam ingestao tabular e diagnosticos
- `openpyxl` remove o bloqueio atual sobre leitura `.xlsx`
- `geopandas`, `shapely`, `fiona` e `pyogrio` sustentam a camada geoespacial do projeto

## Papel dessas dependencias

- leitura de shapefiles e geopackages
- extracao de geometrias `ZE2020`
- calculo de adjacencia geográfica
- validacao estrutural do grafo
- integracao futura de `ZAN`, `FRR`, `QPV` e outras camadas espaciais

## Decisao

- a stack geoespacial passa a ser dependencia oficial do projeto
- o primeiro grafo nao deve ser implementado sem essa base instalada
