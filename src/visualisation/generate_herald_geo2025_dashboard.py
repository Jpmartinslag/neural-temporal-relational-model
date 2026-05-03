#!/usr/bin/env python3
"""Tableau de bord HERALD geo2025 — version 2 corrigée."""
import json, glob, os, warnings, base64
import numpy as np, pandas as pd
from collections import defaultdict
warnings.filterwarnings("ignore")

# Embedder Plotly localmente (funciona offline, sem internet)
PLOTLY_JS_PATH = os.path.expanduser(
    "~/.local/lib/python3.10/site-packages/plotly/package_data/plotly.min.js"
)
if os.path.exists(PLOTLY_JS_PATH):
    with open(PLOTLY_JS_PATH, "r", encoding="utf-8") as _f:
        PLOTLY_INLINE = "<script>" + _f.read() + "</script>"
else:
    PLOTLY_INLINE = '<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>'

ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE  = os.path.join(ROOT,"hpc_results","herald_semi_total_253_geo2025")
JOB0  = os.path.join(BASE,"baselines_v3_v6_stgnn")
CACHE = os.path.join(BASE,"reports","figures","dashboard_data_cache.json")
OUT   = os.path.join(BASE,"reports","figures","herald_geo2025_final_dashboard.html")

class NpEnc(json.JSONEncoder):
    def default(self,o):
        if isinstance(o,np.integer): return int(o)
        if isinstance(o,np.floating): return float(o)
        if isinstance(o,np.ndarray): return o.tolist()
        return super().default(o)
def J(o): return json.dumps(o,cls=NpEnc)

# ── Nomes legíveis ────────────────────────────────────────────────────────────
NICE = {
    "total_h64_no_semi":                            "HERALD V6 h64",
    "total_h32_no_semi":                            "HERALD V6 h32",
    "total_h64_semi_mask0.0_control":               "Semi — contrôle mask0.0",
    "total_h64_semi_mask0.10_random":               "Semi — mask0.10 aléatoire",
    "total_h64_semi_mask0.10_random_warmup0":       "Semi — mask0.10 sans warmup",
    "total_h64_semi_mask0.30_random":               "Semi — mask0.30 aléatoire",
    "total_h64_semi_mask0.05_random":               "Semi — mask0.05 aléatoire",
    "total_h64_semi_mask0.15_random":               "Semi — mask0.15 aléatoire",
    "total_h64_semi_mask0.20_random":               "Semi — mask0.20 aléatoire",
    "total_h64_semi_mask0.10_block":                "Semi — mask0.10 bloc",
    "total_h64_semi_mask0.10_spatial_block":        "Semi — mask0.10 bloc spatial ⚠",
    "total_h64_semi_mask0.20_block":                "Semi — mask0.20 bloc",
    "total_h64_semi_mask0.20_spatial_block":        "Semi — mask0.20 bloc spatial ⚠",
    "total_h32_semi_mask0.10_random":               "Semi — h32 mask0.10",
    "total_h64_semi_mask0.10_random_lam0.01_total": "Semi — λ=0.01 total",
    "total_h64_semi_mask0.10_random_lam0.05_total": "Semi — λ=0.05 total",
    "total_h64_semi_mask0.10_random_lam0.10_total": "Semi — λ=0.10 total",
    "total_h64_semi_mask0.10_random_lam0.05_a10":   "Semi — λ=0.05 secteurs A10",
    "total_h64_semi_mask0.10_random_lam0.05_total_a10": "Semi — λ=0.05 total+A10",
}
def nice(tag): return NICE.get(tag, tag.replace("total_","").replace("_"," "))

# ── Chargement données ────────────────────────────────────────────────────────
print("Chargement…")
def lj(p): return json.load(open(p))

cache     = lj(CACHE)
ZONE_V6   = cache["zone_v6"]
ZONE_SEMI = cache["zone_semi"]
GRAPH     = cache["graph_data"]
SEC_MAP   = cache["sector_map"]
RIDGE_YR  = cache["ridge_per_yr"]
ZE_INFO   = cache["ze_info"]

# Métriques agrégées
semi_runs = {}
for f in sorted(glob.glob(os.path.join(BASE,"*/reports/herald_semi_total_metrics_v1.json"))):
    for k,v in lj(f).items():
        if k not in semi_runs: semi_runs[k] = v
v6_runs = lj(os.path.join(JOB0,"reports","herald_v6_total_metrics_v1.json"))
v3_runs = lj(os.path.join(JOB0,"reports","herald_v3_total_metrics_v1.json"))
tb_data = lj(os.path.join(JOB0,"temporal_baselines","reports","final_temporal_baselines_metrics_v1.json"))
precovid= {}
for f in sorted(glob.glob(os.path.join(BASE,"*/reports/herald_semi_total_precovid_metrics_v1.json"))):
    for k,v in lj(f).items():
        if k not in precovid: precovid[k] = v

stgnn_mod = defaultdict(list); stgnn_yr = defaultdict(lambda: defaultdict(list))
for f in sorted(glob.glob(os.path.join(JOB0,"stgnn_reports","dynamic_stgnn_model_metrics_seed_*_v1.json"))):
    d = lj(f)
    for item in d["summary_mean_wmape"]: stgnn_mod[item["model"]].append(item["wmape"])
    for item in d["metrics_by_model_year"]: stgnn_yr[item["model"]][item["target_year"]].append(item["wmape"])

tb_mod = defaultdict(list); tb_py = defaultdict(lambda: defaultdict(list))
for item in tb_data["summary_mean_wmape"]: tb_mod[item["model"]].append(item["mean_wmape"])
for item in tb_data["metrics_by_model_year"]: tb_py[item["model"]][item["target_year"]].append(item["wmape"])

def by_tag(runs, key="total_wmape_mean"):
    out = defaultdict(list)
    for rk,rd in runs.items(): out[rd.get("run_tag",rk)].append(rd.get(key,rd.get("mean_wmape")))
    return out

semi_bt = by_tag(semi_runs); v6_bt = by_tag(v6_runs)
v3_wmapes = [rd["mean_wmape"] for rd in v3_runs.values()]

def per_year(runs):
    py = defaultdict(lambda: defaultdict(list))
    for rk,rd in runs.items():
        tag = rd.get("run_tag",rk)
        for yr,w in rd.get("per_year_total",{}).items(): py[tag][int(yr)].append(w)
    return py
semi_py = per_year(semi_runs); v6_py = per_year(v6_runs)
v3_py = defaultdict(list)
for rd in v3_runs.values():
    for item in rd.get("per_year",[]): v3_py[item["target_year"]].append(item["wmape"])

# Internals: gamma, adj_delta, gate
gm_d = defaultdict(list); gg_d = defaultdict(list)
adj_d = defaultdict(list); gate_d = defaultdict(lambda: defaultdict(list))
for rk,rd in {**semi_runs,**v6_runs}.items():
    tag = rd.get("run_tag",rk)
    gm_d[tag].append(rd.get("gamma_mob",np.nan)); gg_d[tag].append(rd.get("gamma_geo",np.nan))
    adj_d[tag].append(rd.get("adj_delta_by_year",[]))
    for yr,g in rd.get("gate_by_year",{}).items(): gate_d[tag][int(yr)].append(g)

FOLD_YRS = list(range(2013,2026))
adj_v6   = np.mean([a for a in adj_d.get("total_h64_no_semi",[]) if len(a)==13],axis=0).tolist()
adj_semi = np.mean([a for a in adj_d.get("total_h64_semi_mask0.10_random",[]) if len(a)==13],axis=0).tolist()
gate_v6  = {yr: float(np.mean(v)) for yr,v in gate_d.get("total_h64_no_semi",{}).items()}
gate_sm  = {yr: float(np.mean(v)) for yr,v in gate_d.get("total_h64_semi_mask0.10_random",{}).items()}

GRAPH_TAGS = ["total_h64_no_semi","total_h64_semi_mask0.0_control",
              "total_h64_semi_mask0.10_random","total_h64_semi_mask0.10_spatial_block",
              "total_h64_semi_mask0.30_random"]
gm_means = [float(np.nanmean(gm_d.get(t,[]))) for t in GRAPH_TAGS]
gg_means = [float(np.nanmean(gg_d.get(t,[]))) for t in GRAPH_TAGS]

