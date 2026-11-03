import os, subprocess, numpy as np
exec(open('run9pr/eqcurves.py').read().split("print('== reverb")[0])
m=(cent>=60)&(cent<=8000)
hr=resp(111,False); H={n:(resp(n,False)-hr).mean(0) for n in range(103,109)}
for hp in (0,150,300,500,800,1200,2000):
    d='v167/g_%d'%hp; os.makedirs(d,exist_ok=True)
    env=dict(os.environ,T_ERHP=str(hp))
    for n in range(103,112):
        if not os.path.exists('%s/%03d.f32'%(d,n)): subprocess.run(['v167/render4_l1hp','run9pr/tests9C.syx','run9pr/stims/stim-std.f32',d,str(n)],env=env,check=True,capture_output=True)
    def rp(n):
        y=np.fromfile('%s/%03d.f32'%(d,n),'<f4').reshape(-1,2).astype(float); return np.array([bands(y[SW0:SW0+SEG,c]) for c in (0,1)])
    pr=rp(111); e={n:np.sqrt(np.mean(((rp(n)-pr).mean(0)-H[n])[m]**2)) for n in range(103,109)}
    print('ER HP %4d Hz: mean %.2f  '%(hp,np.mean(list(e.values())))+' '.join('%d:%.2f'%(k,v) for k,v in e.items()))
