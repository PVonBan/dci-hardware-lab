#!/usr/bin/env python3
"""Measure sensitivity: inject one known change at a time into the plug-in (tuning build, environment hooks) and run the
run-10 measures on the result against the unchanged render. A measure is useful only if it flags the changes it is meant
to catch and nothing else. Usage: sens.py <SSP550Test tuning build> <run10 dir> <bank.syx> <out dir>"""
import sys, os, json, subprocess, shutil, numpy as np, soundfile as sf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); import lab10
T, R10, BANK, OUT = sys.argv[1:5]; RL = os.environ.get('REVERBLAB', '/home/claude/dci-effects/tools/reverblab')
SLOTS = {1: 'p001', 109: 'w001'}   # Large Hall 1 factory (with direct) and wet-only
KINDS = ('labimp', 'sweepm12', 'labmisc')
CASES = {'baseline': {},
         'tail -3 dB above 3.5 kHz': {'T_SHDB': '-9'},                      # shelf -6 -> -9
         'reflections +10 ms': {'T_ERF': '10'},                             # 0 -> 10 ms
         'late onset +20 ms': {'T_LATE': '5'},                              # -15 -> +5
         'decay x1.2': {'RVFIX_24': '1.214,1.021,1.053,0'},                 # mid scale 1.012 -> 1.214
         'modulation on (0.35)': {'T_MOD': '0.35'},
         'wet -2 dB': {'T_WET': '-1.0'}}                                    # 1.0 -> -1.0 dB
S = lab10.segs(R10)
def render(name, env):
    d = os.path.join(OUT, name.replace(' ', '_').replace('(', '').replace(')', '')); 
    if os.path.exists(os.path.join(d, 'results.json')): return d
    lab10.mark(d, R10); tmp = os.path.join(d, 'tmp'); os.makedirs(tmp, exist_ok=True)
    for k in KINDS:
        x, r = sf.read(os.path.join(R10, 'stim', k + '.wav'), always_2d=True, dtype='float32'); f32 = os.path.join(tmp, k + '.f32'); x.tofile(f32)
        subprocess.run([T, '--render', os.path.join(tmp, k), f32, BANK] + [str(s) for s in SLOTS], check=True, stdout=subprocess.DEVNULL,
                       env=dict(os.environ, T_ALG='24', **env))
        for s, tag in SLOTS.items():
            y = np.fromfile(os.path.join(tmp, k, '%03d.f32' % s), np.float32).reshape(-1, 2)
            lab10.cut(y, S[k]['segments'], r, tag, d)
            if k == 'labimp': lab10.cut(y, [q for q in S[k]['segments'] if q[0] == 'imp_r1'], r, tag, d, {'imp_r1': 'imp'})
    shutil.rmtree(tmp); lab10.measure(d, RL); return d
base = render('baseline', {})
report = {}
for name, env in CASES.items():
    if name == 'baseline': continue
    d = render(name, env)
    res = lab10.compare(base, d, os.path.join(d, 'cmp.json'))
    flagged = {tag: [k for k, v in res[tag].items() if not v['ok']] for tag in SLOTS.values() if tag in res}
    report[name] = flagged
print('\n=== which measures flag each injected change (p001 = with direct, w001 = wet only)')
for name, fl in report.items():
    for tag, ks in fl.items(): print('%-26s %s: %s' % (name, tag, ', '.join(ks) if ks else 'NOTHING'))
json.dump(report, open(os.path.join(OUT, 'sensitivity.json'), 'w'), indent=1)
