#!/usr/bin/env python3
"""Round-2 capture stimuli (2026-10-21, from the DCI Overdrive chat): what the new comparisons need from a real unit.

  stimuli_round2.py <out dir> [--fs 48000]   -> <out>/r2_*.f32 (mono float32) + segments.json (name, start, length)

  r2_noise_*    band-limited noise (14 kHz) at -20 / -40 / -60 dBFS: a transfer only counts where it is coherent
                (guards.transfer); the quieter levels give a linear one for a driven unit
  r2_smpte      SMPTE intermodulation, 60 Hz + 7 kHz at 4:1, -24 / -18 / -12 dBFS
  r2_chord      a power chord 82.4 + 123.5 Hz, -24 / -18 / -12 dBFS
  r2_recovery   a -40 dBFS 1 kHz tone, a 0.3 s 100 Hz burst at -3 dBFS, the tone again for 2.5 s (bias shift, blocking)
  r2_levels     1 kHz, 0.5 s per step from -60 to 0 dBFS in 6 dB steps (the gain curve)
  r2_attack     single plucks (harmonic, 900 / s attack) at -24 / -12 / -6 dBFS, 1 s apart: attack_nulls on the first 20 ms
Every part starts after 0.5 s of silence (the unit settles; the loop latency is measured as usual from the click).
"""
import json, os, sys
import numpy as np
from scipy import signal

def make(fs=48000):
    t = lambda s: np.arange(int(s * fs)) / fs
    db = lambda d: 10 ** (d / 20)
    parts = {}
    rng = np.random.default_rng(21); b, a = signal.butter(4, 14000, fs=fs)
    for L in (-20, -40, -60):
        n = signal.lfilter(b, a, rng.normal(size=int(6 * fs))); parts[f'r2_noise_{-L}'] = db(L) * n / np.std(n)
    for name, f1, f2, a1, a2 in (('r2_smpte', 60.0, 7000.0, 0.8, 0.2), ('r2_chord', 82.4, 123.5, 0.5, 0.5)):
        parts[name] = np.concatenate([db(L) * (a1 * np.sin(2 * np.pi * f1 * t(2)) + a2 * np.sin(2 * np.pi * f2 * t(2))) for L in (-24, -18, -12)])
    tone = lambda s: db(-40) * np.sin(2 * np.pi * 1000 * t(s))
    parts['r2_recovery'] = np.concatenate([tone(1.0), tone(0.3) + db(-3) * np.sign(np.sin(2 * np.pi * 100 * t(0.3))), tone(2.5)])
    parts['r2_levels'] = np.concatenate([db(L) * np.sin(2 * np.pi * 1000 * t(0.5)) for L in range(-60, 1, 6)])
    def pluck(L):
        tt = t(1.0); x = sum((0.6 ** h) * np.sin(2 * np.pi * 110 * (h + 1) * tt + h) for h in range(8)) * np.exp(-tt * 4) * (1 - np.exp(-tt * 900))
        return db(L) * x / np.abs(x).max()
    parts['r2_attack'] = np.concatenate([pluck(L) for L in (-24, -12, -6)])
    return parts

if __name__ == '__main__':
    out = sys.argv[1]; fs = int(sys.argv[sys.argv.index('--fs') + 1]) if '--fs' in sys.argv else 48000
    os.makedirs(out, exist_ok=True); segs = []; pos = 0
    for k, v in make(fs).items():
        x = np.concatenate([np.zeros(int(0.5 * fs)), v]).astype(np.float32); x.tofile(os.path.join(out, k + '.f32'))
        segs.append([k, pos, len(x)]); pos += len(x)
    json.dump(segs, open(os.path.join(out, 'segments.json'), 'w'), indent=1); print(f'{len(segs)} stimuli, {pos / fs:.0f} s, in {out}')
