# Generates run-4 test programs (two batches for slots 101-128), the restore file and the plan.
U='/mnt/user-data/uploads/Downloads/RSP-550/lab/'
d=open(U+'RSP550-backup-20261018-041833.syx','rb').read()
P={}; i=0
while i+106<=len(d):
    if d[i]==0xF0 and d[i+1]==0x41 and d[i+4]==0x12 and d[i+105]==0xF7 and d[i+5] in (3,4):
        n=d[i+6]+1 if d[i+5]==3 else d[i+6]+129; P[n]=bytearray(d[i+8:i+104]); i+=106
    else: i+=1
def w2(p,off,v): p[off]=v&0x7F; p[off+1]=(v>>7)&0x7F   # 2-byte fields: LSB first (7-bit)
def mk(base,name,**kw):
    p=bytearray(P[base]); p[0:16]=name.ljust(16)[:16].encode()
    for k,v in kw.items():
        off=int(k[1:],16)
        if isinstance(v,tuple): w2(p,off,v[1])
        else: p[off]=v
    return p
A=[]; B=[]
# --- batch A: converters + reverb mapping
# Simple Delay: echo 20H, direct 21H (not the manual's 1FH/20H; corrected after run 4)
A.append(('conv','dry reference',mk(67,'T DRY REF',x20=0,x21=100,x1A=0,x45=100)))
for code in (2,5,10,20,30,50,70,90):
    A.append(('std','Hall1 RT code %d'%code,mk(101,'T H1 RT%d'%code,x21=('w',code),x25=7,x26=4,x2C=0,x2B=100)))
for fc in (1,3,5,7):
    for lv in (0,2):
        A.append(('std','Hall1 RT3 damp f%d l%d'%(fc,lv),mk(101,'T H1 DF%d DL%d'%(fc,lv),x21=('w',30),x25=fc,x26=lv,x2C=0,x2B=100)))
for pre in (0,50,150,400):
    A.append(('std','Hall1 predelay %d'%pre,mk(101,'T H1 PRE%d'%pre,x21=('w',10),x23=('w',pre),x25=7,x26=4,x2C=0,x2B=100)))
for dif in (1,6,12):
    A.append(('std','Hall1 diffusion %d'%dif,mk(101,'T H1 DIF%d'%dif,x21=('w',20),x27=dif,x25=7,x26=4,x2C=0,x2B=100)))
for code in (10,30,60):
    A.append(('std','Hall2 RT code %d'%code,mk(104,'T H2 RT%d'%code,x21=('w',code),x25=7,x26=4,x2C=0,x2B=100)))
A.append(('std','Plate2 RT code 30',mk(108,'T P2 RT30',x21=('w',30),x25=7,x26=4,x2C=0,x2B=100)))
# --- batch B: modulation, pitch, rotary, feedback, gates, controllers
for rate,dep in ((10,100),(50,100),(100,100),(50,30)):
    B.append(('tone','Chorus rate %d depth %d'%(rate,dep),mk(50,'T CHO R%d D%d'%(rate,dep),x1E=rate,x1F=dep,x20=100,x21=0)))
for rate,dep,man in ((10,100,50),(50,100,50),(10,0,50)):
    B.append(('tone','Flanger rate %d depth %d manual %d'%(rate,dep,man),mk(54,'T FLG R%d D%d'%(rate,dep),x16=rate,x17=dep,x18=man,x1D=0,x1C=100,x1E=0)))
for rate,dep in ((20,100),(60,100),(20,30)):
    B.append(('tone','Delay mod rate %d depth %d'%(rate,dep),mk(58,'T DLY MOD R%d D%d'%(rate,dep),x24=rate,x25=dep,x1A=0,x1B=0,x13=7,x20=100,x21=0)))
for man in (0,33,66,100):
    B.append(('std','Phaser static manual %d'%man,mk(70,'T PHS MAN%d'%man,x1A=0,x19=1,x1B=man,x1C=50,x1F=0)))
