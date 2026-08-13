# T05 — Prediction and relational recovery are separate questions

The two halves of this table answer different questions and a method may do well at one and nothing at the other. The decisive column is 'AUPRC S0': a method scoring in the scenario built with no mechanism has reproduced something it was given. Required for recovery: edge F1 ≥ prevalence + 0.10, dense correlation ≥ 0.30, stability ≥ 0.90, AUPRC above prevalence in S1 and no structure in S0. No method passes.

| méthode | skill vs persistance | edge F1 | corr. dense | AUPRC S1 | AUPRC S0 | prévalence | S0 propre | récupération soutenue |
|---|---|---|---|---|---|---|---|---|
| Persistance | +0.0000 | — | — | — | — | — | non | non |
| Granger graphique (Lasso) | +0.0001 | 0.702 | +0.0028 | 0.6983 | 0.7009 | 0.70 | oui | non |
| HERALD @128 | -0.0046 | 0.717 | +0.1159 | 0.7294 | 0.7269 | 0.70 | non | non |
| HERALD @32 | -0.0087 | 0.715 | +0.1160 | 0.7257 | 0.7216 | 0.70 | non | non |
| HERALD @64 | -0.0170 | 0.715 | +0.1118 | 0.7228 | 0.7254 | 0.70 | non | non |
| NRI | -0.0494 | 0.701 | -0.0049 | 0.7005 | 0.7027 | 0.70 | oui | non |
| MTGNN | -0.1977 | 0.705 | +0.0432 | 0.7147 | 0.7079 | 0.70 | oui | non |
