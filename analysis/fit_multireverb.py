import sys,os,subprocess,json,numpy as np,itertools
sys.argv=['x']; exec(open('an4/an4.py').read().split('def main')[0])
x=load('run6pr/stims/stim-std.wav'); mk=markers('run6pr/stims','std')
H=json.load(open('run6pr/hw_std.json'))
TESTS=[114,115,117,119,120,121,122,124]; B=['250','500','1k','2k','4k','8k']
def score(env,tag):
    d='fit158/m_'+tag; os.makedirs(d,exist_ok=True); errs=[]; per={}
    for n in TESTS:
        subprocess.run(['fit158/rtune','run6/tests6A.syx','run6pr/stims/stim-std.f32',d,str(n)],env={**os.environ,**env},check=True,capture_output=True)
        y=load('%s/%03d.f32'%(d,n)); r=an_std(y,x,mk)['t30']; h=H['A-%d-std'%n]['result']['t30']
        e=[np.log(h[b]/r[b]) for b in B]; errs+=e; per[n]=np.round(np.exp(e),2).tolist()
    return float(np.sqrt(np.mean(np.square(errs)))),per
if __name__=='__main__':
    best=[]
    for s,hz,c in itertools.product([0.86,0.89,0.92],[2500,4000,6000],[0.0,0.06,0.12,0.2]):
        sc,per=score({'T_MS':str(s),'T_MH':str(hz),'T_MC':str(c)},'%g_%g_%g'%(s,hz,c)); best.append((sc,s,hz,c)); print('%.4f'%sc,s,hz,c,flush=True)
    best.sort(); print('BEST',best[:3])
    print(score({'T_MS':str(best[0][1]),'T_MH':str(best[0][2]),'T_MC':str(best[0][3])},'best')[1])
