exec(open('run9pr/eqcurves.py').read().split("print('== reverb")[0])
from scipy.optimize import minimize_scalar, minimize
def lo1(f,fc,g): G=10**(g/20); return 10*np.log10((f**2+G**2*fc**2)/(f**2+fc**2))
def hi1(f,fc,g): G=10**(g/20); return 10*np.log10((G**2*f**2+fc**2)/(f**2+fc**2))
def lo2(f,fc,g,q):
    # analog 2nd-order RBJ-like low shelf magnitude via s-domain
    A=10**(g/40); s=1j*f/fc
    H=A*(s**2+np.sqrt(A)/q*s+A)/(A*s**2+np.sqrt(A)/q*s+1); return 20*np.log10(np.abs(H))
def hi2(f,fc,g,q):
    A=10**(g/40); s=1j*f/fc
    H=A*(A*s**2+np.sqrt(A)/q*s+1)/(s**2+np.sqrt(A)/q*s+A); return 20*np.log10(np.abs(H))
m=(cent>=30)&(cent<=12000)
data={}
for ref,tests,kind in ((116,[(114,'lo',-12),(115,'lo',12),(112,'hi',-12),(113,'hi',12)],'delay'),(111,[(107,'lo',-12),(108,'lo',12)],'reverb')):
    hr=resp(ref,False)
    for n,t,g in tests: data[(kind,t,g)]=(resp(n,False)-hr).mean(0)
for t,fn1,fn2 in (('lo',lo1,lo2),('hi',hi1,hi2)):
    keys=[k for k in data if k[1]==t]
    e1=lambda fc: sum(np.sum((fn1(cent[m],fc,k[2])-data[k][m])**2) for k in keys)
    r=minimize_scalar(e1,bounds=(50,20000),method='bounded'); 
    print(t,'1st order fc %.0f Hz rms %.2f dB'%(r.x,np.sqrt(r.fun/(len(keys)*m.sum()))))
    e2=lambda p: sum(np.sum((fn2(cent[m],p[0],k[2],p[1])-data[k][m])**2) for k in keys)
    r2=minimize(e2,[300 if t=='lo' else 4000,0.5],method='Nelder-Mead'); print(t,'2nd order fc %.0f Q %.2f rms %.2f dB'%(r2.x[0],r2.x[1],np.sqrt(r2.fun/(len(keys)*m.sum()))))
    for k in keys: print('  ',k,' '.join('%+5.1f'%(fn1(cent[i],r.x,k[2])-data[k][i]) for i in range(len(cent)) if m[i] and i%2==0))
