import json, sys, numpy as np
sys.path.insert(0,'run9'); import lab10
BK='/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx'
runs={'run6pr':('run6pr/plan4.txt',{'A':'run6pr/tests4A.syx','C':'run6pr/tests4C.syx'}),
      'run7pr':('run7pr/plan4.txt',dict({'C':'run7pr/tests4C.syx'},**{'R%d'%k:'run7/round%d-tests.syx'%k for k in range(1,5)})),
      'run8pr':('run8pr/plan4.txt',{'C':'run8/tests8C.syx'}),
      'run9pr':('run9pr/plan9.txt',{'A':'run9pr/tests9A.syx','C':'run9pr/tests9C.syx'})}
base=lab10._progs(BK)
def alg(run,b,n):
    syx=runs[run][1].get(b)
    M=dict(base); 
    if syx: M.update(lab10._progs(syx))
    p=M.get((3,n-1)) if n<=128 else M.get((4,n-129))
    return p[8+0x11] if p else None
def table(f):
    S=json.load(open(f)); per={}
    for run,d in S.items():
        for k,(lv,tn) in d.items():
            b,n,kind=k.split('-'); a=alg(run,b,int(n))
            per.setdefault(a,[]).append((lv,tn,run+' '+k))
    return per
A=table(sys.argv[1]); B=table(sys.argv[2])
for a in sorted(set(A)|set(B), key=lambda x: x or 0):
    la=[x[0] for x in A.get(a,[])]; lb=[x[0] for x in B.get(a,[])]
    print('alg %2s n=%2d  level median %+5.1f -> %+5.1f   tone %4.1f -> %4.1f'%(a,len(lb),np.median(la),np.median(lb),np.median([x[1] for x in A[a]]),np.median([x[1] for x in B[a]])))
