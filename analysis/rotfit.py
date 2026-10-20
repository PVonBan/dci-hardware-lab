import numpy as np, subprocess, os, sys, itertools
sys.argv=['x']; exec(open('../an4/an4.py').read().split("def main")[0])
C='/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run4/'
cal=Cal(1179,(10**(0.9/20),10**(-4.6/20)))
x=load('../run4/stims/stim-tone.wav'); mk=markers('../run4/stims','tone'); nm,s0,n=mk[0]
def feat(y):
    out=[]
    for ch in (0,1):
        z=y[s0+24000:s0+n-4800,ch]; w=np.hanning(len(z)); N=1<<21; S=np.abs(np.fft.rfft(z*w,N)); f=np.fft.rfftfreq(N,1/FS)
        tot=np.sum(S[(f>440)&(f<560)]**2)
        for off in (-13.4,-6.7,0,6.7,13.4,-8.0,8.0):
            m=np.abs(f-(500+off))<0.35; out.append(max(-45.0,10*np.log10(np.sum(S[m]**2)/tot+1e-12)))
        e=np.abs(signal.hilbert(z))[::48]; e=20*np.log10(e+1e-9); out.append((np.percentile(e,95)-np.percentile(e,5))/3)
    return np.array(out)
hw={k:feat(cal.apply(load(C+'r4B-%d-tone.wav'%k),len(x))) for k in (118,119)}
print('hw119',np.round(hw[119],1))
best=[]
for am,dop in itertools.product((0.28,0.6,0.9),(0.6,1.0,1.4,1.9,2.6)):
    os.environ['ROT_AM']=str(am); os.environ['ROT_DOP']=str(dop)
    e=0
    for k in (118,119):
        subprocess.run(['./render_rot','../run4/tests4B.syx','../run4/stims/stim-tone.f32','.',str(k)],capture_output=True)
        y=np.fromfile('%03d.f32'%k,'<f4').reshape(-1,2).astype(float)
        e+=np.sum((feat(y)-hw[k])**2)
    best.append((e,am,dop)); print(am,dop,round(e,1),flush=True)
print(sorted(best)[:5])
