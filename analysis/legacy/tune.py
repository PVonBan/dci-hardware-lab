import numpy as np, json, re, subprocess, os, sys
exec(open('an.py').read().split("rows=[]")[0].replace("S=sys.argv[1]","S='.'"))
exec(open('rt.py').read().split("out=[]")[0].split("exec(")[0])
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
progs=[n for n in range(101,129) if F[n][0] in (24,25,26,27,28,29,30)]
BANDS=(500,1000,2000,4000)
cache='hwbands.json'
if os.path.exists(cache): HW={int(k):v for k,v in json.load(open(cache)).items()}
else:
    HW={}
    for n in progs:
        hw=rd24(CAP+'/%03d.wav'%n)[LAT:]
        HW[n]=[np.nanmean([t30(band(ir(hw[SW0:SW0+SEG,c])[:SEG],fc)) for c in (0,1)]) for fc in BANDS]
    json.dump(HW,open(cache,'w'))
def evalp(rt,de,tag,rta=0.0):
    env=dict(os.environ,SSP_RT=str(rt),SSP_DE=str(de),SSP_RTA=str(rta))
    os.makedirs('pt',exist_ok=True)
    subprocess.run(['./render','/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx','stim.f32','pt'],env=env,stdout=subprocess.DEVNULL)
    errs=[];rows=[];eb={b:[] for b in BANDS}
    for n in progs:
        pl=np.fromfile('pt/%03d.f32'%n,dtype=np.float32).reshape(-1,2).astype(float)
        P=[np.nanmean([t30(band(ir(pl[SW0:SW0+SEG,c])[:SEG],fc)) for c in (0,1)]) for fc in BANDS]
        for b,h,p in zip(BANDS,HW[n],P):
            nom=F[n][1]['Rev Time'][1]; lim=2.5*(rta+rt*nom)+1.5
            if np.isfinite(h) and np.isfinite(p) and h<lim and p<lim: errs.append(np.log(p/h)); eb[b].append(np.log(p/h))
        rows.append((n,HW[n],P))
    e=np.array(errs); print(tag,'A',rta,'RT',rt,'DE',de,'bands',' '.join('%d:%.3f'%(b,np.median(eb[b])) for b in BANDS),'median log-ratio %.3f'%np.median(e),'rms %.3f'%np.sqrt((e**2).mean()),'n',len(e)); sys.stdout.flush()
    return rows
if __name__=='__main__':
    for a in sys.argv[1:]:
        v=list(map(float,a.split(','))); rows=evalp(v[0],v[1],'',v[2] if len(v)>2 else 0.0)
    if len(sys.argv)==2:
        for n,h,p in rows: print(n,names[n][:14],'nom',F[n][1]['Rev Time'][1],'dmp',F[n][1]['Damp Frq'][1],round(F[n][1]['Damp Lvl'][1],2),' '.join('%.2f/%.2f'%(a,b) for a,b in zip(h,p)))
