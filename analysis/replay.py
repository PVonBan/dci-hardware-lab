# Replay: re-render every targeted test of runs 6-8 (batches and follow-up rounds) with the current build and re-run
# each run's own analysis, so a build is scored against all the recordings at once (no unit needed).
# usage: python3 replay.py [render4 binary] [tag]   -> replay/<run>.txt, replay/scores-<tag>.json, one line per run
import os, subprocess, sys, shutil, time, json
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guards
SP = os.environ.get('DCI_LAB_WORK') or '/tmp/claude-0/-home-claude/43821833-de77-5012-b98f-e22767bd5dd6/scratchpad'   # where runs 6-8 and their plans live
os.chdir(SP)
ARGS = list(sys.argv)   # the runs' analysis code resets sys.argv
R4 = ARGS[1] if len(ARGS) > 1 else 'an4/render4'
# 2026-10-20: render4 has only the effect engines; since 1.6.4 the plug-in adds per-algorithm wet low-pass and shelf,
# output scaling and more in its processor, so render4 no longer matches it (parity failed on 7 of 8 programs). Pass
# the plug-in's test app (SSP550Test) so replay scores what ships.
PLUG = os.path.basename(R4).startswith('SSP550Test')
import lab10
BK = '/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx'
RUNS = [
    ('run6pr', ['run6pr/plan4.txt'], {'A': 'run6pr/tests4A.syx', 'C': 'run6pr/tests4C.syx'}, 'run6pr/an6.py'),
    ('run7pr', ['run7pr/plan4.txt'] + ['run7/round%d-plan.txt' % k for k in range(1, 5)],
     dict({'C': 'run7pr/tests4C.syx'}, **{'R%d' % k: 'run7/round%d-tests.syx' % k for k in range(1, 5)}), 'run7pr/an7.py'),
    ('run8pr', ['run8pr/plan4.txt'], {'C': 'run8/tests8C.syx'}, 'run8pr/an8.py'),
]
os.makedirs('replay', exist_ok=True); os.makedirs('replay/tmp', exist_ok=True)
CENT = 1000 * 2 ** (np.arange(-10, 13) / 3)
def bands(y):
    f, P = signal.welch(y, 48000, nperseg=8192); return np.array([10 * np.log10(P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].mean() + 1e-30) for c in CENT])
hist = {}
for run, plans, syx, an in RUNS:
    t0 = time.time(); n = 0; missing = []
    for pf in plans:
        for line in open(pf):
            f = line.rstrip('\n').split('\t')
            if len(f) < 4: continue
            b, prog, kind = f[0], int(f[1]), f[2]
            stim = '%s/stims/stim-%s.f32' % (run, kind)
            if not os.path.exists(stim): missing.append(kind); continue
            bank = syx.get(b, BK)
            for src in (bank, BK):
                if PLUG:   # the real plug-in engine (processor chain included): SSP550Test --render <dir> <stim> <bank> <prog>
                    # the plug-in loads a .syx in file order, so give it the bank in slot order (lab10.slotbank)
                    sb = 'replay/tmp/slots-' + src.replace('/', '_')   # run6 and run7 both have a tests4C.syx
                    if not os.path.exists(sb): lab10.slotbank(BK, sb, src if src != BK else None)
                    subprocess.run([R4, '--render', 'replay/tmp', stim, sb, str(prog)], check=True, capture_output=True)
                else:
                    subprocess.run([R4, src, stim, 'replay/tmp', str(prog)], check=True, capture_output=True)
                if os.path.exists('replay/tmp/%03d.f32' % prog): break
            shutil.move('replay/tmp/%03d.f32' % prog, '%s/plug/r4%s-%03d-%s.f32' % (run, b, prog, kind)); n += 1
    # uniform score for every test: per-channel level and 1/3-octave tone, hw - plug, over the whole recording
    G = {}; exec(open(an).read().split("if __name__")[0], G)
    rows = []
    for pf in plans:
        for line in open(pf):
            f = line.rstrip('\n').split('\t')
            if len(f) < 4 or f[2] not in G.get('_kinds', [f[2]]): continue
            b, prog, kind, desc = f[0], int(f[1]), f[2], f[3]
            try:
                x, yh, mk = G['get'](b, prog, kind, False); _, yp, _ = G['get'](b, prog, kind, True)
                guards.check_capture(yh, '%s %s%d %s' % (run, b, prog, kind))
            except guards.GuardError as e: rows.append((b, prog, kind, desc, None, None, str(e))); continue
            except Exception as e: rows.append((b, prog, kind, desc, None, None, 'missing: %s' % e)); continue
            m = min(len(yh), len(yp)); d = guards.per_channel(bands, yh[:m], yp[:m])
            lvl = float(np.median(d[(CENT >= 200) & (CENT <= 5000)])); shape = float(np.median(np.abs(d - lvl)[(CENT >= 100) & (CENT <= 12500)]))
            rows.append((b, prog, kind, desc, lvl, shape, ''))
    with open('replay/%s.txt' % run, 'w') as fo:
        for b, prog, kind, desc, lvl, shape, note in rows:
            fo.write('%-3s %3d %-10s %s %s\n' % (b, prog, kind, ('level %+5.1f dB, tone %4.1f dB' % (lvl, shape)) if lvl is not None else 'SKIPPED: ' + note, desc))
    good = [r for r in rows if r[4] is not None]
    hist[run] = {'%s-%d-%s' % r[:3]: [r[4], r[5]] for r in good}
    print('%s: %d tests re-rendered in %.0f s; %d scored (median |level| %.1f dB, median tone %.1f dB), %d skipped -> replay/%s.txt' % (
        run, n, time.time() - t0, len(good), np.median([abs(r[4]) for r in good]), np.median([r[5] for r in good]), len(rows) - len(good), run))

tag = ARGS[2] if len(ARGS) > 2 else time.strftime('%Y%m%d-%H%M')
json.dump(hist, open('replay/scores-%s.json' % tag, 'w'))
print('scores saved: replay/scores-%s.json (compare builds with replay_diff.py)' % tag)
