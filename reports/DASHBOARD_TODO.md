# Dashboard HERALD — O que falta fazer

Data: 2026-05-27

## Em andamento agora

| Item | Estado | Detalhe |
|---|---|---|
| Phase 3E — arquitetura q_tensor | **concluída** | 240/240 runs OK; candidato atual `Q7_effectifs_lag1` |
| Dashboard | **precisa atualizar** | trocar candidato principal para `HERALD no flags Q7` |

---

## Próxima ação

### Atualizar comparação principal

O dashboard deve comparar, em uma tabela e nos gráficos principais:

- `HERALD no flags Q7` (`Q7_effectifs_lag1`) — candidato atual;
- `HERALD no flags Q0` (`Q0_real`) — referência q_tensor completa;
- `HERALD flags clean` — comparação justa com flags manuais e entradas limpas;
- `HERALD flags extended` — controle histórico com entradas ampliadas;
- Ridge AR, ARIMA, LSTM, DCRNN, Dynamic STGNN.

Mensagem curta esperada:

```text
HERALD no flags Q7 usa SIDE limpo e o canal URSSAF effectifs com atraso de um ano.
Ele não vence todos os números, mas é o compromisso mais estável e simples da Phase 3E.
```

---

## Dados em falta no dashboard atual

### Phase 3E por zona e A10

- Verificar se os CSVs/JSONs de `Q7_effectifs_lag1` têm predições por zona, por ano e por A10.
- Se faltarem artefatos A10 completos, usar os valores globais do audit e marcar o detalhe A10 como
  pendente de regeneração.

### HERALD flags clean

- Manter separado de `HERALD flags extended`.
- `flags clean` é a comparação justa.
- `flags extended` é controle histórico com mais entradas; não deve ser tratado como o mesmo modelo.

### KPI Gain HERALD vs Ridge
- **Estado actual**: 63.8% ✅ (corrigido — era 61.5% com valor Ridge errado)
- **Ridge AR 2025**: 0.036085 ✅ (strict exante no_source_flags)

### DCRNN e STGNN 2025
- **Estado actual**: preenchido ✅ (0.031156 e 0.031134 — strict exante no_source_flags)
- **Nota**: estes valores não têm separação por seed (determinísticos)

---

## Melhorias de dashboard desejadas (prioridade média)

| Item | Descrição |
|---|---|
| Tabela de comparação completa | Uma tabela única: todos os modelos × WMAPE 2021, médio, 2025, A10, std |
| WMAPE 2021 em KPI separado | O fold difícil não está em destaque; só visível no gráfico de linhas |
| Intervalos de confiança | Envelope das 10 seeds no gráfico real vs previsto |
| Secção 6 — contexto para leigo | Mostrar regime aprendido sem prometer descoberta econômica completa |
| Nota sobre flags | Explicar `flags clean` vs `flags extended` sem usar termos pejorativos |

---

## Dados externos que precisamos rever

| Dataset | Estado | Ação |
|---|---|---|
| INSEE SIDE 2025 | Integrado | ok |
| Webstat BdF (CONJ, GSTIX) | Ficheiros descargados localmente | Phase 2H mostrou que não melhoram — não incluir no candidato principal |
| Atlas IAT | Auditado, standby | Não incluir até ter plano de uso metodologicamente limpo |
| Graphe mobilité 2021+ | Estático v0 | Verificar se precisa de actualização para a previsão 2026 |

---

## Não fazer (decisões tomadas)

- Macro INSEE/BdF nas entradas do modelo — testado Phase 2H, rejeitado
- Mais de 2 features SIDE — testado Phase 2I, `lag1_growth1y` vence
- Procurar novas features antes de apresentar a comparação Phase 3E
- Chamar `Q7` de prova de sinal local ZE forte; a falsificação espacial ainda é fraca
