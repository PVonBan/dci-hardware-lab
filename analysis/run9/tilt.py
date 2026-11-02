import sys, numpy as np, subprocess, os
sys.argv=['x']; exec(open('run6pr/an6.py').read().split("if __name__")[0])
from scipy import signal
CENT = 1000 * 2 ** (np.arange(-12, 13) / 3)
def bands(y):
    f, P = signal.welch(y, 48000, nperseg=8192); return np.array([10*np.log10(P[(f>=c/2**(1/6))&(f<c*2**(1/6))].mean()+1e-30) for c in CENT])
sys.path.insert(0,'run9'); import lab10
lab10.slotbank('/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx','v167/bk.syx')
for prog in (1,8):
    x,yh,mk=get('B',prog,'file',False)
    rows=[]
    for tag,binp in (('1.6.6','v166/an/SSP550Test-166'),('1.6.7','v167/SSP550Test-167b')):
        os.makedirs('v167/t',exist_ok=True)
        subprocess.run([binp,'--render','v167/t','run6pr/stims/stim-file.f32','v167/bk.syx',str(prog)],check=True,capture_output=True)
        yp=np.fromfile('v167/t/%03d.f32'%prog,'<f4').reshape(-1,2)[:len(x)]
        d=np.mean([bands(yh[:,c])-bands(yp[:,c]) for c in (0,1)],0); d-=np.median(d[(CENT>=200)&(CENT<=5000)])
        rows.append((tag,d))
    print('prog',prog,'unit - ours, loudness matched (dB)')
    print('       '+' '.join('%5.0f'%c for c in CENT[::2]))
    for tag,d in rows: print('%-6s '%tag+' '.join('%+5.1f'%v for v in d[::2]))
