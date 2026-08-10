"""HERALD 66 section 8: which feature group carries the DEC-103 lift?"""
import sys,numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import f1_score
SEC=["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]; TH=0.05
df=pd.read_csv(sys.argv[1]); yrs=sorted(df.target_year.unique()); zs=sorted(df.ZE2020.unique())
zi={z:k for k,z in enumerate(zs)}; yi={y:k for k,y in enumerate(yrs)}
Y=np.zeros((len(yrs),len(zs),9))
for r in df.itertuples(index=False): Y[yi[r.target_year],zi[r.ZE2020]]=[getattr(r,s) for s in SEC]
G=np.full_like(Y,np.nan); G[1:]=np.log1p(Y[1:])-np.log1p(Y[:-1])
S=np.where(G<=-TH,0,np.where(G>=TH,2,1)).astype(float); S[0]=np.nan
NZ=len(zs)
TOT=Y.sum(2); GT=np.full_like(TOT,np.nan); GT[1:]=np.log1p(TOT[1:])-np.log1p(TOT[:-1])
NAT=Y.sum(1); GN=np.full_like(NAT,np.nan); GN[1:]=np.log1p(NAT[1:])-np.log1p(NAT[:-1])
cat=lambda A:np.concatenate([A[:,s] for s in range(9)])

GROUPS={
 "own_lags":     lambda t:[cat(G[t-1]),cat(G[t-2]),cat(G[t-3]),cat(np.log1p(Y[t-1])),
                           cat(Y[t-1]/np.maximum(Y[t-1].sum(1,keepdims=True),1e-9))],
 "own_states":   lambda t:[cat(S[t-1]),cat(S[t-2]),cat(G[t-1]-G[t-2])],
 "zone_total":   lambda t:[np.tile(GT[t-1],9),np.tile(GT[t-2],9)],
 "national_sec": lambda t:[np.repeat(GN[t-1],NZ),np.repeat(GN[t-2],NZ)],
 "excess":       lambda t:[cat(G[t-1])-np.repeat(GN[t-1],NZ)],
}
def build(t,keys): return np.column_stack([x for k in keys for x in GROUPS[k](t)])
def labels(t): return np.concatenate([S[t][:,s] for s in range(9)])
EV=[yi[y] for y in range(2019,2026)]
def score(keys,sd=0):
    f1=[]
    for t in EV:
        tr=list(range(5,t))
        Xtr=np.vstack([build(k,keys) for k in tr]); ytr=np.concatenate([labels(k) for k in tr])
        Xte,yte=build(t,keys),labels(t)
        ok=np.isfinite(ytr); okt=np.isfinite(yte)
        Xtr2,ytr2=np.nan_to_num(Xtr[ok]),ytr[ok]
        m=HistGradientBoostingClassifier(max_iter=400,learning_rate=0.05,max_depth=6,random_state=sd)
        m.fit(Xtr2,ytr2,sample_weight=compute_sample_weight("balanced",ytr2))
        f1.append(f1_score(yte[okt],m.predict(np.nan_to_num(Xte[okt])),average="macro"))
    return np.mean(f1)
ALL=list(GROUPS)
full=np.mean([score(ALL,s) for s in (0,1)])
print(f"completo (todos os grupos): {full:.4f}\n")
print("REMOVER cada grupo:")
for g in ALL:
    keys=[k for k in ALL if k!=g]
    v=np.mean([score(keys,s) for s in (0,1)])
    print(f"  sem {g:14} {v:.4f}   queda {full-v:+.4f}")
print("\nSOZINHO cada grupo:")
for g in ALL:
    v=np.mean([score([g],s) for s in (0,1)])
    print(f"  so  {g:14} {v:.4f}")
print("\n  referencias: aleatorio 0.307 | teto 0.655")
