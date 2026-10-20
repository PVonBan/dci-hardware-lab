exec(open('run6pr/an6.py').read().split("if __name__")[0])
def modshape(b,n,plug):
    x,y,mk=get(b,n,'tone2k',plug); nm,s0,L=mk[0]; f0=2000.0
    sos=signal.butter(4,(f0/1.3,f0*1.3),'bandpass',fs=FS,output='sos'); out={}
    tr=[]
    for c in (0,1):
        z=signal.sosfiltfilt(sos,y[s0+9600:s0+L-4800,c]); d,e=inst_delay(z,f0); d=d[::48]; d=d-np.mean(d); tr.append(d)
    fs2=FS/48; F=np.fft.rfftfreq(len(tr[0])*4,1/fs2)
    S=[np.fft.rfft(t*np.hanning(len(t)),len(t)*4) for t in tr]
    m=(F>0.05)&(F<20); k=np.argmax(np.abs(S[0])*m); f1=F[k]
    k3=np.argmin(np.abs(F-3*f1)); k2=np.argmin(np.abs(F-2*f1))
    h3=20*np.log10(np.abs(S[0][k3-2:k3+3]).max()/np.abs(S[0][k]))
    h2=20*np.log10(np.abs(S[0][k2-2:k2+3]).max()/np.abs(S[0][k]))
    ph=np.degrees(np.angle(S[1][k]/S[0][k]))
    return dict(rate=round(float(f1),3),pp=[round(float(np.percentile(t,99)-np.percentile(t,1)),3) for t in tr],h2=round(float(h2),1),h3=round(float(h3),1),lr_phase=round(float(ph),0))
for b,n in (('A',125),('A',126),('A',127),('A',128)):
    print(b,n,'hw',modshape(b,n,False)); print('      pl',modshape(b,n,True))
