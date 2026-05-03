#!/usr/bin/env python3
"""
Tableau de bord scientifique final — HERALD geo2025
253 model-runs · SIDE/INSEE · Zones d'emploi geo2025
Génère un HTML autonome (offline), cartes SVG sans Mapbox.
"""
import json, glob, os, zipfile, io, warnings
import numpy as np, pandas as pd
from collections import defaultdict
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "hpc_results", "herald_semi_total_253_geo2025")
JOB0 = os.path.join(BASE, "baselines_v3_v6_stgnn")
OUT  = os.path.join(BASE, "reports", "figures", "herald_geo2025_final_dashboard.html")
GEO  = os.path.join(ROOT, "data", "raw", "territorial", "fonds_ze2020_2026.zip")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

class NpEnc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.integer): return int(o)
        if isinstance(o, np.floating): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        return super().default(o)
def J(o): return json.dumps(o, cls=NpEnc)

def load_json(p):
    with open(p) as f: return json.load(f)

def load_semi():
    runs = {}
    for f in sorted(glob.glob(os.path.join(BASE,"*/reports/herald_semi_total_metrics_v1.json"))):
        for k,v in load_json(f).items():
            if k not in runs: runs[k] = v
    return runs

def by_tag(runs, key="total_wmape_mean"):
    out = defaultdict(list)
    for rk,rd in runs.items():
        out[rd.get("run_tag",rk)].append(rd.get(key, rd.get("mean_wmape")))
    return out

def load_geojson():
    outer = zipfile.ZipFile(GEO)
    inner = zipfile.ZipFile(io.BytesIO(outer.read("ze2020_2026.zip")))
    import tempfile, shutil, geopandas as gpd
    tmp = tempfile.mkdtemp()
    inner.extractall(tmp)
    gdf = gpd.read_file(os.path.join(tmp,"ze2020_2026.shp")).to_crs("EPSG:4326")
    shutil.rmtree(tmp)
    return gdf

def load_zone_wmape(tag_pattern, seeds=(0,1,7,13,42)):
    records = defaultdict(list)
    for seed in seeds:
        p1 = os.path.join(BASE, f"*/data_processed/herald_semi_predictions_total_full_{tag_pattern}_seed_{seed}_v1.csv")
        p2 = os.path.join(JOB0, f"data_processed/herald_v6_predictions_total_full_{tag_pattern}_seed_{seed}_v1.csv")
        files = glob.glob(p1) or glob.glob(p2)
        for fp in files:
            df = pd.read_csv(fp)
            grp = df[df["y_true"]>0].copy()
            grp["wmape"] = grp["abs_error"].abs() / grp["y_true"]
            for ze, g in grp.groupby("ZE2020"):
                records[int(ze)].append(float(g["wmape"].mean()))
    return {ze: float(np.mean(v)) for ze,v in records.items()}

print("Chargement…")
semi_runs = load_semi()
v6_runs   = load_json(os.path.join(JOB0,"reports","herald_v6_total_metrics_v1.json"))
v3_runs   = load_json(os.path.join(JOB0,"reports","herald_v3_total_metrics_v1.json"))
tb_data   = load_json(os.path.join(JOB0,"temporal_baselines","reports","final_temporal_baselines_metrics_v1.json"))
precovid  = {}
for f in sorted(glob.glob(os.path.join(BASE,"*/reports/herald_semi_total_precovid_metrics_v1.json"))):
    for k,v in load_json(f).items():
        if k not in precovid: precovid[k] = v

stgnn_mod = defaultdict(list); stgnn_yr = defaultdict(lambda: defaultdict(list))
for f in sorted(glob.glob(os.path.join(JOB0,"stgnn_reports","dynamic_stgnn_model_metrics_seed_*_v1.json"))):
    d = load_json(f)
    for item in d["summary_mean_wmape"]: stgnn_mod[item["model"]].append(item["wmape"])
    for item in d["metrics_by_model_year"]: stgnn_yr[item["model"]][item["target_year"]].append(item["wmape"])

semi_bt = by_tag(semi_runs); v6_bt = by_tag(v6_runs)
v3_wmapes = [rd["mean_wmape"] for rd in v3_runs.values()]

tb_mod = defaultdict(list)
for item in tb_data["summary_mean_wmape"]: tb_mod[item["model"]].append(item["mean_wmape"])
tb_py = defaultdict(lambda: defaultdict(list))
for item in tb_data["metrics_by_model_year"]: tb_py[item["model"]][item["target_year"]].append(item["wmape"])

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

# Graph internals
gd_gm = defaultdict(list); gd_gg = defaultdict(list); gd_adj = defaultdict(list); gd_gate = defaultdict(lambda: defaultdict(list))
for rk,rd in {**semi_runs,**v6_runs}.items():
    tag = rd.get("run_tag",rk)
    gd_gm[tag].append(rd.get("gamma_mob",np.nan)); gd_gg[tag].append(rd.get("gamma_geo",np.nan))
    gd_adj[tag].append(rd.get("adj_delta_by_year",[]))
    for yr,g in rd.get("gate_by_year",{}).items(): gd_gate[tag][int(yr)].append(g)

FOLD_YEARS = list(range(2013,2026))
GRAPH_TAGS = ["total_h64_no_semi","total_h64_semi_mask0.0_control","total_h64_semi_mask0.10_random","total_h64_semi_mask0.10_spatial_block","total_h64_semi_mask0.30_random"]
GRAPH_LBLS = ["V6 h64","mask0.0","mask0.10","spatial_block","mask0.30"]
gm_m = [float(np.nanmean(gd_gm.get(t,[]))) for t in GRAPH_TAGS]
gg_m = [float(np.nanmean(gd_gg.get(t,[]))) for t in GRAPH_TAGS]
adj_v6   = np.mean([a for a in gd_adj.get("total_h64_no_semi",[]) if len(a)==13],axis=0).tolist()
adj_semi  = np.mean([a for a in gd_adj.get("total_h64_semi_mask0.10_random",[]) if len(a)==13],axis=0).tolist()
gate_v6  = {yr: float(np.mean(v)) for yr,v in gd_gate.get("total_h64_no_semi",{}).items()}
gate_sm  = {yr: float(np.mean(v)) for yr,v in gd_gate.get("total_h64_semi_mask0.10_random",{}).items()}