for semis,fine in ((36,50),(12,50),(25,50)):
    B.append(('tone440','Pitch %+d semis'%(semis-24),mk(53,'T PS %+d'%(semis-24),x17=semis,x18=fine,x1C=100,x23=0,x1B=0,x44=0)))
B.append(('tone','Rotary slow',mk(87,'T ROT SLOW',x18=0,x22=0)))
B.append(('tone','Rotary fast',mk(87,'T ROT FAST',x18=1,x22=0)))
B.append(('rotsw','Rotary speed by CC1',mk(87,'T ROT CC1',x18=0,x22=0,x46=1,x47=6,x48=2,x49=0,x4A=2,x4B=0,x4C=100)))
for fb in (100,110,120):
    B.append(('fb','Delay FB %d'%fb,mk(67,'T DLY FB%d'%fb,x14=('w',100),x1A=fb,x20=100,x21=0)))
for atk,hold,rel in ((1,0,1),(40,0,1),(1,60,1),(1,0,60)):
    B.append(('gate','Hall1 gate atk %d hold %d rel %d'%(atk,hold,rel),mk(38,'T GATE A%dH%dR%d'%(atk,hold,rel),x1C=50,x1E=atk,x1D=hold,x1F=rel)))
B.append(('cc','Hall2 Rev Level by CC1, Total Level by aftertouch',mk(104,'T H2 CC',x46=3,x47=6,x48=1,x49=0,x4A=0,x4B=0,x4C=100,x4D=2,x4E=7,x4F=0,x50=0,x51=0,x52=100,x2C=0,x2B=100)))
# --- batch C: enhancer, pitch bend / velocity curves, plus the run-3 programs (121-128) and two unit-only tests
C=[]
for fq,mx in ((40,50),(40,100),(90,100),(10,100)):
    C.append(('enh','Enhancer freq %d mix %d'%(fq,mx),mk(68,'T ENH F%d M%d'%(fq,mx),x16=fq,x17=mx,x18=fq,x19=mx,x45=100)))
C.append(('pb','Hall2 Rev Level by pitch bend',mk(104,'T H2 PB',x46=1,x47=1,x48=1,x49=0,x4A=0,x4B=0,x4C=100,x2C=0,x2B=100)))
C.append(('vel','Hall2 Rev Level by velocity',mk(104,'T H2 VEL',x46=1,x47=4,x48=1,x49=0,x4A=0,x4B=0,x4C=100,x2C=0,x2B=100)))
r3=open('../run3/tests.syx','rb').read(); R3=[]
for i in range(0,len(r3),106): R3.append(bytearray(r3[i+8:i+104]))
assert len(R3)==8
r3kind=['std']*8
CS=list(range(101,107))+list(range(121,129))
C+= [(k,'run3 '+bytes(p[:16]).decode().strip(),p) for k,p in zip(r3kind,R3)]
C.append(('gsweep','run3 gate sweep Thr 70',None)); C.append(('gsweep','run3 gate sweep Thr 30',None))
C.append(('note','Vocoder 100 with held note 48',None)); C.append(('pcgap','Program change 1 -> 4 -> 1 during a tone',None))
CN=CS+[126,127,100,1]
assert len(A)==28 and len(B)==28, (len(A),len(B))
def msg(n,p):
    body=bytes([3,n-1,0])+bytes(p); sm=(128-sum(body)%128)%128
    return bytes([0xF0,0x41,0,0x38,0x12])+body+bytes([sm,0xF7])
AN=list(range(101,129)); BN=AN
for tag,L,N in (('A',A,AN),('B',B,BN),('C',C,CN)):
    open('tests4%s.syx'%tag,'wb').write(b''.join(msg(n,p) for n,(kind,nm,p) in zip(N,L) if p is not None))
open('restore-101-128.syx','wb').write(b''.join(msg(n,P[n]) for n in range(101,129)))
with open('plan4.txt','w') as f:
    for tag,L,N in (('A',A,AN),('B',B,BN),('C',C,CN)):
        for n,(kind,nm,p) in zip(N,L): f.write('%s\t%d\t%s\t%s\n'%(tag,n,kind,nm))
print(open('plan4.txt').read())
