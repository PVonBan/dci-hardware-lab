import sys,os,json,numpy as np
sys.argv=['x']; exec(open('an4/an4.py').read().split('def main')[0])
R6='/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run6'; ST='run6pr/stims'
CAL=Cal(1179,(10**(0.9/20),10**(-4.6/20)))
def get(b,n,kind,plug=False):
    x=load('%s/stim-%s.wav'%(ST,kind)); mk=markers(ST,kind)
    if plug: y=load('run6pr/plug/r4%s-%03d-%s.f32'%(b,n,kind)); y=y[:len(x)]
    else: y=CAL.apply(load('%s/r4%s-%03d-%s.wav'%(R6,b,n,kind)),len(x))
    return x,y,mk
def stereo(b,n,plug=False,kind='stereo'):
    x,y,mk=get(b,n,kind,plug); r={}
    for nm,s0,L in mk:
        if not nm.startswith('noise'): continue
        a=s0+4800; e=s0+L
        ref=rmsdb(x[a:e,0] if 'R' not in nm.split()[0] or 'Both' in nm else x[a:e,1])
        r[nm.split()[0]]=[round(rmsdb(y[a:e,c])-ref,2) for c in (0,1)]
    return r
if __name__=='__main__':
    tests=[l.rstrip('\n').split('\t') for l in open('run6pr/plan4.txt') if '\tstereo' in l]
    for b,n,kind,desc in tests:
        if kind!='stereo': continue
        n=int(n); h=stereo(b,n); p=stereo(b,n,True)
        print('%s%3d %-44s'%(b,n,desc[:44]),'  '.join('%s hw %+5.1f/%+5.1f pl %+5.1f/%+5.1f'%(k[5:],h[k][0],h[k][1],p[k][0],p[k][1]) for k in h))
