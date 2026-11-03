#!/usr/bin/env python3
"""EQ structure test 2: feed-forward boost / feed-back cut. Boost: H = 1 + (10^(g/20) - 1) * F(s); cut: H = 1 / (1 +
(10^(|g|/20) - 1) * F(s)); F a fixed 2nd-order band-pass (mid) or low/high-pass (shelves). One (fc, Q) per band must fit
every gain. Compared with the plug-in's symmetric RBJ (fixed Q per sign) on the same captures."""
import numpy as np, eqfit as E
from scipy import optimize
fs = 48000
def F(kind, fc, q, fr):
    s = 1j * fr / fc; d = 1 + s / q + s ** 2
    return {'bp': (s / q) / d, 'lp': 1 / d, 'hp': s ** 2 / d}[kind]
def model(kind, fc, q, g, fr):
    G = 10 ** (abs(g) / 20) - 1; Fv = F(kind, fc, q, fr)
    H = 1 + G * Fv if g > 0 else 1 / (1 + G * Fv); return 20 * np.log10(np.abs(H))
def rbj_peak(fc, q, g, fr):
    A = 10 ** (g / 40); w0 = 2 * np.pi * fc / fs; c = np.cos(w0); al = np.sin(w0) / (2 * q)
    b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]; z = np.exp(-1j * 2 * np.pi * fr / fs)
    return 20 * np.log10(np.abs((b[0] + b[1] * z + b[2] * z ** 2) / (a[0] + a[1] * z + a[2] * z ** 2)))
def meas(run, a, b, lat):
    cent, da = E.band_db(E.resp(run, a, 1, lat)); _, db = E.band_db(E.resp(run, b, 1, lat)); return cent, da - db
sets = {
 'mid 2 kHz': ('bp', [(meas('run10b', 'r4C-%03d-std.wav' % n, 'r4C-103-std.wav', 1133), g) for n, g in ((105, -12), (106, -6), (107, -3), (108, 3), (109, 6), (110, 12))]),
 'low shelf': ('lp', [(meas('run9', 'r4C-114-std.wav', 'r4C-116-std.wav', 1179), -12), (meas('run9', 'r4C-115-std.wav', 'r4C-116-std.wav', 1179), 12),
                      (meas('run10b', 'r4C-119-std.wav', 'r4C-103-std.wav', 1133), -6), (meas('run10b', 'r4C-120-std-rep2.wav', 'r4C-103-std.wav', 1133), 6)]),
 'high shelf': ('hp', [(meas('run9', 'r4C-112-std.wav', 'r4C-116-std.wav', 1179), -12), (meas('run9', 'r4C-113-std.wav', 'r4C-116-std.wav', 1179), 12),
                       (meas('run10b', 'r4C-117-std.wav', 'r4C-103-std.wav', 1133), -6), (meas('run10b', 'r4C-118-std.wav', 'r4C-103-std.wav', 1133), 6)])}
for name, (kind, data) in sets.items():
    m = lambda c: (c >= 60) & (c <= 16000)
    def res(p): return np.concatenate([model(kind, p[0], p[1], g, c[m(c)]) - d[m(c)] for (c, d), g in data])
    r = optimize.least_squares(res, [2000 if kind == 'bp' else (400 if kind == 'lp' else 3800), 0.7], bounds=([50, 0.1], [16000, 5]))
    per = [np.sqrt(np.mean((model(kind, r.x[0], r.x[1], g, c[m(c)]) - d[m(c)]) ** 2)) for (c, d), g in data]
    print('%-10s feed-forward/feed-back: fc %6.0f Hz Q %.2f   rms per gain (%s): %s' % (name, r.x[0], r.x[1], ' '.join('%+d' % g for _, g in data), ' '.join('%.2f' % v for v in per)))
    if kind == 'bp':
        for sign in (-1, 1):
            sub = [(cd, g) for cd, g in data if np.sign(g) == sign]
            def res2(p): return np.concatenate([rbj_peak(p[0], p[1], g, c[m(c)]) - d[m(c)] for (c, d), g in sub])
            r2 = optimize.least_squares(res2, [2000, 0.9], bounds=([50, 0.1], [16000, 5]))
            per2 = [np.sqrt(np.mean((rbj_peak(r2.x[0], r2.x[1], g, c[m(c)]) - d[m(c)]) ** 2)) for (c, d), g in sub]
            print('           plug-in RBJ one Q per sign (%s): fc %6.0f Q %.2f  rms: %s' % ('cut' if sign < 0 else 'boost', r2.x[0], r2.x[1], ' '.join('%.2f' % v for v in per2)))
