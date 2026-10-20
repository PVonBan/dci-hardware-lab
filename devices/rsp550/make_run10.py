#!/usr/bin/env python3
"""RSP-550 run 10: the reference-lab battery (dci-reference-lab skill, dci-effects tools/reverblab run 3) on the unit.

    make_run10.py <reverblab dir> <backup.syx> <fields.tsv> <out dir>

Writes to <out dir>: stim/*.wav (+ .txt markers, 24-bit; the runner plays them as kind "wav:<name>"), stim/segments.json
(where each test sits in each stimulus), stims/ (the reverb lab's analysis inputs: inverse filters, long-tone table,
pink burst), tests10A.syx (pre-delay test programs, slots 101-108) and plan10.txt.

Battery per program (factory programs by program change, batch B):
  labimp      impulse 4 times after different gaps (7.00 / 7.37 / 7.81 / 8.23 s): the unit's own variance, which is the
              fit tolerance; then left-only and right-only impulses (cross-feed, mono loss)
  sweepm12    the run-2 exponential sweep at -12 dBFS: band T30, 1/3-octave tone as the program sounds
  labmisc     10 s silence (noise), 2 s long tones at 250 Hz-4 kHz (real modulation: spread in cents, rate), a 4 Hz click
              train (time variance from the unit's own onset), a 2 s pink burst (steady tone, high-SNR decay)
  sweepm12_96 the -12 dBFS sweep at 96 kHz (interface rate) against the same sweep at 48 kHz (three programs)
Batch A (slots 101-128): pre-delay 0 / 50 ms on Large Hall 1 (reverb and early-reflection pre-delay), Warm Plate and
  Large Room, one impulse each (imp1): what the control means (from the input, or added to the program's own delay);
  the reverb programs with the direct level at 0 (labimp, sweepm12: decay measures without the direct sound); every
  battery program with its Total Level lowered for the -24 / -12 / 0 dBFS sweeps (level dependence and distortion;
  at the factory level the 0 dBFS sweep would clip the interface).
Batch Z (end): labimp on Large Hall 1 and Warm Plate again (drift over the session: the run-2-vs-run-3 check), std on
  Large Hall 1 and Light Flanger (the same capture as runs 6-9: has the chain changed since?).
"""
import json, os, sys
import numpy as np
import soundfile as sf

RL, BACKUP, FIELDS, OUT = sys.argv[1:5]
sys.path.insert(0, RL)
import make_run2 as m2
import make_run3 as m3

FS = 48000
STIM = os.path.join(OUT, 'stim'); STIMS = os.path.join(OUT, 'stims')
os.makedirs(STIM, exist_ok=True); os.makedirs(STIMS, exist_ok=True)

# the reverb lab's own stimuli and inverse filters (identical signals, so analyse_run3.py applies unchanged)
m3.stimuli(STIMS)
x12, inv12 = m2.ess()
np.save(os.path.join(STIMS, 'sweep-inverse.npy'), inv12.astype(np.float32))
segs = {}


def put(name, parts, fs=FS):
    """parts: list of (segment name or None, stereo array, tail seconds kept in the segment). Writes the stimulus."""
    out, table, pos = [], [], 0
    for seg, x, tail in parts:
        x = np.asarray(x, np.float64)
        if x.ndim == 1: x = np.stack([x, x], 1)
        n = len(x) + int(round(tail * fs))
        if seg: table.append([seg, pos, n])
        out.append(x); out.append(np.zeros((n - len(x), 2))); pos += n
    y = np.concatenate(out)
    sf.write(os.path.join(STIM, name + '.wav'), y.astype(np.float32), fs, subtype='PCM_24')
    with open(os.path.join(STIM, name + '.txt'), 'w') as f:
        for s, p0, n in table: f.write('%s %d %d\n' % (s, p0, n))
    segs[name] = {'fs': fs, 'segments': table, 'length': len(y)}
    return len(y) / fs


imp = np.zeros((1, 2)); imp[0] = 0.5
impL = np.array([[0.5, 0.0]]); impR = np.array([[0.0, 0.5]])
parts = [(None, np.zeros((FS, 2)), 0)]
for i, gap in enumerate((7.0, 7.37, 7.81, 8.23)):
    parts.append(('imp_r%d' % (i + 1), imp, gap - 1 / FS))