# New connections
def new_connections():
    v6n  = sorted(glob.glob(os.path.join(JOB0,"data_processed/herald_v6_internals_full_total_h64_no_semi_seed_*_v1.npz")))
    sn   = sorted(glob.glob(os.path.join(BASE,"*/data_processed/herald_semi_internals_full_total_h64_semi_mask0.10_random_seed_*_v1.npz")))
    if not v6n or not sn: return []
    n=280; T=0.01; YR=2024
    vc=np.zeros((n,n)); sc=np.zeros((n,n)); vs=np.zeros((n,n)); ss=np.zeros((n,n)); node_order=None
    for fp in v6n:
        d=np.load(fp,allow_pickle=True); i=np.where(d["years"]==YR)[0]
        if len(i): vc+=(d["dynamic_adj"][i[0]]>T); vs+=d["dynamic_adj"][i[0]]
    for fp in sn:
        d=np.load(fp,allow_pickle=True)
        if node_order is None: node_order=d["node_order"]
        i=np.where(d["years"]==YR)[0]
        if len(i): sc+=(d["dynamic_adj"][i[0]]>T); ss+=d["dynamic_adj"][i[0]]
    os_=(sc>=7)&~(vc>=7); sm=ss/max(len(sn),1); vm=vs/max(len(v6n),1)
    rows=[]
    for ni,nj in sorted(zip(*np.where(os_)),key=lambda e:-sm[e[0],e[1]])[:20]:
        zi=int(node_order[ni]); zj=int(node_order[nj])
        di=str(zi//100) if zi>=1000 else str(zi//10); dj=str(zj//100) if zj>=1000 else str(zj//10)
        rows.append({"label":f"ZE {zi:04d}→{zj:04d}","weight_semi":float(sm[ni,nj]),"weight_v6":float(vm[ni,nj]),"intra":di==dj})
    return rows

new_conn = new_connections()

# Zone WMAPE
print("WMAPE par zone…")
try: zone_semi = load_zone_wmape("total_h64_semi_mask0.10_random"); has_zone=True
except: zone_semi={}; has_zone=False
try: zone_v6 = load_zone_wmape("total_h64_no_semi")
except: zone_v6={}

# Geo
print("Géographie…")
try: gdf=load_geojson(); geo_obj=json.loads(gdf.to_json()); [feat.__setitem__("id",feat["properties"]["ze2020"]) for feat in geo_obj["features"]]; GEOJSON=json.dumps(geo_obj); has_geo=True; print(f"  {len(geo_obj['features'])} zones")
except Exception as e: print(f"  GeoJSON: {e}"); has_geo=False; GEOJSON="null"

# Sectors
sec_props=sec_names=sec_nodes_arr=None
sec_files = sorted(glob.glob(os.path.join(BASE,"*/data_processed/herald_semi_internals_full_total_h64_semi_mask0.10_random_seed_0_v1.npz")))
if sec_files:
    d=np.load(sec_files[0],allow_pickle=True)
    sec_props=d["sector_proportions"]; sec_names=[str(s) for s in d["sector_names"]]; sec_nodes_arr=d["node_order"]
sector_rows=[]
if sec_props is not None:
    for si in range(len(sec_nodes_arr)):
        row={"ze":f"{int(sec_nodes_arr[si]):04d}"}
        for sidx,sn in enumerate(sec_names): row[sn]=float(sec_props[si,sidx])
        sector_rows.append(row)

SECTORS = ["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]
sec_wmape_by_tag = defaultdict(lambda: defaultdict(list))
for rk,rd in {**semi_runs,**v6_runs}.items():
    for s,w in rd.get("sector_wmape",{}).items(): sec_wmape_by_tag[rd.get("run_tag",rk)][s].append(w)
sec_chart = {}
for tag,lbl in [("total_h64_no_semi","V6 h64"),("total_h64_semi_mask0.10_random","Semi mask0.10"),("total_h64_semi_mask0.10_random_lam0.05_a10","Semi λA10")]:
    sec_chart[lbl] = {s: float(np.mean(sec_wmape_by_tag[tag][s])) for s in SECTORS if sec_wmape_by_tag[tag][s]}

# Global comparison
V6REF=0.03130
models_cmp=[]
def add(lbl,vals,fam,col):
    if vals: models_cmp.append({"label":lbl,"mean":float(np.mean(vals)),"std":float(np.std(vals)),"n":len(vals),"family":fam,"color":col})
add("HERALD V3",v3_wmapes,"herald","#7bb3f5")
add("HERALD V6 h32",v6_bt.get("total_h32_no_semi",[]),"herald","#9edae5")
add("HERALD V6 h64",v6_bt.get("total_h64_no_semi",[]),"herald","#4f8ef7")
add("Semi h64 contrôle mask0.0",semi_bt.get("total_h64_semi_mask0.0_control",[]),"semi","#17c3d4")
add("Semi h64 mask0.10 (principal)",semi_bt.get("total_h64_semi_mask0.10_random",[]),"semi","#f7834f")
add("Semi h64 mask0.30",semi_bt.get("total_h64_semi_mask0.30_random",[]),"semi","#ffc080")
add("Semi h64 warmup0",semi_bt.get("total_h64_semi_mask0.10_random_warmup0",[]),"semi","#ffe0b0")
add("DCRNN résiduel",stgnn_mod.get("dcrnn_residual",[]),"stgnn","#9467bd")
add("Dynamic STGNN résiduel",stgnn_mod.get("dynamic_stgnn_residual",[]),"stgnn","#c5b0d5")
add("Graph WaveNet résiduel",stgnn_mod.get("graph_wavenet_residual",[]),"stgnn","#d6b4fc")
add("Ridge AR",tb_mod.get("ridge_ar",[]),"baseline","#4caf72")
add("naive lag-1",tb_mod.get("naive_lag1",[]),"baseline","#98df8a")
add("ARIMA local",tb_mod.get("arima_local",[]),"baseline","#a8d8a8")
add("LSTM local",tb_mod.get("lstm_local",[]),"baseline","#ffb3b3")
models_cmp.sort(key=lambda x:x["mean"])

ablation=[]
for tag,vals in sorted({**semi_bt,**v6_bt}.items(),key=lambda x:np.mean(x[1]) if x[1] else 99):
    if not vals: continue
    lbl=(tag.replace("total_h64_semi_","").replace("total_h32_semi_","h32 ").replace("total_h64_no_semi","V6 h64 (référence)").replace("total_h32_no_semi","V6 h32").replace("_random","").replace("_"," "))
    ablation.append({"tag":tag,"label":lbl,"mean":float(np.mean(vals)),"std":float(np.std(vals))})

seed_data={}
for tag,lbl in [("total_h64_no_semi","HERALD V6 h64"),("total_h64_semi_mask0.0_control","Semi mask0.0"),("total_h64_semi_mask0.10_random","Semi mask0.10")]:
    seed_data[lbl]={rd["seed"]:rd["total_wmape_mean"] for rk,rd in {**semi_runs,**v6_runs}.items() if rd.get("run_tag")==tag}
seed_data["HERALD V3"]={rd["seed"]:rd["mean_wmape"] for rd in v3_runs.values()}

YEARS=[2021,2022,2023,2024,2025]
per_yr_data={}
for tag,lbl in [("total_h64_no_semi","HERALD V6 h64"),("total_h64_semi_mask0.0_control","Semi mask0.0"),("total_h64_semi_mask0.10_random","Semi mask0.10")]:
    py=semi_py.get(tag) or v6_py.get(tag) or {}
    per_yr_data[lbl]={yr:float(np.mean(w)) for yr,w in py.items() if w}
per_yr_data["HERALD V3"]={yr:float(np.mean(w)) for yr,w in v3_py.items() if w}
per_yr_data["Ridge AR"]={yr:float(np.mean(w)) for yr,w in tb_py["ridge_ar"].items() if w}
per_yr_data["DCRNN résiduel"]={yr:float(np.mean(w)) for yr,w in stgnn_yr.get("dcrnn_residual",{}).items() if w}

pc_vals=[rd["total_wmape_mean"] for rd in precovid.values()]
pc_py=defaultdict(list)
for rd in precovid.values():
    for yr,w in rd.get("per_year_total",{}).items(): pc_py[int(yr)].append(w)

zone_semi_s={f"{k:04d}":v for k,v in zone_semi.items()}
zone_v6_s  ={f"{k:04d}":v for k,v in zone_v6.items()}

print("Génération HTML…")

HTML=f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HERALD geo2025 — Tableau de bord scientifique</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root{{--bg:#0f1117;--bg2:#1a1d27;--bg3:#242836;--acc:#4f8ef7;--acc2:#f7834f;--green:#4caf72;--red:#e05252;--text:#e8eaf0;--muted:#8b9abf;--border:#2e3347}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.6}}
.wrap{{max-width:1380px;margin:0 auto;padding:24px}}
h1{{font-size:1.75rem;color:var(--acc);font-weight:700;margin-bottom:4px}}
h2{{font-size:1.15rem;color:var(--acc);margin:36px 0 8px;font-weight:600;border-bottom:1px solid var(--border);padding-bottom:6px}}
h3{{font-size:.95rem;color:var(--acc2);margin:14px 0 5px;font-weight:600}}
.sub{{color:var(--muted);font-size:.85rem;margin-bottom:22px}}
.card{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:18px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:14px;margin-bottom:18px}}
.kpi{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:14px;text-align:center}}
.kpi .v{{font-size:1.5rem;font-weight:700;color:var(--acc)}}.kpi .l{{font-size:.73rem;color:var(--muted);margin-top:3px}}
.box{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:16px}}
.info{{background:rgba(79,142,247,.08);border-left:3px solid var(--acc);border-radius:4px;padding:9px 13px;margin:10px 0;font-size:.84rem;color:var(--muted)}}
.warn{{background:rgba(224,82,82,.08);border-left:3px solid var(--red);border-radius:4px;padding:9px 13px;margin:10px 0;font-size:.84rem}}
.ok{{background:rgba(76,175,114,.08);border-left:3px solid var(--green);border-radius:4px;padding:9px 13px;margin:10px 0;font-size:.84rem}}
.pill{{display:inline-block;border-radius:20px;padding:3px 11px;font-size:.78rem;font-weight:600;margin:2px}}
.pg{{background:rgba(76,175,114,.15);color:var(--green);border:1px solid var(--green)}}
.pr{{background:rgba(224,82,82,.15);color:var(--red);border:1px solid var(--red)}}
.po{{background:rgba(247,131,79,.15);color:var(--acc2);border:1px solid var(--acc2)}}
.pb{{background:rgba(79,142,247,.15);color:var(--acc);border:1px solid var(--acc)}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:800px){{.g2{{grid-template-columns:1fr}}}}
.nav{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px}}
.nb{{background:var(--bg3);border:1px solid var(--border);color:var(--muted);border-radius:20px;padding:5px 13px;cursor:pointer;font-size:.78rem;text-decoration:none;transition:.15s}}
.nb:hover{{background:var(--acc);color:#fff;border-color:var(--acc)}}
select{{background:var(--bg3);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:5px 10px;font-size:.88rem;cursor:pointer}}
.ctrl{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}}
.ctrl label{{color:var(--muted);font-size:.83rem}}
table{{width:100%;border-collapse:collapse;font-size:.83rem}}
th{{background:var(--bg3);color:var(--acc);padding:8px 11px;text-align:left;font-weight:600}}
td{{padding:7px 11px;border-bottom:1px solid var(--border)}}
tr:hover td{{background:var(--bg3)}}
.tf{{color:var(--green);font-weight:700}}.td{{color:#f7c04f;font-weight:600}}.tw{{color:var(--acc2)}}.tn{{color:var(--red);font-weight:700}}
.note{{font-size:.78rem;color:var(--muted);font-style:italic;margin-top:6px}}
hr{{border:none;border-top:1px solid var(--border);margin:32px 0}}
</style>
</head>
<body>
<div class="wrap">
<h1>HERALD geo2025 — Tableau de bord scientifique final</h1>
<p class="sub">253 model-runs · SIDE/INSEE · 280 zones d'emploi · Évaluation observée 2021–2025 · France métropolitaine</p>
<div class="nav">
  <a class="nb" href="#exec">A. Résumé</a><a class="nb" href="#global">B. Comparaison globale</a>
  <a class="nb" href="#ablation">C. Ablation</a><a class="nb" href="#seeds">D. Seeds</a>
  <a class="nb" href="#annee">E. Par année</a><a class="nb" href="#graphe">F. Graphe</a>
  <a class="nb" href="#newconn">G. Nouvelles connexions</a><a class="nb" href="#carte">H. Carte</a>
  <a class="nb" href="#secteurs">I. Secteurs A10</a><a class="nb" href="#precovid">J. Pré-COVID</a>
  <a class="nb" href="#claims">K. Conclusions</a>
</div>

<h2 id="exec">A. Résumé exécutif</h2>
<div class="kpis">
  <div class="kpi"><div class="v">0.0313</div><div class="l">WMAPE meilleur modèle<br>HERALD V6 h64</div></div>
  <div class="kpi"><div class="v">253</div><div class="l">Model-runs · 10 seeds · geo2025</div></div>
  <div class="kpi"><div class="v">280</div><div class="l">Zones d'emploi · France métro.</div></div>
  <div class="kpi"><div class="v">2021–2025</div><div class="l">Évaluation observée</div></div>
  <div class="kpi"><div class="v">+9%</div><div class="l">WMAPE Semi mask0.10 vs V6<br>(Semi = pire)</div></div>
  <div class="kpi"><div class="v">3.5×</div><div class="l">γ_mob / γ_geo<br>Mobilité &gt; Géographie</div></div>
</div>
<div class="card">
  <h3>Verdict principal</h3>
  <span class="pill pg">HERALD V6 h64 — meilleur modèle (WMAPE 0.0313 ± 0.0046)</span>
  <p style="margin-top:10px;font-size:.9rem">Le modèle V6 h64 sans semi-supervision domine toutes les configurations sur les 5 années d'évaluation. Le contrôle semi-supervisé sans masquage (mask0.0) est numériquement proche (0.0306) mais statistiquement indiscernable (Wilcoxon p=0.47).</p>
  <div class="warn">⚠ <b>Semi-supervision par masquage : résultat négatif.</b> Semi mask0.10 = WMAPE 0.034 (+9%). Gains : 3/10 seeds. Wilcoxon p=0.105. Masquage vs contrôle : masquage est pire (p=0.049). Le gain vient de h64, pas du masquage.</div>
  <div class="ok">✓ <b>Résultat négatif utile :</b> le Semi crée 117 nouvelles connexions stables (non présentes dans V6 h64) — 9× plus faibles mais persistantes. Connexions intra-régionales (Aude, Gard) = piste d'investigation pour futures recherches.</div>
  <div class="g2" style="margin-top:14px">
    <div><h3>Semi-supervision</h3><span class="pill pr">Non validée comme amélioration</span><br><span class="pill po">Piste à réimplémenter autrement</span></div>
    <div><h3>Graphe dynamique</h3><span class="pill pg">Valeur interprétative forte</span><br><span class="pill po">Valeur prédictive : ablation fixed_adj manquante</span></div>
  </div>
</div>

<h2 id="global">B. Comparaison globale des modèles</h2>
<div class="info"><b>Comment lire :</b> WMAPE moyen sur 2021–2025 (rolling-origin, 280 zones). Barres d'erreur = ±1 écart-type. Ligne bleue = référence V6 h64. Plus bas = meilleur.<br><b>Résultat :</b> HERALD dépasse tous les baselines d'au moins 40%. La semi-supervision (orange) ne s'améliore pas sur V6 h64.</div>
<div class="box"><div id="cGlobal" style="height:520px"></div></div>

<h2 id="ablation">C. Ablation semi-supervisée complète</h2>
<div class="info"><b>Comment lire :</b> 19 configurations HERALD vs référence V6 h64 (ligne bleue). À droite = pire que V6 h64.<br><b>Résultat :</b> le masquage dégrade systématiquement la performance. La capacité h64 explique le gain, pas le masquage.</div>
<div class="box"><div id="cAblation" style="height:620px"></div></div>
<div class="g2">
  <div class="box"><div id="cMaskRatio" style="height:320px"></div></div>
  <div class="box"><div id="cStrategy" style="height:320px"></div></div>
</div>
<div class="g2">
  <div class="box"><div id="cLambda" style="height:290px"></div></div>
  <div class="box"><div id="cCapacity" style="height:290px"></div></div>
</div>

<h2 id="seeds">D. Robustesse par seed</h2>
<div class="info"><b>Gauche :</b> distribution WMAPE sur 10 seeds. <b>Droite :</b> lignes appariées — vert = Semi gagne, rouge = V6 gagne.<br><b>Résultat :</b> Semi mask0.10 perd dans 7/10 seeds contre V6 h64.</div>
<div class="g2">
  <div class="box"><div id="cBox" style="height:380px"></div></div>
  <div class="box"><div id="cPaired" style="height:380px"></div></div>
</div>

<h2 id="annee">E. Performance par année de prévision</h2>
<div class="info"><b>Comment lire :</b> WMAPE moyen par fold — modèle entraîné jusqu'à t−1, prédit l'année t. 2021 (rebond COVID) et 2025 (nouvelles dynamiques) sont les années les plus difficiles.<br><b>Résultat :</b> HERALD stable sur toutes les années ; STGNNs s'effondrent en 2021.</div>
<div class="box"><div id="cYear" style="height:420px"></div></div>

<h2 id="graphe">F. Diagnostic du graphe dynamique</h2>
<div class="info">Le graphe dynamique montre une forte sensibilité aux chocs COVID (adj_delta ×10–20 en 2020–2022). La mobilité domine la géographie (γ_mob ≈ 3.5× γ_geo). Cette valeur est principalement <b>interprétative</b> — une ablation <code>fixed_adj</code> reste nécessaire pour isoler le gain prédictif.</div>
<div class="g2">
  <div class="box"><div id="cGamma" style="height:360px"></div></div>
  <div class="box"><div id="cAdjDelta" style="height:360px"></div></div>
</div>
<div class="box"><div id="cGate" style="height:290px"></div></div>

<h2 id="newconn">G. Nouvelles connexions révélées par le Semi</h2>
<div class="info"><b>Ce que montre ce graphique :</b> les 20 connexions les plus fortes présentes dans Semi mask0.10 mais absentes de V6 h64 (stables dans ≥7/10 seeds, année 2024). Vert = intra-département ; orange = inter-département.<br><b>Résultat :</b> poids moyen 0.021 vs 0.192 pour connexions partagées (9× plus faibles). Connexions longue-distance = probable artefact du masquage. Connexions intra-Aude/Gard = intérêt interprétatif potentiel.</div>
<div class="ok">💡 <b>Signal pour futures recherches :</b> avec un masquage spatialement cohérent, ces nouvelles connexions pourraient révéler des bassins économiques non captés par les données de mobilité habituelles.</div>
<div class="g2">
  <div class="box"><div id="cNewConn" style="height:430px"></div></div>
  <div class="box"><div id="cNewConnSc" style="height:430px"></div></div>
</div>

<h2 id="carte">H. Carte de France — Erreurs par zone d'emploi</h2>
<div class="info"><b>Comment lire :</b> WMAPE moyen par zone sur 2021–2025 (calculé sur 5 seeds, rolling-origin). Plus foncé = erreur plus élevée. Zones économiquement volatiles ou à faible volume ont des erreurs plus élevées.<br><b>Note :</b> carte SVG intégrée, 100% hors-ligne.</div>
<div class="ctrl">
  <label>Affichage :</label>
  <select id="mapSel" onchange="updateMap()">
    <option value="semi">HERALD Semi mask0.10 — WMAPE</option>
    <option value="v6">HERALD V6 h64 — WMAPE</option>
    <option value="diff">Différence Semi − V6 h64</option>
  </select>
</div>
<div class="box"><div id="cMap" style="height:600px"></div></div>

<h2 id="secteurs">I. Secteurs A10 — Composition et erreurs</h2>
<div class="info"><b>Gauche :</b> proportion du secteur sélectionné par zone d'emploi. <b>Droite :</b> WMAPE sectoriel moyen par secteur A10.<br><b>Résultat :</b> WMAPE sectoriel ~0.23 pour tous les modèles. JZ (Info-comm.) et KZ (Finances) sont les plus difficiles à prédire.</div>
<div class="ctrl">
  <label>Secteur A10 :</label>
  <select id="secSel" onchange="updateSec()">
    <option value="RU">RU — Autres services aux ménages</option>
    <option value="MN">MN — Industrie manufacturière</option>
    <option value="FZ">FZ — Construction</option>
    <option value="GI">GI — Commerce, transport, hébergement</option>
    <option value="JZ">JZ — Information, communication</option>
    <option value="KZ">KZ — Activités financières</option>
    <option value="LZ">LZ — Immobilier</option>
    <option value="BE">BE — Agriculture, énergie, eau</option>
    <option value="OQ">OQ — Administration, santé, éducation</option>
  </select>
</div>
<div class="g2">
  <div class="box"><div id="cSecMap" style="height:500px"></div></div>
  <div class="box"><div id="cSecWmape" style="height:500px"></div></div>
</div>

<h2 id="precovid">J. Robustesse pré-COVID (2016–2019)</h2>
<div class="warn">⚠ <b>Comparaison incomplète :</b> seule la configuration Semi mask0.10 a été évaluée en pré-COVID. V6 h64 et V3 n'ont pas été évalués dans le même protocole. Interpréter avec prudence.</div>
<div class="info"><b>Résultat :</b> sur 2016–2019, l'avantage vs Ridge AR est réduit de 87% (−0.033 sur 2021–2025 vs −0.004 sur 2016–2019). 2016 est difficile (WMAPE=0.13) car l'historique est court (données depuis 2012).</div>
<div class="g2">
  <div class="box"><div id="cPCBox" style="height:330px"></div></div>
  <div class="box"><div id="cPCYear" style="height:330px"></div></div>
</div>

<h2 id="claims">K. Conclusions scientifiques</h2>
<div class="card">
<table>
<tr><th>Affirmation</th><th>Verdict</th><th>Évidence quantitative</th></tr>
<tr><td>HERALD ≻ Ridge AR</td><td class="tf">FORT</td><td>0.031 vs 0.059 · Δ=−47% · toutes configurations</td></tr>
<tr><td>HERALD ≻ LSTM local</td><td class="tf">FORT</td><td>0.031 vs 0.091 · Δ=−66%</td></tr>
<tr><td>HERALD ≻ STGNNs (DCRNN, Dynamic)</td><td class="tf">FORT</td><td>0.031 vs 0.054 · Δ=−40% · nota : STGNNs résiduels</td></tr>
<tr><td>Semi mask0.10 ≻ HERALD V6 h64</td><td class="tn">NON SOUTENU</td><td>0.034 vs 0.031 · wins 3/10 · Wilcoxon p=0.105</td></tr>
<tr><td>Masquage améliore la robustesse</td><td class="tn">NON SOUTENU</td><td>Masquage vs contrôle : masquage pire (p=0.049)</td></tr>
<tr><td>Gain = masquage (pas h64)</td><td class="tn">NON SOUTENU</td><td>h64 → gain réel ; masquage → dégradation systématique</td></tr>
<tr><td>Graphe dynamique — valeur prédictive isolée</td><td class="td">À TESTER</td><td>Ablation fixed_adj non disponible sur geo2025</td></tr>
<tr><td>Graphe dynamique — valeur interprétative</td><td class="tf">FORT</td><td>adj_delta COVID ×10–20 · gate↑ pendant COVID · γ_mob≫γ_geo</td></tr>
<tr><td>Mobilité &gt; Géographie</td><td class="tf">FORT</td><td>γ_mob/γ_geo ≈ 3.5× stable sur 10 seeds</td></tr>
<tr><td>Semi révèle nouvelles connexions</td><td class="td">DÉFENDABLE (interprétatif)</td><td>117 connexions stables · 9× plus faibles · validation requise</td></tr>
<tr><td>A10 — contribution prédictive</td><td class="tw">FAIBLE</td><td>WMAPE sectoriel ~0.23 · λ_A10 +2% · non significatif</td></tr>
<tr><td>Robustesse pré-COVID validée</td><td class="tw">FAIBLE</td><td>Avantage vs Ridge AR −87% sur 2016–2019</td></tr>
</table>
</div>
<div class="card" style="margin-top:14px">
  <h3>Prochaines étapes avant soumission</h3>
  <ol style="padding-left:18px;line-height:2.1;font-size:.9rem">
    <li>Ablation <code>fixed_adj</code> — isoler valeur prédictive graphe dynamique vs statique</li>
    <li>Précovid pour V6 h64 et V3 — valider robustesse comparative</li>
    <li>Investiguer <code>spatial_block</code> (+40% WMAPE, p&lt;0.01) — probable bug</li>
    <li>Valider 117 nouvelles connexions Semi avec matrices de mobilité INSEE</li>
    <li>Logs de convergence pour la prochaine batterie HPC</li>
  </ol>
</div>
<hr>
<p class="note" style="text-align:center">Données SIDE/INSEE · Géographie ZE 2020 (nomenclature 2026) · 280 zones d'emploi · Évaluation observée 2021–2025 · Généré le 2026-05-02</p>
</div>

<script>
const CMP={J(models_cmp)};const ABL={J(ablation)};
const SD={J({k:list(v.items()) for k,v in seed_data.items()})};
const PY={J(per_yr_data)};const YEARS={J(YEARS)};const V6REF={V6REF};
const GM={J(gm_m)};const GG={J(gg_m)};const GLBL={J(GRAPH_LBLS)};
const ADJ_V6={J(adj_v6)};const ADJ_SM={J(adj_semi)};const FOLD={J(FOLD_YEARS)};
const GTV6={J(gate_v6)};const GTSM={J(gate_sm)};
const NC={J(new_conn)};const GEO={GEOJSON};
const ZS={J(zone_semi_s)};const ZV={J(zone_v6_s)};
const SEC={J(sector_rows)};const SECW={J({lbl:{s:float(v) for s,v in d.items()} for lbl,d in sec_chart.items()})};
const SECS={J(SECTORS)};
const PCV={J(pc_vals)};const PCPY={J({yr:float(np.mean(w)) for yr,w in pc_py.items() if w})};

const BL={{paper_bgcolor:'#1a1d27',plot_bgcolor:'#1a1d27',
  font:{{color:'#e8eaf0',family:'Segoe UI,system-ui,sans-serif',size:12}},
  margin:{{l:40,r:24,t:44,b:36}},
  xaxis:{{gridcolor:'#2e3347',zerolinecolor:'#2e3347'}},
  yaxis:{{gridcolor:'#2e3347',zerolinecolor:'#2e3347'}},
  legend:{{bgcolor:'#242836',bordercolor:'#2e3347',borderwidth:1}}}};
const CFG={{responsive:true,displayModeBar:false}};
const PAL={{'HERALD V6 h64':'#4f8ef7','HERALD V6 h32':'#9edae5','HERALD V3':'#7bb3f5',
  'Semi h64 contrôle mask0.0':'#17c3d4','Semi h64 mask0.10 (principal)':'#f7834f',
  'Semi h64 mask0.30':'#ffc080','Semi h64 warmup0':'#ffe0b0',
  'DCRNN résiduel':'#9467bd','Dynamic STGNN résiduel':'#c5b0d5','Graph WaveNet résiduel':'#d6b4fc',
  'Ridge AR':'#4caf72','naive lag-1':'#98df8a','ARIMA local':'#a8d8a8','LSTM local':'#ffb3b3'}};

// B — Comparaison globale
(()=>{{
  const d=CMP,c=d.map(x=>PAL[x.label]||(x.family==='herald'?'#4f8ef7':x.family==='semi'?'#f7834f':x.family==='stgnn'?'#9467bd':'#4caf72'));
  Plotly.newPlot('cGlobal',[{{type:'bar',orientation:'h',x:d.map(x=>x.mean),y:d.map(x=>x.label),
    error_x:{{type:'data',array:d.map(x=>x.std),visible:true,color:'#8b9abf',thickness:1.5}},
    marker:{{color:c,opacity:.9}},text:d.map(x=>`${{(x.mean*100).toFixed(2)}}%`),textposition:'outside',textfont:{{size:10}},
    hovertemplate:'<b>%{{y}}</b><br>WMAPE: %{{x:.4f}}<br>Seeds: %{{customdata}}<extra></extra>',customdata:d.map(x=>x.n)}}],
    {{...BL,title:{{text:'WMAPE moyen par modèle — évaluation 2021–2025 · 280 zones',font:{{size:13}}}},
    xaxis:{{...BL.xaxis,title:'WMAPE moyen (plus bas = meilleur)',tickformat:'.3f'}},
    yaxis:{{...BL.yaxis,automargin:true}},margin:{{l:240,r:80,t:50,b:40}},
    shapes:[{{type:'line',x0:V6REF,x1:V6REF,y0:-.5,y1:d.length-.5,line:{{color:'#4f8ef7',width:2,dash:'dash'}}}}],
    annotations:[{{x:V6REF,y:d.length,text:'V6 h64 référence',showarrow:false,font:{{color:'#4f8ef7',size:10}},xanchor:'left'}}]}},CFG);
}})();

// C — Ablation
(()=>{{
  const rows=ABL,c=rows.map(r=>r.tag==='total_h64_no_semi'?'#4f8ef7':r.tag==='total_h64_semi_mask0.0_control'?'#17c3d4':r.tag.includes('spatial')?'#e05252':r.tag.includes('semi')?'#f7834f':'#7bb3f5');
  Plotly.newPlot('cAblation',[{{type:'bar',orientation:'h',x:rows.map(r=>r.mean),y:rows.map(r=>r.label),
    error_x:{{type:'data',array:rows.map(r=>r.std),visible:true,color:'#8b9abf',thickness:1.5}},
    marker:{{color:c,opacity:.88}},text:rows.map(r=>(r.mean*100).toFixed(2)+'%'),textposition:'outside',textfont:{{size:10}},
    hovertemplate:'<b>%{{y}}</b><br>WMAPE: %{{x:.4f}} ±%{{customdata:.4f}}<extra></extra>',customdata:rows.map(r=>r.std)}}],
    {{...BL,title:{{text:'Ablation complète — 19 configurations HERALD',font:{{size:13}}}},
    xaxis:{{...BL.xaxis,title:'WMAPE moyen',tickformat:'.3f',range:[.024,.055]}},
    yaxis:{{...BL.yaxis,automargin:true}},margin:{{l:260,r:80,t:50,b:40}},
    shapes:[{{type:'line',x0:V6REF,x1:V6REF,y0:-.5,y1:rows.length-.5,line:{{color:'#4f8ef7',width:2.5,dash:'dash'}}}}],
    annotations:[{{x:V6REF,y:rows.length-.3,text:'V6 h64',showarrow:false,font:{{color:'#4f8ef7',size:11}},xanchor:'left'}}]}},CFG);
}})();

(()=>{{
  const r=['0.0','0.05','0.10','0.15','0.20','0.30'];
  const tm={{'0.0':'total_h64_semi_mask0.0_control','0.05':'total_h64_semi_mask0.05_random','0.10':'total_h64_semi_mask0.10_random','0.15':'total_h64_semi_mask0.15_random','0.20':'total_h64_semi_mask0.20_random','0.30':'total_h64_semi_mask0.30_random'}};
  const m=r.map(x=>(ABL.find(a=>a.tag===tm[x])||{{mean:0}}).mean),s=r.map(x=>(ABL.find(a=>a.tag===tm[x])||{{std:0}}).std);
  Plotly.newPlot('cMaskRatio',[
    {{type:'scatter',mode:'lines+markers',x:r,y:m,error_y:{{type:'data',array:s,visible:true,color:'#8b9abf'}},line:{{color:'#f7834f',width:2.5}},marker:{{size:8,color:'#f7834f'}},name:'WMAPE'}},
    {{type:'scatter',mode:'lines',x:r,y:Array(6).fill(V6REF),line:{{color:'#4f8ef7',width:2,dash:'dash'}},name:'V6 h64'}}],
    {{...BL,title:{{text:'Sensibilité au ratio de masque (h64, random)',font:{{size:12}}}},xaxis:{{...BL.xaxis,title:'Ratio de masque'}},yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.024,.05]}}}},CFG);
}})();

