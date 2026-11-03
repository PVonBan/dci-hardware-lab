# Run 10, follow-up round 2: program EQ, measured cleanly on the Stereo Delay's effect path (run 9 showed the shelves
# are 2nd-order Q~0.5 at ~390 Hz / ~3.8 kHz, and that any Mid setting moved the whole level by -6 dB on a reverb).
#   Mid -12/-6/-3/+3/+6/+12 at 2 kHz; +-12 at 500 / 1000 / 4000 Hz; flat references at each Mid Frq
#   Hi and Lo at +-6 (is the shelf gain linear in dB?)
#   Reverb: wet-only Baroque Hall with ER level 0 and Hi -12 / +12 / flat: does the EQ act on the late field only?
import os, sys
os.chdir(sys.argv[1])            # run9 folder (gen9 data); gen9 writes its own files on import, so exec its head only
src = open('gen9.py').read().split("A = []; C = []")[0]
exec(src)
R = []
DL = BASE[5]
def dl(name, desc, **kv):
    p = named(P[DL], name); eq_flat(p, 5); blocks(p, [b for b in range(14) if getblocks(P[DL]) >> b & 1] + [2]); effect_only(p, 5)
    for nm, v in kv.items(): setv(p, 5, nm.replace('_', ' '), v)
    R.append((['std'], desc, p))
for f in (500, 1000, 2000, 4000):
    dl('T DLM F%d' % f, 'Stereo Delay EQ: all flat, Mid Frq %d (reference)' % f, EQ_Mid_Frq=f)
for g in (-12, -6, -3, 3, 6, 12):
    dl('T DLM %+d@2K' % g, 'Stereo Delay EQ: Mid %+d dB at 2000 Hz' % g, EQ_Mid=g, EQ_Mid_Frq=2000)
for f in (500, 1000, 4000):
    for g in (-12, 12):
        dl('T DLM %+d@%d' % (g, f), 'Stereo Delay EQ: Mid %+d dB at %d Hz' % (g, f), EQ_Mid=g, EQ_Mid_Frq=f)
for nm in ('EQ Hi', 'EQ Lo'):
    for g in (-6, 6):
        dl('T DL%s%+d' % (nm[3:5].upper(), g), 'Stereo Delay EQ: %s %+d dB' % (nm, g), **{nm.replace(' ', '_'): g})
RV = 115
for g, lab in ((0, 'flat'), (-12, 'Hi -12'), (12, 'Hi +12')):
    p = named(P[RV], 'T RVER0 %s' % lab.replace(' ', '')); eq_flat(p, 24); blocks(p, [b for b in range(14) if getblocks(P[RV]) >> b & 1] + [2])
    setv(p, 24, 'ER Lvl', 0); setv(p, 24, 'Dir Lvl', 0); setv(p, 24, 'EQ Hi', g)
    R.append((['std'], 'Reverb EQ with ER level 0 (wet-only Baroque Hall): %s' % lab, p))
assert len(R) <= 28, len(R)
def msg(n, p):
    body = bytes([3, n - 1, 0]) + bytes(p); sm = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0, 0x38, 0x12]) + body + bytes([sm, 0xF7])
out = sys.argv[2]
open(os.path.join(out, 'round2-tests.syx'), 'wb').write(b''.join(msg(101 + k, p) for k, (kinds, nm, p) in enumerate(R)))
with open(os.path.join(out, 'round2-plan.txt'), 'w') as f:
    for k, (kinds, nm, p) in enumerate(R):
        for kind in kinds: f.write('R2\t%d\t%s\t%s\n' % (101 + k, kind, nm))
print(len(R), 'programs')
