#!/usr/bin/env python3
"""Reflection taps and recirculating delays straight from the unit's wet-only impulse responses (run 10, clean take),
beside ours. The unit's reverbs are time-invariant, so the impulse response is a complete description:
  taps     local maxima of |h| in the first 120 ms at 0.1 ms resolution, above the local late level + 12 dB: time, level
           (dB re the strongest tap), side (L / R / both) - the pattern to copy, not to approximate
  loops    real cepstrum of the late part (80-600 ms, both channels): peaks are the recirculating delay lengths
Usage: ertaps.py <hw out dir> <ours out dir> [tags...]"""
import sys, os, numpy as np, soundfile as sf
from scipy import signal
FS = 48000
def taps(y, ms=120, mindb=12):
    h = y[:int(ms * FS / 1000)]; a = np.abs(h)
    out = []
    for c in (0, 1):
        x = a[:, c]; env = signal.convolve(x, np.ones(48) / 48, 'same')   # 1 ms local level
        late = np.median(x[int(0.06 * FS):]) + 1e-9
        pk, _ = signal.find_peaks(x, height=late * 10 ** (mindb / 20), distance=5)
        for p in pk:
            if x[p] >= np.max(x[max(0, p - 24):p + 24]): out.append((p / FS * 1000, 20 * np.log10(x[p] + 1e-12), c))
    out.sort(); return out
def merge(t):
    m = []
    for ms, db, c in t:
        if m and abs(m[-1][0] - ms) < 0.15: m[-1] = (m[-1][0], max(m[-1][1], db), 'LR')
        else: m.append((ms, db, 'L' if c == 0 else 'R'))
    return m
def loops(y, a=0.08, b=0.6):
    z = y[int(a * FS):int(b * FS)].sum(1); z = z * np.hanning(len(z))
    S = np.log(np.abs(np.fft.rfft(z, 1 << 16)) + 1e-9); cep = np.fft.irfft(S)
    q = np.arange(len(cep)) / FS * 1000; m = (q > 5) & (q < 120)
    pk, pr = signal.find_peaks(cep[m], prominence=np.std(cep[m]) * 2.5)
    return sorted([(q[m][p], cep[m][p]) for p in pk], key=lambda v: -v[1])[:10]
H, O = sys.argv[1], sys.argv[2]; tags = sys.argv[3:] or ['w001', 'w008', 'w002', 'w004', 'w005', 'w007', 'w009']
for tag in tags:
    for lab, d in (('unit', H), ('ours', O)):
        y = sf.read(os.path.join(d, 'renders', tag + '_imp_r1.wav'))[0]
        t = merge(taps(y)); ref = max(db for _, db, _ in t) if t else 0
        print('%s %-4s taps (ms, dB re strongest, side): ' % (tag, lab) + '  '.join('%.1f %+.0f %s' % (ms, db - ref, s) for ms, db, s in t[:18]) + ('  ...(%d)' % len(t) if len(t) > 18 else ''))
        print('%s %-4s loops (ms, cepstral peak):        ' % (tag, lab) + '  '.join('%.1f' % q for q, _ in loops(y)))
