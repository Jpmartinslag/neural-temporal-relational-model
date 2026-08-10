"""HERALD 66 section 7: balanced classes + richer features."""
import sys,numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import f1_score,accuracy_score
SEC=["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]; W,TOPK,TH=4,10,0.05
df=pd.read_csv(sys.argv[1]); yrs=sorted(df.target_year.unique()); zs=sorted(df.ZE2020.unique())
zi={z:k for k,z in enumerate(zs)}; yi={y:k for k,y in enumerate(yrs)}
Y=np.zeros((len(yrs),len(zs),9))
for r in df.itertuples(index=False): Y[yi[r.target_year],zi[r.ZE2020]]=[getattr(r,s) for s in SEC]
G=np.full_like(Y,np.nan); G[1:]=np.log1p(Y[1:])-np.log1p(Y[:-1])
S=np.where(G<=-TH,0,np.where(G>=TH,2,1)).astype(float); S[0]=np.nan
NZ=len(zs); sec_of=np.repeat(np.arange(9),NZ)
TOT=Y.sum(2); GT=np.full_like(TOT,np.nan); GT[1:]=np.log1p(TOT[1:])-np.log1p(TOT[:-1])
NAT=Y.sum(1); GN=np.full_like(NAT,np.nan); GN[1:]=np.log1p(NAT[1:])-np.log1p(NAT[:-1])

def build(t,rel):
    cat=lambda A:np.concatenate([A[:,s] for s in range(9)])
    X=[cat(G[t-1]),cat(G[t-2]),cat(G[t-3]),
       cat(np.log1p(Y[t-1])),
       cat(Y[t-1]/np.maximum(Y[t-1].sum(1,keepdims=True),1e-9)),
       np.tile(GT[t-1],9), np.tile(GT[t-2],9),                    # zone total momentum
       np.repeat(GN[t-1],NZ), np.repeat(GN[t-2],NZ),              # national sector momentum
       cat(S[t-1]), cat(S[t-2]),                                  # own recent states
       cat(G[t-1]-G[t-2]),                                        # acceleration
       cat(G[t-1])-np.repeat(GN[t-1],NZ),                         # excess over national sector
       ]
    if rel:
        traj=np.concatenate([G[t-W:t,:,s].T for s in range(9)],axis=0)
        fin=np.isfinite(traj).all(1)
        Tz=np.zeros_like(traj)
        if fin.any():
            m=traj[fin].mean(1,keepdims=True); sd=np.maximum(traj[fin].std(1,keepdims=True),1e-9)
            Tz[fin]=(traj[fin]-m)/sd
        C=Tz@Tz.T/traj.shape[1]
        same=(sec_of[:,None]==sec_of[None,:]); np.fill_diagonal(same,False)
        C=np.where(same&fin[None,:],C,-np.inf)
        ix=np.argpartition(-C,TOPK,axis=1)[:,:TOPK]
        gp=cat(G[t-1]); sp=cat(S[t-1])
        an=sp[ix]
        X += [np.nanmean(gp[ix],axis=1), np.nanstd(gp[ix],axis=1),
              np.nanmean(an==2,axis=1), np.nanmean(an==0,axis=1),   # share of analogues growing / declining
              np.take_along_axis(C,ix,1).mean(1)]                   # how good the match is
    return np.column_stack(X)
def labels(t): return np.concatenate([S[t][:,s] for s in range(9)])

def mk(name,sd):
    if name=="mlp":  return make_pipeline(StandardScaler(),MLPClassifier((128,64),max_iter=800,alpha=1e-3,random_state=sd))
    if name=="gbm":  return HistGradientBoostingClassifier(max_iter=400,learning_rate=0.05,max_depth=6,random_state=sd)
    return make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,class_weight="balanced"))
EV=[yi[y] for y in range(2019,2026)]
out={}
for name in ["mlp","gbm"]:
    for rel in (False,True):
        for sd in [0,1,2]:
            key=f"{name}{'+rel' if rel else ''}_s{sd}"; f1=[]
            for t in EV:
                tr=[k for k in range(W+1,t)]
                Xtr=np.vstack([build(k,rel) for k in tr]); ytr=np.concatenate([labels(k) for k in tr])
                Xte,yte=build(t,rel),labels(t)
                ok=np.isfinite(Xtr).all(1)&np.isfinite(ytr); okt=np.isfinite(Xte).all(1)&np.isfinite(yte)
                Xtr2,ytr2=np.nan_to_num(Xtr[ok]),ytr[ok]
                sw=compute_sample_weight("balanced",ytr2)
                m=mk(name,sd)
                if name=="gbm": m.fit(Xtr2,ytr2,sample_weight=sw)
                else: m.fit(Xtr2,ytr2)          # MLP: no sample_weight support in sklearn
                f1.append(f1_score(yte[okt],m.predict(np.nan_to_num(Xte[okt])),average="macro"))
            out[key]=np.array(f1); print(f"{key:14} {out[key].mean():.4f}",flush=True)
print("\n=== resumo ===")
for name in ["mlp","gbm"]:
    a=np.mean([out[f"{name}_s{s}"].mean() for s in [0,1,2]])
    b=np.mean([out[f"{name}+rel_s{s}"].mean() for s in [0,1,2]])
    w=[int((out[f"{name}+rel_s{s}"]>out[f"{name}_s{s}"]).sum()) for s in [0,1,2]]
    print(f"  {name:4} sem rel {a:.4f} | com rel {b:.4f} | delta {b-a:+.4f} | anos ganhos {w}")
print("\n  referencias: aleatorio 0.307 | anterior mlp+rel 0.340 | teto 0.655")
