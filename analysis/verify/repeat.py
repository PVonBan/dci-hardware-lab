#!/usr/bin/env python3
"""Unit repeatability across sessions: the same program and stimulus captured in two sessions (run 9 on inputs 5/6,
run 10b on 7/8) and within one session (B vs Z copies in run 10b). Reports, per capture pair and overall: level
difference per channel, 1/3-octave tone difference (rms over 100 Hz-10 kHz after removing the level), and left/right
balance. The spread of these is the floor below which no fit is meaningful. Usage: repeat.py <capture dir>"""
import sys, os, numpy as np, soundfile as sf
from scipy import signal
C = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture'
FS = 48000
CAL = {'run9': ((1179 + 32, 1179), np.array([10 ** (0.9 / 20), 10 ** (-4.6 / 20)])),   # inputs 5/6: left 32 samples late
       'run10': ((1133, 1133), np.array([10 ** (-4.1 / 20), 10 ** (-4.6 / 20)])   # inputs 7/8, corrected 2026-11-03 (see lab10.py)),
       'run10b': ((1133, 1133), np.array([10 ** (-4.1 / 20), 10 ** (-4.6 / 20)])   # inputs 7/8, corrected 2026-11-03 (see lab10.py))}
cent = 1000 * 2 ** (np.arange(-10, 11) / 3)   # 100 Hz - 10 kHz
def load(run, f):
    y, _ = sf.read(os.path.join(C, run, f), always_2d=True); (ll, lr), g = CAL[run]
    n = len(y) - max(ll, lr); return np.stack([y[ll:ll + n, 0], y[lr:lr + n, 1]], 1) / g
def tone(y):
    f, P = signal.welch(y, FS, nperseg=8192, axis=0)
    return np.array([[10 * np.log10(P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6)), ch].sum() + 1e-30) for c in cent] for ch in (0, 1)])
def level(y): return 10 * np.log10(np.mean(y ** 2, 0) + 1e-30)
def compare(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    dl = level(b) - level(a); ta, tb = tone(a), tone(b)
    dt = (tb - ta) - dl[:, None]; return dl, np.sqrt(np.mean(dt ** 2, 1)), dt
pairs = []
idx = {r: [l.split('\t')[0] for l in open(os.path.join(C, r, 'run4-index.tsv')).read().split('\n')[1:] if l] for r in CAL}
for f in sorted(set(idx['run9']) & set(idx['run10b'])):
    if '-std' in f or '-file' in f: pairs.append(('run9', f, 'run10b', f))
for f in idx['run10b']:
    if f.startswith('r4Z-'):
        b = f.replace('r4Z-', 'r4B-')
        if b in idx['run10b']: pairs.append(('run10b', b, 'run10b', f))
for f in idx['run10']:
    if f.startswith('r4Z-') and f in idx['run10b']: pairs.append(('run10', f, 'run10b', f))
rows = []
print('%-32s %-8s %-8s   level L/R (dB)   tone rms L/R (dB)' % ('capture', 'from', 'to'))
for ra, fa, rb, fb in pairs:
    try: dl, dt, _ = compare(load(ra, fa), load(rb, fb))
    except FileNotFoundError: continue
    rows.append((ra != rb, dl, dt))
    print('%-32s %-8s %-8s   %+5.2f %+5.2f      %4.2f %4.2f' % (fa.replace('.wav', ''), ra, rb, dl[0], dl[1], dt[0], dt[1]))
for cross in (False, True):
    sel = [r for r in rows if r[0] == cross]
    if not sel: continue
    L = np.array([r[1] for r in sel]); T = np.array([r[2] for r in sel])
    print('%s (%d pairs): level median %+.2f / %+.2f dB, spread (std) %.2f / %.2f; tone rms median %.2f / %.2f dB'
          % ('ACROSS sessions' if cross else 'WITHIN session', len(sel), *np.median(L, 0), *np.std(L, 0), *np.median(T, 0)))