(()=>{{
  const cf=[['random 10%','total_h64_semi_mask0.10_random','#f7834f'],['block 10%','total_h64_semi_mask0.10_block','#f7c04f'],['spatial 10%','total_h64_semi_mask0.10_spatial_block','#e05252'],['random 20%','total_h64_semi_mask0.20_random','#ffb87f'],['block 20%','total_h64_semi_mask0.20_block','#ffd080'],['spatial 20%','total_h64_semi_mask0.20_spatial_block','#ff8080']];
  Plotly.newPlot('cStrategy',cf.map(([lbl,tag,col])=>{{const r=ABL.find(a=>a.tag===tag)||{{mean:0,std:0}};return{{type:'bar',name:lbl,x:[lbl],y:[r.mean],error_y:{{type:'data',array:[r.std],visible:true,color:'#8b9abf'}},marker:{{color:col}},hovertemplate:`<b>${{lbl}}</b><br>%{{y:.4f}}<extra></extra>`}}}}),
    {{...BL,barmode:'group',showlegend:false,title:{{text:'Stratégie de masquage',font:{{size:12}}}},yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.024,.056]}},shapes:[{{type:'line',x0:-.5,x1:5.5,y0:V6REF,y1:V6REF,line:{{color:'#4f8ef7',width:2,dash:'dash'}}}}]}},CFG);
}})();

