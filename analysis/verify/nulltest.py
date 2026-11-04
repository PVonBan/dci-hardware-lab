#!/usr/bin/env python3
"""Null test: the plug-in's render subtracted from the unit's capture of the same program and stimulus, after
sub-sample alignment and a least-squares gain. The residual per octave relative to the unit's signal is the null depth:
what the model misses, at far greater sensitivity than band levels. Only meaningful for time-invariant programs (the
unit's reverbs and delays are; chorus, flanger, phaser and rotary are not).
Usage: nulltest.py <SSP550Test> <bank.syx> <capture dir> <latency> <gainL dB> <gainR dB> <stim wav> <program> <capture wav> [channel]"""
import sys, os, subprocess, numpy as np, soundfile as sf
from scipy import signal
FS = 48000; UP = 8
T, BANK, CAP, LAT, GL, GR, STIM, PROG, CAPF = sys.argv[1:10]; CH = int(sys.argv[10]) if len(sys.argv) > 10 else 1
x, _ = sf.read(STIM, always_2d=True, dtype='float32'); N = len(x); x.tofile('/tmp/null_x.f32')
subprocess.run([T, '--render', '/tmp/nullr', '/tmp/null_x.f32', BANK, PROG], check=True, stdout=subprocess.DEVNULL)
o = np.fromfile('/tmp/nullr/%03d.f32' % int(PROG), '<f4').reshape(-1, 2)[:N, CH].astype(float)
u = sf.read(os.path.join(CAP, CAPF))[0][int(LAT):int(LAT) + N, CH] / 10 ** (float(GR if CH else GL) / 20)
n = min(len(u), len(o)); u, o = u[:n], o[:n]
# sub-sample alignment on the sweep (std stimulus: 8.25-10.75 s; both channels carry signal there), lags within +-20 samples
a0, a1 = 390000, 520000
uu, ou = signal.resample_poly(u[a0:a1], UP, 1), signal.resample_poly(o[a0:a1], UP, 1)
c = signal.correlate(uu, ou, 'full', method='fft'); mid = len(ou) - 1; w = 20 * UP
k = int(np.argmax(c[mid - w:mid + w + 1])) - w
ofull = np.roll(signal.resample_poly(o, UP, 1), k)[::UP][:n]
g = float(np.dot(u, ofull) / (np.dot(ofull, ofull) + 1e-30)); r = u - g * ofull
f, Pu = signal.welch(u, FS, nperseg=8192); _, Pr = signal.welch(r, FS, nperseg=8192)
print('%s program %s: shift %+.3f samples, gain %+.2f dB, overall null %.1f dB' % (CAPF, PROG, k / UP, 20 * np.log10(abs(g) + 1e-30), 10 * np.log10(np.sum(Pr) / np.sum(Pu))))
print('  null depth per octave (residual re unit, dB): ' + ' '.join('%d:%.0f' % (fc, 10 * np.log10(Pr[(f >= fc / 1.41) & (f < fc * 1.41)].sum() / Pu[(f >= fc / 1.41) & (f < fc * 1.41)].sum())) for fc in (63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)))
