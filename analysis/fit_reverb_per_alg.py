# Fit per-algorithm reverb decay corrections: mid scale, LF ratio, damping-corner scale, floor.
import sys, os, json, subprocess, tempfile, numpy as np
from scipy.optimize import minimize
sys.argv=[sys.argv[0]]+sys.argv[1:]
ALG=int(os.environ['ALG'])
exec(open('../an4/an4.py').read().split("def main")[0])
U='/mnt/user-data/uploads/Downloads/RSP-550/lab/'
BK=U+'RSP550-backup-20261018-041833.syx'; T4='../run4/tests4A.syx'
cal=Cal(1179,(10**(0.9/20),10**(-4.6/20)))
xs=load('../run4/stims/stim-std.wav'); mk=markers('../run4/stims','std')
B=('250','500','1k','2k','4k')
import re
alg_of={}
d=open(BK,'rb').read(); i=0
while i+106<=len(d):
    if d[i]==0xF0 and d[i+5] in (3,4) and d[i+105]==0xF7:
        n=d[i+6]+1 if d[i+5]==3 else d[i+6]+129; alg_of[n]=d[i+8+0x11]; i+=106
    else: i+=1
items=[]   # (syx, n, hw-path)
for n in range(101,161):
    if alg_of.get(n)==ALG and os.path.exists(U+'capture/%03d.wav'%n): items.append((BK,n,U+'capture/%03d.wav'%n))
d=open(T4,'rb').read()
for i in range(0,len(d),106):
    n=d[i+6]+1
    if d[i+8+0x11]==ALG and n>=102 and n not in (103,104,110,112,114,116,118,119,120,121,122,123,124): items.append((T4,n,U+'capture/run4/r4A-%03d-std.wav'%n))
HW=[]
for syx,n,f in items:
    t=an_std(cal.apply(load(f),len(xs)),xs,mk)['t30']; HW.append([t[b] for b in B])
HW=np.array(HW,float)
tmp=tempfile.mkdtemp()
def plug(params):
    env=dict(os.environ, **{'RVFIX_%d'%ALG:'%f,%f,%f,%f'%tuple(params)})
    out=[]
    for syx,n,f in items:
        subprocess.run(['../an4/render_tune',syx,'../run4/stims/stim-std.f32',tmp,str(n)],env=env,capture_output=True)
        p=np.fromfile(os.path.join(tmp,'%03d.f32'%n),'<f4').reshape(-1,2).astype(float)
        t=an_std(p,xs,mk)['t30']; out.append([t[b] for b in B])
    return np.array(out,float)
def err(P):
    r=np.log(HW/P); r=r[np.isfinite(r)]; return float(np.sqrt(np.mean(r**2))), r
base=plug([1,1,1,0]); e0,r0=err(base)
def f(x):
    mid,lf,ds,fl=np.exp(x[0]),np.exp(x[1]),np.exp(x[2]),max(0.0,x[3])
    return err(plug([mid,lf,ds,fl]))[0]
res=minimize(f,[0,0,0,0.2],method='Nelder-Mead',options={'xatol':0.01,'fatol':0.001,'maxiter':120,'initial_simplex':[[0,0,0,0.2],[0.1,0,0,0.2],[0,0.15,0,0.2],[0,0,0.3,0.2],[0,0,0,0.7]]})
x=res.x; best=[float(np.exp(x[0])),float(np.exp(x[1])),float(np.exp(x[2])),float(max(0,x[3]))]
P=plug(best); e1,r1=err(P)
med=lambda r: float(np.median(np.abs(np.exp(r)-1)))
out={'alg':ALG,'n':[n for _,n,_ in items],'params':best,'rms_log_before':e0,'rms_log_after':e1,'median_abs_before':med(r0),'median_abs_after':med(r1),
     'hw':HW.round(3).tolist(),'before':base.round(3).tolist(),'after':P.round(3).tolist()}
json.dump(out,open('fit_%d.json'%ALG,'w'),indent=1)
print(ALG,len(items),'progs; params',np.round(best,3),'median |err| %.1f%% -> %.1f%%'%(100*med(r0),100*med(r1)))
