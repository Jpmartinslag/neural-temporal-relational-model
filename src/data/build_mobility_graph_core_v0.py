"""
build_mobility_graph_core_v0.py

Objetivo:
- construir um grafo de mobilidade domicilio-trabalho entre ZE2020 core_v0
- usar a base de fluxos de mobilidade do RP 2021 (origem-destino em nivel comunal)
- agregar fluxos comunais para ZE2020
- produzir matriz de adjacencia [280, 280] como alternativa ao grafo geografico

Fonte:
- base-flux-mobilite-domicile-lieu-travail-2021-csv.zip
  Colunas: CODGEO (comuna residencia), DCLT (comuna trabalho), NBFLUX_C21_ACTOCC15P (fluxo)

Decisao metodologica:
- o grafo geografico atual (adjacencia por fronteira) tem alpha = 1.0 no baseline espacial
  ou seja, nao agrega sinal preditivo sobre persistencia local
- um grafo de mobilidade captura relacoes economicas funcionais entre zonas
  (zonas que trocam trabalhadores tendem a ter dinamicas correlacionadas)
- esta e a proxima hipotese de grafo a testar antes de qualquer STGNN

Regras de construcao:
- fluxo (A -> B) = soma de trabalhadores residindo em ZE2020_A e trabalhando em ZE2020_B
- fluxos intra-zona (A -> A) sao preservados mas nao usados como arestas do grafo
- a matriz e simetrica opcional: mantemos a versao dirigida como primaria
- a versao normalizada usa normalizacao por linha (saida de cada zona soma 1)
- self-loops sao adicionados para compatibilidade com modelos de passagem de mensagem
"""

import json
import pathlib
import zipfile

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]

FLUX_ZIP = ROOT / "data/raw/temporal_depth/rp/base-flux-mobilite-domicile-lieu-travail-2021-csv.zip"
MAPPING_CSV = ROOT / "data/interim/mappings/commune_to_ze2020_2026.csv"
NODES_CSV = ROOT / "data/processed/graph_nodes_ze2020_core_v0.csv"

OUT_EDGES = ROOT / "data/processed/mobility_graph_edges_core_v0.csv"
OUT_ADJ_RAW = ROOT / "data/processed/mobility_adjacency_raw_core_v0.csv"
OUT_ADJ_NORM = ROOT / "data/processed/mobility_adjacency_row_normalized_core_v0.csv"
OUT_NPZ = ROOT / "data/processed/mobility_graph_core_v0.npz"
OUT_JSON = ROOT / "reports/mobility_graph_core_quality_v0.json"
OUT_MD = ROOT / "reports/MOBILITY_GRAPH_CORE_V0.md"


def load_flux():
    with zipfile.ZipFile(FLUX_ZIP) as z:
        fname = [f for f in z.namelist() if f.endswith(".csv")][0]
        with z.open(fname) as f:
            df = pd.read_csv(f, sep=";", dtype={"CODGEO": str, "DCLT": str},
                             low_memory=False)
    # normalizar CODGEO para 5 digitos (alguns chegam como int com 4 ou 5 chars)
    df["CODGEO"] = df["CODGEO"].str.zfill(5)
    df["DCLT"] = df["DCLT"].str.zfill(5)
    return df


def build_ze2020_od(flux, mapping, core_ze):
    """
    Mapeia CODGEO e DCLT para ZE2020 e agrega fluxos.
    Retorna DataFrame com colunas: ze_origin, ze_dest, flux_total.
    Apenas pares onde AMBOS estao em core_ze.
    """
    com2ze = mapping.set_index("CODGEO")["ZE2020"].to_dict()

    flux = flux.copy()
    flux["ze_origin"] = flux["CODGEO"].map(com2ze)
    flux["ze_dest"] = flux["DCLT"].map(com2ze)

    # manter apenas pares com mapeamento valido para o core
    flux = flux.dropna(subset=["ze_origin", "ze_dest"])
    flux = flux[flux["ze_origin"].isin(core_ze) & flux["ze_dest"].isin(core_ze)]

    od = (
        flux.groupby(["ze_origin", "ze_dest"], sort=True)["NBFLUX_C21_ACTOCC15P"]
        .sum()
        .reset_index()
        .rename(columns={"NBFLUX_C21_ACTOCC15P": "flux_total"})
    )
    return od


