# Run 5: the follow-ups from run 4. Slots 101-118 (restored after from the same restore file as run 4).
#  - Simple Delay (alg 3) with the byte map the unit really uses: echo 20H, direct 21H. Dry reference for the converter
#    battery, then feedback 40/80/100/110/120 with the echo only.
#  - Stereo Delay (alg 5) feedback law: FB 30/60/100, damping and FB filter off, mix only.
#  - Stereo Flanger (alg 2) static delay against Manual: depth 0, resonance 0, Dir Mix on, Manual 0/25/50/75/100.
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
A.append(('conv','dry reference (simple delay, echo 0, direct 100)',mk(67,'T DRY REF2',x1A=0,x20=0,x21=100,x45=100)))
for fb in (40,80,100,110,120):
    A.append(('fb','Simple Delay FB %d, echo only'%fb,mk(67,'T SD FB%d'%fb,x14=('w',100),x1A=fb,x20=100,x21=0,x45=100)))
for fb in (30,60,100):
    A.append(('fb','Stereo Delay FB %d, no damping or FB filter'%fb,mk(58,'T STD FB%d'%fb,x18=('w',100),x1A=fb,x1B=0,x1C=7,x1D=4,x1E=0,x13=5,x20=100,x21=0,x45=100)))
for man in (0,25,50,75,100):
    A.append(('std','Flanger static, Manual %d'%man,mk(54,'T FLG MAN%d'%man,x17=0,x18=man,x1A=50,x1D=0,x1C=100,x1E=1,x45=100)))
for kind,nm,p in A: assert len(p)==96
def msg(n,p):
    body=bytes([3,n-1,0])+bytes(p); sm=(128-sum(body)%128)%128
    return bytes([0xF0,0x41,0,0x38,0x12])+body+bytes([sm,0xF7])
open('tests5A.syx','wb').write(b''.join(msg(101+k,p) for k,(kind,nm,p) in enumerate(A)))
open('empty.syx','wb').write(b'')
with open('plan5.txt','w') as f:
    for k,(kind,nm,p) in enumerate(A): f.write('A\t%d\t%s\t%s\n'%(101+k,kind,nm))
    f.write('A\t1\tpcgap\tProgram change 1 -> 4 -> 1 during a tone (repeat)\n')
print(open('plan5.txt').read())
