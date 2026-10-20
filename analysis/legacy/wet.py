import numpy as np, json
src=open('an.py').read().split("rows=[]")[0]
src=src.replace("S=sys.argv[1]; PLUG=sys.argv[2]; OUT=sys.argv[3]","S='.'; PLUG='plug'; OUT='x'")
exec(src)
cent=1000*2**(np.arange(-14,15)/3)
def spec(h):
    W=np.fft.rfft(h,1<<18); fq=np.fft.rfftfreq(1<<18,1/fs); m=np.abs(W)**2
    return np.array([10*np.log10(m[(fq>=c/2**(1/6))&(fq<c*2**(1/6))].mean()+1e-30) for c in cent])
out={}
for n in range(1,129):
    try: hw=rd24(CAP+'/%03d.wav'%n)[LAT:]
    except: continue
    pl=np.fromfile(PLUG+'/%03d.f32'%n,dtype=np.float32).reshape(-1,2).astype(float)
    rows=[]
    for c in (0,1):
        a=ir(hw[SW0:SW0+SEG,c])[:96000]; b=ir(pl[SW0:SW0+SEG,c])[:96000]
        g0=int(0.004*fs)                                   # skip the direct sound
        wa=a[g0:].copy(); wb=b[g0:].copy()
        if (wb**2).sum()<1e-8 or (wa**2).sum()<1e-8: continue
        rows.append(spec(wa)-spec(wb))
    if rows:
        d=np.mean(rows,0); out[n]=(d-d[np.argmin(np.abs(cent-1000))]).tolist()
json.dump({'cent':cent.tolist(),'d':out},open('wet.json','w'))
