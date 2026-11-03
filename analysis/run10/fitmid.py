exec(open('run10r1/mideq.py').read().split("if __name__")[0])
from scipy.optimize import minimize
def peak(fq, f0, g, q):
    A=10**(g/40); s=1j*fq/f0
    H=(s**2+s*A/q+1)/(s**2+s/(A*q)+1); return 20*np.log10(np.abs(H))
REFR={500:resp(101,False),1000:resp(102,False),2000:resp(103,False),4000:resp(104,False)}
data=[]
for n,fc,g in tests:
    d=resp(n,False)-REFR[fc]
    d=d[1] if n in (115,116) else d.mean(0)     # left return was failing from C115 on: right only
    data.append((fc,g,d))
m=(cent>=40)&(cent<=12000)
def err(p, items, mode):
    e=0
    for fc,g,d in items:
        q=p[0] if mode=='one' else p[0]*(1 if g<0 else p[1])
        e+=np.sum((peak(cent[m],fc*p[-1],g,q)-d[m])**2)
    return e
for mode in ('one','two'):
    x0=[1.0,1.0,1.0] if mode=='two' else [1.0,1.0]
    r=minimize(err,x0,args=(data,mode),method='Nelder-Mead')
    print(mode,'params',np.round(r.x,3),'rms %.2f dB'%np.sqrt(r.fun/(len(data)*m.sum())))
    for fc,g,d in data:
        q=r.x[0] if mode=='one' else r.x[0]*(1 if g<0 else r.x[1])
        print('   %+3d@%4d rms %.2f'%(g,fc,np.sqrt(np.mean((peak(cent[m],fc*r.x[-1],g,q)-d[m])**2))))
# per-gain Q check at 2 kHz
for fc,g,d in data:
    if fc==2000:
        rr=minimize(lambda p: np.sum((peak(cent[m],2000*p[1],g*p[2],p[0])-d[m])**2),[1,1,1],method='Nelder-Mead'); print('  2k %+d: Q %.2f f %.0f gainscale %.2f'%(g,rr.x[0],2000*rr.x[1],rr.x[2]))
