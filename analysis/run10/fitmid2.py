exec(open('run10r1/fitmid.py').read().split("for mode in")[0])
def peakB(fq,f0,g,q):
    G=10**(abs(g)/20); s=1j*fq/f0
    H=(s**2+s*G/q+1)/(s**2+s/q+1)
    if g<0: H=1/H
    return 20*np.log10(np.abs(H))
def err(p):
    return sum(np.sum((peakB(cent[m],fc*p[1],g,p[0])-d[m])**2) for fc,g,d in data)
r=minimize(err,[2.0,1.0],method='Nelder-Mead')
print('model B (pole-fixed boost, mirrored cut): Q %.3f fscale %.3f rms %.2f dB'%(r.x[0],r.x[1],np.sqrt(r.fun/(len(data)*m.sum()))))
for fc,g,d in data: print('   %+3d@%4d rms %.2f'%(g,fc,np.sqrt(np.mean((peakB(cent[m],fc*r.x[1],g,r.x[0])-d[m])**2))))
