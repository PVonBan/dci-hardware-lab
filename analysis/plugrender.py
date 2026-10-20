# Renders the plug-in's prediction for every run-4 plan line it can (no MIDI-driven kinds).
# usage: plugrender.py <render4> <run4 dir with plan4.txt, tests4?.syx, stims/> <backup.syx> <outdir>
import sys, os, subprocess, shutil, numpy as np
R, D, BK, O = sys.argv[1:5]; os.makedirs(O, exist_ok=True)
for line in open(os.path.join(D, 'plan4.txt')):
    b, n, kind, desc = line.rstrip('\n').split('\t')
    if kind in ('cc', 'pb', 'vel', 'note', 'rotsw', 'pcgap'): continue
    syx = os.path.join(D, 'tests4%s.syx' % b)
    if kind == 'gsweep': pass
    tmp = os.path.join(O, '_t'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    subprocess.run([R, syx, os.path.join(D, 'stims', 'stim-%s.f32' % kind), tmp, n], check=True, capture_output=True)
    f = os.path.join(tmp, '%03d.f32' % int(n))
    if os.path.exists(f): os.replace(f, os.path.join(O, 'r4%s-%03d-%s.f32' % (b, int(n), kind)))
    else: print('no render for', line.strip())
shutil.rmtree(os.path.join(O, '_t'), ignore_errors=True)
print(len(os.listdir(O)), 'renders')
