# Summary of hardware vs plug-in for the run-4 tests: one line per test with the key numbers side by side.
import json, sys, numpy as np
H=json.load(open(sys.argv[1])); P=json.load(open(sys.argv[2]))
def r(d,k): return d.get(k,{}).get('result',{})
for k in sorted(H):
    if k[0]=='_': continue
    h,p=r(H,k),r(P,k); kind=k.split('-')[2]; d=H[k]['desc'][:30].ljust(30)
    if not p or 'error' in p: continue
    if kind=='std':
        f=lambda x: 'T30 1k %5.2f 4k %5.2f 8k %5.2f lvl %5.1f'%(x['t30']['1k'],x['t30']['4k'],x['t30']['8k'],x['level_db'])
        print(k.ljust(12),d,'HW',f(h),'| PL',f(p))
    elif kind=='tone':
        f=lambda x: 'lvl %5.1f am %5.1f'%(x['L']['level_db'],x['L']['am_pp_db'])
        print(k.ljust(12),d,'HW',f(h),'| PL',f(p))
    elif kind=='tone440':
        f=lambda x: 'semis %6.3f am %4.1f dB @%5.2f Hz'%(x['ratio_semitones'],x['am_pp_db'],x['am_rate_hz'])
        print(k.ljust(12),d,'HW',f(h),'| PL',f(p))
    elif kind=='enh':
        f=lambda x: 'gains %s dist %s'%(x['multitone'][2]['gain_db'],x['multitone'][2]['distortion_db'])
        print(k.ljust(12),d); print('   HW',f(h)); print('   PL',f(p))
    elif kind=='gsweep':
        f=lambda x: 'opens at %s'%next((l for l,g,t in x if t>-60),None)
        print(k.ljust(12),d,'HW',f(h),'| PL',f(p))