parts += [('impL', impL, 7.0 - 1 / FS), ('impR', impR, 7.0 - 1 / FS)]
put('labimp', parts)
put('sweepm24', [('sweepm24', sf.read(os.path.join(STIMS, 'sweep_m24.wav'))[0], 8.1)])
put('sweepm12', [('sweep', x12, 8.1)])
put('sweep0', [('sweep0', sf.read(os.path.join(STIMS, 'sweep_0.wav'))[0], 8.1)])
s96, r96 = sf.read(os.path.join(STIMS, 'sweep96.wav'))
put('sweepm12_96', [('sweep96', s96, 8.1)], fs=r96)
lt = sf.read(os.path.join(STIMS, 'longtones.wav'))[0]
put('labmisc', [('silence', np.zeros((10 * FS, 2)), 0), (None, np.zeros((FS // 2, 2)), 0),
                ('longtones', lt, 4.0), ('clicks', sf.read(os.path.join(STIMS, 'clicks.wav'))[0], 6.0),
                ('pink', sf.read(os.path.join(STIMS, 'pink.wav'))[0], 6.0)])
put('imp1', [(None, np.zeros((FS // 2, 2)), 0), ('predelay50', imp, 6.1)])
json.dump(segs, open(os.path.join(STIM, 'segments.json'), 'w'), indent=1)

# ---- programs (factory bank from the backup; fields from the plug-in's table, as gen9.py)
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
    raw = p[off] | (p[off + 1] << 7) if w == 2 else p[off]
    return vals[raw - mn]
def named(p, name): q = bytearray(p); q[0:16] = name.ljust(16)[:16].encode(); return q
name = lambda n: P[n][0:16].decode().strip()

BATTERY = [1, 8, 2, 4, 5, 7, 9, 33, 50, 54, 60, 70]
RATE96 = [1, 8, 50]
A = []
for n, variants in ((1, (('Rev PreDly', 0), ('Rev PreDly', 50), ('ER PreDly', 0), ('ER PreDly', 50))),
                    (8, (('Rev PreDly', 0), ('Rev PreDly', 50))), (5, (('Rev PreDly', 0), ('Rev PreDly', 50)))):
    a = P[n][0x11]
    for fld, v in variants:
        p = named(P[n], 'T %s %s%d' % (name(n)[:6].upper(), 'ER' if fld.startswith('ER') else 'PD', v)); setv(p, a, fld, v)
        A.append((p, '%s with %s %d ms (program value %g)' % (name(n), fld, v, getv(P[n], a, fld)), ['imp1'], n))
# wet only (direct level 0): the decay measures (EDT, decay shape, build-up, echo density) without the direct sound
for n in BATTERY:
    a = P[n][0x11]
    fld = 'Rev Dir Lvl' if a == 36 else 'Dir Lvl'
    if a in (24, 25, 26, 27, 28, 29, 30, 36):
        p = named(P[n], 'T WET %s' % name(n)[:10].upper()); setv(p, a, fld, 0)
        A.append((p, '%s wet only (%s 0, program value %g)' % (name(n), fld, getv(P[n], a, fld)), ['labimp', 'sweepm12'], n))
# level series (-24 / -12 / 0 dBFS sweeps): the same program with its Total Level lowered so that even the 0 dBFS
# sweep stays below -4 dBFS at the interface (peaks predicted by SSP-550 1.6.6 renders of the 0 dBFS sweep, dBFS);
# the analysis compares the three responses with each other, so the lower output level does not matter
PEAK0 = {1: 10.7, 2: 11.9, 4: 11.3, 5: 12.4, 7: 8.8, 8: 10.9, 9: 12.4, 33: 18.4, 50: 8.1, 54: 3.9, 60: 6.4, 70: 3.6}
for n in BATTERY:
    a = P[n][0x11]; tl = getv(P[n], a, 'Total Lvl')
    new = max(1, int(tl * 10 ** ((-4.0 - PEAK0[n]) / 20)))
    p = named(P[n], 'T LVL %s' % name(n)[:10].upper()); setv(p, a, 'Total Lvl', new)
    A.append((p, '%s at Total Level %d (program value %g), for the level series' % (name(n), new, tl), ['sweepm24', 'sweepm12', 'sweep0'], n))
assert len(A) <= 28, len(A)
def msg(n, p):
    body = bytes([3, n - 1, 0]) + bytes(p); sm = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0, 0x38, 0x12]) + body + bytes([sm, 0xF7])
open(os.path.join(OUT, 'tests10A.syx'), 'wb').write(b''.join(msg(101 + k, p) for k, (p, _, _, _) in enumerate(A)))
L = []
slots = {}
for k, (p, desc, kinds, src) in enumerate(A):
    slots[101 + k] = {'source': src, 'what': desc, 'kinds': kinds}
    for kind in kinds: L.append(('A', 101 + k, 'wav:' + kind, ('Pre-delay: ' if kind == 'imp1' else 'Lab battery, ') + desc))
json.dump(slots, open(os.path.join(OUT, 'slots10.json'), 'w'), indent=1)
for n in BATTERY:
    for kind, what in (('labimp', 'impulse x4 + left/right'), ('sweepm12', 'sweep -12 dBFS'), ('labmisc', 'silence, long tones, clicks, pink')):
        L.append(('B', n, 'wav:' + kind, 'Lab battery (%s): %s' % (what, name(n))))
for n in RATE96: L.append(('B', n, 'wav:sweepm12_96', 'Lab battery (sweep -12 dBFS at 96 kHz): ' + name(n)))
for n in (1, 8): L.append(('Z', n, 'wav:labimp', 'Repeat at the end (drift): ' + name(n)))
for n in (1, 54): L.append(('Z', n, 'std', 'Same capture as runs 6-9 (chain unchanged?): ' + name(n)))
with open(os.path.join(OUT, 'plan10.txt'), 'w') as f:
    for b, n, k, desc in L: f.write('%s\t%d\t%s\t%s\n' % (b, n, k, desc))
tot = 0
for b, n, k, desc in L:
    tot += (segs[k[4:]]['length'] / segs[k[4:]]['fs'] if k.startswith('wav:') else 32) + 3
print('%d lines, %d test programs, about %.0f min of captures' % (len(L), len(A), tot / 60))