# Nouvelles connexions (top-20 pour liste)
new_conn_list = []
try:
    import glob as _g
    v6n  = sorted(_g.glob(os.path.join(JOB0,"data_processed/herald_v6_internals_full_total_h64_no_semi_seed_*_v1.npz")))
    sn   = sorted(_g.glob(os.path.join(BASE,"*/data_processed/herald_semi_internals_full_total_h64_semi_mask0.10_random_seed_*_v1.npz")))
    if v6n and sn:
        n=280; T=0.01; YR=2024
        vc=np.zeros((n,n)); sc=np.zeros((n,n)); vs=np.zeros((n,n)); ss=np.zeros((n,n)); no=None
        for fp in v6n:
            d=np.load(fp,allow_pickle=True); i=np.where(d["years"]==YR)[0]
            if len(i): vc+=(d["dynamic_adj"][i[0]]>T); vs+=d["dynamic_adj"][i[0]]
        for fp in sn:
            d=np.load(fp,allow_pickle=True)
            if no is None: no=d["node_order"]
            i=np.where(d["years"]==YR)[0]
            if len(i): sc+=(d["dynamic_adj"][i[0]]>T); ss+=d["dynamic_adj"][i[0]]
        os_=(sc>=7)&~(vc>=7); sm=ss/max(len(sn),1); vm=vs/max(len(v6n),1)
        for ni,nj in sorted(zip(*np.where(os_)),key=lambda e:-sm[e[0],e[1]])[:20]:
            zi=int(no[ni]); zj=int(no[nj])
            zi_s = str(zi); zj_s = str(zj)
            ni_s = ZE_INFO.get(zi_s,{}).get('name',f'ZE {zi:04d}')
            nj_s = ZE_INFO.get(zj_s,{}).get('name',f'ZE {zj:04d}')
            di=str(zi//100) if zi>=1000 else str(zi//10)
            dj=str(zj//100) if zj>=1000 else str(zj//10)
            new_conn_list.append({
                "label":f"{ni_s} → {nj_s}",
                "weight_semi":float(sm[ni,nj]),"weight_v6":float(vm[ni,nj]),
                "intra":di==dj,"dept_i":di,"dept_j":dj
            })
except Exception as e: print(f"  New connections: {e}")

# Tableau comparatif global
V6REF = 0.03130
models_cmp = []
def add(lbl,vals,fam,col):
    if vals: models_cmp.append({"label":lbl,"mean":float(np.mean(vals)),"std":float(np.std(vals)),"n":len(vals),"family":fam,"col":col})
add("HERALD V3", v3_wmapes, "herald","#7bb3f5")
add("HERALD V6 h32", v6_bt.get("total_h32_no_semi",[]), "herald","#9edae5")
add("HERALD V6 h64", v6_bt.get("total_h64_no_semi",[]), "herald","#4f8ef7")
add("Semi — contrôle mask0.0 ≈ V6 h64", semi_bt.get("total_h64_semi_mask0.0_control",[]), "semi","#17c3d4")
add("Semi — mask0.10 (config. principale)", semi_bt.get("total_h64_semi_mask0.10_random",[]), "semi","#f7834f")
add("Semi — mask0.30", semi_bt.get("total_h64_semi_mask0.30_random",[]), "semi","#ffc080")
add("DCRNN résiduel", stgnn_mod.get("dcrnn_residual",[]), "stgnn","#9467bd")
add("Dynamic STGNN résiduel", stgnn_mod.get("dynamic_stgnn_residual",[]), "stgnn","#c5b0d5")
add("Graph WaveNet résiduel", stgnn_mod.get("graph_wavenet_residual",[]), "stgnn","#d6b4fc")
add("Ridge AR", tb_mod.get("ridge_ar",[]), "baseline","#4caf72")
add("naive lag-1", tb_mod.get("naive_lag1",[]), "baseline","#98df8a")
add("ARIMA local", tb_mod.get("arima_local",[]), "baseline","#a8d8a8")
add("LSTM local", tb_mod.get("lstm_local",[]), "baseline","#ffb3b3")
models_cmp.sort(key=lambda x:x["mean"])

ablation = []
for tag,vals in sorted({**semi_bt,**v6_bt}.items(), key=lambda x:np.mean(x[1]) if x[1] else 99):
    if not vals: continue
    ablation.append({"tag":tag,"label":nice(tag),"mean":float(np.mean(vals)),"std":float(np.std(vals))})

seed_data = {}
for tag,lbl in [("total_h64_no_semi","HERALD V6 h64"),
                ("total_h64_semi_mask0.0_control","Semi contrôle mask0.0"),
                ("total_h64_semi_mask0.10_random","Semi mask0.10")]:
    seed_data[lbl] = {rd["seed"]:rd["total_wmape_mean"] for rk,rd in {**semi_runs,**v6_runs}.items() if rd.get("run_tag")==tag}
seed_data["HERALD V3"] = {rd["seed"]:rd["mean_wmape"] for rd in v3_runs.values()}

YEARS=[2021,2022,2023,2024,2025]
per_yr_data={}
for tag,lbl in [("total_h64_no_semi","HERALD V6 h64"),
                ("total_h64_semi_mask0.0_control","Semi contrôle mask0.0"),
                ("total_h64_semi_mask0.10_random","Semi mask0.10")]:
    py = semi_py.get(tag) or v6_py.get(tag) or {}
    per_yr_data[lbl]={yr:float(np.mean(w)) for yr,w in py.items() if w}
per_yr_data["HERALD V3"]={yr:float(np.mean(w)) for yr,w in v3_py.items() if w}
per_yr_data["Ridge AR"]={yr:float(np.mean(w)) for yr,w in tb_py["ridge_ar"].items() if w}
per_yr_data["DCRNN résiduel"]={yr:float(np.mean(w)) for yr,w in stgnn_yr.get("dcrnn_residual",{}).items() if w}

pc_vals=[rd["total_wmape_mean"] for rd in precovid.values()]
pc_py=defaultdict(list)
for rd in precovid.values():
    for yr,w in rd.get("per_year_total",{}).items(): pc_py[int(yr)].append(w)

sec_wmape_bt = defaultdict(lambda: defaultdict(list))
for rk,rd in {**semi_runs,**v6_runs}.items():
    for s,w in rd.get("sector_wmape",{}).items(): sec_wmape_bt[rd.get("run_tag",rk)][s].append(w)
SECS=["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]
sec_wmape_chart={}
for tag,lbl in [("total_h64_no_semi","HERALD V6 h64"),("total_h64_semi_mask0.10_random","Semi mask0.10"),("total_h64_semi_mask0.10_random_lam0.05_a10","Semi λ A10")]:
    sec_wmape_chart[lbl]={s:float(np.mean(sec_wmape_bt[tag][s])) for s in SECS if sec_wmape_bt[tag][s]}

# GeoJSON simplifié (235KB vs 14MB original) — chargé depuis le cache
GEO_SIMP = os.path.join(BASE,"reports","figures","ze2020_simplified.json")
with open(GEO_SIMP) as _gf:
    geojson_obj = json.load(_gf)
GEOJSON = json.dumps(geojson_obj, separators=(',',':'))
ZE_NAMES = {feat['properties']['ze2020']: feat['properties']['libze2020']
            for feat in geojson_obj['features']}

SEC_COLORS={'BE':'#66c2a5','FZ':'#fc8d62','GI':'#8da0cb','JZ':'#e78ac3',
            'KZ':'#a6d854','LZ':'#ffd92f','MN':'#e5c494','OQ':'#b3b3b3','RU':'#e41a1c'}
SEC_FULL={'BE':'Agriculture / Énergie / Eau','FZ':'Construction',
          'GI':'Commerce, Transport, Hébergement','JZ':'Information et Communication',
          'KZ':'Activités Financières et Assurances','LZ':'Immobilier',
          'MN':'Industrie Manufacturière','OQ':'Administration, Santé, Éducation',
          'RU':'Autres Services aux Ménages'}

# ── ZONA INTERATIVIDADE ──────────────────────────────────────────────────────
zone_sector_comp = {}
zone_timeseries = {}
zone_edges = {}
SECS = list(SEC_COLORS.keys())

for sec_item in SEC_MAP:
    ze_str = sec_item['ze']
    zone_sector_comp[ze_str] = {s: float(sec_item.get(s, 0.0)) for s in SECS}

for ye in sorted(ZONE_V6.keys()):
    for ze_str, wmape_val in ZONE_V6.get(ye, {}).items():
        if ze_str not in zone_timeseries:
            zone_timeseries[ze_str] = {"v6": {}, "semi": {}}
        zone_timeseries[ze_str]["v6"][ye] = float(wmape_val)

for ye in sorted(ZONE_SEMI.keys()):
    for ze_str, wmape_val in ZONE_SEMI.get(ye, {}).items():
        if ze_str not in zone_timeseries:
            zone_timeseries[ze_str] = {"v6": {}, "semi": {}}
        zone_timeseries[ze_str]["semi"][ye] = float(wmape_val)

for ze_str in ZE_NAMES.keys():
    zone_edges[ze_str] = {"in": [], "out": []}
    edge_dict = defaultdict(lambda: {"weight": 0, "name": ""})
    
    for yr_data in GRAPH.values():
        if isinstance(yr_data, list):
            for edge in yr_data:
                zi_str = str(int(float(edge.get("ze_i", "0").split()[-1]) if isinstance(edge.get("ze_i"), str) else edge.get("ze_i", 0))).zfill(4)
                zj_str = str(int(float(edge.get("ze_j", "0").split()[-1]) if isinstance(edge.get("ze_j"), str) else edge.get("ze_j", 0))).zfill(4)
                w = float(edge.get("weight", 0))
                
                if zi_str == ze_str and zj_str in ZE_NAMES:
                    key = f"out_{zj_str}"
                    edge_dict[key]["weight"] = max(edge_dict[key]["weight"], w)
                    edge_dict[key]["name"] = ZE_NAMES.get(zj_str, f"ZE {zj_str}")
                if zj_str == ze_str and zi_str in ZE_NAMES:
                    key = f"in_{zi_str}"
                    edge_dict[key]["weight"] = max(edge_dict[key]["weight"], w)
                    edge_dict[key]["name"] = ZE_NAMES.get(zi_str, f"ZE {zi_str}")
    
    for key, val in sorted(edge_dict.items(), key=lambda x: x[1]["weight"], reverse=True):
        if key.startswith("out_"):
            zone_edges[ze_str]["out"].append({"to": key[4:], "name": val["name"], "weight": val["weight"]})
        else:
            zone_edges[ze_str]["in"].append({"from": key[3:], "name": val["name"], "weight": val["weight"]})
    
    zone_edges[ze_str]["in"] = zone_edges[ze_str]["in"][:10]
    zone_edges[ze_str]["out"] = zone_edges[ze_str]["out"][:10]

print("Génération HTML…")

HTML = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HERALD geo2025 — Tableau de bord scientifique</title>
{PLOTLY_INLINE}
<style>
:root{{--bg:#0f1117;--bg2:#1a1d27;--bg3:#242836;--acc:#4f8ef7;--acc2:#f7834f;
      --green:#4caf72;--red:#e05252;--text:#e8eaf0;--muted:#8b9abf;--bdr:#2e3347}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.6}}
.wrap{{max-width:1400px;margin:0 auto;padding:24px}}
h1{{font-size:1.7rem;color:var(--acc);font-weight:700;margin-bottom:4px}}
h2{{font-size:1.1rem;color:var(--acc);margin:34px 0 8px;font-weight:600;border-bottom:1px solid var(--bdr);padding-bottom:5px}}
h3{{font-size:.9rem;color:var(--acc2);margin:12px 0 4px;font-weight:600}}
.sub{{color:var(--muted);font-size:.83rem;margin-bottom:20px}}
.card{{background:var(--bg2);border:1px solid var(--bdr);border-radius:10px;padding:18px;margin-bottom:16px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin-bottom:16px}}
.kpi{{background:var(--bg2);border:1px solid var(--bdr);border-radius:8px;padding:13px;text-align:center}}
.kpi .v{{font-size:1.45rem;font-weight:700;color:var(--acc)}}.kpi .l{{font-size:.72rem;color:var(--muted);margin-top:2px}}
.box{{background:var(--bg2);border:1px solid var(--bdr);border-radius:10px;padding:13px;margin-bottom:14px}}
.info{{background:rgba(79,142,247,.07);border-left:3px solid var(--acc);border-radius:3px;padding:8px 12px;margin:9px 0;font-size:.83rem;color:var(--muted)}}
.warn{{background:rgba(224,82,82,.07);border-left:3px solid var(--red);border-radius:3px;padding:8px 12px;margin:9px 0;font-size:.83rem}}
.ok{{background:rgba(76,175,114,.07);border-left:3px solid var(--green);border-radius:3px;padding:8px 12px;margin:9px 0;font-size:.83rem}}
.pill{{display:inline-block;border-radius:20px;padding:2px 10px;font-size:.76rem;font-weight:600;margin:2px}}
.pg{{background:rgba(76,175,114,.14);color:var(--green);border:1px solid var(--green)}}
.pr{{background:rgba(224,82,82,.14);color:var(--red);border:1px solid var(--red)}}
.po{{background:rgba(247,131,79,.14);color:var(--acc2);border:1px solid var(--acc2)}}
.pb{{background:rgba(79,142,247,.14);color:var(--acc);border:1px solid var(--acc)}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}
@media(max-width:900px){{.g2,.g3{{grid-template-columns:1fr}}}}
.nav{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:22px}}
.nb{{background:var(--bg3);border:1px solid var(--bdr);color:var(--muted);border-radius:18px;
     padding:4px 12px;font-size:.76rem;text-decoration:none;transition:.15s}}
.nb:hover{{background:var(--acc);color:#fff;border-color:var(--acc)}}
select{{background:var(--bg3);color:var(--text);border:1px solid var(--bdr);border-radius:6px;padding:5px 10px;font-size:.86rem;cursor:pointer}}
.ctrl{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:9px}}
.ctrl label{{color:var(--muted);font-size:.81rem}}
table{{width:100%;border-collapse:collapse;font-size:.82rem}}
th{{background:var(--bg3);color:var(--acc);padding:7px 10px;text-align:left;font-weight:600}}
td{{padding:6px 10px;border-bottom:1px solid var(--bdr)}}
tr:hover td{{background:var(--bg3)}}
.tf{{color:var(--green);font-weight:700}}.td{{color:#f7c04f;font-weight:600}}
.tw{{color:var(--acc2)}}.tn{{color:var(--red);font-weight:700}}
hr{{border:none;border-top:1px solid var(--bdr);margin:28px 0}}
.legend-dot{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:middle}}
</style>
</head>
<body>
<div class="wrap">

<h1>HERALD geo2025 — Tableau de bord scientifique final</h1>
<p class="sub">253 model-runs · SIDE/INSEE · 280 zones d'emploi · Évaluation observée 2021–2025 · France métropolitaine</p>

<div class="nav">
  <a class="nb" href="#exec">A. Résumé</a>
  <a class="nb" href="#global">B. Comparaison globale</a>
  <a class="nb" href="#ablation">C. Ablation</a>
  <a class="nb" href="#seeds">D. Robustesse seeds</a>
  <a class="nb" href="#annee">E. Par année</a>
  <a class="nb" href="#graphe">F. Graphe dynamique</a>
  <a class="nb" href="#carte">H. Carte erreurs</a>
  <a class="nb" href="#precovid">J. Pré-COVID</a>
  <a class="nb" href="#claims">K. Conclusions</a>
</div>

<!-- ═══ A. RÉSUMÉ ═══ -->
<h2 id="exec">A. Résumé exécutif</h2>
<div class="kpis">
  <div class="kpi"><div class="v">0.0313</div><div class="l">WMAPE · HERALD V6 h64<br>(meilleur modèle)</div></div>
  <div class="kpi"><div class="v">253</div><div class="l">Model-runs · 10 seeds</div></div>
  <div class="kpi"><div class="v">280</div><div class="l">Zones d'emploi France métro.</div></div>
  <div class="kpi"><div class="v">−47%</div><div class="l">HERALD vs Ridge AR</div></div>
  <div class="kpi"><div class="v">3.5×</div><div class="l">Mobilité / Géographie<br>(γ_mob / γ_geo)</div></div>
  <div class="kpi"><div class="v">×10–20</div><div class="l">adj_delta COVID<br>vs pré-COVID</div></div>
</div>
<div class="card">
  <span class="pill pg">HERALD V6 h64 — meilleur modèle (WMAPE 0.0313 ± 0.0046)</span>
  <div class="warn" style="margin-top:10px">⚠ <b>Semi-supervision avec masquage : résultat négatif.</b> Le contrôle mask0.0 (sans masquage) est statistiquement identique à V6 h64 (Wilcoxon p=0.47 — même modèle, même entraînement). Le masquage actif (mask0.10) dégrade la performance (+9% WMAPE, Wilcoxon p=0.049 vs contrôle). Le gain vient de la capacité h64, pas du masquage.</div>
  <div class="ok">✓ <b>117 nouvelles connexions stables</b> révélées par le Semi (non présentes dans V6 h64) — valeur interprétative pour future recherche sur les bassins économiques.</div>
  <div class="ok">✓ <b>Graphe dynamique</b> détecte le choc COVID : adj_delta ×10–20 en 2020–2022 · la mobilité domine la géographie (γ_mob/γ_geo ≈ 3.5×).</div>
</div>

<!-- ═══ B. COMPARAISON GLOBALE ═══ -->
<h2 id="global">B. Comparaison globale des modèles</h2>
<div class="info">
  <b>Comment lire :</b> WMAPE moyen sur 5 folds (2021–2025), 280 zones d'emploi. Barres d'erreur = ±1 écart-type inter-seeds. Ligne bleue pointillée = HERALD V6 h64 (référence). Plus bas = meilleur prédicteur.<br>
  <b>Résultat :</b> HERALD bat tous les baselines de 40–66%. La configuration Semi (orange) avec masquage actif ne dépasse pas V6 h64. Le contrôle mask0.0 est statistiquement identique à V6 h64.
</div>
<div class="box"><div id="cGlobal" style="height:500px"></div></div>

<!-- ═══ C. ABLATION ═══ -->
<h2 id="ablation">C. Ablation semi-supervisée complète</h2>
<div class="info">
  <b>Comment lire :</b> chaque barre = WMAPE moyen d'une configuration. Ligne bleue = V6 h64 (0.0313). À droite de la ligne = pire que V6 h64. Barres rouges = configurations dégradées (bloc spatial).<br>
  <b>Conclusion :</b> aucune configuration avec masquage actif ne dépasse V6 h64. Le masquage bloc spatial est catastrophique (+40%).
</div>
<div class="box"><div id="cAblation" style="height:600px"></div></div>
<div class="g2">
  <div>
    <div class="info"><b>Sensibilité au ratio de masque :</b> mask0.0 (sans masquage) est le meilleur. Augmenter le masquage dégrade progressivement. Aucun ratio ne dépasse V6 h64.</div>
    <div class="box"><div id="cMaskRatio" style="height:300px"></div></div>
  </div>
  <div>
    <div class="info"><b>Stratégie de masquage :</b> aléatoire est le moins mauvais. Le bloc spatial est catastrophique car il masque précisément les voisins géographiques, annulant le signal du graphe géographique.</div>
    <div class="box"><div id="cStrategy" style="height:300px"></div></div>
  </div>
</div>
<div class="g2">
  <div>
    <div class="info"><b>Capacité h32 vs h64 :</b> le gain de V6 h32→h64 (+7%) provient de la capacité du modèle. Le Semi h64 récupère partiellement ce gain mais ne dépasse pas V6 h64 sans masquage.</div>
    <div class="box"><div id="cCapacity" style="height:280px"></div></div>
  </div>
  <div>
    <div class="info"><b>Lambda semi :</b> augmenter λ ne change presque rien au WMAPE total. Le signal semi-supervisé est trop faible face à la loss principale.</div>
    <div class="box"><div id="cLambda" style="height:280px"></div></div>
  </div>
</div>

<!-- ═══ D. ROBUSTESSE SEEDS ═══ -->
<h2 id="seeds">D. Robustesse par seed</h2>
<div class="info">
  <b>Gauche — points individuels :</b> chaque point = 1 entraînement indépendant (seed). Le losange <b>◆</b> = moyenne sur 10 seeds. La dispersion verticale mesure la sensibilité au tirage aléatoire.<br>
  <b>Droite — seed par seed :</b> chaque ligne relie la <i>même seed</i> entre V6 h64 et Semi mask0.10. <span style="color:#4caf72">Vert</span> = Semi gagne · <span style="color:#e05252">Rouge</span> = V6 gagne. V6 h64 gagne sur 7 des 10 seeds.
</div>
<div class="g2">
  <div class="box"><div id="cBox" style="height:380px"></div></div>
  <div class="box"><div id="cPaired" style="height:380px"></div></div>
</div>

<!-- ═══ E. PAR ANNÉE ═══ -->
<h2 id="annee">E. Performance par année de prévision</h2>
<div class="info">
  <b>Lecture :</b> chaque barre = WMAPE moyen sur 280 zones pour l'année prévue. V6 h64 (bleu) = meilleur modèle, Semi mask0.10 (orange), Ridge AR (vert) = baseline simple.<br>
  <b>2021</b> = fold le plus difficile (rebond COVID brutal). <b>⚠ 2025 :</b> Ridge AR revient au niveau de HERALD — signe de nouvelles dynamiques post-COVID où les patterns simples redeviennent compétitifs.
</div>
<div class="box"><div id="cYear" style="height:420px"></div></div>

<!-- ═══ F. GRAPHE DYNAMIQUE ═══ -->
<h2 id="graphe">F. Graphe dynamique — diagnostics</h2>
<div class="info">
  <b>Mobilité vs Géographie :</b> γ_mob ≈ 1.0, γ_geo ≈ 0.28 pour V6 h64 (ratio 3.5×). La mobilité domicile-travail est systématiquement plus informative que la proximité géographique pour prédire les créations d'établissements.<br>
  <b>adj_delta COVID :</b> la variation structurelle du graphe est 10–20× plus grande en 2020–2022 qu'avant COVID. Le modèle détecte automatiquement le choc économique — sans aucune information explicite sur COVID.<br>
  <b>Gate de mobilité :</b> augmente pendant COVID (2020), confirmant que la mobilité devient encore plus informative lors des perturbations.
</div>
<div class="g2">
  <div class="box"><div id="cGamma" style="height:350px"></div></div>
  <div class="box"><div id="cAdjDelta" style="height:350px"></div></div>
</div>
<div class="box"><div id="cGate" style="height:280px"></div></div>

<h3 id="graphemap" style="color:var(--acc2);margin:28px 0 8px;font-size:.95rem;border-bottom:1px solid var(--bdr);padding-bottom:4px">Visualisation territoriale — connexions apprises par le modèle</h3>
<div class="info">
  <b>Comment lire :</b> chaque ligne = connexion de haut poids dans la matrice d'adjacence apprise (HERALD V6 h64, moyennée sur 10 seeds). L'épaisseur et la couleur représentent le poids de la connexion. Les connexions sont affichées pour les top-40 arêtes par dessus un seuil de 0.05.<br>
  <b>Résultat clé :</b> les connexions les plus fortes sont des paires de zones économiquement liées — souvent des métropoles et leurs périphéries directes. Pendant COVID (2021–2022), les connexions changent légèrement, reflétant les perturbations des flux domicile-travail.
</div>
<div class="warn">⚠ Le <b>adj_delta</b> montre une variation structurelle pendant COVID, mais les connexions absolues restent similaires (le choc est relatif, pas une réorganisation totale). Le graphe détecte principalement un changement d'intensité des liens existants.</div>
<div class="ctrl">
  <label>Année :</label>
  <select id="graphYrSel" onchange="updateGraphMap()">
    <option value="2019">2019 — Avant COVID (référence)</option>
    <option value="2021">2021 — COVID / rebond</option>
    <option value="2022">2022 — Récupération</option>
    <option value="2024">2024 — Post-COVID stable</option>
  </select>
</div>
<div class="box"><div id="cGraphMap" style="height:600px"></div></div>

<!-- ═══ H. CARTE ERREURS ═══ -->
<h2 id="carte">H. Carte de France — Erreurs de prévision par zone d'emploi</h2>
<div class="info">
  <b>Comment lire :</b> intensité de couleur = WMAPE par zone. <span style="color:#fdae6b">Jaune clair</span> = faible erreur · <span style="color:#d94801">Rouge foncé</span> = erreur élevée. Les zones à fort volume de créations ont généralement des erreurs plus faibles (dénominateur plus grand dans le WMAPE).<br>
  <b>Changer l'année</b> pour voir quels territoires sont difficiles à prédire. 2021 = zones les plus perturbées par le rebond COVID.<br>
  <b>&#x1F449; Cliquez sur une zone</b> pour afficher son profil : série temporelle, composition sectorielle et connexions.
</div>
<div class="ctrl">
  <label>Modèle :</label>
  <select id="mapMdl" onchange="updateMap()">
    <option value="v6">Erreur WMAPE — HERALD V6 h64</option>
    <option value="semi">Erreur WMAPE — HERALD Semi mask0.10</option>
    <option value="diff">Différence Semi − V6 h64 (rouge = Semi pire)</option>
    <option value="sector">Secteur A10 dominant</option>
  </select>
  <span id="mapYrGroup"><label>Année :</label>
  <select id="mapYr" onchange="updateMap()">
    <option value="all">Moyenne 2021–2025</option>
    <option value="2021">2021 — rebond COVID</option>
    <option value="2022">2022 — récupération</option>
    <option value="2023">2023</option>
    <option value="2024">2024</option>
    <option value="2025">2025</option>
  </select>
  </span>
</div>
<div class="box"><div id="cMap" style="height:600px"></div></div>

<div id="panel-regional" style="display:none; background:var(--bg2); border:2px solid var(--acc); border-radius:10px; padding:20px; margin-top:16px; margin-bottom:20px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
    <h3 id="zone-breadcrumb" style="color:var(--acc); font-size:1rem;">Zone sélectionnée</h3>
    <button onclick="clearSelection()" style="background:var(--acc2); color:#fff; border:none; padding:6px 14px; border-radius:4px; cursor:pointer; font-size:.84rem;">&#x2715; Fermer</button>
  </div>
  <div class="g3">
    <div id="regional-timeseries" style="min-height:300px;"></div>
    <div id="regional-sectors" style="min-height:300px;"></div>
    <div id="regional-edges" style="min-height:300px;"></div>
  </div>
</div>

<!-- ═══ I. SECTEURS A10 ═══ -->
<h2 id="secteurs">I. Secteurs A10 — difficulté de prévision par secteur</h2>
<div class="info">
  <b>Chaque barre = WMAPE moyen sur 280 zones, 10 seeds.</b> JZ (Information/Communication) et KZ (Finance) sont les plus difficiles à prédire (∼0.40 vs 0.03 global). OQ (Administration) est le plus stable. Sélectionnez <b>"Secteur A10 dominant"</b> dans la carte H pour voir la répartition géographique.
</div>
<div class="box">
    <div id="cSecWmape" style="height:320px"></div>
    <div style="margin-top:12px;padding:8px">
      <p style="font-size:.82rem;color:var(--muted);margin-bottom:8px"><b>Légende des secteurs A10 :</b></p>
      {chr(10).join(f'<div style="margin:3px 0;font-size:.8rem"><span class="legend-dot" style="background:{SEC_COLORS[s]}"></span><b>{s}</b> — {SEC_FULL[s]}</div>' for s in SECS)}
    </div>
</div>

<!-- ═══ J. PRÉ-COVID ═══ -->
<h2 id="precovid">J. Robustesse pré-COVID (2016–2019)</h2>
<div class="warn">⚠ <b>Comparaison incomplète :</b> seule la configuration Semi mask0.10 a été évaluée en pré-COVID. V6 h64 et V3 n'ont pas été testés sur ce protocole.</div>
<div class="info">
  <b>Comment lire :</b> barres bleues = WMAPE de HERALD Semi par année (2016–2019). Points verts = Ridge AR sur la même année. Points cyan = WMAPE moyen de HERALD sur 2021–2025 (pour référence).<br>
  <b>Résultat :</b> sur 2016–2019, l'avantage de HERALD sur Ridge AR chute de −0.033 (période principale) à −0.004 (pré-COVID). 2016 est particulièrement difficile (WMAPE = 0.13) car le modèle n'a que 4 ans d'historique.
</div>
<div class="box"><div id="cPrecovid" style="height:400px"></div></div>

<!-- ═══ K. CONCLUSIONS ═══ -->
<h2 id="claims">K. Conclusions scientifiques</h2>
<div class="card">
<table>
<tr><th>Affirmation scientifique</th><th>Verdict</th><th>Évidence</th></tr>
<tr><td>HERALD ≻ Ridge AR</td><td class="tf">FORT</td><td>WMAPE 0.031 vs 0.059 · Δ = −47% · toutes configs HERALD</td></tr>
<tr><td>HERALD ≻ LSTM local</td><td class="tf">FORT</td><td>WMAPE 0.031 vs 0.091 · Δ = −66%</td></tr>
<tr><td>HERALD ≻ STGNNs literature (DCRNN, Dynamic)</td><td class="tf">FORT</td><td>WMAPE 0.031 vs 0.054 · Δ = −40% · nota : STGNNs résiduels</td></tr>
<tr><td>Semi mask0.10 ≻ HERALD V6 h64</td><td class="tn">NON SOUTENU</td><td>0.034 vs 0.031 · wins 3/10 seeds · Wilcoxon p = 0.105</td></tr>
<tr><td>Masquage améliore la robustesse</td><td class="tn">NON SOUTENU</td><td>Masquage vs contrôle : masquage pire, p = 0.049</td></tr>
<tr><td>Gain Semi = masquage (pas capacité h64)</td><td class="tn">NON SOUTENU</td><td>h64 → gain réel de 7% · masquage → dégradation systématique</td></tr>
<tr><td>Graphe dynamique — valeur prédictive isolée</td><td class="td">À TESTER</td><td>Ablation fixed_adj non disponible sur geo2025</td></tr>
<tr><td>Graphe dynamique — valeur interprétative</td><td class="tf">FORT</td><td>adj_delta COVID ×10–20 · gate↑ pendant COVID · γ_mob/γ_geo = 3.5×</td></tr>
<tr><td>Mobilité &gt; Géographie pour prédire les créations</td><td class="tf">FORT</td><td>γ_mob/γ_geo ≈ 3.5× stable sur 10 seeds et 19 configurations</td></tr>
<tr><td>Semi révèle nouvelles connexions territoriales</td><td class="td">DÉFENDABLE (interprétatif)</td><td>117 connexions stables · 9× plus faibles · validation requise</td></tr>
<tr><td>A10 — contribution prédictive forte</td><td class="tw">FAIBLE</td><td>WMAPE sectoriel ~0.23 · λ A10 améliore de 2% · non significatif</td></tr>
<tr><td>Robustesse pré-COVID validée</td><td class="tw">FAIBLE</td><td>Avantage vs Ridge AR réduit de 87% sur 2016–2019</td></tr>
</table>
</div>
<div class="card" style="margin-top:12px">
  <h3>Étapes nécessaires avant soumission</h3>
  <ol style="padding-left:18px;line-height:2;font-size:.88rem">
    <li>Ablation <code>fixed_adj</code> — isoler la valeur prédictive du graphe dynamique vs statique</li>
    <li>Précovid pour V6 h64 et V3 — comparer la robustesse sur la même période</li>
    <li>Investiguer <code>spatial_block</code> (+40% WMAPE, p&lt;0.01) — probable bug d'implémentation</li>
    <li>Valider les 117 nouvelles connexions Semi avec les données de mobilité INSEE</li>
    <li>Activer les logs de convergence dans la prochaine batterie HPC</li>
  </ol>
</div>

<hr>
<p style="font-size:.75rem;color:var(--muted);text-align:center">Données SIDE/INSEE · Géographie ZE 2020 (nomenclature 2026) · 280 zones d'emploi · Évaluation observée 2021–2025 · Généré 2026-05-02</p>
</div>

<script>
// ══════════════════════════════════════════════════════════
// DONNÉES
// ══════════════════════════════════════════════════════════
const CMP       = {J(models_cmp)};
const ABL       = {J(ablation)};
const SD        = {J({k:list(v.items()) for k,v in seed_data.items()})};
const PY        = {J(per_yr_data)};
const YEARS     = {J(YEARS)};
const V6REF     = {V6REF};
const GM        = {J(gm_means)};
const GG        = {J(gg_means)};
const GTAGS     = {J([nice(t) for t in GRAPH_TAGS])};
const ADJ_V6    = {J(adj_v6)};
const ADJ_SEMI  = {J(adj_semi)};
const FOLD_YRS  = {J(FOLD_YRS)};
const GATE_V6   = {J(gate_v6)};
const GATE_SM   = {J(gate_sm)};
const PC_VALS   = {J(pc_vals)};
const PC_PY     = {J({yr:float(np.mean(w)) for yr,w in pc_py.items() if w})};
const RIDGE_YR  = {J({str(k):v for k,v in {yr:float(np.mean(w)) for yr,w in tb_py["ridge_ar"].items() if w}.items()})};
const NEW_CONN  = {J(new_conn_list)};
const GEOJSON   = {GEOJSON};
const ZONE_V6   = {J({str(k):v for k,v in ZONE_V6.items()})};
const ZONE_SEMI = {J({str(k):v for k,v in ZONE_SEMI.items()})};
const ZE_NAMES  = {J(ZE_NAMES)};
const GRAPH_DATA= {J(GRAPH)};
const SEC_MAP   = {J(SEC_MAP)};
const SEC_WMAPE = {J(sec_wmape_chart)};
const SECS      = {J(SECS)};
const SEC_COLORS= {J(SEC_COLORS)};
const SEC_FULL  = {J(SEC_FULL)};
const ZONE_SECTOR_COMP = {J(zone_sector_comp)};
const ZONE_TIMESERIES = {J(zone_timeseries)};
const ZONE_EDGES = {J(zone_edges)};

const BL = {{
  paper_bgcolor:'#1a1d27',plot_bgcolor:'#1a1d27',
  font:{{color:'#e8eaf0',family:'Segoe UI,system-ui,sans-serif',size:12}},
  margin:{{l:40,r:24,t:44,b:36}},
  xaxis:{{gridcolor:'#2e3347',zerolinecolor:'#2e3347'}},
  yaxis:{{gridcolor:'#2e3347',zerolinecolor:'#2e3347'}},
  legend:{{bgcolor:'#242836',bordercolor:'#2e3347',borderwidth:1}},
}};
const CFG = {{responsive:true,displayModeBar:false}};

// ── B. COMPARAISON GLOBALE ────────────────────────────────

(()=>{{
  const rows=ABL;
  const c=rows.map(r=>
    r.tag==='total_h64_no_semi'?'#4f8ef7':
    r.tag==='total_h64_semi_mask0.0_control'?'#17c3d4':
    r.tag.includes('spatial')?'#e05252':
    r.tag.includes('semi')?'#f7834f':'#7bb3f5'
  );
  Plotly.newPlot('cAblation',[{{
    type:'bar',orientation:'h',
    x:rows.map(r=>r.mean), y:rows.map(r=>r.label),
    error_x:{{type:'data',array:rows.map(r=>r.std),visible:true,color:'#8b9abf',thickness:1.5}},
    marker:{{color:c,opacity:.88}},
    text:rows.map(r=>(r.mean*100).toFixed(2)+'%'),
    textposition:'outside',textfont:{{size:10}},
    hovertemplate:'<b>%{{y}}</b><br>WMAPE: %{{x:.4f}} ± %{{customdata:.4f}}<extra></extra>',
    customdata:rows.map(r=>r.std),
  }}],{{
    ...BL,
    title:{{text:'Ablation complète — 19 configurations HERALD classées par WMAPE',font:{{size:13}}}},
    xaxis:{{...BL.xaxis,title:'WMAPE moyen',tickformat:'.3f',range:[.023,.056]}},
    yaxis:{{...BL.yaxis,automargin:true}},
    margin:{{l:280,r:90,t:50,b:40}},
    shapes:[{{type:'line',x0:V6REF,x1:V6REF,y0:-.5,y1:rows.length-.5,
              line:{{color:'#4f8ef7',width:2.5,dash:'dash'}}}}],
    annotations:[{{x:V6REF,y:rows.length,text:'V6 h64 référence (0.031)',
                   showarrow:false,font:{{color:'#4f8ef7',size:11}},xanchor:'left'}}],
  }},CFG);
}})();

// Mask ratio
(()=>{{
  const r=['0.0','0.05','0.10','0.15','0.20','0.30'];
  const tm={{'0.0':'total_h64_semi_mask0.0_control','0.05':'total_h64_semi_mask0.05_random',
    '0.10':'total_h64_semi_mask0.10_random','0.15':'total_h64_semi_mask0.15_random',
    '0.20':'total_h64_semi_mask0.20_random','0.30':'total_h64_semi_mask0.30_random'}};
  const m=r.map(x=>(ABL.find(a=>a.tag===tm[x])||{{mean:0}}).mean);
  const s=r.map(x=>(ABL.find(a=>a.tag===tm[x])||{{std:0}}).std);
  Plotly.newPlot('cMaskRatio',[
    {{type:'scatter',mode:'lines+markers',x:r,y:m,
      error_y:{{type:'data',array:s,visible:true,color:'#8b9abf'}},
      line:{{color:'#f7834f',width:2.5}},marker:{{size:9,color:'#f7834f'}},
      name:'WMAPE Semi'}},
    {{type:'scatter',mode:'lines',x:r,y:Array(6).fill(V6REF),
      line:{{color:'#4f8ef7',width:2,dash:'dash'}},name:'V6 h64 (0.031)'}},
  ],{{
    ...BL,
    title:{{text:'Sensibilité au ratio de masque (h64, random)',font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:'Ratio de masque (0 = pas de masquage)'}},
    yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.024,.05]}},
    annotations:[{{x:'0.0',y:m[0],text:'Pas de masquage<br>(= V6 h64)',
      showarrow:true,arrowhead:2,arrowcolor:'#17c3d4',font:{{color:'#17c3d4',size:9}},
      ax:30,ay:-30}}],
  }},CFG);
}})();

// Stratégie
(()=>{{
  const cf=[
    ['Aléatoire 10%','total_h64_semi_mask0.10_random','#f7834f'],
    ['Bloc 10%','total_h64_semi_mask0.10_block','#f7c04f'],
    ['Bloc spatial 10%','total_h64_semi_mask0.10_spatial_block','#e05252'],
    ['Aléatoire 20%','total_h64_semi_mask0.20_random','#ffb87f'],
    ['Bloc 20%','total_h64_semi_mask0.20_block','#ffd080'],
    ['Bloc spatial 20%','total_h64_semi_mask0.20_spatial_block','#ff8080'],
  ];
  Plotly.newPlot('cStrategy',cf.map(([lbl,tag,col])=>{{
    const r=ABL.find(a=>a.tag===tag)||{{mean:0,std:0}};
    return {{type:'bar',name:lbl,x:[lbl],y:[r.mean],
      error_y:{{type:'data',array:[r.std],visible:true,color:'#8b9abf'}},
      marker:{{color:col}},hovertemplate:`<b>${{lbl}}</b><br>%{{y:.4f}}<extra></extra>`}};
  }}),{{
    ...BL,barmode:'group',showlegend:false,
    title:{{text:'Stratégie de masquage — impact sur WMAPE',font:{{size:12}}}},
    yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.024,.057]}},
    shapes:[{{type:'line',x0:-.5,x1:5.5,y0:V6REF,y1:V6REF,
              line:{{color:'#4f8ef7',width:2,dash:'dash'}}}}],
    annotations:[{{x:5.2,y:V6REF,text:'V6 h64',showarrow:false,
                   font:{{color:'#4f8ef7',size:9}},yanchor:'bottom'}}],
  }},CFG);
}})();

