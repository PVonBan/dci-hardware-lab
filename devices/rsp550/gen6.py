# Run 6: reverb decay data for Hall 3 / Room 1 / multi-effect reverbs, modulation waveforms (slots 101-128, restored
# after), plus factory programs by program change: steady-tone reverb response, stereo routing, vocoder/outlier
# probes and A/B listening material.
U='/mnt/user-data/uploads/Downloads/RSP-550/lab/'
d=open(U+'RSP550-backup-20261018-041833.syx','rb').read()
P={}; i=0
while i+106<=len(d):
    if d[i]==0xF0 and d[i+1]==0x41 and d[i+4]==0x12 and d[i+105]==0xF7 and d[i+5] in (3,4):
        n=d[i+6]+1 if d[i+5]==3 else d[i+6]+129; P[n]=bytearray(d[i+8:i+104]); i+=106
    else: i+=1
def mk(base,name,**kw):
    p=bytearray(P[base]); p[0:16]=name.ljust(16)[:16].encode()
    for k,v in kw.items():
        off=int(k[1:],16)
        if isinstance(v,tuple): p[off]=v[1]&0x7F; p[off+1]=(v[1]>>7)&0x7F
        else: p[off]=v
    return p
A=[]
for rt in (5,10,20,30,60):
    A.append(('std','Hall3 RT code %d, damping off'%rt,mk(102,'T H3 RT%d'%rt,x21=('w',rt),x25=7,x26=4,x2C=0,x2B=100)))
for rt in (3,6,10,20,40):
    A.append(('std','Room1 RT code %d, damping off'%rt,mk(105,'T R1 RT%d'%rt,x21=('w',rt),x25=7,x26=4,x2C=0,x2B=100)))
A.append(('std','Hall3 program 83, direct off',mk(83,'T 83 WET',x2C=0)))
A.append(('std','Room1 program 29, direct off',mk(29,'T 29 WET',x2C=0)))
A.append(('std','Room1 program 30, direct off',mk(30,'T 30 WET',x2C=0)))
for base,alg in ((77,7),(84,6),(76,9),(85,35)):
    for rt in (10,40):
        A.append(('std','alg %d (prog %d) reverb only, Rev Time code %d'%(alg,base,rt),mk(base,'T A%d RT%d'%(alg,rt),x37=('w',rt),x41=0,x40=100)))
A.append(('std','alg 38 (prog 91) reverb only, Rev Time code 10',mk(91,'T A38 RT10',x37=('w',10),x44=0,x40=100)))
for rt in (10,40):
    A.append(('std','alg 37 (prog 160) reverbs only, Rev 1/2 Time code %d'%rt,mk(160,'T A37 RT%d'%rt,x19=('w',rt),x37=('w',rt),x44=0)))
for ph in (18,27):
    A.append(('tone2k','Flanger LFO shape, rate 5, depth 100, phase %d'%ph,mk(54,'T FLG LFO P%d'%ph,x16=5,x17=100,x18=50,x1A=50,x1B=ph,x1D=0,x1C=100,x1E=0)))
for wave in (0,1):
    A.append(('tone2k','Delay mod LFO wave %d, rate 20, depth 100'%wave,mk(58,'T DM WAVE%d'%wave,x23=wave,x24=20,x25=100,x1A=0,x1B=0,x13=7,x20=100,x21=0)))
assert len(A)==28, len(A)
# --- batch C (second Bulk Load, slots 101-111): isolate one Quad PS voice, the Vocoder Mic Mix curve, the chorus mix law
C=[]
q=dict(x1D=0,x24=0,x2B=0,x44=0,x34=0,x2E=24,x2F=50,x30=('w',0),x32=100,x33=50,x2D=0)   # voice 4 only, unison, no direct/FB
C.append(('std','Quad PS one voice, unison, mode 0',mk(98,'T QPS UNI M0',**q)))
C.append(('std','Quad PS one voice, unison, mode 1',mk(98,'T QPS UNI M1',**{**q,'x2D':1})))
C.append(('std','Quad PS one voice, +5 semitones, mode 0',mk(98,'T QPS +5 M0',**{**q,'x2E':29})))
C.append(('tone440','Quad PS one voice, unison, mode 0 (timing)',mk(98,'T QPS UNI T440',**q)))
C.append(('std','Quad PS one voice, unison, mix 50',mk(98,'T QPS UNI MIX50',**{**q,'x32':50})))
for mic in (0,33,66,100):   # Total Level 25 (-12 dB, linear) keeps Mic Mix 100 below clipping
    C.append(('stereo','Vocoder Mic Mix %d, Total Level 25'%mic,mk(100,'T VOC MIC%d TL25'%mic,x15=mic,x45=25)))
for wet,dr in ((0,100),(100,0),(0,50),(50,0)):
    C.append(('std','Stereo Chorus effect %d direct %d'%(wet,dr),mk(50,'T CHO E%d D%d'%(wet,dr),x20=wet,x21=dr)))
def msg(n,p):
    body=bytes([3,n-1,0])+bytes(p); sm=(128-sum(body)%128)%128
    return bytes([0xF0,0x41,0,0x38,0x12])+body+bytes([sm,0xF7])
open('tests6A.syx','wb').write(b''.join(msg(101+k,p) for k,(kind,nm,p) in enumerate(A)))
open('empty.syx','wb').write(b'')
open('tests6C.syx','wb').write(b''.join(msg(101+k,p) for k,(kind,nm,p) in enumerate(C)))
pc=[('tsteps',1,'Large Hall 1 steady tones'),('tsteps',4,'Medium Hall 2 steady tones'),('tsteps',8,'Warm Plate steady tones'),('tsteps',5,'Large Room steady tones'),
    ('stereo',67,'Doubling Echo routing'),('stereo',54,'Light Flanger routing'),('stereo',100,'Vocoder routing, no note'),('stereonote',100,'Vocoder routing, note 48 held'),
    ('stereo',78,'Rhodes Vibrato routing'),('stereo',94,'MIDI Note->Chord routing, no note'),('stereonote',94,'MIDI Note->Chord, note 48 held'),('stereo',45,'SDD-320 Mode 3 routing'),
    ('tone2k',50,'Wide Chorus voices (2 kHz)'),
    ('stereo',95,'Quad PS Skip! (two unison voices + direct)'),('stereo',98,'Quad PS 1 Note Arpeggio (one unison voice)'),('stereo',99,'Quad PS BarberPole (no unison voice)'),('tone440',98,'Quad PS unison voice timing'),
    ('stereo',71,'Round Phaser routing'),('stereo',72,'Jungle Phaser routing'),('stereo',73,'Accent Phaser routing'),('stereo',93,'Hitting Saw routing'),('stereo',97,'12 String Guitar routing'),('stereo',36,'Jazz Club routing'),
    ('file',1,'A/B Large Hall 1'),('file',8,'A/B Warm Plate'),('file',50,'A/B Wide Chorus'),('file',54,'A/B Light Flanger'),('file',58,'A/B Shimmer'),('file',87,'A/B Soft Rotary')]
with open('plan6.txt','w') as f:
    for k,(kind,nm,p) in enumerate(A): f.write('A\t%d\t%s\t%s\n'%(101+k,kind,nm))
    for kind,n,nm in pc: f.write('B\t%d\t%s\t%s\n'%(n,kind,nm))
    for k,(kind,nm,p) in enumerate(C): f.write('C\t%d\t%s\t%s\n'%(101+k,kind,nm))
print(open('plan6.txt').read())
