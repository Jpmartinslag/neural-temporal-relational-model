# Policy Download Organization v0

Data: 2026-04-09

Objetivo:

- tirar os downloads de politica do topo do repositorio
- organizar os arquivos brutos por subfamilia institucional
- registrar essa organizacao nos artefatos de projeto

## Estrutura criada

- [data/raw/policy/zrr](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zrr)
- [data/raw/policy/frr](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/frr)
- [data/raw/policy/qpv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv)
- [data/raw/policy/zan](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan)
- [data/raw/policy/legal](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/legal)

## Arquivos organizados

### ZRR

- [diffusion-zonages-historique-zrr-2019.xls](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zrr/diffusion-zonages-historique-zrr-2019.xls)
- [diffusion-zonages-zrr-cog2021.xls](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zrr/diffusion-zonages-zrr-cog2021.xls)

### FRR

- [dataset-1775678390572.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/frr/dataset-1775678390572.zip)

### QPV

- [liste-1514qp2015.xlsx](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/liste-1514qp2015.xlsx)
- [liste-correspondance-qp2024-qp2015.csv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/liste-correspondance-qp2024-qp2015.csv)
- [listeqp2024-cog2024.csv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/listeqp2024-cog2024.csv)
- [qp-politiquedelaville-shp.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/qp-politiquedelaville-shp.zip)
- [qpv-2024-geojson.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/qpv-2024-geojson.zip)
- [qpv-2024-gpkg.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/qpv-2024-gpkg.zip)
- [qpv-2024-shp.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/qpv-2024-shp.zip)
- [qpv-2024.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/qpv-2024.zip)

### ZAN

- [conso2009-2024-resultats-com.csv](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/conso2009-2024-resultats-com.csv)
- [description-indicateurs-2009-2024.pdf](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/description-indicateurs-2009-2024.pdf)
- [obs-artif-conso-com-2009-2024.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/obs-artif-conso-com-2009-2024.zip)
- [obs-artif-conso-com-2009-2024-971.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/obs-artif-conso-com-2009-2024-971.zip)
- [obs-artif-conso-com-2009-2024-972.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/obs-artif-conso-com-2009-2024-972.zip)
- [obs-artif-conso-com-2009-2024-973.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/obs-artif-conso-com-2009-2024-973.zip)
- [obs-artif-conso-com-2009-2024-974.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/obs-artif-conso-com-2009-2024-974.zip)
- [obs-artif-conso-com-2009-2024-carroyage-lea.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/obs-artif-conso-com-2009-2024-carroyage-lea.zip)

Sous-dossiers ZAN:

- [data/raw/policy/zan/ocs_ge](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/ocs_ge)
- [data/raw/policy/zan/pnb_action7](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/pnb_action7)

Nouveaux fichiers notables:

- [pnb_action7-selected.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/pnb_action7/pnb_action7-selected.zip)
- jeux `OCS-GE-ARTIFICIALISATION_2-0_DIFF-*` dans [data/raw/policy/zan/ocs_ge](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/zan/ocs_ge)

### Legal

- [joe_20240620_0144_0051.pdf](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/legal/joe_20240620_0144_0051.pdf)

## Decisao

- o topo do repositorio fica reservado ao pipeline vivo e ao acervo principal herdado
- os downloads brutos de politica passam a ficar centralizados em `data/raw/policy`
- a familia `policy_layers` agora tem separacao clara entre bruto, interim e design canonico
- os nouveaux jeux `OCS GE` et `PNB Action7` ficam registrados dentro do bloco `ZAN`
