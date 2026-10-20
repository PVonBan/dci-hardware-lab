import sys,os,subprocess,numpy as np
sys.path.insert(0,'run6pr'); exec(open('run6pr/an6.py').read().split("if __name__")[0])
BK='/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx'
def rend(syx,n,kind,env):
    d='fit158/p_'+'_'.join(env.values()); os.makedirs(d,exist_ok=True)
    subprocess.run(['fit158/ptune',syx,'run6pr/stims/stim-%s.f32'%kind,d,str(n)],env={**os.environ,**env},check=True,capture_output=True)
    os.replace('%s/%03d.f32'%(d,n),'run6pr/plug/r4X-%03d-%s.f32'%(n,kind))
def st(n,env,b='B'):
    rend(BK,n,'stereo',env); return stereo('X',n,True)
for g in ('1','0.84','0.7'):
    env={'T_P2':g,'T_P4':g}
    out=[]
    for n in (97,98,95,99):
        h=stereo('B',n); p=st(n,env)
        out.append('%d: '%n+' '.join('%s %+.1f/%+.1f'%(k[5:],p[k][0]-h[k][0],p[k][1]-h[k][1]) for k in h))
    print('g',g,' | '.join(out))