// Capacité
(()=>{{
  const cf=[
    ['V6 h32','total_h32_no_semi','#9edae5'],
    ['V6 h64 (référence)','total_h64_no_semi','#4f8ef7'],
    ['Semi h32 mask0.10','total_h32_semi_mask0.10_random','#ffc07f'],
    ['Semi h64 mask0.10','total_h64_semi_mask0.10_random','#f7834f'],
  ];
  const rows=cf.map(([lbl,tag,col])=>{{const r=ABL.find(a=>a.tag===tag)||{{mean:0,std:0}};return{{lbl,mean:r.mean,std:r.std,col}}}});
  Plotly.newPlot('cCapacity',[{{
    type:'bar',x:rows.map(r=>r.lbl),y:rows.map(r=>r.mean),
    marker:{{color:rows.map(r=>r.col)}},
    error_y:{{type:'data',array:rows.map(r=>r.std),visible:true,color:'#8b9abf'}},
    text:rows.map(r=>(r.mean*100).toFixed(2)+'%'),textposition:'outside',textfont:{{size:10}},
    hovertemplate:'<b>%{{x}}</b><br>%{{y:.4f}}<extra></extra>',
  }}],{{
    ...BL,
    title:{{text:'Capacité h32 vs h64 — avec et sans masquage',font:{{size:12}}}},
    yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.022,.047]}},
  }},CFG);
}})();

