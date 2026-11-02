import sys,os,json,numpy as np
sys.argv=['x']; exec(open('an4/an4.py').read().split('def main')[0])
R6='/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run9'; ST="run9pr/stims"
CAL=Cal(1179,(10**(0.9/20),10**(-4.6/20)))
def get(b,n,kind,plug=False):
    x=load('%s/stim-%s.wav'%(ST,kind)); mk=markers(ST,kind)
    if plug: y=load('run9pr/plug/r4%s-%03d-%s.f32'%(b,n,kind)); y=y[:len(x)]
    else: y=CAL.apply(load('%s/r4%s-%03d-%s.wav'%(R6,b,n,kind)),len(x))
    return x,y,mk
