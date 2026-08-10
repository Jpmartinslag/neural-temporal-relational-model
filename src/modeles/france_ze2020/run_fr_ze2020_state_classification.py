"""HERALD 66 (DEC-100): three-state classification, with and without relational features."""
import sys,numpy as np,pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import f1_score,accuracy_score
SEC=["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]; W,TOPK,TH=4,10,0.05
df=pd.read_csv(sys.argv[1]); yrs=sorted(df.target_year.unique()); zs=sorted(df.ZE2020.unique())
zi={z:k for k,z in enumerate(zs)}; yi={y:k for k,y in enumerate(yrs)}
Y=np.zeros((len(yrs),len(zs),9))
for r in df.itertuples(index=False): Y[yi[r.target_year],zi[r.ZE2020]]=[getattr(r,s) for s in SEC]
G=np.full_like(Y,np.nan); G[1:]=np.log1p(Y[1:])-np.log1p(Y[:-1])
S=np.where(G<=-TH,0,np.where(G>=TH,2,1)).astype(float); S[0]=np.nan   # 0 decline 1 stagn 2 grow
NZ=len(zs); sec_of=np.repeat(np.arange(9),NZ)

def build(t,relational):
    """Features for evaluation year index t, using only years <= t-1."""
    lag=[G[t-k][:, :].T.reshape(-1) for k in range(1,4)]          # g_{t-1..t-3} per node
    lag=[np.concatenate([G[t-k][:,s] for s in range(9)]) for k in range(1,4)]
    lvl=np.concatenate([np.log1p(Y[t-1][:,s]) for s in range(9)])
    shr=np.concatenate([Y[t-1][:,s]/np.maximum(Y[t-1].sum(1),1e-9) for s in range(9)])
    X=[*lag,lvl,shr]
    if relational:
        traj=np.concatenate([G[t-W:t,:,s].T for s in range(9)],axis=0)
        fin=np.isfinite(traj).all(1)
        Tz=np.zeros_like(traj); m=traj[fin].mean(1,keepdims=True); sd=np.maximum(traj[fin].std(1,keepdims=True),1e-9)
        Tz[fin]=(traj[fin]-m)/sd
        C=Tz@Tz.T/traj.shape[1]
        same=(sec_of[:,None]==sec_of[None,:]); np.fill_diagonal(same,False)
        C=np.where(same&fin[None,:],C,-np.inf)
        ix=np.argpartition(-C,TOPK,axis=1)[:,:TOPK]
        prev=np.concatenate([S[t-1][:,s] for s in range(9)])       # analogues' LAST state
        gprev=np.concatenate([G[t-1][:,s] for s in range(9)])
        X += [np.nanmean(prev[ix],axis=1), np.nanmean(gprev[ix],axis=1),
              np.nanstd(gprev[ix],axis=1)]
    return np.column_stack(X)

def labels(t): return np.concatenate([S[t][:,s] for s in range(9)])
SEEDS=[0,1,2,3,4]
MODELS={f"mlp_s{sd}": (lambda sd=sd: make_pipeline(StandardScaler(),MLPClassifier((64,32),max_iter=600,random_state=sd))) for sd in SEEDS}
EV=[yi[y] for y in range(2019,2026)]
res={}
for rel in (False,True):
    for name,mk in MODELS.items():
        key=f"{name}{'+rel' if rel else ''}"; f1s=[];accs=[]
        for t in EV:
            tr=[k for k in range(W+1,t)]
            Xtr=np.vstack([build(k,rel) for k in tr]); ytr=np.concatenate([labels(k) for k in tr])
            Xte,yte=build(t,rel),labels(t)
            ok=np.isfinite(Xtr).all(1)&np.isfinite(ytr); okt=np.isfinite(Xte).all(1)&np.isfinite(yte)
            m=mk(); m.fit(Xtr[ok],ytr[ok]); p=m.predict(Xte[okt])
            f1s.append(f1_score(yte[okt],p,average="macro")); accs.append(accuracy_score(yte[okt],p))
        res[key]=(np.array(f1s),np.array(accs))
# baselines, incl. stratified random
rng=np.random.default_rng(7)
pers=[];maj=[];rand=[]
for t in EV:
    yte=labels(t); ok=np.isfinite(yte); yt=yte[ok]; so=sec_of[ok]
    pers.append(f1_score(yt,np.ones_like(yt),average="macro"))
    prev=labels(t-1); mm=np.array([np.bincount(prev[np.isfinite(prev)&(sec_of==s)].astype(int),minlength=3).argmax() for s in range(9)])
    maj.append(f1_score(yt,mm[so],average="macro"))
    prv=labels(t-1); pv=prv[np.isfinite(prv)].astype(int)
    pr=np.bincount(pv,minlength=3)/len(pv)
    rand.append(np.mean([f1_score(yt,rng.choice(3,size=len(yt),p=pr),average="macro") for _ in range(20)]))
res["persistence"]=(np.array(pers),np.array([np.nan]*len(pers)))
res["sector_prev_mode"]=(np.array(maj),np.array([np.nan]*len(maj)))
res["random_stratified"]=(np.array(rand),np.array([np.nan]*len(rand)))
print(f"{'modelo':18}"+"".join(f"{y:>7}" for y in range(2019,2026))+f"{'F1med':>8}{'acc':>7}")
for k,(f,a) in sorted(res.items(),key=lambda x:-np.mean(x[1][0])):
    print(f"{k:18}"+"".join(f"{x:7.3f}" for x in f)+f"{f.mean():8.3f}{np.nanmean(a):7.3f}")
print("\n=== S1 gate por seed: mlp+rel vs mlp ===")
wins=[]
for n in MODELS:
    a,b=res[n][0],res[f"{n}+rel"][0]; w=int((b>a).sum()); wins.append(w)
    print(f"  {n:9} {b.mean():.3f} vs {a.mean():.3f} | ganha {w}/7 | delta {b.mean()-a.mean():+.4f}")
print(f"\n  seeds que passam (>=5/7): {sum(1 for w in wins if w>=5)}/{len(wins)}")
rb=res["random_stratified"][0].mean()
print(f"  baseline aleatorio estratificado: {rb:.3f}")
for n in MODELS:
    print(f"  {n}+rel acima do aleatorio: {res[n+'+rel'][0].mean()-rb:+.3f}")
