import subprocess, numpy as np, json
from scipy.optimize import minimize
H=json.load(open('../an4/hw.json'))
B=('500','1k','2k','4k','8k')
def run(rt,hz,ratio,bh,br,vi=0):
    o=subprocess.run(['./rvtune_c',str(vi),str(rt),'1.0',str(hz),str(ratio),str(bh),str(br)],capture_output=True,text=True).stdout.split()
    return dict(zip(('125','250','500','1k','2k','4k','8k'),map(float,o)))
def err(t,target):
    return sum((np.log(t[b]/t['1k'])-np.log(target[b]/target['1k']))**2 for b in B)
# 1) baseline for hall 1 from the undamped RT tests (code 20/30/50)
tgt={b:np.mean([H['A-%d-std'%n]['result']['t30'][b]/H['A-%d-std'%n]['result']['t30']['1k'] for n in (105,106,107)]) for b in B}
tgt['1k']=1.0
f=lambda p: err(run(3.7,20000,1.0,np.exp(p[0]),min(1,p[1])),tgt)
r=minimize(f,[np.log(3000),0.88],method='Nelder-Mead',options={'xatol':1e-3,'fatol':1e-5,'maxiter':60})
bh,br=float(np.exp(r.x[0])),float(min(1,r.x[1])); print('baseline hz %.0f ratio %.3f err %.5f'%(bh,br,r.fun), run(3.7,20000,1,bh,br))
res={'base':(bh,br)}
for n,(fc,lv) in zip(range(110,118),[(1,0),(1,2),(3,0),(3,2),(5,0),(5,2),(7,0),(7,2)]):
    t=H['A-%d-std'%n]['result']['t30']
    def g(p):
        x=run(3.7,np.exp(p[0]),min(1,max(0.05,p[1])),bh,br)
        # also match the 1 kHz loss relative to the undamped 4.07 s
        return err(x,t)+ (np.log(x['1k']/3.73)-np.log(t['1k']/4.07))**2
    best=None
    for h0 in (1500,3000,6000):
        rr=minimize(g,[np.log(h0),0.4],method='Nelder-Mead',options={'xatol':1e-3,'fatol':1e-5,'maxiter':80})
        if best is None or rr.fun<best.fun: best=rr
    hz,ra=float(np.exp(best.x[0])),float(min(1,max(0.05,best.x[1])))
    res['f%d l%d'%(fc,lv)]=(hz,ra,best.fun); print('f%d l%d -> hz %.0f ratio %.3f err %.4f'%(fc,lv,hz,ra,best.fun))
json.dump(res,open('dampfit.json','w'),indent=1)
