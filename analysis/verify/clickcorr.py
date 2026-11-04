#!/usr/bin/env python3
"""Is the unit time-variant, or does each click just land at a different phase of its free-running clock?
The run-10 click train (4 Hz) through a reverb: each click's response (first 80 ms) against the first click's, correlation
after integer alignment (the battery's measure) and after sub-sample alignment (x16 upsampling, best lag). If the
sub-sample value is ~1, there is no time variance to model. Also the unit's loop latency jitter from the run-10 direct
impulses (p-tags, four impulses + L/R): arrival of the direct impulse at sub-sample resolution.
Usage: clickcorr.py <hw out dir> [tags...]"""
import sys, os, numpy as np, soundfile as sf
from scipy import signal
FS = 48000; UP = 16
def responses(y, nclicks=8, period=0.25, win=0.08):
    m = np.sum(np.abs(y), 1); first = int(np.argmax(m > 0.2 * m.max()))
    out = []
    for k in range(nclicks):
        i = first + int(k * period * FS) - 48
        seg = y[i:i + int(win * FS)].mean(1)
        if len(seg) == int(win * FS): out.append(seg)
    return out
def corr(a, b):
    return float(np.dot(a, b) / np.sqrt(np.dot(a, a) * np.dot(b, b) + 1e-30))
def best_corr(a, b):
    au, bu = signal.resample_poly(a, UP, 1), signal.resample_poly(b, UP, 1)
    c = signal.correlate(bu, au, 'full', method='fft'); mid = len(au) - 1
    k = int(np.argmax(c[mid - 3 * UP:mid + 3 * UP + 1])) - 3 * UP
    bs = np.roll(bu, -k); return corr(au, bs), k / UP
H = sys.argv[1]; tags = sys.argv[2:] or ['p001', 'p008', 'p002', 'p005']
for tag in tags:
    f = os.path.join(H, 'renders', tag + '_clicks.wav')
    if not os.path.exists(f): continue
    r = responses(sf.read(f)[0])
    ints = [corr(r[0], x) for x in r[1:]]; subs = [best_corr(r[0], x) for x in r[1:]]
    print('%s clicks: integer-aligned corr %s | sub-sample-aligned %s (shifts %s samples)' % (tag, ' '.join('%.2f' % v for v in ints), ' '.join('%.2f' % v for v, _ in subs), ' '.join('%+.2f' % s for _, s in subs)))
print('direct-impulse arrival (sub-sample, re the first), four repeats then L-only and R-only:')
for tag in tags:
    arr = []
    for k in ('imp_r1', 'imp_r2', 'imp_r3', 'imp_r4', 'impL', 'impR'):
        f = os.path.join(H, 'renders', '%s_%s.wav' % (tag, k))
        if not os.path.exists(f): continue
        y = sf.read(f)[0][:2000]; c = 0 if k != 'impR' else 1
        u = signal.resample_poly(y[:, c], UP, 1); arr.append(int(np.argmax(np.abs(u))) / UP)
    if arr: print('  %s: %s ms' % (tag, ' '.join('%+.3f' % ((a - arr[0]) / FS * 1000) for a in arr)))