// Lambda
(()=>{{
  const cf=[
    ['λ=0 (base)','total_h64_semi_mask0.10_random'],
    ['λ=0.01 total','total_h64_semi_mask0.10_random_lam0.01_total'],
    ['λ=0.05 total','total_h64_semi_mask0.10_random_lam0.05_total'],
    ['λ=0.10 total','total_h64_semi_mask0.10_random_lam0.10_total'],
    ['λ=0.05 secteurs','total_h64_semi_mask0.10_random_lam0.05_a10'],
    ['λ=0.05 tot+sec','total_h64_semi_mask0.10_random_lam0.05_total_a10'],
  ];
  const d=cf.map(([lbl,tag])=>{{const r=ABL.find(a=>a.tag===tag)||{{mean:0,std:0}};return{{lbl,mean:r.mean,std:r.std}}}});
  Plotly.newPlot('cLambda',[
    {{type:'bar',x:d.map(r=>r.lbl),y:d.map(r=>r.mean),marker:{{color:'#f7834f',opacity:.85}},
      error_y:{{type:'data',array:d.map(r=>r.std),visible:true,color:'#8b9abf'}},
      hovertemplate:'<b>%{{x}}</b><br>%{{y:.4f}}<extra></extra>'}},
    {{type:'scatter',mode:'lines',x:d.map(r=>r.lbl),y:Array(d.length).fill(V6REF),
      line:{{color:'#4f8ef7',width:2,dash:'dash'}},name:'V6 h64'}},
  ],{{
    ...BL,
    title:{{text:'Semi lambda — impact sur WMAPE total',font:{{size:12}}}},
    xaxis:{{...BL.xaxis,tickangle:-15}},
    yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.022,.04]}},
  }},CFG);
}})();

