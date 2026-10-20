#!/usr/bin/env python3
"""RSP-550 run 10: turn the unit's captures, or the same battery rendered by the SSP-550, into the reverb lab's file
layout, so tools/reverblab/analyse_run3.py measures both with exactly the same code (dci-reference-lab rule).

  lab10.py hw   <capture/run10 dir> <run10 dir> <out dir>       the unit: loop latency and gain removed (run 1 cal)
  lab10.py ours <SSP550Test> <run10 dir> <out dir> <backup.syx> renders every battery program with our build (the
                                                                unit's bank in slot order, test programs in their slots)
  lab10.py measure <out dir> <reverblab dir>                    analyse_run3.py on <out>/renders -> <out>/results.json
  lab10.py simulate <ours out> <run10 dir> <capture dir>        a fake unit capture from our renders (self-test)
  lab10.py addnoise <ours out> <hw out>                          the unit's idle noise added to our renders (before measure)
  lab10.py compare <hw out> <ours out> [--json f]               ours against the unit, per measure, with the unit's
                                                                own repeat spread as the tolerance

<out>/renders/p001_imp_r1.wav ... (run-3 names), <out>/run2/p001_sweep.wav (-12 dBFS sweep) and p001_imp.wav (the
end-of-session repeat), <out>/predelay.json (onset of each pre-delay test program).
"""
import glob, json, os, re, subprocess, sys
import numpy as np
import soundfile as sf

FS = 48000
LAT, GAIN = 1179, np.array([10 ** (0.9 / 20), 10 ** (-4.6 / 20)])   # loop calibration (run 1)


def segs(run10):
    return json.load(open(os.path.join(run10, 'stim', 'segments.json')))


def cut(y, table, fs, tag, dest, rename=None):
    for name, p0, n in table:
        if name.startswith('imp'): n = min(n, int(6.1 * fs))   # every impulse window the same length (run-3 renders: 6.1 s)
        seg = y[p0:p0 + n]
        if len(seg) < n: seg = np.vstack([seg, np.zeros((n - len(seg), 2))])
        nm = (rename or {}).get(name, name)
        sub = 'run2' if nm in ('sweep', 'imp') else 'renders'
        os.makedirs(os.path.join(dest, sub), exist_ok=True)
        sf.write(os.path.join(dest, sub, '%s_%s.wav' % (tag, nm)), seg.astype(np.float32), fs, subtype='FLOAT')


def onset_ms(y, fs):
    m = np.abs(np.sum(y, 1)); return float(np.argmax(m > 0.05 * np.max(m)) / fs * 1000)


def mark(out, run10):
    os.makedirs(out, exist_ok=True); json.dump({'run10': os.path.abspath(run10)}, open(os.path.join(out, 'run10.json'), 'w'))


def hw(capdir, run10, out):
    mark(out, run10)
    S = segs(run10)
    idx = [l.rstrip('\n').split('\t') for l in open(os.path.join(capdir, 'run4-index.tsv'))][1:]
    pre = {}
    slots = json.load(open(os.path.join(run10, 'slots10.json')))
    for f, batch, prog, kind, desc, stored in idx:
        if not kind.startswith('wav:'): continue
        k = kind[4:]; fs = S[k]['fs']
        y, r = sf.read(os.path.join(capdir, f), always_2d=True)
        lat = LAT if r == FS else 0      # 96 kHz: latency unknown, only the deconvolved response is used
        y = y[lat:] / GAIN
        if '(stimulus -10 dB)' in desc: y = y * 10 ** (10 / 20)    # a clipped take retaken 10 dB lower
        tag = 'p%03d' % int(prog)
        if batch == 'A' and k != 'imp1':          # wet-only variants: tag w<program>; level series: l<program>
            cut(y, S[k]['segments'], fs, ('l' if 'Total Level' in slots[prog]['what'] else 'w') + '%03d' % slots[prog]['source'], out)
        elif batch == 'A':
            seg = S[k]['segments'][0]; z = y[seg[1]:seg[1] + seg[2]]
            pre['%s %s' % (prog, desc)] = {'onset_ms': onset_ms(z, fs), 'retake': '-m10' in f}
            os.makedirs(os.path.join(out, 'predelay'), exist_ok=True)
            sf.write(os.path.join(out, 'predelay', '%s.wav' % prog), z.astype(np.float32), fs, subtype='FLOAT')
        elif batch == 'Z' and k == 'labimp':
            cut(y, [s for s in S[k]['segments'] if s[0] == 'imp_r1'], fs, tag, out, {'imp_r1': 'imp'})
        elif batch == 'B':
            cut(y, S[k]['segments'], fs, tag, out)
            if '-m10' in f: open(os.path.join(out, 'retakes.txt'), 'a').write(f + '\n')
    json.dump(pre, open(os.path.join(out, 'predelay.json'), 'w'), indent=1)


