import numpy as np, subprocess, sys, os
from scipy import signal
os.chdir('/tmp/claude-0/-home-claude/43821833-de77-5012-b98f-e22767bd5dd6/scratchpad')
src=open('cmp/an.py').read().split('rows=[]')[0]; sys.argv=['x','.','x','/dev/null']; exec(src.replace("stim=np.fromfile(S+'/stim.f32'","stim=np.fromfile('cmp/stim.f32'"))
plan=[l.rstrip('\n').split('\t') for l in open('run9/plan9.txt')]
def render(syx,stim,n):
    subprocess.run(['an4/render4',syx,stim,'run9/r',str(n)],check=True,capture_output=True)
    return np.fromfile('run9/r/%03d.f32'%n,'<f4').reshape(-1,2).astype(float)
cent=np.array([100,250,1000,4000,8000,10000,12500,16000])
def tf(y):
    out=[]
    for c in (0,1):
        h=ir(y[SW0:SW0+SEG,c]); H=np.abs(np.fft.rfft(h[:SEG]))**2; fq=np.fft.rfftfreq(SEG,1/fs)
        out.append([10*np.log10(H[(fq>=k/1.12)&(fq<k*1.12)].mean()+1e-30) for k in cent])
    return np.array(out).mean(0)
def directratio(y):
    r=[]
    for c in (0,1):
        h=ir(y[SW0:SW0+SEG,c]); d=np.sum(np.concatenate([h[-24:],h[:48]])**2); w=np.sum(h[48:96000]**2)
        r.append(10*np.log10(d/(w+1e-30)+1e-30))
    return np.mean(r)
problems=[]; ref={}
for b,n,kind,desc in plan:
    n=int(n)
    if b not in ('A','C'): continue
    syx='run9/tests9%s.syx'%b
    stim='run7pr/stims/stim-%s.f32'%kind
    y=render(syx,stim,n); pk=np.abs(y).max(); rms=10*np.log10((y**2).mean()+1e-30)
    note=''
    if pk>0.89: problems.append('%s%d %s peak %.2f'%(b,n,kind,pk))
    if rms<-70: problems.append('%s%d %s silent (%.0f dB)'%(b,n,kind,rms))
    if kind=='std':
        t=tf(y); dr=directratio(y)
        if desc.startswith('Effect path') or 'effect only' in desc:
            note='direct/effect %+.0f dB'%dr
            inherent = int(n) in (101, 105, 109, 115, 119, 122)   # phaser/flanger/vibrato/ensemble: the effect itself starts within 1 ms
            if dr>-15 and not inherent: problems.append('%s%d direct not off (%.0f dB): %s'%(b,n,dr,desc))
        if 'flat, EQ on' in desc: ref[desc.split(':')[0]]=t
        note+=' tf '+' '.join('%+.0f'%v for v in t-t[2])
        ref[(b,n)]=t
    print('%s %3d %-9s pk %.2f rms %+5.0f  %s | %s'%(b,n,kind,pk,rms,note,desc[:60]),flush=True)
# EQ series against their flat references
print('\nEQ series, plug-in render minus flat reference (dB) at',list(cent))
for b,n,kind,desc in plan:
    if desc.startswith(('Reverb EQ: EQ','Stereo Delay EQ: EQ')):
        r=ref[desc.split(':')[0]]; d=ref[(b,int(n))]-r
        print('  %-50s'%desc[:50],' '.join('%+5.1f'%v for v in d))
        if np.abs(d).max()<1.0 and 'Mid +12' not in desc: problems.append('EQ test flat: '+desc)   # mid boost: the plug-in models it at a third, the test measures the unit
# phaser manual series must differ
ph=[]
for b,n,kind,desc in plan:
    if desc.startswith('Multi Phaser mode 4'):
        y=np.fromfile('run9/r/%03d.f32'%int(n),'<f4').reshape(-1,2) if False else render('run9/tests9C.syx','run7pr/stims/stim-stereo.f32',int(n))
        f,P=signal.welch(y[int(6.6*48000):int(8.6*48000),0],48000,nperseg=4096); ph.append(10*np.log10(P+1e-30))
ph=np.array(ph); dif=[np.abs(ph[i]-ph[0])[(f>200)&(f<8000)].mean() for i in range(len(ph))]
print('\nphaser mode-4 spectra, mean |difference| from Manual 0 / reso 0:',' '.join('%.1f'%x for x in dif))
if min(dif[1:])<0.5: problems.append('phaser manual series too similar')
print('\nPROBLEMS:' if problems else '\nALL RUN-9 TESTS VALID ON THE PLUG-IN', *problems, sep='\n  ')