// ── D. SEEDS ─────────────────────────────────────────────
(()=>{{
  const configs=["HERALD V6 h64","Semi contr\u00f4le mask0.0","Semi mask0.10","HERALD V3"];
  const cols={{"HERALD V6 h64":"#4f8ef7","Semi contr\u00f4le mask0.0":"#17c3d4",
               "Semi mask0.10":"#f7834f","HERALD V3":"#7bb3f5"}};
  const trs=configs.flatMap(cfg=>{{
    if(!SD[cfg]) return [];
    const pts=SD[cfg];
    const vals=pts.map(([s,v])=>v);
    const mn=vals.reduce((a,b)=>a+b,0)/vals.length;
    return [
      {{type:"scatter",mode:"markers",name:cfg,
        x:pts.map(()=>cfg),y:vals,
        marker:{{size:11,color:cols[cfg]||"#aaa",opacity:.75}},
        text:pts.map(([s])=>"Seed "+s),
        hovertemplate:"<b>"+cfg+"</b><br>%{{text}}: %{{y:.4f}}<extra></extra>",
        showlegend:true}},
      {{type:"scatter",mode:"markers",name:cfg+" moy.",
        x:[cfg],y:[mn],showlegend:false,
        marker:{{size:18,color:cols[cfg]||"#aaa",symbol:"diamond",line:{{width:2.5,color:"white"}}}},
        hovertemplate:"Moyenne: "+mn.toFixed(4)+"<extra></extra>"}}
    ];
  }});
  Plotly.newPlot("cBox",trs,{{
    ...BL,showlegend:false,
    title:{{text:"Variabilit\u00e9 inter-seeds \u2014 chaque point = 1 seed \u00b7 \u25c6 = moyenne",font:{{size:12}}}},
    xaxis:{{...BL.xaxis,type:"category"}},
    yaxis:{{...BL.yaxis,title:"WMAPE",range:[.015,.065]}},
    shapes:[
      {{type:"line",x0:-.5,x1:3.5,y0:V6REF,y1:V6REF,line:{{color:"#4f8ef7",width:2,dash:"dash"}}}},
      {{type:"line",x0:-.5,x1:3.5,y0:.059,y1:.059,line:{{color:"#4caf72",width:1.5,dash:"dot"}}}},
    ],
    annotations:[
      {{x:3.4,y:V6REF,text:"V6 h64",showarrow:false,font:{{color:"#4f8ef7",size:9}},yanchor:"bottom"}},
      {{x:3.4,y:.059,text:"Ridge AR",showarrow:false,font:{{color:"#4caf72",size:9}},yanchor:"bottom"}},
    ],
  }},CFG);
}})();