def ours(test, run10, out, bank=None):
    mark(out, run10)
    S = segs(run10)
    plan = [l.rstrip('\n').split('\t') for l in open(os.path.join(run10, 'plan10.txt')) if l.strip()]
    tmp = os.path.join(out, 'tmp'); os.makedirs(tmp, exist_ok=True)
    progs = {}
    for b, n, k, d in plan:
        if b in ('B', 'Z') and k.startswith('wav:'): progs.setdefault(k[4:], set()).add(int(n))
    for k, ps in progs.items():
        x, r = sf.read(os.path.join(run10, 'stim', k + '.wav'), always_2d=True, dtype='float32')
        f32 = os.path.join(tmp, k + '.f32'); x.astype(np.float32).tofile(f32)
        env = dict(os.environ, SSP_RENDER_RATE=str(r))
        if bank and not os.path.exists(os.path.join(tmp, 'bank.syx')): slotbank(bank, os.path.join(tmp, 'bank.syx'))
        args = [test, '--render', os.path.join(tmp, k), f32] + ([os.path.join(tmp, 'bank.syx')] if bank else []) + [str(p) for p in sorted(ps)]
        subprocess.run(args, check=True, env=env, stdout=subprocess.DEVNULL)
        for p in ps:
            y = np.fromfile(os.path.join(tmp, k, '%03d.f32' % p), np.float32).reshape(-1, 2)
            cut(y, S[k]['segments'], r, 'p%03d' % p, out)
            if k == 'labimp':    # ours is deterministic: the "end of session" repeat is the same render
                cut(y, [s for s in S[k]['segments'] if s[0] == 'imp_r1'], r, 'p%03d' % p, out, {'imp_r1': 'imp'})
    # batch A test programs (tests10A.syx, slots 101-116): wet-only variants measured like the battery, pre-delay pairs
    bk = os.path.join(tmp, 'bank10A.syx'); pre = {}
    if not bank: raise SystemExit('ours: give the unit\'s bank (backup .syx) so the test programs land in their slots')
    slotbank(bank, bk, os.path.join(run10, 'tests10A.syx'))
    slots = json.load(open(os.path.join(run10, 'slots10.json')))
    for k in ('labimp', 'sweepm24', 'sweepm12', 'sweep0'):
        ps = [int(n) for n, v in slots.items() if k in v['kinds']]
        if not ps: continue
        x, r = sf.read(os.path.join(run10, 'stim', k + '.wav'), always_2d=True, dtype='float32')
        f32 = os.path.join(tmp, k + '.f32'); x.tofile(f32)
        subprocess.run([test, '--render', os.path.join(tmp, 'A' + k), f32, bk] + [str(p) for p in ps], check=True, stdout=subprocess.DEVNULL)
        for p in ps:
            y = np.fromfile(os.path.join(tmp, 'A' + k, '%03d.f32' % p), np.float32).reshape(-1, 2)
            tag = ('l' if 'Total Level' in slots[str(p)]['what'] else 'w') + '%03d' % slots[str(p)]['source']
            cut(y, S[k]['segments'], r, tag, out)
            if k == 'labimp': cut(y, [s for s in S[k]['segments'] if s[0] == 'imp_r1'], r, tag, out, {'imp_r1': 'imp'})
    if os.path.exists(bk):
        x, r = sf.read(os.path.join(run10, 'stim', 'imp1.wav'), always_2d=True, dtype='float32')
        f32 = os.path.join(tmp, 'imp1.f32'); x.tofile(f32)
        A = [l.rstrip('\n').split('\t') for l in open(os.path.join(run10, 'plan10.txt')) if l.startswith('A\t') and 'imp1' in l]
        subprocess.run([test, '--render', os.path.join(tmp, 'imp1'), f32, bk] + [a[1] for a in A], check=True, stdout=subprocess.DEVNULL)
        seg = S['imp1']['segments'][0]
        for b, n, k, d in A:
            y = np.fromfile(os.path.join(tmp, 'imp1', '%03d.f32' % int(n)), np.float32).reshape(-1, 2)
            z = y[seg[1]:seg[1] + seg[2]]
            pre['%s %s' % (n, d)] = {'onset_ms': onset_ms(z, r), 'retake': False}
            os.makedirs(os.path.join(out, 'predelay'), exist_ok=True)
            sf.write(os.path.join(out, 'predelay', '%s.wav' % n), z.astype(np.float32), r, subtype='FLOAT')
    json.dump(pre, open(os.path.join(out, 'predelay.json'), 'w'), indent=1)


