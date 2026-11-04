#!/usr/bin/env python3
"""Run 11 (designed 2026-11-03 from the verification of runs 9-10b; docs/NEXT_UNIT_PROCESS.md): the first run that
runs itself. The user patches the calibration loop, double-clicks, loads two batches in the first 20 minutes, and
comes back for the restore. Everything else (about 2 hours) is factory programs by program change.

  python3 make_run11.py <reverblab dir> <backup.syx> <fields.tsv> <run10 dir (its stim/ is reused)> <filelo.wav> <out dir>

Batch A (28 slots, std stimulus): the program EQ
  - Stereo Delay effect path (where 1.6.9's gain-dependent shapes were measured at +-6 / +-12): Hi and Lo at
    -10 -3 -1 +1 +3 +10, Mid at 2 kHz -9 -1.5 +1.5 +9, EQ Total -6 / +6 (the level law)
  - Ambience effect-only: Hi +-6, Lo +-6, Mid +-6 (replay of run 7: the delay-path shapes are 1.7 dB off here)
  - Stereo Chorus effect-only at Wide Chorus's settings with the EQ flat, and each of its bands alone (Hi +10,
    Lo +7.5, Mid -5.5): does the EQ act on the chorus path as on the delay path?
Batch C (28 slots): controls never varied (COVERAGE.md) and the wet-only pre-delay
  - Large Hall 1 wet only: Rev PreDly 0 / 50 / 100 ms, ER PreDly 0 / 50 (labimp)
  - Small Room (Room 2) and Bright Plate (Plate 1): Rev Time low / mid / high, Rev PreDly 50, Damp Lvl high
  - Gate reverb (program 45): Gate Time x3, Gate Mode, Density
  - Stereo Pitch (program 97?): PS1 Fine +50, PS1 PreDly 100, PS1 FB 50
  - 8 Tap Delay (program 61): T1 time x2, T1 FB
  - Mod Reverb (Heaven): Mod Depth 0, Rev Time long
  - Soft Rotary at the fast speed
Batch B (program changes, unattended): Soft Rotary, Large Hall 1 and Wide Chorus on music at three levels and on
  tones at three levels (the rotary's 5 dB clip-to-clip level difference); in-phase / anti-phase noise on one program
  per algorithm (input routing); a 1 kHz level series and bursts on one program per family (gain curve, attack and
  release); periodic noise on the 12 battery programs (third response method); then every factory program 1-126 with
  labimp + sweepm12 (the first complete battery of the bank: per-program comparison and the audibility ranking).
Z: Large Hall 1 labimp every 20 lines (drift through the run; the runner records in plan order since run 11).
No 96 kHz lines (the MHLink stalled on the rate switch in run 10)."""
import json, os, sys, shutil
import numpy as np, soundfile as sf

RL, BACKUP, FIELDS, RUN10, FILELO, OUT = sys.argv[1:7]
FS = 48000
STIM = os.path.join(OUT, 'stim'); os.makedirs(STIM, exist_ok=True)
for f in os.listdir(os.path.join(RUN10, 'stim')):
    if f.startswith(('labimp', 'sweepm12.', 'segments')): shutil.copy(os.path.join(RUN10, 'stim', f), STIM)
segs = json.load(open(os.path.join(STIM, 'segments.json')))
segs = {k: v for k, v in segs.items() if k in ('labimp', 'sweepm12')}

def put(name, parts):
    out, table, pos = [], [], 0
    for seg, x, tail in parts:
        x = np.asarray(x, np.float64)
        if x.ndim == 1: x = np.stack([x, x], 1)
        n = len(x) + int(round(tail * FS))
        if seg: table.append([seg, pos, n])
        out.append(x); out.append(np.zeros((n - len(x), 2))); pos += n
    y = np.concatenate(out)
    sf.write(os.path.join(STIM, name + '.wav'), np.clip(y, -1, 1).astype(np.float32), FS, subtype='PCM_24')
    with open(os.path.join(STIM, name + '.txt'), 'w') as f:
        for s, p0, n in table: f.write('%s %d %d\n' % (s, p0, n))
    segs[name] = {'fs': FS, 'segments': table, 'length': len(y)}

