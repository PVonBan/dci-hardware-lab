import numpy as np, json, sys
src=open('an.py').read().split("rows=[]")[0].replace("S=sys.argv[1]; PLUG=sys.argv[2]; OUT=sys.argv[3]","S='.'; PLUG=sys.argv[1] if len(sys.argv)>1 else 'plug'; OUT='x'")
exec(src)
R=json.load(open(sys.argv[2] if len(sys.argv)>2 else 'res_new.json')); lv=np.array([r['lvl'] for r in R]); g=np.nanmedian(np.where(np.abs(lv)<60,lv,np.nan),0)
cent=1000*2**(np.arange(-14,15)/3)
def spec(h):
    W=np.fft.rfft(h,1<<18); fq=np.fft.rfftfreq(1<<18,1/fs); m=np.abs(W)**2
    return np.array([10*np.log10(m[(fq>=c/2**(1/6))&(fq<c*2**(1/6))].mean()+1e-30) for c in cent])
def bl(x):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/fs); X[(f<200)|(f>5000)]=0; return np.fft.irfft(X,len(x))
out={}
for n in range(1,129):
    try: hw=rd24(CAP+'/%03d.wav'%n)[LAT:]
    except: continue
    pl=np.fromfile(PLUG+'/%03d.f32'%n,dtype=np.float32).reshape(-1,2).astype(float)
    sp=[];lvl=[]
    for c in (0,1):
        a=ir(hw[SW0:SW0+SEG,c])[:96000]; b=ir(pl[SW0:SW0+SEG,c])[:96000]
        g0=int(0.004*fs); wa=a[g0:]; wb=b[g0:]
        ea=(bl(wa)**2).sum(); eb=(bl(wb)**2).sum()
        if ea>1e-9 and eb>1e-9:
            d=spec(wa)-spec(wb); sp.append(d-d[np.argmin(np.abs(cent-1000))]); lvl.append(10*np.log10(ea/eb)-g[c])
    if sp: out[n]=dict(spec=np.mean(sp,0).tolist(),lvl=float(np.mean(lvl)))
json.dump({'cent':cent.tolist(),'d':out},open('wet_%s.json'%PLUG,'w'))
algs={}; names={}
for l in open(CAP+'/index.txt'):
    p=l.split('\t'); algs[int(p[0])]=int(p[2].split()[1]); names[int(p[0])]=p[1].strip()
show=[63,125,250,500,1000,2000,4000,6300,8000,10000,12500,16000]
ix=[int(np.argmin(np.abs(cent-c))) for c in show]
by={}
for n,v in out.items(): by.setdefault(algs[n],[]).append(v)
print('alg  n  wetlvl  ', ' '.join('%5s'%(str(c) if c<1000 else '%gk'%(c/1000)) for c in show))
for a in sorted(by):
    m=np.median(np.array([v['spec'] for v in by[a]]),0); L=np.median([v['lvl'] for v in by[a]])
    print('%3d %2d %+6.1f   '%(a,len(by[a]),L), ' '.join('%5.1f'%m[i] for i in ix))