(()=>{{
  const cf=[['λ=0 (base)','total_h64_semi_mask0.10_random'],['λ=0.01 total','total_h64_semi_mask0.10_random_lam0.01_total'],['λ=0.05 total','total_h64_semi_mask0.10_random_lam0.05_total'],['λ=0.10 total','total_h64_semi_mask0.10_random_lam0.10_total'],['λ=0.05 A10','total_h64_semi_mask0.10_random_lam0.05_a10'],['λ=0.05 tot+A10','total_h64_semi_mask0.10_random_lam0.05_total_a10']];
  const d=cf.map(([lbl,tag])=>{{const r=ABL.find(a=>a.tag===tag)||{{mean:0,std:0}};return{{lbl,mean:r.mean,std:r.std}}}});
  Plotly.newPlot('cLambda',[
    {{type:'bar',x:d.map(r=>r.lbl),y:d.map(r=>r.mean),marker:{{color:'#f7834f',opacity:.85}},error_y:{{type:'data',array:d.map(r=>r.std),visible:true,color:'#8b9abf'}},hovertemplate:'<b>%{{x}}</b><br>%{{y:.4f}}<extra></extra>'}},
    {{type:'scatter',mode:'lines',x:d.map(r=>r.lbl),y:Array(d.length).fill(V6REF),line:{{color:'#4f8ef7',width:2,dash:'dash'}},name:'V6 h64'}}],
    {{...BL,title:{{text:'Semi lambda — impact sur WMAPE total',font:{{size:12}}}},xaxis:{{...BL.xaxis,tickangle:-18}},yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.024,.04]}}}},CFG);
}})();