def build_adjacency(od, core_ze_sorted):
    """
    Constroi matriz de adjacencia [N, N] a partir do OD ZE2020.
    Diagonal (auto-fluxo) e preservada na matriz raw mas zerada nas arestas do grafo.
    """
    n = len(core_ze_sorted)
    ze_idx = {ze: i for i, ze in enumerate(core_ze_sorted)}

    adj = np.zeros((n, n), dtype=np.float64)
    for _, row in od.iterrows():
        i = ze_idx.get(row["ze_origin"])
        j = ze_idx.get(row["ze_dest"])
        if i is not None and j is not None:
            adj[i, j] = row["flux_total"]

    return adj


def row_normalize_with_self_loop(adj):
    """
    Adiciona self-loop e normaliza por linha.
    Cada zona: peso proprio + pesos dos vizinhos somam 1.
    Compativel com modelos de passagem de mensagem (GCN, GraphSAGE, etc.).
    """
    n = adj.shape[0]
    adj_sl = adj.copy()
    # self-loop: diagonal recebe o maximo de outflow por linha (proxy de retencao)
    # ou simplesmente adiciona 1.0 como identidade
    np.fill_diagonal(adj_sl, adj_sl.diagonal() + 1.0)
    row_sum = adj_sl.sum(axis=1, keepdims=True)
    row_sum = np.where(row_sum == 0, 1.0, row_sum)
    return adj_sl / row_sum


def symmetrize(adj):
    """A_sym = (A + A^T) / 2"""
    return (adj + adj.T) / 2.0


