#!/usr/bin/env python3
"""Which EQ structure is the unit's? Fit every shelf capture (both gains, both sessions) jointly with one fixed
(corner, Q) per band under two models:
  rbj       RBJ shelf, gain as set (corner is the midpoint; the plug-in's 1.6.7 model)
  additive  H(f) = 1 + (10^(g/20) - 1) * L(f), L a 2nd-order low-pass (low shelf) or high-pass (high shelf) of fixed
            corner and Q: the gain is applied to a filtered copy and added, as a digital unit of 1991 would do it
The model that fits all gains with one corner is the unit's."""
import numpy as np
from scipy import optimize
import eqfit as E
def lp2(fc, q, fr, hi):
    s = 1j * fr / fc; H = 1 / (1 + s / q + s ** 2) if not hi else (s ** 2) / (1 + s / q + s ** 2); return H
def additive(fc, q, g, hi, fr): return 20 * np.log10(np.abs(1 + (10 ** (g / 20) - 1) * lp2(fc, q, fr, hi)))
data = []
for run, a, b, ch, lat, hi, g, name in E.tests:
    cent, da = E.band_db(E.resp(run, a, ch, lat)); _, db = E.band_db(E.resp(run, b, ch, lat)); data.append((hi, g, cent, da - db, name))
for hi in (False, True):
    sel = [d for d in data if d[0] == hi]; m = lambda c: (c >= 60) & (c <= 16000)
    for model, fn in (('rbj', E.shelf), ('additive', additive)):
        def res(p): return np.concatenate([fn(p[0], p[1], g, hi, c[m(c)]) - d[m(c)] for _, g, c, d, _ in sel])
        r = optimize.least_squares(res, [3000 if hi else 400, 0.5], bounds=([50, 0.2], [16000, 3]))
        per = [np.sqrt(np.mean((fn(r.x[0], r.x[1], g, hi, c[m(c)]) - d[m(c)]) ** 2)) for _, g, c, d, _ in sel]
        print('%s shelf, %-8s corner %6.0f Hz Q %.2f  rms per capture: %s' % ('high' if hi else 'low', model, r.x[0], r.x[1], ' '.join('%.2f' % v for v in per)))