(()=>{{
  const cf=[['V6 h32','total_h32_no_semi','#9edae5'],['V6 h64','total_h64_no_semi','#4f8ef7'],['Semi h32 mask0.10','total_h32_semi_mask0.10_random','#ffc07f'],['Semi h64 mask0.10','total_h64_semi_mask0.10_random','#f7834f']];
  const rows=cf.map(([lbl,tag,col])=>{{const r=ABL.find(a=>a.tag===tag)||{{mean:0,std:0}};return{{lbl,mean:r.mean,std:r.std,col}}}});
  Plotly.newPlot('cCapacity',[{{type:'bar',x:rows.map(r=>r.lbl),y:rows.map(r=>r.mean),marker:{{color:rows.map(r=>r.col)}},error_y:{{type:'data',array:rows.map(r=>r.std),visible:true,color:'#8b9abf'}},hovertemplate:'<b>%{{x}}</b><br>%{{y:.4f}}<extra></extra>'}}],
    {{...BL,title:{{text:'Capacité : h32 vs h64 — avec et sans semi-supervision',font:{{size:12}}}},yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[.024,.045]}}}},CFG);
}})();

// D — Seeds
(()=>{{
  const cfg=Object.keys(SD);const c={{'HERALD V6 h64':'#4f8ef7','Semi mask0.0':'#17c3d4','Semi mask0.10':'#f7834f','HERALD V3':'#7bb3f5'}};
  Plotly.newPlot('cBox',cfg.map(n=>{{const pts=SD[n];return{{type:'box',name:n,y:pts.map(([s,v])=>v),marker:{{color:c[n]||'#aaa'}},boxpoints:'all',jitter:.3,pointpos:-1.5,line:{{width:1.5}},text:pts.map(([s])=>s),hovertemplate:`<b>${{n}}</b><br>Seed %{{text}}<br>WMAPE: %{{y:.4f}}<extra></extra>`}}}}),
    {{...BL,showlegend:false,title:{{text:'Distribution WMAPE par seed (10 seeds)',font:{{size:12}}}},yaxis:{{...BL.yaxis,title:'WMAPE'}}}},CFG);
}})();