(()=>{{
  const sA=Object.fromEntries(SD['HERALD V6 h64']||[]);
  const sB=Object.fromEntries(SD['Semi mask0.10']||[]);
  const seeds=Object.keys(sA).filter(s=>s in sB).map(Number).sort((a,b)=>a-b);
  const wins=seeds.filter(s=>sB[s]<sA[s]).length;
  const loses=seeds.length-wins;
  const trs=seeds.map(s=>{{
    const win=sB[s]<sA[s];
    return {{type:'scatter',mode:'lines+markers',
      x:['HERALD V6 h64','Semi mask0.10'],y:[sA[s],sB[s]],
      line:{{color:win?'#4caf72':'#e05252',width:2,dash:win?'solid':'dot'}},
      marker:{{size:8}},name:`Seed ${{s}}`,showlegend:false,
      hovertemplate:`Seed ${{s}}<br>V6 h64: ${{sA[s].toFixed(4)}}<br>Semi: ${{sB[s].toFixed(4)}}<br>${{win?'✓ Semi gagne cette seed':'✗ V6 h64 gagne cette seed'}}<extra></extra>`}};
  }});
  Plotly.newPlot('cPaired',trs,{{
    ...BL,showlegend:false,
    title:{{text:`Comparaison appariée seed par seed — Semi gagne ${{wins}}/10 · V6 h64 gagne ${{loses}}/10`,font:{{size:12}}}},
    xaxis:{{...BL.xaxis,type:'category'}},
    yaxis:{{...BL.yaxis,title:'WMAPE par seed',range:[.018,.056]}},
    annotations:[
      {{x:.5,y:.055,text:`<b>Semi gagne ${{wins}}/10</b>`,showarrow:false,
        font:{{color:'#4caf72',size:13}},xanchor:'center'}},
      {{x:.5,y:.051,text:`V6 h64 gagne ${{loses}}/10`,showarrow:false,
        font:{{color:'#e05252',size:11}},xanchor:'center'}},
    ],
  }},CFG);
}})();

// ── E. PAR ANNÉE ─────────────────────────────────────────
(()=>{{
  const cfgs=[
    {{"lbl":"HERALD V6 h64","col":"#4f8ef7"}},
    {{"lbl":"Semi mask0.10","col":"#f7834f"}},
    {{"lbl":"Ridge AR","col":"#4caf72"}},
  ];
  const trs=cfgs.map(({{lbl,col}})=>{{
    const py=PY[lbl]||{{}};
    return {{type:"bar",name:lbl,
      x:YEARS,y:YEARS.map(yr=>py[yr]||0),
      marker:{{color:col,opacity:.88}},
      hovertemplate:"<b>"+lbl+"</b><br>%{{x}} : WMAPE = %{{y:.4f}}<extra></extra>"}};
  }});
  Plotly.newPlot("cYear",trs,{{
    ...BL,barmode:"group",
    title:{{text:"WMAPE par ann\u00e9e \u2014 V6 h64 vs Semi vs Ridge AR (280 zones)",font:{{size:13}}}},
    xaxis:{{...BL.xaxis,title:"Ann\u00e9e de pr\u00e9vision",type:"category"}},
    yaxis:{{...BL.yaxis,title:"WMAPE moyen",range:[0,.15]}},
    shapes:[
      {{type:"rect",x0:-.5,x1:.5,y0:0,y1:.15,fillcolor:"rgba(255,200,0,.07)",line:{{width:0}}}},
      {{type:"rect",x0:3.5,x1:4.5,y0:0,y1:.15,fillcolor:"rgba(139,154,191,.06)",line:{{width:0}}}},
    ],
    annotations:[
      {{x:0,y:.143,text:"Rebond COVID",showarrow:false,font:{{color:"#f7c04f",size:10}},xanchor:"center"}},
      {{x:4,y:.143,text:"2025 : Ridge AR revient",showarrow:false,font:{{color:"#8b9abf",size:10}},xanchor:"center"}},
    ],
  }},CFG);
}})();


// ── F. GRAPHE DYNAMIQUE ───────────────────────────────────
(()=>{{
  const v6i=GTAGS.findIndex(t=>t.indexOf("V6 h64")>=0);
  const gm=v6i>=0?GM[v6i]:(GM[0]||1.0);
  const gg=v6i>=0?GG[v6i]:(GG[0]||0.28);
  const ratio=(gm/Math.max(gg,0.001)).toFixed(1);
  Plotly.newPlot("cGamma",[
    {{type:"bar",orientation:"h",
      x:[gm,gg],
      y:["Mobilit\u00e9 domicile-travail (\u03b3_mob)","G\u00e9ographie zonale (\u03b3_geo)"],
      marker:{{color:["#4f8ef7","#f7834f"],opacity:.9}},
      text:[gm.toFixed(3)+" (\u00d7"+ratio+" vs g\u00e9o)",gg.toFixed(3)],
      textposition:"outside",textfont:{{size:13,color:"#e8eaf0"}},
      hovertemplate:"%{{y}}<br>\u03b3 = %{{x:.4f}}<extra></extra>"}},
  ],{{
    ...BL,showlegend:false,
    title:{{text:"Poids relatifs appris \u2014 Mobilit\u00e9 vs G\u00e9ographie (V6 h64, moy. 10 seeds)",font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:"Valeur gamma",range:[0,1.6]}},
    yaxis:{{...BL.yaxis,automargin:true}},
    margin:{{l:240,r:130,t:50,b:40}},
    annotations:[{{
      x:gm+.02,y:0,text:"<b>Ratio "+ratio+"\u00d7</b>",xanchor:"left",yanchor:"middle",
      showarrow:false,font:{{color:"#4f8ef7",size:14}}
    }}],
  }},CFG);
}})();


(()=>{{
  Plotly.newPlot('cGamma',[
    {{type:'bar',name:'γ_mob — Mobilité',x:GTAGS,y:GM,
      marker:{{color:'#4f8ef7',opacity:.85}},
      hovertemplate:'<b>%{{x}}</b><br>γ_mob = %{{y:.4f}}<extra></extra>'}},
    {{type:'bar',name:'γ_geo — Géographie',x:GTAGS,y:GG,
      marker:{{color:'#f7834f',opacity:.85}},
      hovertemplate:'<b>%{{x}}</b><br>γ_geo = %{{y:.4f}}<extra></extra>'}},
  ],{{
    ...BL,barmode:'group',
    title:{{text:'γ_mob vs γ_geo — poids des deux graphes (appris par le modèle)',font:{{size:12}}}},
    xaxis:{{...BL.xaxis,tickangle:-12}},
    yaxis:{{...BL.yaxis,title:'Valeur gamma moyenne (10 seeds)',range:[0,1.3]}},
    annotations:[{{
      x:.5,y:1.25,xref:'paper',yref:'paper',
      text:'La mobilité pèse en moyenne 3.5× plus que la géographie',
      showarrow:false,font:{{color:'#e8eaf0',size:10}},xanchor:'center',
    }}],
  }},CFG);
}})();

(()=>{{
  const yr_labels=FOLD_YRS.map(y=>String(y));
  const isCovid=yr_labels.map(y=>parseInt(y)>=2020&&parseInt(y)<=2022);
  const preMean=ADJ_V6.slice(0,7).reduce((a,b)=>a+b,0)/Math.max(ADJ_V6.slice(0,7).length,1);
  Plotly.newPlot("cAdjDelta",[
    {{type:"bar",name:"HERALD V6 h64",x:yr_labels,y:ADJ_V6,
      marker:{{color:isCovid.map(c=>c?"#f7c04f":"#4f8ef7"),opacity:.88}},
      hovertemplate:"<b>Transition vers %{{x}}</b><br>adj_delta = %{{y:.4f}}<extra></extra>"}},
    {{type:"scatter",mode:"lines",name:"Moy. pr\u00e9-COVID",
      x:yr_labels,y:yr_labels.map(()=>preMean),
      line:{{color:"#4caf72",width:1.5,dash:"dot"}},showlegend:true,
      hovertemplate:"Moy. pr\u00e9-COVID: "+preMean.toFixed(4)+"<extra></extra>"}},
  ],{{
    ...BL,showlegend:true,
    title:{{text:"Variation structurelle du graphe (adj_delta) \u2014 barres jaunes = p\u00e9riode COVID",font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:"Transition vers l'ann\u00e9e",tickangle:-35}},
    yaxis:{{...BL.yaxis,title:"adj_delta normalis\u00e9",range:[0,.6]}},
    annotations:[
      {{x:"2021",y:.56,text:"COVID : \u00d710\u201320 vs moy. pr\u00e9-2020",showarrow:false,font:{{color:"#f7c04f",size:10}}}},
      {{x:"2015",y:preMean,text:"moy. pr\u00e9-COVID",xanchor:"left",yanchor:"bottom",showarrow:false,font:{{color:"#4caf72",size:9}}}},
    ],
  }},CFG);
}})();

(()=>{{
  const yrs=Object.keys(GATE_V6).map(Number).sort();
  Plotly.newPlot('cGate',[
    {{type:'scatter',mode:'lines+markers',name:'HERALD V6 h64',x:yrs,
      y:yrs.map(y=>GATE_V6[y]||null),line:{{color:'#4f8ef7',width:2.5}},marker:{{size:8}},
      hovertemplate:'V6 h64 · %{{x}} : gate = %{{y:.4f}}<extra></extra>'}},
    {{type:'scatter',mode:'lines+markers',name:'Semi mask0.10',x:yrs,
      y:yrs.map(y=>GATE_SM[y]||null),line:{{color:'#f7834f',width:2.5}},marker:{{size:8}},
      hovertemplate:'Semi · %{{x}} : gate = %{{y:.4f}}<extra></extra>'}},
  ],{{
    ...BL,
    title:{{text:'Gate de mobilité par année — proportion du signal mobilité utilisé (0=géo pur, 1=mob pur)',font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:'Année du fold',dtick:1}},
    yaxis:{{...BL.yaxis,title:'Gate moyen (10 seeds)',range:[.4,.95]}},
    shapes:[{{type:'rect',x0:2019.5,x1:2022.5,y0:.4,y1:.95,
              fillcolor:'rgba(255,200,0,.05)',line:{{width:0}}}}],
    annotations:[{{x:2021,y:.93,text:'Gate↑ pendant COVID',showarrow:false,
                   font:{{color:'#f7c04f',size:10}}}}],
  }},CFG);
}})();

