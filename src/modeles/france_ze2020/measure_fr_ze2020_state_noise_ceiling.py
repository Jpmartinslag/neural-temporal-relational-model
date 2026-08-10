"""HERALD 66 section 6: how much of the three-state label is counting noise?

Poisson-resample each cell at its observed mean, rebuild the labels, and measure how often
the state flips. An oracle that knew the true rate would still be scored against a noisy
realisation, so the flip rate bounds attainable macro-F1.
"""
import sys,numpy as np,pandas as pd
from sklearn.metrics import f1_score
SEC=["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]; TH=0.05
df=pd.read_csv(sys.argv[1]); yrs=sorted(df.target_year.unique()); zs=sorted(df.ZE2020.unique())
zi={z:k for k,z in enumerate(zs)}; yi={y:k for k,y in enumerate(yrs)}
Y=np.zeros((len(yrs),len(zs),9))
for r in df.itertuples(index=False): Y[yi[r.target_year],zi[r.ZE2020]]=[getattr(r,s) for s in SEC]
def states(A):
    G=np.full_like(A,np.nan); G[1:]=np.log1p(np.maximum(A[1:],0))-np.log1p(np.maximum(A[:-1],0))
    return np.where(G<=-TH,0,np.where(G>=TH,2,1)).astype(float),G
S0,_=states(Y)
EV=[yi[y] for y in range(2019,2026)]
rng=np.random.default_rng(20260810)
flips=[];f1s=[]
for _ in range(40):
    Yr=rng.poisson(np.maximum(Y,0)).astype(float)
    Sr,_=states(Yr)
    a=np.concatenate([S0[t].ravel() for t in EV]); b=np.concatenate([Sr[t].ravel() for t in EV])
    ok=np.isfinite(a)&np.isfinite(b)
    flips.append(float((a[ok]!=b[ok]).mean()))
    f1s.append(f1_score(a[ok],b[ok],average="macro"))
print(f"celulas avaliadas por replica: {int(ok.sum())}")
print(f"\ntaxa de troca de estado so por ruido de contagem: {100*np.mean(flips):.1f}%  (sd {100*np.std(flips):.2f})")
print(f"macro-F1 de um ORACULO que conhece a taxa verdadeira: {np.mean(f1s):.3f}  (sd {np.std(f1s):.4f})")
print(f"   -> teto pratico da tarefa ~= {np.mean(f1s):.3f}")
print(f"\nreferencias:")
print(f"   mlp+relacional   0.340")
print(f"   mlp              0.327")
print(f"   aleatorio        0.307")
share=(0.340-0.307)/max(np.mean(f1s)-0.307,1e-9)
print(f"\nfracao do espaco disponivel (aleatorio -> teto) ja capturada pelo mlp+rel: {100*share:.0f}%")
# per-class flip detail
lab=["declina","estagna","cresce"]
a=np.concatenate([S0[t].ravel() for t in EV]); ok0=np.isfinite(a)
print("\ndistribuicao real das classes:")
for c in range(3): print(f"   {lab[c]:9} {100*(a[ok0]==c).mean():5.1f}%")
