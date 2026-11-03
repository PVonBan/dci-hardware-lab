#!/usr/bin/env python3
"""Objective difference score for a loudness-matched A/B pair, calibrated on the user's blind results.
Features per pair (A unit, B plug-in, both already BS.1770-matched):
  spec   long-term 1/3-octave spectrum difference, rms dB over 100 Hz - 12 kHz
  dyn    short-term (50 ms) band-level difference, rms dB over frames within 40 dB of the peak (time structure, decay)
  stereo rms difference of per-band L/R correlation
  mod    rms difference of per-band level fluctuation (std of 50 ms levels, dB)
Usage: audib.py <pairs dir with NN-a.wav NN-b.wav> [results json: {"01": 9, ...} correct of 10]"""
import sys, os, json, numpy as np, soundfile as sf
from scipy import signal
FS = 48000; cent = 1000 * 2 ** (np.arange(-10, 11) / 3)
def bands(y):
    out = []
    for c in cent:
        sos = signal.butter(3, [c / 2 ** (1 / 6), min(c * 2 ** (1 / 6), 23000)], 'band', fs=FS, output='sos')
        out.append(signal.sosfilt(sos, y, axis=0))
    return np.array(out)   # band, time, ch
def feats(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]; ba, bb = bands(a), bands(b)
    w = int(0.05 * FS); fr = np.arange(0, n - w, w)
    def lev(bx): return 10 * np.log10(np.array([[np.mean(bx[k, i:i + w] ** 2) for i in fr] for k in range(len(cent))]) + 1e-20)   # band, frame (both ch)
    la, lb = lev(ba), lev(bb)
    spec = np.sqrt(np.mean((10 * np.log10(np.mean(ba ** 2, (1, 2)) + 1e-20) - 10 * np.log10(np.mean(bb ** 2, (1, 2)) + 1e-20)) ** 2))
    m = la > la.max() - 40; dyn = np.sqrt(np.mean((la[m] - lb[m]) ** 2))
    def corr(bx): return np.array([np.mean(bx[k, :, 0] * bx[k, :, 1]) / np.sqrt(np.mean(bx[k, :, 0] ** 2) * np.mean(bx[k, :, 1] ** 2) + 1e-30) for k in range(len(cent))])
    stereo = np.sqrt(np.mean((corr(ba) - corr(bb)) ** 2))
    def fl(l): return np.array([np.std(l[k][l[k] > l[k].max() - 30]) for k in range(len(cent))])
    mod = np.sqrt(np.mean((fl(la) - fl(lb)) ** 2))
    return dict(spec=spec, dyn=dyn, stereo=stereo, mod=mod)
if __name__ == '__main__':
    d = sys.argv[1]; res = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    rows = {}
    for f in sorted(os.listdir(d)):
        if f.endswith('-a.wav'):
            k = f[:2]; a = sf.read(os.path.join(d, f))[0]; b = sf.read(os.path.join(d, k + '-b.wav'))[0]
            rows[k] = feats(a, b)
    print('pair  spec   dyn  stereo   mod   heard')
    for k, r in rows.items(): print('%s  %5.2f %5.2f  %5.3f %5.2f   %s' % (k, r['spec'], r['dyn'], r['stereo'], r['mod'], res.get(k, '')))
    json.dump(rows, open(os.path.join(d, '..', 'audib-%s.json' % os.path.basename(os.path.abspath(d).rstrip('/').split('/')[-2])), 'w'), indent=1)
