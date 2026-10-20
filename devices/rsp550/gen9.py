# Run 9: direct measurements for what v1.6.4 had to infer, plus repeatability and cleaner listening material.
#   A (slots 101-128): effect path of every band-limited delay/modulation algorithm with the direct off, depth 0,
#     feedback 0, EQ flat (sweep: the effect's own frequency response); Jet Flanging split into effect-only and
#     direct-only; one-field variants of Bright Plate * / Industrial * / Church *.
#   C (slots 101-128): program EQ series on a wet-only reverb and a wet-only Stereo Delay; Multi Phaser mode 4 with
#     the LFO stopped at five Manual settings and two resonances; Round Phaser in mode 4 with the LFO running.
#   B (program change): repeatability references, Jet Phasing noise at three levels, music 10 dB lower than run 6
#     (filelo) plus two more clips (file2lo, file3lo).
#   Z (program change, last): the same repeatability references again, to measure drift over the session.
import sys
U = '/mnt/user-data/uploads/Downloads/RSP-550/lab/'
d = open(U + 'RSP550-backup-20261018-041833.syx', 'rb').read()
P = {}; i = 0
while i + 106 <= len(d):
    if d[i] == 0xF0 and d[i + 1] == 0x41 and d[i + 4] == 0x12 and d[i + 105] == 0xF7 and d[i + 5] in (3, 4):
        n = d[i + 6] + 1 if d[i + 5] == 3 else d[i + 6] + 129; P[n] = bytearray(d[i + 8:i + 104]); i += 106
    else: i += 1

# field tables from the plug-in (fdump): alg -> name -> (off, width, min, max, values)
F = {}
for l in open('fields.tsv'):
    a, off, w, mn, mx, nm, full, vals = l.rstrip('\n').split('\t')
    if int(off) + int(w) > 96: continue   # plug-in extras (0x60+), not on the unit
    F.setdefault(int(a), {})[nm] = (int(off), int(w), int(mn), int(mx), [float(v) for v in vals.split(',')])

def raw_for(alg, nm, value):
    off, w, mn, mx, vals = F[alg][nm]
    k = min(range(len(vals)), key=lambda j: abs(vals[j] - value)); return mn + k
def setf(p, alg, nm, raw):
    off, w, mn, mx, vals = F[alg][nm]
    raw = max(mn, min(mx, raw))
    if w == 2: p[off] = raw & 0x7F; p[off + 1] = (raw >> 7) & 0x7F
    else: p[off] = raw
def setv(p, alg, nm, value): setf(p, alg, nm, raw_for(alg, nm, value))
def has(alg, nm): return nm in F.get(alg, {})
def blocks(p, bits):
    v = 0
    for b in bits: v |= 1 << b
    p[0x12] = (v >> 7) & 0x7F; p[0x13] = v & 0x7F
def getblocks(p): return (p[0x12] << 7) | p[0x13]
def named(p, name): q = bytearray(p); q[0:16] = name.ljust(16)[:16].encode(); return q

def eq_flat(p, alg):
    for nm in ('EQ Hi', 'EQ Mid', 'EQ Lo', 'EQ Total'):
        if has(alg, nm): setv(p, alg, nm, 0.0)

# effect path, generic: depth / feedback / resonance / tremolo / cross terms 0, direct off, EQ flat
def effect_only(p, alg):
    for nm in list(F[alg]):
        low = nm.lower()
        if any(k in low for k in ('depth', 'trem')) and 'pre' not in low: setv(p, alg, nm, 0.0)
        elif low in ('fb', 'reso', 'cross fb', 'feedback') or low.endswith(' fb') or low.startswith('fb'): setv(p, alg, nm, 0.0)
        elif low in ('dir mix', 'dir lvl', 'direct lvl') or low.endswith(' dir lvl'): setf(p, alg, nm, F[alg][nm][2])
        elif 'cross mix' in low: setf(p, alg, nm, F[alg][nm][2])
    eq_flat(p, alg)

BASE = {}
for n in sorted(P):
    a = P[n][0x11]
    if 1 <= a <= 39 and (a not in BASE or (BASE[a] > 100 and n <= 100)): BASE[a] = n