def main():
    print("Carregando fluxos de mobilidade...")
    flux = load_flux()
    print(f"  Fluxos brutos: {len(flux):,} pares comunais")

    mapping = pd.read_csv(MAPPING_CSV, dtype=str)
    nodes = pd.read_csv(NODES_CSV, dtype=str)
    core_ze = set(nodes["ze2020"].tolist())
    core_ze_sorted = sorted(core_ze)
    n = len(core_ze_sorted)
    print(f"  Core ZE2020: {n} zonas")

    print("Mapeando comunas para ZE2020 e agregando fluxos...")
    od = build_ze2020_od(flux, mapping, core_ze)

    # remover auto-fluxos para analise de arestas inter-zona
    od_inter = od[od["ze_origin"] != od["ze_dest"]].copy()
    od_intra = od[od["ze_origin"] == od["ze_dest"]].copy()

    print(f"  Pares ZE2020 com fluxo inter-zona: {len(od_inter):,}")
    print(f"  Pares ZE2020 com fluxo intra-zona: {len(od_intra):,}")

    # matriz completa (inclui diagonal)
    adj_raw = build_adjacency(od, core_ze_sorted)
    # matriz apenas inter-zona (diagonal zerada)
    adj_inter = build_adjacency(od_inter, core_ze_sorted)

    # versao simetrica inter-zona
    adj_sym = symmetrize(adj_inter)

    # normalizacao por linha com self-loop sobre matriz simetrica
    adj_norm = row_normalize_with_self_loop(adj_sym)

    # --- metricas de qualidade ---
    # arestas nao nulas inter-zona (sem diagonal)
    n_edges = int((adj_inter > 0).sum())
    n_edges_geo = None  # sera comparado com grafo geografico depois

    # cobertura: quantas zonas tem pelo menos 1 aresta de saida
    zones_with_outflow = int((adj_inter.sum(axis=1) > 0).sum())

    # fluxo total capturado no core vs. fluxo total bruto
    total_flux_core = float(od_inter["flux_total"].sum())
    total_flux_raw = float(flux["NBFLUX_C21_ACTOCC15P"].sum())
    coverage_ratio = total_flux_core / total_flux_raw if total_flux_raw > 0 else 0.0

    # top 5 pares por fluxo
    top5 = od_inter.nlargest(5, "flux_total")[["ze_origin", "ze_dest", "flux_total"]].to_dict(orient="records")

    # grau medio sainte (outflow)
    degree_out_mean = float((adj_inter > 0).sum(axis=1).mean())
    degree_out_median = float(np.median((adj_inter > 0).sum(axis=1)))

    quality = {
        "source": "base-flux-mobilite-domicile-lieu-travail-2021",
        "year": 2021,
        "core_ze_count": n,
        "od_pairs_inter_zone": len(od_inter),
        "od_pairs_intra_zone": len(od_intra),
        "adjacency_edges_nonzero": n_edges,
        "zones_with_outflow": zones_with_outflow,
        "total_flux_core": round(total_flux_core, 1),
        "total_flux_all": round(total_flux_raw, 1),
        "core_flux_coverage_ratio": round(coverage_ratio, 4),
        "mean_out_degree": round(degree_out_mean, 1),
        "median_out_degree": round(degree_out_median, 1),
        "top5_pairs_by_flux": [
            {k: (round(v, 0) if k == "flux_total" else v) for k, v in rec.items()}
            for rec in top5
        ],
        "adjacency_variants": {
            "raw_directed": "mobility_adjacency_raw_core_v0.csv",
            "row_normalized_symmetric_self_loop": "mobility_adjacency_row_normalized_core_v0.csv",
            "npz_package": "mobility_graph_core_v0.npz",
        },
        "note": (
            "Adjacencia dirigida bruta preserva fluxos absolutos. "
            "Versao normalizada e simetrica com self-loop e recomendada para GNN. "
            "Comparar com grafo geografico: baseline espacial com adjacencia de mobilidade "
            "deve ser executado antes de qualquer STGNN."
        ),
    }

    # --- salvar artefatos ---
    od_inter.to_csv(OUT_EDGES, index=False)

    adj_df_raw = pd.DataFrame(adj_inter, index=core_ze_sorted, columns=core_ze_sorted)
    adj_df_raw.to_csv(OUT_ADJ_RAW)

    adj_df_norm = pd.DataFrame(adj_norm, index=core_ze_sorted, columns=core_ze_sorted)
    adj_df_norm.to_csv(OUT_ADJ_NORM)

    np.savez_compressed(
        OUT_NPZ,
        adjacency_raw=adj_inter.astype(np.float32),
        adjacency_symmetric=adj_sym.astype(np.float32),
        adjacency_row_normalized_self_loop=adj_norm.astype(np.float32),
        ze2020_index=np.array(core_ze_sorted),
    )

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2, ensure_ascii=False)

    # --- relatorio ---
    geo_note = "grafo geografico atual: 1486 arestas em 280 nos"
    lines = [
        "# Mobility Graph Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- substituir o grafo geografico estatico por um grafo de mobilidade funcional",
        "- fonte: fluxos domicilio-trabalho em nivel comunal (RP 2021), agregados para ZE2020",
        "- hipotese: zonas que trocam trabalhadores tem dinamicas economicas correlacionadas",
        "",
        "## Motivacao",
        "",
        "O baseline espacial com grafo geografico escolheu `alpha = 1.0` (ignorar vizinhos).",
        "Isso indica que proximidade geografica nao implica correlacao de dinamica economica.",
        "Um grafo de mobilidade captura relacoes funcionais: se trabalhadores de A trabalham em B,",
        "as economias de A e B sao interdependentes, independente de compartilharem fronteira.",
        "",
        "## Fonte",
        "",
        "- `base-flux-mobilite-domicile-lieu-travail-2021-csv.zip`",
        "- par (CODGEO, DCLT): comuna de residencia, comuna de trabalho",
        "- campo de fluxo: `NBFLUX_C21_ACTOCC15P` (ativos ocupados 15+ anos)",
        "- ano: 2021",
        "",
        "## Resultados",
        "",
        f"- pares ZE2020 inter-zona com fluxo: `{quality['od_pairs_inter_zone']:,}`",
        f"- arestas nao nulas na matriz `[280, 280]`: `{quality['adjacency_edges_nonzero']:,}`",
        f"- zonas com pelo menos 1 saida: `{quality['zones_with_outflow']}` / `{n}`",
        f"- cobertura de fluxo (core/total): `{quality['core_flux_coverage_ratio']:.1%}`",
        f"- grau medio de saida: `{quality['mean_out_degree']:.1f}` arestas por zona",
        f"- grau mediano de saida: `{quality['median_out_degree']:.1f}`",
        "",
        f"Comparacao: {geo_note}.",
        "",
        "## Top 5 Pares por Fluxo",
        "",
        "| ZE origem | ZE destino | fluxo (trabalhadores) |",
        "|---|---|---|",
    ]
    for rec in quality["top5_pairs_by_flux"]:
        lines.append(f"| `{rec['ze_origin']}` | `{rec['ze_dest']}` | `{int(rec['flux_total']):,}` |")

    lines += [
        "",
        "## Variantes de Adjacencia",
        "",
        "- `adjacency_raw`: dirigida, valores brutos de fluxo (trabalhadores por par ZE2020)",
        "- `adjacency_symmetric`: media de (A + A^T), nao dirigida",
        "- `adjacency_row_normalized_self_loop`: simetrica + self-loop + normalizacao por linha",
        "  recomendada para modelos de passagem de mensagem (GCN, GraphSAGE, STGNN)",
        "",
        "## Artefatos",
        "",
        "- [mobility_graph_edges_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_graph_edges_core_v0.csv)",
        "- [mobility_adjacency_raw_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_raw_core_v0.csv)",
        "- [mobility_adjacency_row_normalized_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_row_normalized_core_v0.csv)",
        "- [mobility_graph_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_graph_core_v0.npz)",
        "",
        "## Decisao",
        "",
        "- o grafo de mobilidade esta pronto para ser usado no baseline espacial",
        "- proximo passo: repetir o baseline espacial (persistencia vs. media ponderada por mobilidade)",
        "  usando `adjacency_row_normalized_self_loop` no lugar do grafo geografico",
        "- apenas se o grafo de mobilidade mostrar ganho sobre persistencia e que o grafo",
        "  sera tratado como sinal preditivo confirmado",
        "",
        "## Proxima Etapa",
        "",
        "- avaliar baseline espacial com grafo de mobilidade",
        "- comparar: persistencia, media-vizinhos-geo, media-vizinhos-mobilidade",
        "- registrar decisao sobre qual grafo usar no pacote tensorial final",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("=" * 60)
    print("MOBILITY GRAPH — CORE v0")
    print("=" * 60)
    print(f"Pares inter-zona com fluxo : {quality['od_pairs_inter_zone']:,}")
    print(f"Arestas [280x280]          : {quality['adjacency_edges_nonzero']:,}")
    print(f"Zonas com outflow          : {quality['zones_with_outflow']}/{n}")
    print(f"Cobertura fluxo            : {quality['core_flux_coverage_ratio']:.1%}")
    print(f"Grau medio saida           : {quality['mean_out_degree']:.1f}")
    print()
    print("Top 5 pares por fluxo:")
    for rec in quality["top5_pairs_by_flux"]:
        print(f"  {rec['ze_origin']} -> {rec['ze_dest']}: {int(rec['flux_total']):,} trabalhadores")
    print()
    print("Artefatos salvos:")
    for p in [OUT_EDGES, OUT_ADJ_RAW, OUT_ADJ_NORM, OUT_NPZ, OUT_JSON, OUT_MD]:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
