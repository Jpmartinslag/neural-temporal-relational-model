# ZAN Consumption ZE2020 Inspection v0

Data: 2026-04-09

Artefatos:

- [build_zan_consumption_ze2020_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_zan_consumption_ze2020_v0.py)
- [zan_consumption_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zan_consumption_ze2020_v0.csv)
- [zan_consumption_ze2020_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/zan_consumption_ze2020_quality_v0.json)

Regra aplicada:

- agregacao apenas de colunas claramente aditivas
- sem traducao normativa automatica
- sem uso de razoes originais da tabela comunal

Colunas principais agregadas:

- `zan_naf09art24_total`
- `zan_art09act24_total`
- `zan_art09hab24_total`
- `zan_art09mix24_total`
- `zan_art09inc24_total`
- `zan_art09rou24_total`
- `zan_art09fer24_total`
- `zan_artcom0924_total`
- `zan_pop21_total`
- `zan_emp21_total`
- `zan_surfcom2024_total`

Derivados incluidos:

- `zan_artif_per_pop21`
- `zan_artif_per_surface`

Leitura metodologica:

- esta camada ja torna `ZAN` utilizavel no nivel `ZE2020`
- ela ainda nao equivale a uma regra de aceitacao ou rejeicao
- o proximo passo sera definir sinais para agentes e/ou restricoes de conformidade
