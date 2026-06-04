
================================================================================
Phase 4E-C — Job IDs HPC
================================================================================

  STAMP:  20260603_230709
  Submit: 2026-06-03T23:07:12

  Job array  País  JobName           State      ExitCode
  ---------  ----  ----------------  ---------  --------
  7426150    FR    herald-phase4ec   COMPLETED  0:0 (10/10)
  7426151    NL    herald-phase4ec   COMPLETED  0:0 (10/10)
  7426152    BE    herald-phase4ec   COMPLETED  0:0 (10/10)
  7426153    PT    herald-phase4ec   COMPLETED  0:0 (10/10)

  Constraint: #SBATCH --constraint="mpi" (linha 11 do sbatch)
  Nós problemáticos: nenhum — todos em hpcgpu/pascalgpu/hpcdgx/hpcnode/iccfgpu

================================================================================
Phase 4E-C [FR] herald_phase4e_c_fr_20260603_230709_r1
================================================================================
configs=6 expected=6 jsons=60
label                        mean      std   n      Δc0 macro_set      falsif
-----------------------------------------------------------------------------
c2_labor                 0.098736 0.008558  10 -0.004852 eu_labor       False
c3_esi                   0.100187 0.005756  10 -0.003401 eu_esi         False
c0_winner_4e_b           0.103588 0.008346  10 +0.000000 none           False
c5_all_eu_perm           0.111119 0.008241  10 +0.007532 eu_all_perm    True
c1_gdp                   0.121138 0.021247  10 +0.017550 eu_gdp         False
c4_all_eu                0.122364 0.011606  10 +0.018776 eu_all         False

C0 vs Phase 4E-B baseline: 0.103588 vs 0.1031  Δ=+0.000488  [OK]

--- Victory criteria ---
  Configs beating c0 by >1%: []
  Configs degrading c0 by >1%: ['c1_gdp', 'c4_all_eu']
  C5 permuted Δc0=+0.007532  [OK]

================================================================================
Phase 4E-C [NL] herald_phase4e_c_nl_20260603_230709_r1
================================================================================
configs=6 expected=6 jsons=60
label                        mean      std   n      Δc0 macro_set      falsif
-----------------------------------------------------------------------------
c2_labor                 0.098565 0.006235  10 -0.003288 eu_labor       False
c0_winner_4e_b           0.101853 0.007966  10 +0.000000 none           False
c5_all_eu_perm           0.115183 0.006465  10 +0.013330 eu_all_perm    True
c3_esi                   0.117134 0.007388  10 +0.015281 eu_esi         False
c1_gdp                   0.127413 0.012507  10 +0.025560 eu_gdp         False
c4_all_eu                0.132581 0.015078  10 +0.030728 eu_all         False

C0 vs Phase 4E-B baseline: 0.101853 vs 0.1017  Δ=+0.000153  [OK]

--- Victory criteria ---
  Configs beating c0 by >1%: []
  Configs degrading c0 by >1%: ['c3_esi', 'c1_gdp', 'c4_all_eu']
  C5 permuted Δc0=+0.013330  [OK]

================================================================================
Phase 4E-C [BE] herald_phase4e_c_be_20260603_230709_r1
================================================================================
configs=6 expected=6 jsons=60
label                        mean      std   n      Δc0 macro_set      falsif
-----------------------------------------------------------------------------
c4_all_eu                0.137765 0.005904  10 -0.011047 eu_all         False
c5_all_eu_perm           0.144007 0.007509  10 -0.004805 eu_all_perm    True
c2_labor                 0.145102 0.008686  10 -0.003710 eu_labor       False
c3_esi                   0.145508 0.005385  10 -0.003304 eu_esi         False
c1_gdp                   0.148719 0.006374  10 -0.000093 eu_gdp         False
c0_winner_4e_b           0.148812 0.006462  10 +0.000000 none           False

C0 vs Phase 4E-B baseline: 0.148812 vs 0.1488  Δ=+0.000012  [OK]

--- Victory criteria ---
  Configs beating c0 by >1%: ['c4_all_eu']
  Configs degrading c0 by >1%: []
  C5 permuted Δc0=-0.004805  [OK]

================================================================================
Phase 4E-C [PT] herald_phase4e_c_pt_20260603_230709_r1
================================================================================
configs=6 expected=6 jsons=60
label                        mean      std   n      Δc0 macro_set      falsif
-----------------------------------------------------------------------------
c1_gdp                   0.185453 0.005851  10 -0.042756 eu_gdp         False
c4_all_eu                0.200941 0.008720  10 -0.027269 eu_all         False
c3_esi                   0.205606 0.008162  10 -0.022603 eu_esi         False
c5_all_eu_perm           0.210768 0.008772  10 -0.017442 eu_all_perm    True
c2_labor                 0.227180 0.006362  10 -0.001030 eu_labor       False
c0_winner_4e_b           0.228209 0.010970  10 +0.000000 none           False

C0 vs Phase 4E-B baseline: 0.228209 vs 0.2286  Δ=-0.000391  [OK]

--- Victory criteria ---
  Configs beating c0 by >1%: ['c1_gdp', 'c4_all_eu', 'c3_esi']
  Configs degrading c0 by >1%: []
  C5 permuted Δc0=-0.017442  [WARN: permuted EU beats c0 by >1% — spurious regularization]

================================================================================
Cross-country EU signal summary
================================================================================

  c1_gdp         NOT consistent (<2 countries)
    fr:+0.0176  nl:+0.0256  be:-0.0001  pt:-0.0428
    Improving: ['pt']
    Degrading: ['fr', 'nl']

  c2_labor       NOT consistent (<2 countries)
    fr:-0.0049  nl:-0.0033  be:-0.0037  pt:-0.0010

  c3_esi         NOT consistent (<2 countries)
    fr:-0.0034  nl:+0.0153  be:-0.0033  pt:-0.0226
    Improving: ['pt']
    Degrading: ['nl']

  c4_all_eu      CONSISTENT (>=2 countries)
    fr:+0.0188  nl:+0.0307  be:-0.0110  pt:-0.0273
    Improving: ['be', 'pt']
    Degrading: ['fr', 'nl']
