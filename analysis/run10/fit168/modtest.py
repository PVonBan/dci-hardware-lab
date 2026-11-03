import sys, os, json, subprocess, numpy as np, soundfile as sf
sys.path.insert(0, '/home/claude/dci-effects/tools/reverblab'); import analyse_run3 as A
S = '/tmp/claude-0/-home-claude/43821833-de77-5012-b98f-e22767bd5dd6/scratchpad'
lt = [(int(k), float(f), int(s), int(n)) for k, f, s, n in (l.split('\t') for l in open(S + '/run10/stims/longtones.txt').read().split('\n') if l)]
x, _ = sf.read(S + '/run10/stim/labmisc.wav', always_2d=True, dtype='float32'); seg = (504000, 672000)
f32 = S + '/v168/lt.f32'
if not os.path.exists(f32): x[:seg[0] + seg[1]].tofile(f32)
R = json.load(open(S + '/r10/cmp167e.json'))
progs = {1: 24, 8: 30, 2: 26, 4: 25, 9: 29, 5: 27}
for mod in sys.argv[1:]:
    line = []
    for p, alg in progs.items():
        out = S + '/v168/mt'; subprocess.run([S + '/v168/T', '--render', out, f32, S + '/v168/bankA.syx', str(p)], check=True, stdout=subprocess.DEVNULL, env=dict(os.environ, T_ALG=str(alg), T_MOD=mod))
        y = np.fromfile(out + '/%03d.f32' % p, '<f4').reshape(-1, 2).astype(float)[seg[0]:seg[0] + seg[1]]
        ft = A.longtone_features(y, lt); r = R['p%03d' % p]
        line.append('p%03d ' % p + ' '.join('%d:%.2f/%.2f fl %.2f/%.2f' % (f['f'], f['spread_cents'], r['spread %d Hz' % f['f']]['unit'], f['level_fluct_dB'], r['level fluct %d Hz' % f['f']]['unit']) for f in ft))
    print('== mod', mod); print('\n'.join(line))
