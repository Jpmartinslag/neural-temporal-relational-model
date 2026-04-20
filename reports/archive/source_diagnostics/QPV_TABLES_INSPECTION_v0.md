# QPV Tables Inspection v0

Data: 2026-04-09

Arquivos de entrada:

- [listeqp2024-cog2024.csv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/listeqp2024-cog2024.csv)
- [liste-correspondance-qp2024-qp2015.csv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/liste-correspondance-qp2024-qp2015.csv)

Artefatos gerados:

- [qpv_2024_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/qpv_2024_communes_v0.csv)
- [qpv_correspondance_2024_2015_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/qpv_correspondance_2024_2015_v0.csv)
- [policy_commune_status_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/policy_commune_status_v0.csv)

Resumo:

- a camada `QPV` veio em arquivos separados por `;`
- o recorte principal de 2024 tem `1584` linhas
- a tabela de correspondencia `2024 -> 2015` tambem tem `1584` linhas
- a integracao canônica adicionou `1584` linhas `QPV` em `policy_commune_status_v0.csv`
- a camada cobre `823` comunas distintas

Leitura metodologica:

- `QPV` entra como camada institucional/social da familia `policy_layers`
- ela nao substitui features preditivas
- seu uso principal futuro sera alimentar o `policy_agent`, o contexto territorial e a explicabilidade

Decisao:

- `QPV` passa a ser camada ativa da familia `policy_layers`
- `FRR/FRR+` e `ZAN` continuam pendentes no registro ate integracao confiavel
