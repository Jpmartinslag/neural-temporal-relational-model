# Scan Workflow v0

Data: 2026-04-09

Objetivo:

- permitir um scan completo e reprodutivel do repositorio
- gerar um pacote unico para revisao posterior

## Script

- [scan_full_repository_v0.sh](/home/jpdark/Downloads/project_recomm/dataset/src/data/scan_full_repository_v0.sh)

## O que ele gera

Diretorio:

- [scan_output](/home/jpdark/Downloads/project_recomm/dataset/scan_output)

Bundle:

- [scan_output_bundle.tar.gz](/home/jpdark/Downloads/project_recomm/dataset/scan_output_bundle.tar.gz)

Principais artefatos:

- `files_all.txt`
- `project_size.txt`
- `files_by_size.tsv`
- `sha256_all.txt`
- `zip_files.txt`
- `zip_listing.txt`
- `zip_test.txt`
- `csv_files.txt`
- `csv_preview.txt`
- `parquet_schema.txt`
- `excel_sheets.txt`
- `territorial_temporal_hits.txt`
- `scan_run_info.txt`

## Como rodar

No diretorio do projeto:

```bash
bash src/data/scan_full_repository_v0.sh
```

O progresso passa a aparecer no proprio terminal durante a execucao.

Tambem fica salvo em:

- `scan_output/progress.log`

## Observacoes da execucao

- a versao atual do script ignora `.git`, `.venv`, `scan_output` e o bundle anterior
- isso evita poluicao do resultado com dependencias do ambiente

## Como usar depois

Os arquivos mais uteis para revisao analitica sao:

- `zip_test.txt`
- `csv_preview.txt`
- `parquet_schema.txt`
- `excel_sheets.txt`
- `files_by_size.tsv`

Se o scan levar muito tempo, isso e esperado. O objetivo aqui e cobertura, nao velocidade.
