import numpy as np, wave, glob, os, sys, json
S=sys.argv[1]; PLUG=sys.argv[2]; OUT=sys.argv[3]; CAP='/mnt/user-data/uploads/Downloads/RSP-550/lab/capture'
fs=48000
def rd24(f):
    w=wave.open(f); n=w.getnframes(); b=np.frombuffer(w.readframes(n),dtype=np.uint8).reshape(-1,3).astype(np.int32)
    x=b[:,0]|(b[:,1]<<8)|(b[:,2]<<16); x=np.where(x>=1<<23,x-(1<<24),x)/2**23; return x.reshape(-1,2)
stim=np.fromfile(S+'/stim.f32',dtype=np.float32).reshape(-1,2).astype(float)
names={}; algs={}
for l in open(CAP+'/index.txt'):
    p=l.rstrip('\n').split('\t'); names[int(p[0])]=p[1].strip(); algs[int(p[0])]=int(p[2].split()[1])
for _n,_nm,_a in ((56,'Tapping Delay',33),(67,'Doubling Echo',3),(160,'Hall / Room *',37)): names.setdefault(_n,_nm); algs.setdefault(_n,_a)
SW0=396002; SWN=120000; SEG=SWN+144000
LAT=1179
x=stim[SW0:SW0+SEG,0]
NF=1<<19
X=np.fft.rfft(x,NF); f=np.fft.rfftfreq(NF,1/fs)
band=(f>20)&(f<20000)
Xi=np.where(band,1/np.where(np.abs(X)>1e-9,X,1),0)
def ir(y): return np.fft.irfft(np.fft.rfft(y,NF)*Xi,NF)
cent=1000*2**(np.arange(-17,15)/3)   # 1/3-oct 20 Hz..20 kHz
def third(H):
    m=np.abs(H)**2; out=[]
    for c in cent:
        s=(f>=c/2**(1/6))&(f<c*2**(1/6)); out.append(10*np.log10(m[s].mean()+1e-20))
    return np.array(out)
def edt_t30(h):
    e=np.cumsum((h**2)[::-1])[::-1]; e=10*np.log10(e/e[0]+1e-30)
    def t(db): i=np.where(e<db)[0]; return i[0]/fs if len(i) else np.nan
    t5,t35=t(-5),t(-35); return (t35-t5)*2 if np.isfinite(t5) and np.isfinite(t35) else np.nan
rows=[]
for fh in sorted(glob.glob(CAP+'/[0-9][0-9][0-9].wav')):
    n=int(os.path.basename(fh)[:3])
    hw=rd24(fh); pl=np.fromfile(S+'/'+PLUG+'/%03d.f32'%n,dtype=np.float32).reshape(-1,2).astype(float)
    hw=hw[LAT:]; hw=np.vstack([hw,np.zeros((LAT,2))])     # remove loop latency
    r={'n':n,'name':names[n],'alg':algs[n]}
    Hh=[];Hp=[];ih=[];ip=[]
    for c in (0,1):
        a=ir(hw[SW0:SW0+SEG,c]); b=ir(pl[SW0:SW0+SEG,c]); ih.append(a); ip.append(b)
        Hh.append(np.fft.rfft(a[:SEG])); Hp.append(np.fft.rfft(b[:SEG]))
    # broadband level (sweep segment energy)
    eh=[(hw[SW0:SW0+SEG,c]**2).sum() for c in (0,1)]; ep=[(pl[SW0:SW0+SEG,c]**2).sum() for c in (0,1)]
    r['lvl']=[10*np.log10(eh[c]/(ep[c]+1e-20)+1e-20) for c in (0,1)]
    global ff
    fq=np.fft.rfftfreq(len(ih[0][:SEG]) if False else SEG,1/fs)
    def third2(H):
        m=np.abs(H)**2; out=[]
        for c in cent:
            s=(fq>=c/2**(1/6))&(fq<c*2**(1/6)); out.append(10*np.log10(m[s].mean()+1e-20))
        return np.array(out)
    th=[third2(Hh[c]) for c in (0,1)]; tp=[third2(Hp[c]) for c in (0,1)]
    r['th']=[t.tolist() for t in th]; r['tp']=[t.tolist() for t in tp]
    # timing: cross-correlation of IRs (first 0.5 s)
    L=24000; lag=[]; corr=[]
    for c in (0,1):
        a=ih[c][:L]; b=ip[c][:L]
        cc=np.fft.irfft(np.fft.rfft(a,2*L)*np.conj(np.fft.rfft(b,2*L)),2*L); k=int(np.argmax(np.abs(cc)))
        lag.append(k if k<L else k-2*L); corr.append(float(np.abs(cc).max()/np.sqrt((a**2).sum()*(b**2).sum()+1e-30)))
    r['lag']=lag; r['corr']=corr
    r['t30']=[[edt_t30(ih[c][:SEG]),edt_t30(ip[c][:SEG])] for c in (0,1)]
    # level steps (1 kHz) L channel: gain at each step
    st=[660002+j*19200 for j in range(5)]
    def stepdb(y,a): s=y[a+2400:a+12000]; return 20*np.log10(np.sqrt((s**2).mean())*1.4142+1e-12)
    r['steps_h']=[stepdb(hw[:,0],a) for a in st]; r['steps_p']=[stepdb(pl[:,0],a) for a in st]
    # noise-free tail check: energy 1-3 s after the L impulse
    r['tail']=[10*np.log10((hw[12000+48000:12000+144000,0]**2).mean()+1e-20),10*np.log10((pl[12000+48000:12000+144000,0]**2).mean()+1e-20)]
    rows.append(r)
json.dump(rows,open(S+'/'+OUT,'w'),default=float)
print(len(rows))