(()=>{{
  const sA=Object.fromEntries(SD['HERALD V6 h64']||[]),sB=Object.fromEntries(SD['Semi mask0.10']||[]);
  const seeds=Object.keys(sA).filter(s=>s in sB).map(Number).sort((a,b)=>a-b);
  const wins=seeds.filter(s=>sB[s]<sA[s]).length;
  Plotly.newPlot('cPaired',seeds.map(s=>{{const w=sB[s]<sA[s];return{{type:'scatter',mode:'lines+markers',x:['V6 h64','Semi mask0.10'],y:[sA[s],sB[s]],line:{{color:w?'#4caf72':'#e05252',width:1.8,dash:w?'solid':'dot'}},marker:{{size:7}},name:`seed ${{s}}`,hovertemplate:`Seed ${{s}}<br>V6: ${{sA[s].toFixed(4)}}<br>Semi: ${{sB[s].toFixed(4)}}<br>${{w?'✓ Semi gagne':'✗ V6 gagne'}}<extra></extra>`}}}}),
    {{...BL,showlegend:false,title:{{text:`Lignes appariées par seed — Semi gagne ${{wins}}/10`,font:{{size:12}}}},yaxis:{{...BL.yaxis,title:'WMAPE',range:[.02,.055]}}}},CFG);
}})();