// ── G. GRAFO NO MAPA ─────────────────────────────────────
function updateGraphMap(){{
  const yr=document.getElementById('graphYrSel').value;
  const edges=GRAPH_DATA[yr]||[];
  if(!edges.length){{
    document.getElementById('cGraphMap').innerHTML='<p style="padding:60px;text-align:center;color:#8b9abf">Données non disponibles pour cette année</p>';
    return;
  }}
  // Sort by weight descending
  const sorted=[...edges].sort((a,b)=>b.weight-a.weight);
  const wmax=sorted[0]?.weight||1;
  // Build edge traces (one per edge for hover)
  const edgeTrs=sorted.map(e=>{{
    const w=e.weight/wmax;
    const col=`rgba(79,${{Math.round(142+100*w)}},${{Math.round(247*(1-w)+255*w)}},0.7)`;
    return {{
      type:'scattergeo',mode:'lines',
      lon:[e.lon0,e.lon1],lat:[e.lat0,e.lat1],
      line:{{width:1+w*3,color:col}},
      text:`${{e.name_i}} → ${{e.name_j}}<br>Poids: ${{e.weight.toFixed(4)}}`,
      hovertemplate:'%{{text}}<extra></extra>',
      showlegend:false,
    }};
  }});
  // Node trace
  const allZes=Object.entries(ZE_NAMES);
  const nodeZe=allZes.map(([ze,name])=>ze);
  Plotly.newPlot('cGraphMap',[
    ...edgeTrs,
    {{type:'scattergeo',mode:'markers',
      lon:allZes.map(([ze])=>{{const info=Object.values(window._ze_centroids||{{}}).find(v=>v.ze_str===ze);return info?info.lon:null}}),
      lat:allZes.map(([ze])=>{{const info=Object.values(window._ze_centroids||{{}}).find(v=>v.ze_str===ze);return info?info.lat:null}}),
      text:allZes.map(([ze,n])=>n),
      marker:{{size:3,color:'#8b9abf',opacity:.5}},
      hovertemplate:'<b>%{{text}}</b><extra></extra>',
      showlegend:false}},
  ],{{
    ...BL,
    title:{{text:`Top-40 connexions du graphe dynamique — année ${{yr}} · épaisseur/couleur = force de la connexion`,font:{{size:12}}}},
    geo:{{
      scope:'europe',center:{{lon:2.5,lat:46.5}},
      projection:{{type:'mercator',scale:5.5}},
      showframe:false,showcoastlines:true,coastlinecolor:'#3a4060',
      showland:true,landcolor:'#181b28',showocean:true,oceancolor:'#0f1117',
      lonaxis:{{range:[-5.5,10]}},lataxis:{{range:[41,52]}},bgcolor:'#0f1117',
    }},
    margin:{{l:0,r:0,t:50,b:0}},
  }},CFG);
}}

// Pour la carte du graphe, on a besoin des centroides des ZEs
// On va les extraire du GEOJSON en calculant le centre de la bbox
(()=>{{
  if(!GEOJSON) return;
  const centroids={{}};
  GEOJSON.features.forEach(feat=>{{
    const ze=feat.properties.ze2020;
    // Centroide approché = centre de la bounding box
    const coords=feat.geometry.type==='Polygon'?feat.geometry.coordinates[0]:
                 feat.geometry.coordinates[0][0];
    if(!coords||!coords.length) return;
    const lons=coords.map(c=>c[0]), lats=coords.map(c=>c[1]);
    centroids[ze]={{
      ze_str:ze,
      lon:(Math.min(...lons)+Math.max(...lons))/2,
      lat:(Math.min(...lats)+Math.max(...lats))/2,
    }};
  }});
  window._ze_centroids=centroids;
  // Replot avec centroides
  const yr=document.getElementById('graphYrSel').value;
  const edges=GRAPH_DATA[yr]||[];
  if(!edges.length) return;
  const sorted=[...edges].sort((a,b)=>b.weight-a.weight);
  const wmax=sorted[0]?.weight||1;
  const edgeTrs=sorted.map(e=>{{
    const w=e.weight/wmax;
    return {{
      type:'scattergeo',mode:'lines',
      lon:[e.lon0,e.lon1],lat:[e.lat0,e.lat1],
      line:{{width:1+w*3,color:`rgba(${{Math.round(247-150*w)}},${{Math.round(131+80*w)}},${{Math.round(79+150*w)}},0.75)`}},
      text:`<b>${{e.name_i}}</b> → <b>${{e.name_j}}</b><br>Poids: ${{e.weight.toFixed(4)}}`,
      hovertemplate:'%{{text}}<extra></extra>',showlegend:false,
    }};
  }});
  const allC=Object.entries(centroids);
  Plotly.newPlot('cGraphMap',[
    ...edgeTrs,
    {{type:'scattergeo',mode:'markers',
      lon:allC.map(([,c])=>c.lon),lat:allC.map(([,c])=>c.lat),
      text:allC.map(([ze])=>ZE_NAMES[ze]||ze),
      marker:{{size:3,color:'#6b7ab5',opacity:.4}},
      hovertemplate:'<b>%{{text}}</b><extra></extra>',showlegend:false}},
  ],{{
    ...BL,
    title:{{text:`Top-40 connexions du graphe dynamique appris — ${{yr}} · jaune/large = fort · bleu/fin = faible`,font:{{size:12}}}},
    geo:{{scope:'europe',center:{{lon:2.5,lat:46.5}},projection:{{type:'mercator',scale:5.5}},
      showframe:false,showcoastlines:true,coastlinecolor:'#3a4060',
      showland:true,landcolor:'#181b28',showocean:true,oceancolor:'#0f1117',
      lonaxis:{{range:[-5.5,10]}},lataxis:{{range:[41,52]}},bgcolor:'#0f1117'}},
    margin:{{l:0,r:0,t:50,b:0}},
  }},CFG);
}})();

document.getElementById('graphYrSel').onchange=()=>{{
  if(!window._ze_centroids) return;
  const yr=document.getElementById('graphYrSel').value;
  const edges=GRAPH_DATA[yr]||[];
  const sorted=[...edges].sort((a,b)=>b.weight-a.weight);
  const wmax=sorted[0]?.weight||1;
  const edgeTrs=sorted.map(e=>{{
    const w=e.weight/wmax;
    return {{type:'scattergeo',mode:'lines',lon:[e.lon0,e.lon1],lat:[e.lat0,e.lat1],
      line:{{width:1+w*3,color:`rgba(${{Math.round(247-150*w)}},${{Math.round(131+80*w)}},${{Math.round(79+150*w)}},0.75)`}},
      text:`<b>${{e.name_i}}</b> → <b>${{e.name_j}}</b><br>Poids: ${{e.weight.toFixed(4)}}`,
      hovertemplate:'%{{text}}<extra></extra>',showlegend:false}};
  }});
  const allC=Object.entries(window._ze_centroids);
  Plotly.newPlot('cGraphMap',[...edgeTrs,
    {{type:'scattergeo',mode:'markers',lon:allC.map(([,c])=>c.lon),lat:allC.map(([,c])=>c.lat),
      text:allC.map(([ze])=>ZE_NAMES[ze]||ze),
      marker:{{size:3,color:'#6b7ab5',opacity:.4}},
      hovertemplate:'<b>%{{text}}</b><extra></extra>',showlegend:false}}],
    {{...BL,
    title:{{text:`Top-40 connexions du graphe dynamique appris — ${{yr}} · jaune/large = fort · bleu/fin = faible`,font:{{size:12}}}},
    geo:{{scope:'europe',center:{{lon:2.5,lat:46.5}},projection:{{type:'mercator',scale:5.5}},
      showframe:false,showcoastlines:true,coastlinecolor:'#3a4060',showland:true,
      landcolor:'#181b28',showocean:true,oceancolor:'#0f1117',
      lonaxis:{{range:[-5.5,10]}},lataxis:{{range:[41,52]}},bgcolor:'#0f1117'}},
    margin:{{l:0,r:0,t:50,b:0}}}},CFG);
}};

