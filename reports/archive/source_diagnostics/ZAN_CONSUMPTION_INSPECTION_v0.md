# ZAN Consumption Inspection v0

Data: 2026-04-09

Arquivo de entrada:

- [conso2009-2024-resultats-com.csv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/conso2009-2024-resultats-com.csv)

Artefatos gerados:

- [extract_zan_consumption_communes_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_zan_consumption_communes_v0.py)
- [zan_consumption_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/zan_consumption_communes_v0.csv)
- [zan_consumption_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/zan_consumption_quality_v0.json)

Resumo:

- tabela comunal `ZAN` com `34905` linhas
- `138` colunas
- cobertura temporal nominal `2009-2024`
- a camada e quantitativa, nao binaria

Leitura metodologica:

- `ZAN` nao deve ser forcada imediatamente em `policy_commune_status_v0`
- nesta fase, ela entra como tabela quantitativa interim da familia `policy_layers`
- o passo seguinte sera derivar sinais ou regras de conformidade a partir dela

Decisao:

- `ZAN` passa a ter camada interim ativa
- a agregacao para `ZE2020` e a traducao para sinais de agente ficam para a proxima rodada