# music at three levels: filelo is the listening material 10 dB down (peaks -13 dBFS); +10 = the original level
m, r = sf.read(FILELO, always_2d=True); assert r == FS
put('musichi', [('music', m * 10 ** (10 / 20), 2.0)]); put('musiclo', [('music', m * 10 ** (-10 / 20), 2.0)])
# tones at three levels for the rotary and the halls: 250 Hz and 1 kHz, 4 s each, at -30 / -20 / -10 dBFS
parts = [(None, np.zeros((FS // 2, 2)), 0)]
t = np.arange(4 * FS) / FS; fade = np.minimum(1, np.minimum(t / 0.01, (4 - t) / 0.01))
for db in (-30, -20, -10):
    for f in (250, 1000):
        parts.append(('tone%d_%d' % (f, -db), 10 ** (db / 20) * np.sin(2 * np.pi * f * t) * fade, 2.0))
put('tonelv', parts)
# three tests added 2026-11-03 evening (NOTES.md, "additional tests"):
#   antiphase  3 s pink noise in phase (L = R) then 3 s anti-phase (L = -R), -20 dBFS: an algorithm that sums its inputs
#              to mono gives no effect on the second half; one that keeps them apart does. One program per algorithm.
#   levser     1 kHz, 2 s at each of -50 .. -6 dBFS in 4 dB steps (gain curve: compression or clipping, harmonics tell
#              which), then a burst series -30 -> -10 -> -30 dBFS (attack and release). One program per family.
#   pnoise     one 1 s period of pink noise repeated 8 times, -20 dBFS: the same response by synchronous averaging, to
#              be compared with the sweep and the impulse on the same program (three methods must agree).
rng = np.random.default_rng(1103)
def pink(n):
    w = rng.standard_normal(n); X = np.fft.rfft(w); f = np.fft.rfftfreq(n, 1 / FS); X[1:] /= np.sqrt(f[1:] / f[1]); X[0] = 0
    y = np.fft.irfft(X, n); return y / np.sqrt(np.mean(y ** 2))
pk = pink(3 * FS) * 10 ** (-20 / 20); fd = np.minimum(1, np.minimum(np.arange(3 * FS) / (0.02 * FS), (3 * FS - np.arange(3 * FS)) / (0.02 * FS))); pk *= fd
put('antiphase', [(None, np.zeros((FS // 2, 2)), 0), ('inphase', np.stack([pk, pk], 1), 3.0), ('antiphase', np.stack([pk, -pk], 1), 3.0)])
parts = [(None, np.zeros((FS // 2, 2)), 0)]; t2 = np.arange(2 * FS) / FS; f2 = np.minimum(1, np.minimum(t2 / 0.01, (2 - t2) / 0.01))
for db in range(-50, -5, 4): parts.append(('lev%d' % -db, 10 ** (db / 20) * np.sin(2 * np.pi * 1000 * t2) * f2, 0.5))
tb = np.arange(5 * FS) / FS; env = np.where((tb >= 2) & (tb < 3), 10 ** (-10 / 20), 10 ** (-30 / 20))
parts.append(('burst', env * np.sin(2 * np.pi * 1000 * tb), 2.0))
put('levser', parts)
per = pink(FS) * 10 ** (-20 / 20)
put('pnoise', [(None, np.zeros((FS // 2, 2)), 0), ('pnoise', np.tile(np.stack([per, per], 1), (8, 1)), 4.0)])
json.dump(segs, open(os.path.join(STIM, 'segments.json'), 'w'), indent=1)

# programs
d = open(BACKUP, 'rb').read(); P = {}; i = 0
while i + 106 <= len(d):
    if d[i] == 0xF0 and d[i + 1] == 0x41 and d[i + 4] == 0x12 and d[i + 105] == 0xF7 and d[i + 5] in (3, 4):
        n = d[i + 6] + 1 if d[i + 5] == 3 else d[i + 6] + 129; P[n] = bytearray(d[i + 8:i + 104]); i += 106
    else: i += 1
F = {}
for l in open(FIELDS):
    a, off, w, mn, mx, nm, full, vals = l.rstrip('\n').split('\t')
    if int(off) + int(w) > 96: continue
    F.setdefault(int(a), {})[nm] = (int(off), int(w), int(mn), int(mx), [float(v) for v in vals.split(',')])
def setv(p, alg, nm, value):
    off, w, mn, mx, vals = F[alg][nm]
    raw = mn + min(range(len(vals)), key=lambda j: abs(vals[j] - value))
    if w == 2: p[off] = raw & 0x7F; p[off + 1] = (raw >> 7) & 0x7F
    else: p[off] = raw
def getv(p, alg, nm):
    off, w, mn, mx, vals = F[alg][nm]
    raw = p[off] | (p[off + 1] << 7) if w == 2 else p[off]; return vals[raw - mn]
def named(p, name): q = bytearray(p); q[0:16] = name.ljust(16)[:16].encode(); return q
name = lambda n: P[n][0:16].decode().strip()
alg = lambda n: P[n][0x11]
def byalg(a, prefer=None):
    for n in ([prefer] if prefer else []) + sorted(P):
        if n in P and alg(n) == a and n <= 128: return n
    raise SystemExit('no factory program with algorithm %d' % a)
def eq_flat(p, a):
    for nm in ('EQ Hi', 'EQ Mid', 'EQ Lo', 'EQ Total'): setv(p, a, nm, 0)
def test(src, label, desc, kinds, **kv):
    a = alg(src); p = named(P[src], label[:16])
    for nm, v in kv.items(): setv(p, a, nm.replace('_', ' '), v)
    return (p, desc, kinds, src)

A, C = [], []
DL = byalg(5, 58)   # Stereo Delay (Shimmer)
def dl(label, desc, **kv):
    a = alg(DL); p = named(P[DL], label); eq_flat(p, a); setv(p, a, 'Dly Dir Lvl', 0); setv(p, a, 'FB', 0); setv(p, a, 'Cross FB', 0); setv(p, a, 'Mod Depth', 0)
    for nm, v in kv.items(): setv(p, a, nm.replace('_', ' '), v)
    A.append((p, desc, ['std'], DL))
dl('T DL EQ FLAT', 'Stereo Delay EQ: all flat (reference)')
for g in (-10, -3, -1, 1, 3, 10):
    dl('T DL HI %+d' % g, 'Stereo Delay EQ: EQ Hi %+d dB' % g, EQ_Hi=g)
    dl('T DL LO %+d' % g, 'Stereo Delay EQ: EQ Lo %+d dB' % g, EQ_Lo=g)
for g in (-9, 9):
    dl('T DL MID %+g' % g, 'Stereo Delay EQ: Mid %+g dB at 2000 Hz' % g, EQ_Mid=g, EQ_Mid_Frq=2000)
for g in (-6, 6):
    dl('T DL TOT %+d' % g, 'Stereo Delay EQ: EQ Total %+d dB (level law)' % g, EQ_Total=g)
AM = byalg(15, 35)   # Ambience
def amb(label, desc, **kv):
    a = alg(AM); p = named(P[AM], label); eq_flat(p, a); setv(p, a, 'Amb Dir Lvl', 0); setv(p, a, 'Edge Mix', 0)
    for nm, v in kv.items(): setv(p, a, nm.replace('_', ' '), v)
    A.append((p, desc, ['std'], AM))
amb('T AMB EQ FLAT', 'Ambience effect-only EQ: all flat (reference)')
for nm in ('EQ Hi', 'EQ Lo', 'EQ Mid'):
    for g in (-6, 6): amb('T AMB %s%+d' % (nm[3:5].upper(), g), 'Ambience effect-only EQ: %s %+d dB%s' % (nm, g, ' at 2000 Hz' if nm == 'EQ Mid' else ''), **({nm.replace(' ', '_'): g} | ({'EQ_Mid_Frq': 2000} if nm == 'EQ Mid' else {})))
WC = byalg(13, 50)   # Wide Chorus: EQ Hi +10, Mid -5.5 (frq 8), Lo +7.5
def cho(label, desc, **kv):
    a = alg(WC); p = named(P[WC], label); eq_flat(p, a); setv(p, a, 'Cho Dir Lvl', 0)
    for nm, v in kv.items(): setv(p, a, nm.replace('_', ' '), v)
    A.append((p, desc, ['std', 'wav:musichi'], WC))
cho('T WC EQ FLAT', 'Wide Chorus effect-only, EQ flat (reference)')
cho('T WC HI+10', 'Wide Chorus effect-only, EQ Hi +10 only', EQ_Hi=10)
cho('T WC LO+7.5', 'Wide Chorus effect-only, EQ Lo +7.5 only', EQ_Lo=7.5)
cho('T WC MID-5.5', 'Wide Chorus effect-only, EQ Mid -5.5 only (program Mid Frq)', EQ_Mid=-5.5, EQ_Mid_Frq=getv(P[WC], 13, 'EQ Mid Frq'))
assert len(A) == 28, len(A)

LH = 1
for v in (0, 50, 100): C.append(test(LH, 'T LH1 WET PD%d' % v, 'Large Hall 1 wet only, Rev PreDly %d ms' % v, ['wav:labimp'], Dir_Lvl=0, Rev_PreDly=v))
for v in (0, 50): C.append(test(LH, 'T LH1 WET ER%d' % v, 'Large Hall 1 wet only, ER PreDly %d ms' % v, ['wav:labimp'], Dir_Lvl=0, ER_PreDly=v))
for a, nm in ((28, 'Room 2'), (29, 'Plate 1')):
    n = byalg(a, 7 if a == 28 else 9)
    for v, lab in ((0.5, 'low'), (2.0, 'mid'), (6.0, 'high')):   # seconds; the unit's own ceiling is about 8.3 s (run 4)
        C.append(test(n, 'T %s RT %s' % (nm[:3].upper(), lab[:2].upper()), '%s (%s) wet only, Rev Time %g (%s)' % (name(n), nm, v, lab), ['wav:labimp', 'wav:sweepm12'], Dir_Lvl=0, Rev_Time=v))
    C.append(test(n, 'T %s PD50' % nm[:3].upper(), '%s (%s) wet only, Rev PreDly 50 ms' % (name(n), nm), ['wav:labimp'], Dir_Lvl=0, Rev_PreDly=50))
    C.append(test(n, 'T %s DAMP' % nm[:3].upper(), '%s (%s) wet only, Damp Lvl at its strongest (code 0)' % (name(n), nm), ['wav:sweepm12'], Dir_Lvl=0, Damp_Lvl=F[a]['Damp Lvl'][4][0]))
GT = byalg(16, 45)
gv = F[16]['Gate Time'][4]
for v in (gv[2], gv[len(gv) // 2], gv[-2]): C.append(test(GT, 'T GATE T%g' % v, '%s (gate reverb) wet only, Gate Time %g' % (name(GT), v), ['wav:labimp'], Dir_Lvl=0, Gate_Time=v))
C.append(test(GT, 'T GATE MODE', '%s wet only, the other Gate Mode' % name(GT), ['wav:labimp'], Dir_Lvl=0, Gate_Mode=F[16]['Gate Mode'][4][1 if getv(P[GT], 16, 'Gate Mode') == F[16]['Gate Mode'][4][0] else 0]))
C.append(test(GT, 'T GATE DENS', '%s wet only, Density low' % name(GT), ['wav:labimp'], Dir_Lvl=0, Density=F[16]['Density'][4][1]))
PS = byalg(21, 97)
C.append(test(PS, 'T PS FINE+50', '%s: PS1 Fine +50, direct off' % name(PS), ['wav:sweepm12', 'wav:labimp'], Dir_Lvl=0, PS1_Fine=50))
C.append(test(PS, 'T PS PD100', '%s: PS1 PreDly 100 ms, direct off' % name(PS), ['wav:labimp'], Dir_Lvl=0, PS1_PreDly=100))
C.append(test(PS, 'T PS FB50', '%s: PS1 FB 50, direct off' % name(PS), ['wav:labimp'], Dir_Lvl=0, PS1_FB=50))
TD = byalg(31, 61)
C.append(test(TD, 'T 8TAP T1x2', '%s: Tap 1 time doubled, direct off' % name(TD), ['wav:labimp'], Dir_Lvl=0, T1_Dly_Time=min(getv(P[TD], 31, 'T1 Dly Time') * 2, F[31]['T1 Dly Time'][4][-1])))
C.append(test(TD, 'T 8TAP FB50', '%s: Tap 1 FB 50, direct off' % name(TD), ['wav:labimp'], Dir_Lvl=0, T1_FB=50))
MR = byalg(36, 33)
C.append(test(MR, 'T HEAVEN MOD0', '%s wet only, Mod Depth 0' % name(MR), ['wav:labimp', 'wav:sweepm12'], Rev_Dir_Lvl=0, Mod_Depth=0))
C.append(test(MR, 'T HEAVEN RTLO', '%s wet only, Rev Time short' % name(MR), ['wav:labimp'], Rev_Dir_Lvl=0, Rev_Time=F[36]['Rev Time'][4][2]))
RO = byalg(39, 87)
C.append(test(RO, 'T ROTARY FAST', '%s at the fast speed (the factory program has no overdrive block)' % name(RO), ['wav:tonelv', 'wav:musichi'], Speed=F[39]['Speed'][4][1]))
assert len(C) <= 28, len(C)

def msg(n, p):
    body = bytes([3, n - 1, 0]) + bytes(p); sm = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0, 0x38, 0x12]) + body + bytes([sm, 0xF7])
open(os.path.join(OUT, 'tests11A.syx'), 'wb').write(b''.join(msg(101 + k, p) for k, (p, _, _, _) in enumerate(A)))
open(os.path.join(OUT, 'tests11C.syx'), 'wb').write(b''.join(msg(101 + k, p) for k, (p, _, _, _) in enumerate(C)))
L, slots = [], {}
ref = ('Z', 1, 'wav:labimp', 'Reference (drift): Large Hall 1')
def add(row):
    L.append(row)
    if len([r for r in L if r[0] != 'Z']) % 20 == 0: L.append(ref)
add(ref)
for b, T in (('A', A), ('C', C)):
    for k, (p, desc, kinds, src) in enumerate(T):
        slots['%s%d' % (b, 101 + k)] = {'source': src, 'what': desc, 'kinds': kinds}
        for kind in kinds: add((b, 101 + k, kind, desc))
for n in (RO, LH, WC):
    for kind in ('wav:musichi', 'wav:musiclo', 'wav:tonelv'): add(('B', n, kind, 'Level dependence (%s): %s' % (kind[4:], name(n))))
firstOf = {}
for n in sorted(P):
    if n <= 126: firstOf.setdefault(alg(n), n)
for a_, n in sorted(firstOf.items()): add(('B', n, 'wav:antiphase', 'Input routing (in-phase then anti-phase noise), algorithm %d: %s' % (a_, name(n))))
for a_ in (1, 2, 5, 13, 15, 16, 21, 24, 30, 34, 36, 39, 23, 3, 31):
    if a_ in firstOf: add(('B', firstOf[a_], 'wav:levser', 'Level series and bursts, algorithm %d: %s' % (a_, name(firstOf[a_]))))
for n in (1, 8, 2, 4, 5, 7, 9, 33, 50, 54, 60, 70): add(('B', n, 'wav:pnoise', 'Periodic noise (third method): %s' % name(n)))
for n in sorted(P):
    if n > 126: continue
    for kind, what in (('wav:labimp', 'impulse x4 + left/right'), ('wav:sweepm12', 'sweep -12 dBFS')):
        add(('B', n, kind, 'Whole bank (%s): %s' % (what, name(n))))
add(ref)
json.dump(slots, open(os.path.join(OUT, 'slots11.json'), 'w'), indent=1)
with open(os.path.join(OUT, 'plan11.txt'), 'w') as f:
    for b, n, k, desc in L: f.write('%s\t%d\t%s\t%s\n' % (b, n, k, desc))
tot = sum((segs[k[4:]]['length'] / FS if k.startswith('wav:') else 32) + 4 for _, _, k, _ in L)
print('%d lines, %d + %d test programs, about %.0f min of captures' % (len(L), len(A), len(C), tot / 60))
