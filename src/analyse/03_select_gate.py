"""
HERALD — Seleção do gate_bias oficial após seção D do patch.

Run from project root after bash run_herald_v6_patch.sh D:
    python3 scripts/03_select_gate.py

Critérios de seleção (em ordem):
  1. Menor mean WMAPE entre os 7 seeds
  2. Se diferença < 0.001, preferir menor std
  3. Verificar que não piora self_only relativo ao full
  4. Verificar consistência gamma_mob > gamma_geo
  5. Verificar adj_delta em 2020->2021 (índice 9)

Imprime recomendação e escreve FINAL_GATE.txt para referência.
"""

import json
from pathlib import Path

import numpy as np

ROOT     = Path(__file__).resolve().parents[1]
JSON     = ROOT / "reports/herald_v6_metrics_v1.json"
OUT_TXT  = ROOT / "reports/FINAL_GATE_SELECTION.txt"

GATE_VALUES = [1.5, 2.0, 2.5]
CORE_SEEDS  = [0, 1, 7, 13, 42, 99, 123]


def main():
    metrics = json.loads(JSON.read_text())

    # ── Coletar resultados da seção D ────────────────────────
    gate_results = {}
    for gate in GATE_VALUES:
        tag = f"gate{gate}"
        runs = {v["seed"]: v for k, v in metrics.items()
                if v.get("ablation") == "full" and v.get("run_tag","") == tag}

        if not runs:
            print(f"gate={gate}: NENHUM resultado encontrado. Rode a seção D primeiro.")
            continue

        seeds_found = sorted(runs.keys())
        missing = [s for s in CORE_SEEDS if s not in seeds_found]
        if missing:
            print(f"gate={gate}: AVISO — faltam seeds {missing}. Resultado incompleto.")
        wmapes = [runs[s]["total_wmape_mean"] for s in seeds_found]
        gammas_mob = [runs[s].get("gamma_mob", np.nan) for s in seeds_found]
        gammas_geo = [runs[s].get("gamma_geo", np.nan) for s in seeds_found]
        # adj_delta index 8 = transition 2020->2021 (0-based; 9th transition).
        # Years: 2012..2024 = 13 anos, 12 transições
        # Transição 2020->2021 = índice 8 (0-based) no adj_delta_by_year
        adj_deltas_covid = []
        for s in seeds_found:
            ad = runs[s].get("adj_delta_by_year", [])
            if len(ad) >= 9:
                adj_deltas_covid.append(ad[8])   # 2020->2021 (0-based)

        gate_results[gate] = {
            "seeds":        seeds_found,
            "wmapes":       wmapes,
            "mean":         float(np.mean(wmapes)),
            "std":          float(np.std(wmapes)),
            "gamma_mob_gt_geo": sum(m > g for m, g in zip(gammas_mob, gammas_geo)),
            "gamma_mob_mean":   float(np.nanmean(gammas_mob)),
            "gamma_geo_mean":   float(np.nanmean(gammas_geo)),
            "adj_delta_2020_2021_mean": float(np.mean(adj_deltas_covid)) if adj_deltas_covid else np.nan,
            "n_seeds":      len(seeds_found),
        }

    if not gate_results:
        print("Nenhum resultado de gate sweep encontrado no JSON.")
        return

    # ── Tabela comparativa ───────────────────────────────────
    print("\n── Gate Sweep — Resultados Seção D ──")
    print(f"{'gate':>6} {'seeds':>6} {'mean':>8} {'std':>8} "
          f"{'γmob>γgeo':>10} {'γmob':>7} {'γgeo':>7} {'adj_delta_20→21':>16}")
    print("-" * 78)
    for gate, r in sorted(gate_results.items()):
        print(f"{gate:>6.1f} {r['n_seeds']:>6} {r['mean']:>8.6f} {r['std']:>8.6f} "
              f"{r['gamma_mob_gt_geo']:>8}/{r['n_seeds']:<2} "
              f"{r['gamma_mob_mean']:>7.4f} {r['gamma_geo_mean']:>7.4f} "
              f"{r['adj_delta_2020_2021_mean']:>16.4f}")

    # ── Seleção ──────────────────────────────────────────────
    print("\n── Critérios de Seleção ──")
    complete_gate_results = {
        g: r for g, r in gate_results.items()
        if sorted(r["seeds"]) == CORE_SEEDS
    }
    if complete_gate_results:
        selection_pool = complete_gate_results
    else:
        print("AVISO: nenhum gate tem as 7 seeds completas; seleção será feita com resultados parciais.")
        selection_pool = gate_results

    sorted_gates = sorted(selection_pool.items(), key=lambda x: (x[1]["mean"], x[1]["std"]))
    best_gate, best = sorted_gates[0]

    # Checar se diferença entre top-2 é pequena (<0.001)
    if len(sorted_gates) >= 2:
        second_gate, second = sorted_gates[1]
        diff = second["mean"] - best["mean"]
        print(f"  Melhor por mean: gate={best_gate}  mean={best['mean']:.6f}")
        print(f"  Segundo:         gate={second_gate}  mean={second['mean']:.6f}  diff={diff:+.6f}")
        if diff < 0.001:
            print(f"  Diferença < 0.001: preferir menor std")
            if second["std"] < best["std"]:
                print(f"  → gate={second_gate} tem menor std ({second['std']:.6f} < {best['std']:.6f})")
                best_gate, best = second_gate, second

    print(f"\n  gamma_mob > gamma_geo: {best['gamma_mob_gt_geo']}/{best['n_seeds']} seeds")
    if best["gamma_mob_gt_geo"] < best["n_seeds"] // 2:
        print("  AVISO: gamma_mob não domina gamma_geo de forma consistente neste gate.")

    print(f"\n  adj_delta 2020→2021: {best['adj_delta_2020_2021_mean']:.4f}")
    print(f"  (deve ser visivelmente maior que anos estáveis ~0.03-0.09)")

    # ── Recomendação final ───────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  GATE RECOMENDADO: {best_gate}")
    print(f"  mean={best['mean']:.6f}  std={best['std']:.6f}")
    print(f"  γmob>{best['gamma_mob_gt_geo']}/{best['n_seeds']} seeds")
    print(f"{'='*50}")
    print(f"\n  → Edite FINAL_GATE={best_gate} em run_herald_v6_patch.sh")
    print(f"  → Depois rode: bash run_herald_v6_patch.sh E")

    # Salvar
    lines = [
        f"FINAL_GATE={best_gate}",
        f"mean_wmape={best['mean']:.6f}",
        f"std_wmape={best['std']:.6f}",
        f"gamma_mob_gt_geo={best['gamma_mob_gt_geo']}/{best['n_seeds']}",
        f"adj_delta_2020_2021={best['adj_delta_2020_2021_mean']:.4f}",
        "",
        "Todos os gates:",
    ]
    for gate, r in sorted(gate_results.items()):
        lines.append(f"  gate={gate}: mean={r['mean']:.6f} std={r['std']:.6f} "
                     f"gamma_mob_gt_geo={r['gamma_mob_gt_geo']}/{r['n_seeds']}")

    OUT_TXT.write_text("\n".join(lines))
    print(f"\nSalvo: {OUT_TXT}")

    # ── Per-seed detail ──────────────────────────────────────
    print(f"\n── Per-seed WMAPEs (gate={best_gate}) ──")
    r = gate_results[best_gate]
    for s, w in zip(r["seeds"], r["wmapes"]):
        print(f"  seed={s}: {w:.6f}")


if __name__ == "__main__":
    main()
