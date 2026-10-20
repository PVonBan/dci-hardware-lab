# Automatic bank checks from existing recordings (no unit): inter-channel timing per program, IR wrap flags, and
# the stored settings each error follows (field regression). Uses guards.py. Run after every build.
import numpy as np, sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guards
CMP = '/tmp/claude-0/-home-claude/43821833-de77-5012-b98f-e22767bd5dd6/scratchpad/cmp'
os.chdir(CMP)
src = open('an.py').read().split('rows=[]')[0]; PL = sys.argv[1] if len(sys.argv) > 1 else 'plug_v16'
sys.argv = ['x', '.', PL, '/dev/null']; exec(src)
F = {}
for l in open('fields.txt'):
    p = l.rstrip('\n').split('\t'); n = int(p[0]); F[n] = {}
    for kv in p[2:]:
        m = re.match(r'(.+?)=(-?\d+)\((.*)\)', kv)
        if m: F[n][m.group(1)] = float(m.group(3))
timing = {}; wraps = []; errs = {}
for n in range(1, 129):
    try: hw = rd24(CAP + '/%03d.wav' % n)[LAT:]
    except Exception: continue
    hw = np.vstack([hw, np.zeros((LAT, 2))])
    pl = np.fromfile(PL + '/%03d.f32' % n, '<f4').reshape(-1, 2).astype(float)
    ih = [ir(hw[SW0:SW0 + SEG, c]) for c in (0, 1)]; ip = [ir(pl[SW0:SW0 + SEG, c]) for c in (0, 1)]
    timing[n] = (guards.channel_timing(ih[0], ih[1], right_offset=33), guards.channel_timing(ip[0], ip[1]))
    d = max(guards.late_energy_shift(x[c], SEG) for x in (ih, ip) for c in (0, 1))
    if d > 1.0: wraps.append((n, names[n], 0, d))
    # level error 200 Hz-5 kHz (hw - plug), per channel then averaged
    errs[n] = float(np.mean([10 * np.log10((hw[SW0:SW0 + SEG, c] ** 2).sum() / ((pl[SW0:SW0 + SEG, c] ** 2).sum() + 1e-30)) for c in (0, 1)]))
print('Inter-channel timing of the first arrival (right minus left, samples), programs with a direct sound, differences >= 2:')
def has_direct(n):
    f = F.get(n, {})
    for k in ('Dir Lvl', 'Dir Mix', 'Cho Dir Lvl', 'Dly Dir Lvl', 'Direct Lvl'):
        if k in f: return f[k] > 0
    return algs[n] in (1, 10, 23, 39)   # phasers / rotary: the dry path is part of the effect
for n, ((hl, hr, hd), (pl_, pr, pd)) in sorted(timing.items()):
    if has_direct(n) and abs(hd - pd) >= 2: print('  %3d %-16s alg %2d  unit %+d  plug-in %+d' % (n, names[n], algs[n], hd, pd))
print('\n%d programs whose full-window sweep spectrum changes > 1 dB at 4-16 kHz when the last 1.5 s is removed (not evidence; use gated IRs, noise or click trains):' % len(set(w[0] for w in wraps)))
print('  ' + ', '.join(sorted(set('%d %s' % (w[0], w[1]) for w in wraps), key=lambda t: int(t.split()[0]))))
med = np.median(list(errs.values())); E = {n: e - med for n, e in errs.items()}
print('\nStored settings the level error follows across the bank (rank correlation, >= 12 programs; strongest first):')
for a, r, k, cnt, nm in guards.field_regression(E, F)[:8]: print('  %-14s r %+.2f  %+.2f dB per unit  n=%d' % (nm, r, k, cnt))