def _progs(path):
    d = open(path, 'rb').read(); M = {}; i = 0
    while i + 106 <= len(d):
        if d[i] == 0xF0 and d[i + 1] == 0x41 and d[i + 4] == 0x12 and d[i + 105] == 0xF7 and d[i + 5] in (3, 4):
            M[(d[i + 5], d[i + 6])] = d[i:i + 106]; i += 106
        else: i += 1
    return M


def slotbank(backup, out, overlay=None):
    """The unit's whole bank in slot order, with the programs of `overlay` (a test bank) put in their own slots.
    The plug-in's bank loader ignores SysEx addresses and fills its programs in file order, so a test bank loaded
    alone lands in programs 1-28, and a bank out of order misplaces programs (program 2 rendered silent impulses)."""
    M = _progs(backup)
    if overlay: M.update(_progs(overlay))
    open(out, 'wb').write(b''.join(M[k] for k in sorted(M)))


def simulate(ours_out, run10, capdir):
    """A fake unit for the self-test: our own renders (from `ours`) put through the loop model - latency, loop gain,
    -87 dBFS white noise - and written as a capture folder with run4-index.tsv, exactly as the runner writes one."""
    S = segs(run10); T = os.path.join(ours_out, 'tmp'); os.makedirs(capdir, exist_ok=True)
    idx = ['file\tbatch\tprogram\tkind\tdescription\tstored-name']; names = set()
    for l in open(os.path.join(run10, 'plan10.txt')):
        b, n, k, d = l.rstrip('\n').split('\t')
        if not k.startswith('wav:'): continue
        k = k[4:]; n = int(n)
        src = os.path.join(T, 'imp1' if k == 'imp1' else ('A' + k if b == 'A' else k), '%03d.f32' % n)
        y = np.fromfile(src, np.float32).reshape(-1, 2); fs = S[k]['fs']; lat = LAT if fs == FS else 0
        z = np.vstack([np.zeros((lat, 2)), y])[:len(y)] * GAIN
        z = z + np.random.default_rng(n).standard_normal(z.shape) * 10 ** (-87 / 20)
        f = 'r4%s-%03d-%s.wav' % (b, n, k)
        if f in names: f = f[:-4] + '-rep2.wav'
        names.add(f)
        sf.write(os.path.join(capdir, f), z.astype(np.float32), fs, subtype='FLOAT')
        idx.append('%s\t%s\t%d\twav:%s\t%s\t?' % (f, b, n, k, d))
    open(os.path.join(capdir, 'run4-index.tsv'), 'w').write('\n'.join(idx) + '\n')