# multi-effects: keep only the modulation (or delay) block so one effect path is measured
MULTI_KEEP = {6: [1], 7: [1], 8: [1], 9: [2], 35: [0], 37: [2], 38: [0]}
EFFECT_ALGS = [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 18, 19, 31, 32, 33, 35, 37, 38]

A = []; C = []
for a in EFFECT_ALGS:
    n = BASE[a]; p = named(P[n], 'T EFF A%02d' % a); effect_only(p, a)
    if a in MULTI_KEEP:
        blocks(p, MULTI_KEEP[a])
        # stages after the measured one pass the signal through whatever the unit does with a switched-off block
        for nm in F[a]:
            if a in (6, 7, 8, 9, 35):
                if nm in ('Dly Dir Lvl', 'Rev Dir Lvl'): setf(p, a, nm, F[a][nm][3])
                elif nm in ('Dly Mix', 'Rev Lvl', 'PSDir Lvl'): setf(p, a, nm, F[a][nm][2])
            else:   # 37 / 38: delay kept, reverbs silent
                if nm in ('Rev 1 Mix', 'Rev 2 Lvl', 'Rev Lvl', 'Dir Lvl'): setf(p, a, nm, F[a][nm][2])
    if a in (31, 32):                                # tap delays: their feedback switch/levels are per tap
        for nm in F[a]:
            if 'FB' in nm: setv(p, a, nm, 0.0)
    A.append((['std'], 'Effect path alg %d (%s): direct off, depth 0, feedback 0, EQ flat' % (a, P[n][0:16].decode().strip()), p))
# Jet Flanging split (75): effect only / direct only, sweep and noise
p = named(P[75], 'T JETFL EFF'); setf(p, 2, 'Dir Mix', 0); A.append((['std', 'stereo'], 'Jet Flanging effect only (Direct Mix off)', p))
p = named(P[75], 'T JETFL DIR'); setf(p, 2, 'Mix', 0); A.append((['std', 'stereo'], 'Jet Flanging direct only (Mix 0)', p))
# one-field variants of the wet-only outliers
def var(n, name, desc, **kv):
    p = named(P[n], name); a = p[0x11]
    for nm, v in kv.items():
        nm = nm.replace('_', ' ')
        if nm == 'EQ flat': eq_flat(p, a)
        else: setv(p, a, nm, v)
    return (['std'], desc, p)
A.append(var(109, 'T BRPL EQFLAT', 'Bright Plate * with EQ flat', EQ_flat=1))
A.append(var(109, 'T BRPL DIFF12', 'Bright Plate * with Diffusion 120', Diffusion=120))
A.append(var(121, 'T INDU PRE0', 'Industrial * with Pre-Delay 0', Rev_PreDly=0))
A.append(var(121, 'T INDU RT2', 'Industrial * with Reverb Time 2.0', Rev_Time=2.0))
A.append(var(123, 'T CHUR EQFLAT', 'Church * with EQ flat', EQ_flat=1))
C.append(var(121, 'T INDU DAMP', 'Industrial * with Damp Level 0.71', Damp_Lvl=0.707946))
C.append(var(123, 'T CHUR ER0', 'Church * with ER Level 0', ER_Lvl=0))

# program EQ series: wet-only reverb (Baroque Hall *, EQ flat) and wet-only Stereo Delay
def eqtest(n, a, eqbit, name, desc, **kv):
    p = named(P[n], name); eq_flat(p, a); blocks(p, [b for b in range(14) if getblocks(P[n]) >> b & 1] + [eqbit])
    if a == 5: effect_only(p, a)
    for nm, v in kv.items(): setv(p, a, nm.replace('_', ' '), v)
    return (['std'], desc, p)
