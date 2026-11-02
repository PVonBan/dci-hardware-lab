# Run 9 program-EQ series: EQ curve = (test / flat reference) per 1/3 octave, per channel, unit vs plug-in 1.6.6
import numpy as np, soundfile as sf
fs=48000; SW0, SWN = 396002, 120000; SEG = SWN + 144000; NF = 1 << 19
U='/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run9/'
LAT=1179; G=np.array([10**(0.9/20),10**(-4.6/20)])
x,_=sf.read('run9pr/stims/stim-std.wav'); xs=x[SW0:SW0+SEG,0]
X=np.fft.rfft(xs,NF); f=np.fft.rfftfreq(NF,1/fs); Xi=np.where((f>20)&(f<20000),1/np.where(np.abs(X)>1e-9,X,1),0)
cent=1000*2**(np.arange(-14,13)/3)
def bands(y):
    H=np.fft.rfft(y,NF)*Xi; m=np.abs(H)**2
    return np.array([10*np.log10(m[(f>=c/2**(1/6))&(f<c*2**(1/6))].mean()+1e-30) for c in cent])
def resp(n,plug):
    if plug: y=np.fromfile('run9pr/plug/r4C-%03d-std.f32'%n,'<f4').reshape(-1,2).astype(float)
    else: y=sf.read(U+'r4C-%03d-std.wav'%n)[0][LAT:]/G
    return np.array([bands(y[SW0:SW0+SEG,c]) for c in (0,1)])
def show(ref, tests):
    hr,pr=resp(ref,False),resp(ref,True)
    sel=[i for i,c in enumerate(cent) if c in cent[::2]]
    print('band       '+' '.join('%6.0f'%cent[i] for i in sel))
    for n,name in tests:
        h=(resp(n,False)-hr).mean(0); p=(resp(n,True)-pr).mean(0)
        print('%-11s'%(name+' U')+' '.join('%+6.1f'%h[i] for i in sel))
        print('%-11s'%('   ours')+' '.join('%+6.1f'%p[i] for i in sel))
        print('%-11s'%('   diff')+' '.join('%+6.1f'%(p[i]-h[i]) for i in sel))
print('== reverb (wet-only Baroque Hall), vs C111 flat')
show(111,[(103,'Hi-12'),(104,'Hi-6'),(105,'Hi+6'),(106,'Hi+12'),(107,'Lo-12'),(108,'Lo+12'),(109,'Mid-12'),(110,'Mid+12')])
print('== stereo delay, vs C116 flat')
show(116,[(112,'Hi-12'),(113,'Hi+12'),(114,'Lo-12'),(115,'Lo+12')])
