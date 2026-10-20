import numpy as np, wave, json, re
exec(open('an.py').read().split("rows=[]")[0].replace("S=sys.argv[1]","S='.'"))
F={}
for l in open('fields.txt'):
    p=l.rstrip('\n').split('\t'); n=int(p[0]); d={}
    for kv in p[2:]:
        m=re.match(r'(.+)=(-?\d+)\((.+)\)',kv); d[m.group(1)]=(int(m.group(2)),float(m.group(3)))
    F[n]=(int(p[1]),d)
def band(h,fc):
    H=np.fft.rfft(h); fq=np.fft.rfftfreq(len(h),1/fs); H[(fq<fc/1.414)|(fq>fc*1.414)]=0; return np.fft.irfft(H,len(h))
def t30(h):
    e=np.cumsum((h**2)[::-1])[::-1]; e=10*np.log10(e/e[0]+1e-30)
    def t(db): i=np.where(e<db)[0]; return i[0]/fs if len(i) else np.nan
    a,b=t(-5),t(-25); return (b-a)*3
out=[]
for n in range(1,129):
    if n not in F or F[n][0] not in (24,25,26,27,28,29,30,36): continue
    try: hw=rd24(CAP+'/%03d.wav'%n)
    except: continue
    pl=np.fromfile('plug/%03d.f32'%n,dtype=np.float32).reshape(-1,2).astype(float)
    hw=hw[LAT:]
    res=[]
    for fc in (500,1000,4000):
        vals=[]
        for src in (hw,pl):
            ts=[t30(band(ir(src[SW0:SW0+SEG,c])[:SEG],fc)) for c in (0,1)]
            vals.append(np.nanmean(ts))
        res.append(vals)
    d=F[n][1]
    out.append((n,names[n],F[n][0],d.get('Rev Time',(0,np.nan))[1],d.get('Damp Frq',(0,0))[1],d.get('Damp Lvl',(0,0))[1],res))
    print(n,names[n][:14],F[n][0],'RT',d.get('Rev Time',(0,np.nan))[1],'damp',d.get('Damp Frq',(0,0))[1],round(d.get('Damp Lvl',(0,0))[1],2),' 500/1k/4k hw:plug', ' '.join('%.2f:%.2f'%tuple(v) for v in res))
json.dump(out,open('rt.json','w'),default=float)