RV, DL = 115, BASE[5]
for nm, vals in (('EQ Hi', (-12, -6, 6, 12)), ('EQ Lo', (-12, 12)), ('EQ Mid', (-12, 12))):
    for v in vals:
        kw = {nm.replace(' ', '_'): v}
        if nm == 'EQ Mid': kw['EQ_Mid_Frq'] = 2000
        C.append(eqtest(RV, 29 if P[RV][0x11] == 29 else P[RV][0x11], 2, 'T RVEQ %s%+d' % (nm[3:].upper()[:2], v), 'Reverb EQ: %s %+d dB (wet-only %s)' % (nm, v, P[RV][0:16].decode().strip()), **kw))
C.append(eqtest(RV, P[RV][0x11], 2, 'T RVEQ FLAT', 'Reverb EQ: all flat, EQ on (reference)'))
for nm, vals in (('EQ Hi', (-12, 12)), ('EQ Lo', (-12, 12))):
    for v in vals:
        C.append(eqtest(DL, 5, 2, 'T DLEQ %s%+d' % (nm[3:].upper()[:2], v), 'Stereo Delay EQ: %s %+d dB (effect only, feedback 0)' % (nm, v), **{nm.replace(' ', '_'): v}))
C.append(eqtest(DL, 5, 2, 'T DLEQ FLAT', 'Stereo Delay EQ: all flat, EQ on (reference)'))

# Multi Phaser mode 4: LFO stopped, Manual x resonance; then Round Phaser in mode 4 with the LFO running
for reso in (0.0, 92.0):
    for man in (0, 25, 50, 75, 100):
        p = named(P[74], 'T PH4 M%d R%d' % (man, reso)); setv(p, 1, 'Depth', 0); setf(p, 1, 'Manual', man); setv(p, 1, 'Reso', reso); setv(p, 1, 'Trem', 0)
        C.append((['stereo'], 'Multi Phaser mode 4, depth 0, Manual %d, Resonance %g' % (man, reso), p))
p = named(P[71], 'T ROUND MODE4'); setf(p, 1, 'Mode', 4); setf(p, 1, 'Total Lvl', 50)   # plug-in render peaked 0.99 at -15 dB with 76
C.append((['stereolo', 'stereo', 'stereohi'], 'Round Phaser in mode 4, LFO running, noise at -30/-20/-15', p))

assert len(A) <= 28 and len(C) <= 28, (len(A), len(C))

def msg(n, p):
    body = bytes([3, n - 1, 0]) + bytes(p); sm = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0, 0x38, 0x12]) + body + bytes([sm, 0xF7])
open('tests9A.syx', 'wb').write(b''.join(msg(101 + k, p) for k, (kinds, nm, p) in enumerate(A)))
open('tests9C.syx', 'wb').write(b''.join(msg(101 + k, p) for k, (kinds, nm, p) in enumerate(C)))

REP = [(1, 'std'), (61, 'std'), (54, 'std')]
B = [(n, k, 'Repeatability reference (start): ' + P[n][0:16].decode().strip()) for n, k in REP]
B += [(74, k, 'Jet Phasing noise at %s' % lv) for k, lv in (('stereolo', '-30'), ('stereo', '-20'), ('stereohi', '-15'))]
for n in (1, 8, 50, 54, 58, 87):
    for k in ('filelo', 'file2lo', 'file3lo'):
        B.append((n, k, 'Listening material 10 dB lower (%s): %s' % (k, P[n][0:16].decode().strip())))
Z = [(n, k, 'Repeatability reference (end): ' + P[n][0:16].decode().strip()) for n, k in REP]
with open('plan9.txt', 'w') as f:
    for k, (kinds, nm, p) in enumerate(A):
        for kind in kinds: f.write('A\t%d\t%s\t%s\n' % (101 + k, kind, nm))
    for n, kind, nm in B: f.write('B\t%d\t%s\t%s\n' % (n, kind, nm))
    for k, (kinds, nm, p) in enumerate(C):
        for kind in kinds: f.write('C\t%d\t%s\t%s\n' % (101 + k, kind, nm))
    for n, kind, nm in Z: f.write('Z\t%d\t%s\t%s\n' % (n, kind, nm))
if __name__ == '__main__':
    print(open('plan9.txt').read()); print('A', len(A), 'C', len(C), 'lines', sum(1 for _ in open('plan9.txt')))