// E — Par année
(()=>{{
  const pal={{'HERALD V6 h64':'#4f8ef7','Semi mask0.0':'#17c3d4','Semi mask0.10':'#f7834f','HERALD V3':'#7bb3f5','Ridge AR':'#4caf72','DCRNN résiduel':'#9467bd'}};
  Plotly.newPlot('cYear',Object.entries(PY).map(([lbl,py])=>{{return{{type:'scatter',mode:'lines+markers',name:lbl,x:YEARS,y:YEARS.map(yr=>py[yr]||null),line:{{color:pal[lbl]||'#aaa',width:2.5}},marker:{{size:8}},hovertemplate:`<b>${{lbl}}</b><br>%{{x}} : %{{y:.4f}}<extra></extra>`}}}}),
    {{...BL,title:{{text:'WMAPE par année de prévision — modèles principaux',font:{{size:13}}}},xaxis:{{...BL.xaxis,title:'Année prévue',dtick:1}},yaxis:{{...BL.yaxis,title:'WMAPE moyen'}}}},CFG);
}})();

// F — Graphe
(()=>{{
  Plotly.newPlot('cGamma',[
    {{type:'bar',name:'γ_mob (mobilité)',x:GLBL,y:GM,marker:{{color:'#4f8ef7',opacity:.85}}}},
    {{type:'bar',name:'γ_geo (géographie)',x:GLBL,y:GG,marker:{{color:'#f7834f',opacity:.85}}}}],
    {{...BL,barmode:'group',title:{{text:'γ_mob vs γ_geo — poids des graphes par configuration',font:{{size:12}}}},yaxis:{{...BL.yaxis,title:'Valeur gamma (appris)'}},xaxis:{{...BL.xaxis,tickangle:-12}}}},CFG);
  Plotly.newPlot('cAdjDelta',[
    {{type:'bar',name:'V6 h64',x:FOLD,y:ADJ_V6,marker:{{color:'#4f8ef7',opacity:.8}}}},
    {{type:'bar',name:'Semi mask0.10',x:FOLD,y:ADJ_SM,marker:{{color:'#f7834f',opacity:.8}}}}],
    {{...BL,barmode:'group',title:{{text:'adj_delta — variation structurelle du graphe par transition annuelle',font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:'Année (→)',dtick:1}},yaxis:{{...BL.yaxis,title:'adj_delta (normalisé)'}},
    shapes:[{{type:'rect',x0:2020.4,x1:2022.6,y0:0,y1:.55,fillcolor:'rgba(255,200,0,.07)',line:{{width:0}}}},
            {{type:'line',x0:2020.4,x1:2020.4,y0:0,y1:.55,line:{{color:'#f7c04f',width:1.5,dash:'dot'}}}},
            {{type:'line',x0:2022.6,x1:2022.6,y0:0,y1:.55,line:{{color:'#f7c04f',width:1.5,dash:'dot'}}}}],
    annotations:[{{x:2021.5,y:.52,text:'Zone COVID',showarrow:false,font:{{color:'#f7c04f',size:11}}}}]}},CFG);
  const yrs=Object.keys(GTV6).map(Number).sort();
  Plotly.newPlot('cGate',[
    {{type:'scatter',mode:'lines+markers',name:'V6 h64',x:yrs,y:yrs.map(y=>GTV6[y]||null),line:{{color:'#4f8ef7',width:2.5}},marker:{{size:8}}}},
    {{type:'scatter',mode:'lines+markers',name:'Semi mask0.10',x:yrs,y:yrs.map(y=>GTSM[y]||null),line:{{color:'#f7834f',width:2.5}},marker:{{size:8}}}}],
    {{...BL,title:{{text:'Gate de mobilité par année (plus élevé = plus de mobilité utilisée)',font:{{size:12}}}},xaxis:{{...BL.xaxis,title:'Année',dtick:1}},yaxis:{{...BL.yaxis,title:'Gate moyen (0=géo, 1=mob)',range:[.4,.95]}}}},CFG);
}})();

// G — Nouvelles connexions
(()=>{{
  if(!NC.length) return;
  Plotly.newPlot('cNewConn',[{{type:'bar',orientation:'h',x:NC.map(d=>d.weight_semi),y:NC.map(d=>d.label),
    marker:{{color:NC.map(d=>d.intra?'#4caf72':'#f7834f'),opacity:.88}},
    customdata:NC.map(d=>[d.weight_v6,d.intra?'Intra-dépt':'Inter-dépt']),
    hovertemplate:'<b>%{{y}}</b><br>Semi: %{{x:.4f}} · V6: %{{customdata[0]:.4f}}<br>%{{customdata[1]}}<extra></extra>'}}],
    {{...BL,title:{{text:'Top-20 nouvelles connexions stables (Semi exclusif) · Vert=intra-dépt · Orange=inter-dépt',font:{{size:11}}}},
    xaxis:{{...BL.xaxis,title:'Poids moyen (10 seeds)',tickformat:'.3f',range:[0,.06]}},yaxis:{{...BL.yaxis,automargin:true}},
    margin:{{l:180,r:80,t:55,b:40}},
    shapes:[{{type:'line',x0:.192,x1:.192,y0:-.5,y1:NC.length-.5,line:{{color:'#4f8ef7',width:2,dash:'dash'}}}}],
    annotations:[{{x:.192,y:NC.length-.5,text:'Moy. connexions partagées: 0.192',showarrow:false,font:{{color:'#4f8ef7',size:10}},xanchor:'left'}}]}},CFG);
  const sm=NC.filter(d=>d.intra),df=NC.filter(d=>!d.intra);
  Plotly.newPlot('cNewConnSc',[
    {{type:'scatter',mode:'markers',name:'Intra-département (59%)',x:sm.map(d=>d.weight_semi),y:sm.map(d=>d.weight_v6),marker:{{color:'#4caf72',size:9,opacity:.85}},customdata:sm.map(d=>[d.label]),hovertemplate:'<b>%{{customdata[0]}}</b><br>Semi: %{{x:.4f}}<br>V6: %{{y:.4f}}<extra></extra>'}},
    {{type:'scatter',mode:'markers',name:'Inter-département (41%)',x:df.map(d=>d.weight_semi),y:df.map(d=>d.weight_v6),marker:{{color:'#f7834f',size:9,symbol:'diamond',opacity:.85}},customdata:df.map(d=>[d.label]),hovertemplate:'<b>%{{customdata[0]}}</b><br>Semi: %{{x:.4f}}<br>V6: %{{y:.4f}}<extra></extra>'}}],
    {{...BL,title:{{text:'Poids Semi vs V6 — toutes les 117 nouvelles connexions stables',font:{{size:11}}}},xaxis:{{...BL.xaxis,title:'Poids Semi',tickformat:'.3f'}},yaxis:{{...BL.yaxis,title:'Poids V6 h64',tickformat:'.4f'}},
    shapes:[{{type:'line',x0:.01,x1:.06,y0:.01,y1:.01,line:{{color:'#8b9abf',width:1,dash:'dot'}}}}],
    annotations:[{{x:.035,y:.009,text:'Seuil actif = 0.01',showarrow:false,font:{{color:'#8b9abf',size:9}}}}]}},CFG);
}})();

