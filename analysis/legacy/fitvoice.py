import numpy as np, json
from scipy.optimize import least_squares
fs=48000
W=json.load(open('wet_plug.json')); cent=np.array(W['cent'])
R={r['n']:r for r in json.load(open('res_new.json'))}
lv=np.array([r['lvl'] for r in R.values()]); g=np.nanmedian(np.where(np.abs(lv)<60,lv,np.nan),0)
cent17=1000*2**(np.arange(-17,15)/3)
algs={}
for l in open('/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/index.txt'):
    p=l.split('\t'); algs[int(p[0])]=int(p[2].split()[1])
def rbj(kind,f0,gdb,q=0.7071):
    A=10**(gdb/40); w=2*np.pi*f0/fs; c=np.cos(w); s=np.sin(w); al=s/(2*q)
    if kind=='ls':
        b=[A*((A+1)-(A-1)*c+2*np.sqrt(A)*al),2*A*((A-1)-(A+1)*c),A*((A+1)-(A-1)*c-2*np.sqrt(A)*al)]
        a=[(A+1)+(A-1)*c+2*np.sqrt(A)*al,-2*((A-1)+(A+1)*c),(A+1)+(A-1)*c-2*np.sqrt(A)*al]
    elif kind=='hs':
        b=[A*((A+1)+(A-1)*c+2*np.sqrt(A)*al),-2*A*((A-1)+(A+1)*c),A*((A+1)+(A-1)*c-2*np.sqrt(A)*al)]
        a=[(A+1)-(A-1)*c+2*np.sqrt(A)*al,2*((A-1)-(A+1)*c),(A+1)-(A-1)*c-2*np.sqrt(A)*al]
    else: # lp
        b=[(1-c)/2,1-c,(1-c)/2]; a=[1+al,-2*c,1-al]
    return np.array(b)/a[0],np.array(a)/a[0]
def resp(b,a,f):
    z=np.exp(-1j*2*np.pi*f/fs); return 20*np.log10(np.abs((b[0]+b[1]*z+b[2]*z*z)/(a[0]+a[1]*z+a[2]*z*z)))
def model(p,kinds,f):
    out=np.zeros_like(f); i=0
    for k in kinds:
        if k=='lp': b,a=rbj('lp',p[i],0,p[i+1]); i+=2
        elif k=='lp4': 
            b,a=rbj('lp',p[i],0,0.5412); out+=resp(b,a,f); b,a=rbj('lp',p[i],0,1.3066); i+=1
        else: b,a=rbj(k,p[i],p[i+1]); i+=2
        out+=resp(b,a,f)
    return out
def fit(target,f,kinds,p0,lo,hi,w=None):
    w=np.ones_like(f) if w is None else w
    r=least_squares(lambda p:(model(p,kinds,f)-model(p,kinds,np.array([1000.0]))[0]-target)*w,p0,bounds=(lo,hi))
    return r.x, np.sqrt(np.mean(((model(r.x,kinds,f)-model(r.x,kinds,np.array([1000.0]))[0]-target))**2))
specs={}
def med_wet(a):
    v=[np.array(W['d'][str(n)]['spec']) for n in W['d'] if algs[int(n)]==a]; L=[W['d'][str(n)]['lvl'] for n in W['d'] if algs[int(n)]==a]
    return np.median(v,0), float(np.median(L))
def med_full(alist):
    v=[]; L=[]
    for n,r in R.items():
        if r['alg'] in alist:
            d=(np.array(r['th'])-np.array(r['tp'])-g[:,None]).mean(0); v.append(d-d[np.argmin(np.abs(cent17-1000))]); L.append(np.mean(np.array(r['lvl'])-g))
    return np.median(v,0), float(np.median(L))
sel=(cent>=40)&(cent<=16500); f=cent[sel]
plan={  # alg: (kinds, p0, lo, hi)
 2:(['lp'],[8000,0.7],[1500,0.4],[20000,2.0]),
 17:(['lp'],[12000,0.7],[3000,0.4],[22000,2.0]),
 21:(['lp'],[14000,0.7],[3000,0.4],[22000,2.0]),
 25:(['hs'],[6000,-6],[1500,-20],[16000,6]),
 30:(['hs'],[4000,-8],[1500,-20],[16000,6]),
 24:(['hs'],[4000,3],[1000,-6],[16000,8]),
 26:(['hs'],[4000,3],[1000,-6],[16000,8]),
 27:(['hs'],[4000,4],[1000,-6],[16000,8]),
 31:(['lp'],[11000,0.7],[3000,0.4],[22000,2.0]),
 36:(['hs'],[8000,8],[1500,-6],[18000,16]),
}
res={}
for a,(k,p0,lo,hi) in plan.items():
    t,L=med_wet(a); p,e=fit(t[sel],f,k,p0,lo,hi); res[a]=(k,p.tolist(),L); print('alg %2d %s %s  wet level %+.1f dB  fit rms %.1f dB'%(a,k,np.round(p,2).tolist(),L,e))
# rotary: full response (no dry), 23+39 together
t,L=med_full([23,39]); f17=cent17[(cent17>=40)&(cent17<=16500)]; t17=t[(cent17>=40)&(cent17<=16500)]
k=['ls','lp4','lp']; p,e=fit(t17,f17,k,[150,9,5500,9000,0.7],[40,0,2000,3000,0.4],[600,15,12000,20000,2.0]); res[23]=res[39]=(k,p.tolist(),L)
print('rotary',np.round(p,2).tolist(),'level %+.1f fit rms %.1f'%(L,e))
# levels only
for a in (11,14,15,16,28,32):
    t,L=med_wet(a); res[a]=([],[],L); print('alg %2d level %+.1f'%(a,L))
json.dump(res,open('voicing.json','w'))