// ── H. CARTE ERREURS ─────────────────────────────────────
function updateMap(){{
  const mdl=document.getElementById("mapMdl").value;
  const yr=document.getElementById("mapYr").value;
  const grpEl=document.getElementById("mapYrGroup");
  if(grpEl) grpEl.style.display=(mdl==="sector")?"none":"inline";
  const geo=GEOJSON;
  const zcs=geo.features.map(f=>f.properties.ze2020);
  const names=zcs.map(z=>ZE_NAMES[z]||z);
  const GEO={{scope:"europe",center:{{lon:2.5,lat:46.5}},projection:{{type:"mercator",scale:5.5}},
    showframe:false,showcoastlines:true,coastlinecolor:"#3a4060",
    showland:true,landcolor:"#181b28",showocean:true,oceancolor:"#0f1117",
    lonaxis:{{range:[-5.5,10]}},lataxis:{{range:[41,52]}},bgcolor:"#0f1117"}};
  const regClick=gd=>gd.on("plotly_click",d=>{{
    if(d.points&&d.points[0]){{const loc=d.points[0].location;if(loc)onZoneClick(loc);}}
  }});
  if(mdl==="sector"){{
    const byZe={{}};SEC_MAP.forEach(r=>byZe[r.ze]=r);
    const secTrs=SECS.map(sec=>{{
      const secZes=zcs.filter(z=>byZe[z]&&byZe[z].dominant===sec);
      if(!secZes.length) return null;
      return {{
        type:"choropleth",geojson:geo,locations:secZes,z:secZes.map(()=>1),
        featureidkey:"properties.ze2020",
        colorscale:[[0,SEC_COLORS[sec]],[1,SEC_COLORS[sec]]],
        zmin:0,zmax:1,showscale:false,
        name:sec+" \u2014 "+SEC_FULL[sec],
        marker:{{line:{{width:.5,color:"#0f1117"}}}},
        text:secZes.map(z=>{{
          const r=byZe[z];if(!r)return z;
          return "<b>"+(ZE_NAMES[z]||z)+"</b> (ZE "+z+")<br>Dominant: "+sec+" \u2014 "+SEC_FULL[sec]+"<br>"+SECS.map(s=>s+": "+(r[s]*100).toFixed(1)+"%").join("<br>");
        }}),
        hovertemplate:"%{{text}}<extra></extra>",showlegend:true
      }};
    }}).filter(Boolean);
    Plotly.newPlot("cMap",secTrs,{{
      ...BL,
      title:{{text:"Secteur A10 dominant par zone d'emploi \u2014 survolez pour la composition",font:{{size:13}}}},
      geo:GEO,margin:{{l:0,r:0,t:50,b:0}},legend:{{x:1.01,y:.5,font:{{size:10}}}},
    }},CFG).then(regClick);
  }} else {{
    const src_v6=ZONE_V6[yr]||{{}},src_sm=ZONE_SEMI[yr]||{{}};
    let vals,title,cs,zmn,zmx;
    if(mdl==="diff"){{
      vals=zcs.map(z=>{{const s=src_sm[z],v=src_v6[z];return(s&&v)?(s-v):null}});
      const vv=vals.filter(x=>x!==null);const ma=Math.max(...vv.map(Math.abs));
      zmn=-ma;zmx=ma;
      title="Diff\u00e9rence Semi \u2212 V6 h64 \u00b7 "+(yr==="all"?"2021\u20132025":yr)+" (rouge = Semi pire)";
      cs=[[0,"#2166ac"],[.5,"#f7f7f7"],[1,"#d73027"]];
    }} else {{
      vals=zcs.map(z=>(mdl==="v6"?src_v6:src_sm)[z]||null);
      const vv=vals.filter(x=>x!==null);
      zmn=Math.min(...vv);zmx=Math.max(...vv);
      title=(mdl==="v6"?"HERALD V6 h64":"HERALD Semi mask0.10")+" \u00b7 "+(yr==="all"?"Moyenne 2021\u20132025":yr);
      cs=[[0,"#fff5eb"],[.25,"#fdd0a2"],[.5,"#fdae6b"],[.75,"#f16913"],[1,"#7f2704"]];
    }}
    Plotly.newPlot("cMap",[{{
      type:"choropleth",geojson:geo,locations:zcs,z:vals,
      featureidkey:"properties.ze2020",
      colorscale:cs,zmin:zmn,zmax:zmx,
      colorbar:{{title:"WMAPE",thickness:14,len:.7,tickformat:".3f"}},
      marker:{{line:{{width:.5,color:"#0f1117"}}}},
      text:zcs.map((z,i)=>"<b>"+names[i]+"</b> (ZE "+z+")<br>WMAPE: "+(vals[i]!==null?(vals[i]*100).toFixed(2)+"%":"N/D")),
      hovertemplate:"%{{text}}<extra></extra>",
    }}],{{
      ...BL,title:{{text:title,font:{{size:13}}}},
      geo:GEO,margin:{{l:0,r:0,t:50,b:0}},
    }},CFG).then(regClick);
  }}
}}
updateMap();

// ── I. SECTEURS A10 ───────────────────────────────────────
(()=>{{ // (carte sectorielle via option "Secteur A10" dans la carte H)
  const secTrsW=Object.entries(SEC_WMAPE).map(([lbl,sw])=>{{
    const pal2={{'HERALD V6 h64':'#4f8ef7','Semi mask0.10':'#f7834f','Semi λ A10':'#17c3d4'}};
    return {{type:'bar',name:lbl,x:SECS,y:SECS.map(s=>sw[s]||0),
      marker:{{color:pal2[lbl]||'#aaa',opacity:.85}},
      hovertemplate:`<b>${{lbl}}</b><br>Secteur %{{x}}: %{{y:.4f}}<br>${{SECS.map(s=>SEC_FULL[s])['dummy']}}<extra></extra>`}};
  }});
  Plotly.newPlot('cSecWmape',secTrsW,{{
    ...BL,barmode:'group',
    title:{{text:'WMAPE sectoriel A10 — erreur par secteur',font:{{size:11}}}},
    xaxis:{{...BL.xaxis,title:'Secteur A10'}},
    yaxis:{{...BL.yaxis,title:'WMAPE moyen (10 seeds)',range:[0,.65]}},
    shapes:[{{type:'line',x0:-.5,x1:8.5,y0:.031,y1:.031,
              line:{{color:'#4f8ef7',width:1.5,dash:'dash'}}}}],
    annotations:[{{x:8,y:.031,text:'WMAPE total V6',showarrow:false,
                   font:{{color:'#4f8ef7',size:9}},yanchor:'bottom'}}],
  }},CFG);
}})();

// ── J. PRÉ-COVID ─────────────────────────────────────────
(()=>{{
  const yrs=Object.keys(PC_PY).map(Number).sort();
  const precBars={{type:"bar",name:"HERALD Semi pr\u00e9-COVID 2016\u20132019",
    x:yrs,y:yrs.map(y=>PC_PY[y]),marker:{{color:"#f7c04f",opacity:.88}},
    hovertemplate:"HERALD Semi %{{x}} : WMAPE = %{{y:.4f}}<extra></extra>"}};
  const postYrs=YEARS;
  const v6post={{type:"bar",name:"HERALD V6 h64 post-COVID 2021\u20132025",
    x:postYrs,y:postYrs.map(yr=>(PY["HERALD V6 h64"]||{{}})[yr]||0),
    marker:{{color:"#4f8ef7",opacity:.88}},
    hovertemplate:"HERALD V6 %{{x}} : WMAPE = %{{y:.4f}}<extra></extra>"}};
  const ridgePost={{type:"scatter",mode:"markers+lines",name:"Ridge AR post-COVID",
    x:postYrs,y:postYrs.map(yr=>RIDGE_YR[String(yr)]||null),
    marker:{{color:"#4caf72",size:9}},line:{{color:"#4caf72",width:2}},
    hovertemplate:"Ridge AR %{{x}} : %{{y:.4f}}<extra></extra>"}};
  Plotly.newPlot("cPrecovid",[precBars,v6post,ridgePost],{{
    ...BL,barmode:"group",
    title:{{text:"HERALD avant/apr\u00e8s COVID \u2014 avantage sur Ridge AR r\u00e9duit de 87% en pr\u00e9-COVID",font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:"Ann\u00e9e de pr\u00e9vision",dtick:1}},
    yaxis:{{...BL.yaxis,title:"WMAPE moyen (280 zones)",range:[0,.20]}},
    shapes:[{{type:"rect",x0:2019.5,x1:2020.5,y0:0,y1:.20,fillcolor:"rgba(100,100,100,.12)",line:{{width:0}}}}],
    annotations:[
      {{x:2016,y:.14,text:"Historique court",showarrow:true,arrowhead:2,arrowcolor:"#8b9abf",font:{{color:"#8b9abf",size:9}},ax:25,ay:18}},
      {{x:2020,y:.19,text:"Rupture COVID",showarrow:false,font:{{color:"#8b9abf",size:9}},xanchor:"center"}},
      {{x:2019,y:.008,text:"Avantage pr\u00e9-COVID: -0.004",showarrow:false,font:{{color:"#f7c04f",size:9}},xanchor:"right"}},
      {{x:2024,y:.008,text:"Avantage post-COVID: -0.033 (x8)",showarrow:false,font:{{color:"#4f8ef7",size:9}},xanchor:"center"}},
    ],
  }},CFG);
}})();

// ──── INTERATIVIDADE DE ZONAS ────
let selectedZone = null;

function onZoneClick(zeId) {{
  selectedZone = zeId;
  const name = ZE_NAMES[zeId] || ("ZE " + zeId);
  document.getElementById("zone-breadcrumb").textContent = "Zone : " + name;
  const panel = document.getElementById("panel-regional");
  panel.style.display = "block";
  panel.scrollIntoView({{behavior:"smooth", block:"nearest"}});
  updateRegionalTimeseries(zeId);
  updateRegionalSectors(zeId);
  updateRegionalEdges(zeId);
}}

function clearSelection() {{
  selectedZone = null;
  document.getElementById('panel-regional').style.display = 'none';
}}

function updateRegionalTimeseries(zeId) {{
  const data = ZONE_TIMESERIES[zeId];
  if (!data) return;
  const years = ['2021','2022','2023','2024','2025'];
  const v6_wmapes = years.map(y => data.v6?.[y] ?? null);
  const semi_wmapes = years.map(y => data.semi?.[y] ?? null);
  Plotly.newPlot('regional-timeseries',[
    {{type:'scatter',mode:'lines+markers',name:'V6',x:years,y:v6_wmapes,line:{{color:'#4f8ef7',width:2}},marker:{{size:6}}}},
    {{type:'scatter',mode:'lines+markers',name:'Semi',x:years,y:semi_wmapes,line:{{color:'#f7834f',width:2}},marker:{{size:6}}}}
  ],{{...BL,title:{{text:'WMAPE par année',font:{{size:11}}}},xaxis:{{...BL.xaxis,title:'Année'}},yaxis:{{...BL.yaxis,title:'WMAPE',tickformat:'.1%'}},margin:{{l:60,r:20,t:40,b:40}}}},CFG);
}}

function updateRegionalSectors(zeId) {{
  const sectors = ZONE_SECTOR_COMP[zeId];
  if (!sectors) return;
  const secs = Object.keys(sectors);
  Plotly.newPlot('regional-sectors',[{{type:'pie',labels:secs.map(s=>s+' '+SEC_FULL[s]),values:secs.map(s=>sectors[s]),marker:{{colors:secs.map(s=>SEC_COLORS[s])}}}}],{{...BL,title:{{text:'Composition sectorielle',font:{{size:11}}}}}},CFG);
}}

function updateRegionalEdges(zeId) {{
  const edges = ZONE_EDGES[zeId];
  if (!edges || (!edges.in.length && !edges.out.length)) return;
  const allEdges = [...edges.out.map(e=>{{return{{name:'→ '+e.name,weight:e.weight,type:'out'}}}}),...edges.in.map(e=>{{return{{name:'← '+e.name,weight:e.weight,type:'in'}}}})].sort((a,b)=>b.weight-a.weight).slice(0,10);
  if (!allEdges.length) return;
  Plotly.newPlot('regional-edges',[{{type:'bar',orientation:'h',y:allEdges.map(e=>e.name),x:allEdges.map(e=>e.weight),marker:{{color:allEdges.map(e=>e.type==='out'?'#4f8ef7':'#f7834f')}}}}],{{...BL,title:{{text:'Top 10 connexions',font:{{size:11}}}},xaxis:{{...BL.xaxis,title:'Poids'}},yaxis:{{...BL.yaxis,automargin:true}},margin:{{l:160,r:20,t:40,b:40}}}},CFG);
}}


</script>
</body>
</html>"""

with open(OUT,"w",encoding="utf-8") as f:
    f.write(HTML)
print(f"Dashboard: {OUT}")
print(f"Tamanho: {os.path.getsize(OUT)/1024/1024:.1f} MB")
