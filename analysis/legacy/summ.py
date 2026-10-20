import json, numpy as np, sys
cent=1000*2**(np.arange(-17,15)/3); sel=(cent>=80)&(cent<=12500)
def load(fn):
    R=json.load(open(fn)); lv=np.array([r['lvl'] for r in R]); g=np.nanmedian(np.where(np.abs(lv)<60,lv,np.nan),0)
    out={}
    for r in R:
        th=np.array(r['th']);tp=np.array(r['tp']); d=th-tp-g[:,None]
        lvl=float(np.mean(np.array(r['lvl'])-g))
        shape=d-np.median(d[:,sel]); sdev=float(np.median(np.abs(shape[:,sel])))
        t=np.array(r['t30'],float); tr=np.nanmean(t[:,0]/t[:,1]) if np.all(np.isfinite(t)) else np.nan
        out[r['n']]=dict(name=r['name'],alg=r['alg'],lvl=lvl,sdev=sdev,t30r=tr,steps=(np.array(r['steps_h'])-np.array(r['steps_p'])-g[0]).tolist())
    return out,g
O,go=load('res_old.json'); N,gn=load('res_new.json')
print('loop gain L/R old',go.round(2),'new',gn.round(2))
rev=[n for n in N if N[n]['alg'] in (24,25,26,27,28,29,30) and n>100]
for nm,D in (('old',O),('new',N)):
    l=np.array([abs(D[n]['lvl']) for n in D if abs(D[n]['lvl'])<60]); s=np.array([D[n]['sdev'] for n in D])
    t=np.array([D[n]['t30r'] for n in rev])
    print(nm,'level |dev| median %.1f dB, >3 dB: %d progs; spectral median dev %.1f dB; reverb T30 hw/plug median %.2f (IQR %.2f-%.2f)'%(np.median(l),(l>3).sum(),np.median(s),np.nanmedian(t),np.nanpercentile(t,25),np.nanpercentile(t,75)))
print('\nworst level mismatches (new):')
for n in sorted(N,key=lambda n:-abs(N[n]['lvl']))[:15]: print('  %3d %-16s alg %2d  level hw-plug %+.1f dB  (old %+.1f)'%(n,N[n]['name'],N[n]['alg'],N[n]['lvl'],O[n]['lvl']))
