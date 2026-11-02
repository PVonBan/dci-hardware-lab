exec(open('run9pr/eqcurves.py').read().split("print('== reverb")[0])
import glob
def respd(n,d):
    y=np.fromfile('%s/%03d.f32'%(d,n),'<f4').reshape(-1,2).astype(float); return np.array([bands(y[SW0:SW0+SEG,c]) for c in (0,1)])
m=(cent>=60)&(cent<=8000)
for d in sorted(glob.glob('v167/out_*')):
    tot=[]
    out=[]
    for ref,tests in ((111,(103,104,105,106,107,108)),(116,(112,113,114,115))):
        hr=resp(ref,False); pr=respd(ref,d)
        for n in tests:
            e=((respd(n,d)-pr)-(resp(n,False)-hr)).mean(0)[m]; tot.append(np.sqrt(np.mean(e**2))); out.append('%d:%.2f'%(n,tot[-1]))
    print(d.split('out_')[1], 'mean rms %.2f dB'%np.mean(tot), ' '.join(out))
