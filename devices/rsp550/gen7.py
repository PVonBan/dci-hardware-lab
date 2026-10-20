# Run 7: reverb decay data for Hall 3 / Room 1 / multi-effect reverbs, modulation waveforms (slots 101-128, restored
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

C=[]
# Multi Phaser: what makes Round/Jungle Phaser ~5-6 dB quieter on the unit? one setting at a time from Round Phaser (71)
C.append(('stereo','Round Phaser, Tremolo 0',mk(71,'T PH71 TREM0',x1F=0)))
C.append(('stereo','Round Phaser, Mode 1',mk(71,'T PH71 MODE1',x14=1)))
C.append(('stereo','Round Phaser, Step Rate 0',mk(71,'T PH71 STEP0',x1D=0)))
C.append(('stereo','Round Phaser, Resonance 50',mk(71,'T PH71 RESO50',x1C=50)))
C.append(('stereo','Light Phaser (70), Tremolo 59',mk(70,'T PH70 TREM59',x1F=59)))
# Light Flanger level: direct off, no resonance, direct only
C.append(('stereo','Light Flanger, direct off',mk(54,'T FL54 DIR0',x1E=0)))
C.append(('stereo','Light Flanger, resonance 50',mk(54,'T FL54 RESO50',x1A=50)))
C.append(('stereo','Light Flanger, effect 0 (direct only)',mk(54,'T FL54 MIX0',x1C=0)))
# Flanger LFO by click train: direct off, no resonance, depth 100, manual 50
for rate,ph in ((5,18),(5,27),(20,18)):
    C.append(('clicktrain','Flanger LFO rate %d phase %d'%(rate,ph),mk(54,'T FLG R%d P%d'%(rate,ph),x16=rate,x17=100,x18=50,x1A=50,x1B=ph,x1D=0,x1C=100,x1E=0)))
# Vocoder Mic Mix between 66 and 100 (Total Level 25, as run 6)
for mic in (75,85,92):
    C.append(('stereo','Vocoder Mic Mix %d, Total Level 25'%mic,mk(100,'T VOC MIC%d TL25'%mic,x15=mic,x45=25)))
# Ambience (Jazz Club 36): are its effect and direct levels absolute too?
for wet,dr in ((100,0),(50,0),(0,100)):
    C.append(('stereo','Ambience effect %d direct %d'%(wet,dr),mk(36,'T AMB E%d D%d'%(wet,dr),x22=wet,x23=dr)))
C.append(('note440','Vocoder, note 48 held, Total Level 50 (sawtooth carrier?)',mk(100,'T VOC NOTE TL50',x45=50)))
C.append(('tone440','Vocoder, no note, Total Level 50',mk(100,'T VOC TONE TL50',x45=50)))
assert len(C)<=28, len(C)
def msg(n,p):
    body=bytes([3,n-1,0])+bytes(p); sm=(128-sum(body)%128)%128
    return bytes([0xF0,0x41,0,0x38,0x12])+body+bytes([sm,0xF7])
open('tests7C.syx','wb').write(b''.join(msg(101+k,p) for k,(kind,nm,p) in enumerate(C)))
pc=[('note440',94,'Note->Chord, note 48 held'),('tone440',94,'Note->Chord, no note'),
    ('stereolo',36,'Jazz Club at -30'),('stereohi',36,'Jazz Club at -15'),('stereolo',37,'Live Sound at -30'),('stereohi',37,'Live Sound at -15'),
    ('stereo',35,'Ambience program 35'),
    ('stereolo',100,'Vocoder at -30'),('stereohi',100,'Vocoder at -15'),
    ('stereolo',73,'Accent Phaser at -30'),('stereohi',73,'Accent Phaser at -15'),
    ('stereolo',54,'Light Flanger at -30'),('stereohi',54,'Light Flanger at -15'),('clicktrain',54,'Light Flanger click train'),
    ('stereolo',71,'Round Phaser at -30'),
    ('std',107,'Small Room * (run-1 outlier, repeat)'),('std',123,'Church * (repeat)'),('std',109,'Bright Plate * (repeat)')]
with open('plan7.txt','w') as f:
    for kind,n,nm in pc: f.write('B\t%d\t%s\t%s\n'%(n,kind,nm))
    for k,(kind,nm,p) in enumerate(C): f.write('C\t%d\t%s\t%s\n'%(101+k,kind,nm))
print(open('plan7.txt').read())
