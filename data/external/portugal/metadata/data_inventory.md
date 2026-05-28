# Portugal — Data Inventory (Phase 4 HERALD)

**Date:** 2026-05-28
**Status:** ✅ ingested — panels validated, HPC-ready (tensor framing ⚠️ ver ci-dessous)

---

## Panels produits

| Fichier | Rows | Zones | Years | Description |
|---------|------|-------|-------|-------------|
| `processed/portugal_births_panel_nuts3.csv` | 375 | 25 | 2008–2022 | Births (INE 0009702) reagregados NUTS3 |
| `processed/portugal_stock_panel_nuts3.csv` | 375 | 25 | 2008–2022 | Stock (INE 0009819) directo NUTS3 |
| `processed/portugal_qtensor_births_cae_nuts3.csv` | 3750 | 25 | 2008–2022 | Sector births × CAE→A10 × NUTS3 (**⚠️ NÃO é Q7 effectifs**) |

Zone IDs: `PT_111`, `PT_112`, ..., `PT_300` (25 NUTS3 Portugal continental + ilhas).

---

## Sources

| Composant | Source | Indicateur INE | Licence |
|-----------|--------|---------------|---------|
| Births | INE — demografia empresas | 0009702 (× forma jurídica × município) | CC BY 4.0 |
| Births por setor | INE — demografia empresas | 0009703 (× CAE section × município) | CC BY 4.0 |
| Stock | INE — SCIE | 0009819 (× NUTS3 × Dimensão, "Total") | CC BY 4.0 |

API: `https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd={indicator}&Dim1=S7A{year}&lang=PT`

---

## ⚠️ Tensor framing — CRÍTICO

O ficheiro `portugal_qtensor_births_cae_nuts3.csv` é um **sector_births_tensor**, NÃO um Q7 effectifs.

| | France Q7 | Portugal tensor |
|--|-----------|----------------|
| Conceito | Stock de assalariados (effectifs URSSAF) | Nascimentos de empresas por setor CAE |
| Sinal | Labour supply stock | Entrepreneurial activity flow |
| Equivalência | — | ⚠️ Proxy apenas |

**Regras:**
- Nunca chamar de `Q7 effectifs`, `tensor laboral`, ou `qtensor_jobs` para Portugal.
- Usar label: `sector_births_tensor` ou `sector_births_lag1` em todos os configs HPC.
- Testar como **variante separada** vs NL/BE (que têm employment real).
- KZ = 0 everywhere: esperado (sector financeiro não aparece em nascimentos de empresas INE).

### Q7-equivalente para Portugal

Requer **GEP Quadros de Pessoal** (pessoal ao serviço × CAE × município, fonte MTSSS).
- Séries históricas disponíveis via GEP, mas acesso para anos recentes pode ser formal.
- **Não ingested ainda** — pendente para Phase 4B se necessário para comparação directa.

---

## Notes méthodologiques

### Réagrégation municípios → NUTS3
- Codes município INE: 7 chars (ex. `1111601`). NUT3 = `geocod[:3]` (ex. `111` = Alto Minho).
- 308 municípios → 25 NUTS3 (reagregação por soma).
- Mapping testé: zero municípios perdus, zero NUT3 manquants.

### Fenêtre de modélisation effective
- Births + stock + tensor: 2008–2022
- **Première évaluation: 2009** (lag-1 sur 2008 disponible)

### Ingestion
Script: `src/data/ingest_portugal_panel_nuts3.py`
- Reutiliza raw files `0009702_*.json` e `0009703_*.json` já presentes em `raw/ine/`
- Descarrega `0009819_*.json` directamente ao nível NUTS3
