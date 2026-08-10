"""HERALD 66 section 9: depth of history, hyperparameters, per-sector models, threshold sensitivity."""
import sys,itertools,numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import f1_score
SEC=["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]
df=pd.read_csv(sys.argv[1]); yrs=sorted(df.target_year.unique()); zs=sorted(df.ZE2020.unique())
zi={z:k for k,z in enumerate(zs)}; yi={y:k for k,y in enumerate(yrs)}
Y=np.zeros((len(yrs),len(zs),9))
for r in df.itertuples(index=False): Y[yi[r.target_year],zi[r.ZE2020]]=[getattr(r,s) for s in SEC]
G=np.full_like(Y,np.nan); G[1:]=np.log1p(Y[1:])-np.log1p(Y[:-1])
NZ=len(zs); sec_of=np.repeat(np.arange(9),NZ)
cat=lambda A:np.concatenate([A[:,s] for s in range(9)])

def make_states(th):
    S=np.where(G<=-th,0,np.where(G>=th,2,1)).astype(float); S[0]=np.nan; return S
def make_states_tercile():
    S=np.full_like(G,np.nan)
    for t in range(1,G.shape[0]):
        v=G[t].ravel(); ok=np.isfinite(v)
        if ok.sum()<10: continue
        lo,hi=np.quantile(v[ok],[1/3,2/3])
        S[t]=np.where(G[t]<=lo,0,np.where(G[t]>=hi,2,1))
    return S
def build(t,nlag):
    X=[cat(G[t-k]) for k in range(1,nlag+1)]
    X+= [cat(np.log1p(Y[t-1])), cat(Y[t-1]/np.maximum(Y[t-1].sum(1,keepdims=True),1e-9))]
    return np.column_stack(X)
def labels(S,t): return np.concatenate([S[t][:,s] for s in range(9)])
EV=[yi[y] for y in range(2019,2026)]

def score(S,nlag,params,per_sector=False,sd=0):
    f1=[]
    for t in EV:
        tr=list(range(max(nlag+1,6),t))   # fixed start so lag depth does not change the training window
        Xtr=np.vstack([build(k,nlag) for k in tr]); ytr=np.concatenate([labels(S,k) for k in tr])
        Xte,yte=build(t,nlag),labels(S,t)
        okt=np.isfinite(yte)
        if per_sector:
            pred=np.full(len(yte),np.nan)
            str_=np.concatenate([np.tile(sec_of,1) for _ in tr]) if False else np.concatenate([sec_of for _ in tr])
            for s in range(9):
                mtr=(str_==s)&np.isfinite(ytr); mte=(sec_of==s)&okt
                if mtr.sum()<50: continue
                m=HistGradientBoostingClassifier(random_state=sd,**params)
                m.fit(np.nan_to_num(Xtr[mtr]),ytr[mtr],sample_weight=compute_sample_weight("balanced",ytr[mtr]))
                pred[mte]=m.predict(np.nan_to_num(Xte[mte]))
        else:
            ok=np.isfinite(ytr)
            m=HistGradientBoostingClassifier(random_state=sd,**params)
            m.fit(np.nan_to_num(Xtr[ok]),ytr[ok],sample_weight=compute_sample_weight("balanced",ytr[ok]))
            pred=np.full(len(yte),np.nan); pred[okt]=m.predict(np.nan_to_num(Xte[okt]))
        good=okt&np.isfinite(pred)
        f1.append(f1_score(yte[good],pred[good],average="macro"))
    return float(np.mean(f1))

S5=make_states(0.05)
BASE=dict(max_iter=400,learning_rate=0.05,max_depth=6)
print("=== profundidade de historia (params base) ===")
best_lag,best=3,-1
for nl in [2,3,4,5]:
    v=np.mean([score(S5,nl,BASE,sd=s) for s in (0,1)])
    print(f"  {nl} lags: {v:.4f}")
    if v>best: best,best_lag=v,nl
print(f"  -> melhor {best_lag} lags ({best:.4f})")
print("\n=== hiperparametros (melhor n de lags) ===")
grid=[dict(max_iter=mi,learning_rate=lr,max_depth=md,min_samples_leaf=ml)
      for mi,lr,md,ml in itertools.product([200,600],[0.03,0.1],[3,6],[20,100])]
res=[]
for p in grid:
    v=score(S5,best_lag,p,sd=0); res.append((v,p))
res.sort(reverse=True,key=lambda x:x[0])
for v,p in res[:5]: print(f"  {v:.4f}  {p}")
bp=res[0][1]
bv=np.mean([score(S5,best_lag,bp,sd=s) for s in (0,1,2)])
print(f"  -> melhor config, 3 seeds: {bv:.4f}")
print("\n=== por setor vs conjunto ===")
ps=np.mean([score(S5,best_lag,bp,per_sector=True,sd=s) for s in (0,1)])
print(f"  conjunto {bv:.4f} | por setor {ps:.4f} | delta {ps-bv:+.4f}")
print("\n=== sensibilidade ao limiar (pre-registada) ===")
for th in [0.03,0.05,0.10]:
    print(f"  +-{th:.2f}: {score(make_states(th),best_lag,bp,sd=0):.4f}")
print(f"  tercis:  {score(make_states_tercile(),best_lag,bp,sd=0):.4f}")
print("\n  referencias: aleatorio 0.307 | anterior 0.3886 | teto 0.655")
