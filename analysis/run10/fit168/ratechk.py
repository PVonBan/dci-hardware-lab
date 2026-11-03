import numpy as np, subprocess, os, sys
def bands(sr, env, prog=int(os.environ.get("P", "101"))):
    n = int(sr * 4); rng = np.random.default_rng(int(os.environ.get("SEED", "3"))); x = (0.1 * (rng.random((n, 2)) * 2 - 1)).astype('<f4'); x.tofile('rn.f32')
    subprocess.run(['./T', '--render', 'rr', 'rn.f32', str(prog)], check=True, stdout=subprocess.DEVNULL, env=dict(os.environ, SSP_RENDER_RATE=str(int(sr)), **env))
    y = np.fromfile('rr/%03d.f32' % prog, '<f4').reshape(-1, 2)[:n].astype(float)
    N = 1 << 14; Px = np.zeros(N // 2 + 1); Py = np.zeros(N // 2 + 1); h = np.hanning(N)
    for s in range(n - int(2 * sr), n - N + 1, N // 2):
        for c in (0, 1): Px += np.abs(np.fft.rfft(x[s:s + N, c] * h)) ** 2; Py += np.abs(np.fft.rfft(y[s:s + N, c] * h)) ** 2
    f = np.fft.rfftfreq(N, 1 / sr); out = []
    fc = 125
    while fc <= 8000:
        k = (f >= fc / 1.41) & (f < fc * 1.41); out.append(10 * np.log10(Py[k].sum() / Px[k].sum())); fc *= 2
    return np.array(out)
for e in sys.argv[1:]:
    env = dict(kv.split('=') for kv in e.split()) if e != '-' else {}
    a, b = bands(48000, env), bands(96000, env)
    print('%-28s 96k-48k: ' % e + ' '.join('%+5.2f' % v for v in b - a))
