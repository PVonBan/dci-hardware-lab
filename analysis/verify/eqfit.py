#!/usr/bin/env python3
"""Re-derive the program EQ from the raw captures, independently of the 1.6.7 hand fit: the Stereo Delay effect path
with one band set and the same program flat (run 9 C-112..116 on inputs 5/6, right channel; run 10b C-117..120 and
their flat reference C-116/101 on 7/8). The measured EQ-on / flat ratio over the sweep is fitted by least squares with
an RBJ shelf (corner, Q, gain) or peak. Prints the fitted values next to the plug-in's constants."""
import numpy as np, soundfile as sf, os
from scipy import optimize
C = '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture'; fs = 48000
SW0, SWN = 396002, 120000; SEG = SWN + 144000; NF = 1 << 19
x = sf.read(C + '/run10b/stim-std.wav')[0][:, 0]; xs = x[SW0:SW0 + SEG]
X = np.fft.rfft(xs, NF); f = np.fft.rfftfreq(NF, 1 / fs)
def resp(run, fname, ch, lat):
    y = sf.read(os.path.join(C, run, fname))[0][lat:, ch]; Y = np.fft.rfft(y[SW0:SW0 + SEG], NF); return Y / np.where(np.abs(X) > 1e-9, X, 1)
def band_db(H):
    cent = 1000 * 2 ** (np.arange(-16, 13) / 3); out = []
    for c in cent:
        k = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6)); out.append(10 * np.log10(np.mean(np.abs(H[k]) ** 2) + 1e-30))
    return cent, np.array(out)
def shelf(fc, q, g, hi, fr):
    A = 10 ** (g / 40); w0 = 2 * np.pi * fc / fs; c = np.cos(w0); al = np.sin(w0) / (2 * q); sa = 2 * np.sqrt(A) * al
    if hi: b = [A * ((A + 1) + (A - 1) * c + sa), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sa)]; a = [(A + 1) - (A - 1) * c + sa, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sa]
    else: b = [A * ((A + 1) - (A - 1) * c + sa), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sa)]; a = [(A + 1) + (A - 1) * c + sa, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sa]
    z = np.exp(-1j * 2 * np.pi * fr / fs); H = (b[0] + b[1] * z + b[2] * z ** 2) / (a[0] + a[1] * z + a[2] * z ** 2); return 20 * np.log10(np.abs(H))
def fit(cent, d, hi, g0):
    m = (cent >= 60) & (cent <= 16000)
    r = optimize.least_squares(lambda p: shelf(p[0], p[1], p[2], hi, cent[m]) - d[m], [3000 if hi else 400, 0.5, g0], bounds=([50, 0.2, -20], [16000, 3, 20]))
    return r.x, np.sqrt(np.mean(r.fun ** 2))
tests = [('run9', 'r4C-112-std.wav', 'r4C-116-std.wav', 1, 1179, True, -12, 'Hi -12 (run 9, R)'), ('run9', 'r4C-113-std.wav', 'r4C-116-std.wav', 1, 1179, True, 12, 'Hi +12 (run 9, R)'),
         ('run9', 'r4C-114-std.wav', 'r4C-116-std.wav', 1, 1179, False, -12, 'Lo -12 (run 9, R)'), ('run9', 'r4C-115-std.wav', 'r4C-116-std.wav', 1, 1179, False, 12, 'Lo +12 (run 9, R)'),
         ('run10b', 'r4C-117-std.wav', 'r4C-103-std.wav', 1, 1133, True, -6, 'Hi -6 (run 10b, R)'), ('run10b', 'r4C-118-std.wav', 'r4C-103-std.wav', 1, 1133, True, 6, 'Hi +6 (run 10b, R)'),
         ('run10b', 'r4C-119-std.wav', 'r4C-103-std.wav', 1, 1133, False, -6, 'Lo -6 (run 10b, R)'), ('run10b', 'r4C-120-std-rep2.wav', 'r4C-103-std.wav', 1, 1133, False, 6, 'Lo +6 (run 10b, R)')]
print('plug-in 1.6.7/1.6.8: low shelf 394 Hz Q 0.47, high shelf 3842 Hz Q 0.49, gain = the set value')
print('%-20s  corner Hz    Q    gain dB   fit rms dB' % 'test')
for run, a, b, ch, lat, hi, g, name in tests:
    try: cent, da = band_db(resp(run, a, ch, lat)); _, db = band_db(resp(run, b, ch, lat))
    except FileNotFoundError as e: print(name, 'missing', e.filename); continue
    (fc, q, gg), rms = fit(cent, da - db, hi, g)
    print('%-20s  %7.0f   %4.2f   %+5.1f     %.2f' % (name, fc, q, gg, rms))