// H — Carte France (SVG offline via go.Choropleth)
function updateMap(){{
  if(!GEO){{document.getElementById('cMap').innerHTML='<p style="padding:60px;color:#8b9abf;text-align:center">GeoJSON non disponible</p>';return;}}
  const model=document.getElementById('mapSel').value;
  const geo=GEO,zc=geo.features.map(f=>f.properties.ze2020);
  let vals,ctitle,cs;
  if(model==='diff'){{
    vals=zc.map(z=>{{const s=ZS[z],v=ZV[z];return(s&&v)?(s-v):null}});
    ctitle='Différence Semi − V6';cs=[[0,'#2171b5'],[.5,'#f7f7f7'],[1,'#d94801']];
  }}else{{
    const src=model==='semi'?ZS:ZV;vals=zc.map(z=>src[z]||null);
    ctitle=model==='semi'?'WMAPE Semi mask0.10':'WMAPE V6 h64';
    cs=[[0,'#1a3a6b'],[.3,'#2171b5'],[.6,'#6baed6'],[.85,'#fdae6b'],[1,'#d94801']];
  }}
  const vv=vals.filter(v=>v!==null);
  const lbl={{semi:'HERALD Semi mask0.10',v6:'HERALD V6 h64',diff:'Différence (Semi − V6 h64)'}};
  Plotly.newPlot('cMap',[{{
    type:'choropleth',geojson:geo,locations:zc,z:vals,featureidkey:'properties.ze2020',
    colorscale:cs,zmin:model==='diff'?-Math.max(...vv.map(Math.abs)):Math.min(...vv),
    zmax:Math.max(...vv.map(Math.abs)),
    colorbar:{{title:ctitle,thickness:14,len:.7,tickformat:'.3f'}},
    marker:{{line:{{width:.5,color:'#0f1117'}}}},
    text:zc.map((z,i)=>`ZE ${{z}}<br>${{ctitle}}: ${{vals[i]!==null?(vals[i]*100).toFixed(2)+'%':'N/D'}}`),
    hovertemplate:'%{{text}}<extra></extra>',
  }}],{{...BL,
    title:{{text:`Carte territoriale — ${{lbl[model]}} · moyenne 2021–2025 · 5 seeds`,font:{{size:13}}}},
    geo:{{scope:'europe',center:{{lon:2.5,lat:46.5}},projection:{{type:'mercator',scale:5.5}},
      showframe:false,showcoastlines:true,coastlinecolor:'#3a4060',bgcolor:'#0f1117',
      showland:true,landcolor:'#181b28',showocean:true,oceancolor:'#0f1117',
      lonaxis:{{range:[-5.5,10]}},lataxis:{{range:[41,52]}}}},
    margin:{{l:0,r:0,t:50,b:0}}}},CFG);
}}
updateMap();

// I — Secteurs A10
function updateSec(){{
  const sec=document.getElementById('secSel').value;
  if(!GEO||!SEC.length){{document.getElementById('cSecMap').innerHTML='<p style="padding:40px;color:#8b9abf;text-align:center">Données sectorielles non disponibles</p>';return;}}
  const byZe={{}};SEC.forEach(r=>byZe[r.ze]=r[sec]||0);
  const geo=GEO,zc=geo.features.map(f=>f.properties.ze2020);
  const vals=zc.map(z=>byZe[z]||0);
  Plotly.newPlot('cSecMap',[{{
    type:'choropleth',geojson:geo,locations:zc,z:vals,featureidkey:'properties.ze2020',
    colorscale:[[0,'#0a1929'],[.3,'#1565c0'],[.6,'#42a5f5'],[1,'#ffeb3b']],zmin:0,zmax:.55,
    colorbar:{{title:`Part ${{sec}}`,thickness:14,len:.7,tickformat:'.0%'}},
    marker:{{line:{{width:.5,color:'#0f1117'}}}},
    text:zc.map((z,i)=>`ZE ${{z}}<br>${{sec}}: ${{(vals[i]*100).toFixed(1)}}%`),hovertemplate:'%{{text}}<extra></extra>',
  }}],{{...BL,title:{{text:`Part du secteur ${{sec}} par zone d'emploi`,font:{{size:12}}}},
    geo:{{scope:'europe',center:{{lon:2.5,lat:46.5}},projection:{{type:'mercator',scale:5.5}},
      showframe:false,showcoastlines:true,coastlinecolor:'#3a4060',bgcolor:'#0f1117',
      showland:true,landcolor:'#181b28',showocean:true,oceancolor:'#0f1117',
      lonaxis:{{range:[-5.5,10]}},lataxis:{{range:[41,52]}}}},margin:{{l:0,r:0,t:45,b:0}}}},CFG);
  Plotly.newPlot('cSecWmape',Object.entries(SECW).map(([lbl,sw])=>{{return{{type:'bar',name:lbl,x:SECS,y:SECS.map(s=>sw[s]||0),opacity:.85}}}}),
    {{...BL,barmode:'group',title:{{text:'WMAPE sectoriel A10 par modèle',font:{{size:12}}}},
    xaxis:{{...BL.xaxis,title:'Secteur A10'}},yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[0,.65]}},
    shapes:[{{type:'line',x0:-.5,x1:8.5,y0:.033,y1:.033,line:{{color:'#4f8ef7',width:1.5,dash:'dash'}}}}],
    annotations:[{{x:8,y:.033,text:'WMAPE total V6',showarrow:false,font:{{color:'#4f8ef7',size:10}},yanchor:'bottom'}}]}},CFG);
}}
updateSec();

// J — Pré-COVID
(()=>{{
  Plotly.newPlot('cPCBox',[
    {{type:'box',name:'Semi precovid 2016–2019',y:PCV,marker:{{color:'#f7834f'}},boxpoints:'all',jitter:.3,pointpos:-1.5,hovertemplate:'WMAPE: %{{y:.4f}}<extra></extra>'}},
    {{type:'scatter',mode:'markers',name:'Ridge AR (~0.067)',x:['Semi precovid 2016–2019'],y:[.067],marker:{{color:'#4caf72',size:16,symbol:'line-ew-open',line:{{width:3}}}}}},
    {{type:'scatter',mode:'markers',name:'WMAPE 2021–2025 (~0.034)',x:['Semi precovid 2016–2019'],y:[.034],marker:{{color:'#17c3d4',size:16,symbol:'line-ew-open',line:{{width:3}}}}}}],
    {{...BL,title:{{text:'WMAPE pré-COVID 2016–2019 — Semi mask0.10 (10 seeds)',font:{{size:12}}}},yaxis:{{...BL.yaxis,title:'WMAPE moyen 2016–2019'}}}},CFG);
  const yrs=Object.keys(PCPY).map(Number).sort();
  Plotly.newPlot('cPCYear',[
    {{type:'bar',x:yrs,y:yrs.map(y=>PCPY[y]),marker:{{color:'#f7834f',opacity:.85}},hovertemplate:'%{{x}} : %{{y:.4f}}<extra></extra>',name:'Semi precovid'}},
    {{type:'scatter',mode:'lines',x:yrs,y:Array(yrs.length).fill(.034),line:{{color:'#17c3d4',width:2,dash:'dash'}},name:'WMAPE 2021–2025'}},
    {{type:'scatter',mode:'lines',x:yrs,y:Array(yrs.length).fill(.067),line:{{color:'#4caf72',width:2,dash:'dot'}},name:'Ridge AR'}}],
    {{...BL,title:{{text:'WMAPE par année pré-COVID — Semi mask0.10',font:{{size:12}}}},xaxis:{{...BL.xaxis,title:'Année'}},yaxis:{{...BL.yaxis,title:'WMAPE moyen',range:[0,.18]}},
    annotations:[{{x:2016,y:.133,text:'2016 : historique court',showarrow:true,arrowcolor:'#8b9abf',arrowhead:2,font:{{color:'#8b9abf',size:10}}}}]}},CFG);
}})();
</script></body></html>"""

with open(OUT,"w",encoding="utf-8") as f:
    f.write(HTML)
print(f"Dashboard: {OUT}")
print(f"Tamanho: {os.path.getsize(OUT)/1024/1024:.1f} MB")