def addnoise(ours_out, hw_out):
    """Give our renders the unit's own idle noise (spectrum per channel from its silence captures), so measures that
    read near the floor (NED, late decay slope, cross-feed, distortion at -24 dBFS) compare like with like. Our silence
    renders stay untouched: the noise level itself is reported as a gap, not hidden."""
    from scipy import signal
    sil = sorted(glob.glob(os.path.join(hw_out, 'renders', 'p*_silence.wav')))
    if not sil: print('no unit silence captures: noise not added'); return
    z = np.concatenate([sf.read(f, always_2d=True)[0][FS // 2:] for f in sil])
    rng = np.random.default_rng(10)
    for f in glob.glob(os.path.join(ours_out, 'renders', '*.wav')) + glob.glob(os.path.join(ours_out, 'run2', '*.wav')):
        if f.endswith('_silence.wav'): continue
        y, r = sf.read(f, always_2d=True)
        for c in range(2):
            fr, P = signal.welch(z[:, c], FS, nperseg=8192)
            fq = np.fft.rfftfreq(len(y), 1 / r)
            h = np.fft.irfft(np.fft.rfft(rng.standard_normal(len(y))) * np.sqrt(np.interp(fq, fr, P, right=0)), len(y))
            y[:, c] += h * np.sqrt(np.mean(z[:, c] ** 2)) / (np.sqrt(np.mean(h ** 2)) + 1e-30)
        sf.write(f, y.astype(np.float32), r, subtype='FLOAT')
    open(os.path.join(ours_out, 'NOISE_ADDED'), 'w').write('unit noise from %d silence captures in %s\n' % (len(sil), hw_out))


def measure(out, rl):
    stims = os.path.join(json.load(open(os.path.join(out, 'run10.json')))['run10'], 'stims')   # written by hw / ours
    subprocess.run([sys.executable, os.path.join(rl, 'analyse_run3.py'), os.path.join(out, 'renders'), '--run2', os.path.join(out, 'run2'),
                    '--stims2', stims, '--stims3', stims, '--out', os.path.join(out, 'results.json')], check=True)


def compare(hwo, ouo, jout=None):
    H = json.load(open(os.path.join(hwo, 'results.json'))); O = json.load(open(os.path.join(ouo, 'results.json')))
    BANDS = ['125', '250', '500', '1000', '2000', '4000', '8000']
    rows, res = [], {}
    def num(v):
        try: v = float(v); return v if np.isfinite(v) else None
        except (TypeError, ValueError): return None
    for tag in sorted(H):
        h, o = H[tag], O.get(tag)
        if not o: continue
        r = {}
        rep = h.get('repeat', {})
        # decay: band T30 of the -12 dBFS sweep; tolerance = 2 x the unit's own spread over its 4 impulses (min 3 %)
        if 'm12' in h.get('level', {}) and 'm12' in o.get('level', {}):
            for b in BANDS:
                a, c = num(h['level']['m12']['T30'].get(b)), num(o['level']['m12']['T30'].get(b))
                sd = num(rep.get('T30_sd', {}).get(b)) or 0.0
                if a and c: r['T30 %s' % b] = (c, a, max(2 * sd, 0.03 * a), 's')
            th, to = h['level']['m12']['tone'], o['level']['m12']['tone']
            for f in ('63', '125', '250', '500', '2000', '4000', '8000', '12699', '16000'):
                if f in th and f in to: r['tone %s' % f] = (to[f], th[f], 1.5, 'dB')
        for lv in ('m24', '0'):
            if lv in h.get('level', {}) and lv in o.get('level', {}):
                r['distortion %s' % lv] = (o['level'][lv]['distortion_dB'], h['level'][lv]['distortion_dB'], 6.0, 'dB')
        if rep and o.get('repeat'):
            orp = o['repeat']
            for i, t in enumerate((10, 25, 50, 100, 200, 350)):
                r['NED %d ms' % t] = (orp['ned_mean'][i], rep['ned_mean'][i], max(2 * rep['ned_sd'][i], 0.05), '')
            for k in ('0-50', '50-150', '150-300'):
                r['density %s' % k] = (orp['wdensity'][k], rep['wdensity'][k], max(2 * rep['wdensity_sd'][k], 0.05), '')
            for b in ('250', '1000', '4000'):
                r['build %s' % b] = (orp['band_build_ms'][b], rep['band_build_ms'][b], max(2 * rep['peak_ms_sd'], 10.0), 'ms')
            for k in ('EDT', 'T20', 'late', 'curvature'):
                a, c = num(rep['shape_1k'][k]), num(orp['shape_1k'][k])
                if a and c: r['shape 1k %s' % k] = (c, a, max(0.1 * abs(a), 0.05), '')
        if 'sides' in h and 'sides' in o:
            for s in ('L', 'R'): r['crossfeed %s' % s] = (o['sides'][s]['crossfeed_dB'], h['sides'][s]['crossfeed_dB'], 2.0, 'dB')
            r['mono loss'] = (o['sides']['mono_loss_dB'], h['sides']['mono_loss_dB'], 1.0, 'dB')
        if 'longtones' in h and 'longtones' in o:
            for a, c in zip(h['longtones'], o['longtones']):
                r['spread %d Hz' % a['f']] = (c['spread_cents'], a['spread_cents'], max(0.25 * a['spread_cents'], 1.0), 'c')
                r['level fluct %d Hz' % a['f']] = (c['level_fluct_dB'], a['level_fluct_dB'], max(0.3 * a['level_fluct_dB'], 0.3), 'dB')
        if 'clicks' in h and 'clicks' in o:
            r['click corr'] = (o['clicks']['early_corr_mean'], h['clicks']['early_corr_mean'], 0.1, '')
        if 'pink' in h and 'pink' in o:
            for f in ('125', '500', '2000', '8000'):
                if f in h['pink']['tone'] and f in o['pink']['tone']: r['pink %s' % f] = (o['pink']['tone'][f], h['pink']['tone'][f], 1.5, 'dB')
        if 'noise' in h and 'noise' in o:    # informational: ours has no idle noise unless Bit Depth adds the unit's
            res.setdefault('_noise', {})[tag] = {'ours': o['noise']['silence']['rms_dBFS'], 'unit': h['noise']['silence']['rms_dBFS']}
        if 'rate96' in h and 'rate96' in o:
            for b in ('500', '1000', '2000'):
                a, c = num(h['rate96']['T30'].get(b)), num(o['rate96']['T30'].get(b))
                if a and c: r['96k T30 %s' % b] = (c, a, 0.08 * a, 's')
        res[tag] = {k: {'ours': v[0], 'unit': v[1], 'tol': v[2], 'unit_of': v[3], 'ok': bool(abs(v[0] - v[1]) <= v[2])} for k, v in r.items()}
        bad = [k for k, v in res[tag].items() if not v['ok']]
        rows.append('%s: %d of %d within tolerance; outside: %s' % (tag, len(r) - len(bad), len(r),
                    ', '.join('%s %.2f vs %.2f' % (k, r[k][0], r[k][1]) for k in bad[:14]) + (' ...' if len(bad) > 14 else '') if bad else 'none'))
    pa = os.path.join(hwo, 'predelay.json'); pb = os.path.join(ouo, 'predelay.json')
    if os.path.exists(pa) and os.path.exists(pb):
        A, B = json.load(open(pa)), json.load(open(pb))
        for k in A:
            if k in B: rows.append('pre-delay %s: unit onset %.1f ms, ours %.1f ms' % (k, A[k]['onset_ms'], B[k]['onset_ms']))
        # what the control means: the delay between the 0 and 50 ms versions of a program (cross-correlation of their
        # 2 ms energy envelopes over the first 600 ms; 50 = the whole response moves, less = only part of it)
        def lag(d, a, b):
            pa, pb = os.path.join(d, 'predelay', '%d.wav' % a), os.path.join(d, 'predelay', '%d.wav' % b)
            if not (os.path.exists(pa) and os.path.exists(pb)): return None
            e = []
            for p in (pa, pb):
                y, r = sf.read(p, always_2d=True); w = int(0.002 * r)
                e.append(np.convolve(np.sum(y[:int(0.6 * r)] ** 2, 1), np.ones(w) / w, 'same'))
            c = np.correlate(e[1], e[0], 'full'); k = int(np.argmax(c)) - (len(e[0]) - 1)
            return k / r * 1000
        lags = {}
        for a, b, what in ((101, 102, 'Large Hall 1 Rev PreDly 0 -> 50'), (103, 104, 'Large Hall 1 ER PreDly 0 -> 50'),
                           (105, 106, 'Warm Plate Rev PreDly 0 -> 50'), (107, 108, 'Large Room Rev PreDly 0 -> 50')):
            lu, lo = lag(hwo, a, b), lag(ouo, a, b)
            if lu is not None and lo is not None:
                lags[what] = {'unit_ms': lu, 'ours_ms': lo, 'ok': abs(lu - lo) <= 2.0}
                rows.append('pre-delay meaning, %s: response moves %.1f ms on the unit, %.1f ms on ours' % (what, lu, lo))
        res['_predelay'] = {'unit': A, 'ours': B, 'lags': lags}
    print('\n'.join(rows))
    if jout: json.dump(res, open(jout, 'w'), indent=1)
    return res


def validate(run10, ours_out, backup):
    """Before the unit runs: every test program differs from its source only in its name and the one field it tests;
    every render of ours is finite and not silent; captures our render predicts will clip (the runner retakes those)."""
    d = open(backup, 'rb').read(); P = {}; i = 0
    while i + 106 <= len(d):
        if d[i] == 0xF0 and d[i + 1] == 0x41 and d[i + 4] == 0x12 and d[i + 105] == 0xF7 and d[i + 5] in (3, 4):
            P[d[i + 6] + 1 if d[i + 5] == 3 else d[i + 6] + 129] = d[i + 8:i + 104]; i += 106
        else: i += 1
    t = open(os.path.join(run10, 'tests10A.syx'), 'rb').read(); slots = json.load(open(os.path.join(run10, 'slots10.json')))
    bad = 0
    for k in range(len(t) // 106):
        m = t[k * 106:(k + 1) * 106]; slot = m[6] + 1; body = m[8:104]
        assert m[5] == 3 and 101 <= slot <= 128 and (128 - sum(m[5:104]) % 128) % 128 == m[104]
        src = P[slots[str(slot)]['source']]
        diff = [j for j in range(16, 96) if body[j] != src[j]]
        ok = 1 <= len(diff) <= 2 or (len(diff) == 0 and 'ms (program value 0)' in slots[str(slot)]['what'] and ' 0 ms' in slots[str(slot)]['what'])
        # one field (two bytes when it is 14-bit); a 0 ms test on a program already at 0 is its own baseline
        bad += not ok
        print('slot %d: %s; bytes changed %s%s' % (slot, slots[str(slot)]['what'], diff, '' if ok else '  <- PROBLEM'))
    for f in sorted(glob.glob(os.path.join(ours_out, 'renders', '*.wav')) + glob.glob(os.path.join(ours_out, 'run2', '*.wav'))):
        y, r = sf.read(f, always_2d=True)
        if not np.all(np.isfinite(y)): print('not finite:', f); bad += 1
        elif np.max(np.abs(y)) < 1e-7 and 'silence' not in f: print('silent:', f); bad += 1
        elif np.max(np.abs(y)) > 0.99 / 1.11: print('predicted retake (clips at the interface): %s peak %.1f dBFS' % (os.path.basename(f), 20 * np.log10(np.max(np.abs(y)))))
    print('VALIDATE OK' if not bad else 'VALIDATE PROBLEMS (%d)' % bad)
    return bad


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'hw': hw(*sys.argv[2:5])
    elif c == 'ours': ours(*sys.argv[2:6])
    elif c == 'measure': measure(*sys.argv[2:4])
    elif c == 'slotbank': slotbank(*sys.argv[2:5])
    elif c == 'simulate': simulate(*sys.argv[2:5])
    elif c == 'addnoise': addnoise(*sys.argv[2:4])
    elif c == 'validate': sys.exit(1 if validate(*sys.argv[2:5]) else 0)
    elif c == 'compare': compare(sys.argv[2], sys.argv[3], sys.argv[5] if len(sys.argv) > 5 and sys.argv[4] == '--json' else None)
